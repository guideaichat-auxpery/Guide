const express = require('express');
const cors = require('cors');
const crypto = require('crypto');
const Stripe = require('stripe');
const { Pool } = require('pg');
const { Resend } = require('resend');
require('dotenv').config();

let resendClient = null;
let resendFromEmail = null;

async function getResendCredentials() {
  const hostname = process.env.REPLIT_CONNECTORS_HOSTNAME;
  const xReplitToken = process.env.REPL_IDENTITY
    ? 'repl ' + process.env.REPL_IDENTITY
    : process.env.WEB_REPL_RENEWAL
      ? 'depl ' + process.env.WEB_REPL_RENEWAL
      : null;

  if (!xReplitToken || !hostname) {
    console.log('Resend credentials not available via Replit connector');
    return null;
  }

  try {
    const response = await fetch(
      `https://${hostname}/api/v2/connection?include_secrets=true&connector_names=resend`,
      {
        headers: {
          'Accept': 'application/json',
          'X_REPLIT_TOKEN': xReplitToken
        }
      }
    );
    const data = await response.json();
    const connectionSettings = data.items?.[0];

    if (!connectionSettings?.settings?.api_key) {
      console.log('Resend connection not found');
      return null;
    }

    return {
      apiKey: connectionSettings.settings.api_key,
      fromEmail: connectionSettings.settings.from_email || 'noreply@auxpery.com.au'
    };
  } catch (err) {
    console.error('Error fetching Resend credentials:', err.message);
    return null;
  }
}

const app = express();
const PORT = process.env.PAYMENTS_PORT || 3001;

// Fetch Stripe credentials - prioritize STRIPE_SECRET_KEY for live mode
async function getStripeCredentials() {
  // First check if STRIPE_SECRET_KEY is explicitly set (for live mode)
  const envSecretKey = process.env.STRIPE_SECRET_KEY;
  if (envSecretKey) {
    const isLiveKey = envSecretKey.startsWith('sk_live_');
    console.log(`Using STRIPE_SECRET_KEY from environment (${isLiveKey ? 'LIVE' : 'TEST'} mode)`);
    return { secretKey: envSecretKey };
  }

  // Fall back to Replit connection API for sandbox/development
  const hostname = process.env.REPLIT_CONNECTORS_HOSTNAME;
  const xReplitToken = process.env.REPL_IDENTITY
    ? 'repl ' + process.env.REPL_IDENTITY
    : process.env.WEB_REPL_RENEWAL
      ? 'depl ' + process.env.WEB_REPL_RENEWAL
      : null;

  if (!xReplitToken || !hostname) {
    throw new Error('Stripe credentials not found. Set STRIPE_SECRET_KEY or set up Stripe connection.');
  }

  const isProduction = process.env.REPLIT_DEPLOYMENT === '1';
  const targetEnvironment = isProduction ? 'production' : 'development';

  const url = new URL(`https://${hostname}/api/v2/connection`);
  url.searchParams.set('include_secrets', 'true');
  url.searchParams.set('connector_names', 'stripe');
  url.searchParams.set('environment', targetEnvironment);

  const response = await fetch(url.toString(), {
    headers: {
      'Accept': 'application/json',
      'X_REPLIT_TOKEN': xReplitToken
    }
  });

  const data = await response.json();
  const connectionSettings = data.items?.[0];

  if (!connectionSettings?.settings?.secret) {
    throw new Error(`Stripe ${targetEnvironment} connection not found and STRIPE_SECRET_KEY not set`);
  }

  console.log(`Using Stripe credentials from Replit connection (${targetEnvironment})`);
  return {
    secretKey: connectionSettings.settings.secret,
    publishableKey: connectionSettings.settings.publishable
  };
}

// Initialize Stripe client (will be set during startup)
let stripe = null;
const db = new Pool({ connectionString: process.env.DATABASE_URL });

const REPLIT_DOMAIN = process.env.REPLIT_DOMAINS?.split(',')[0] || 'localhost:5000';
const BASE_URL = `https://${REPLIT_DOMAIN}`;
const GUIDE_APP_URL = process.env.GUIDE_APP_URL || 'https://guide.auxpery.com.au';

function generateInviteToken() {
  return crypto.randomBytes(32).toString('hex');
}
const PAYMENTS_API_SECRET = process.env.PAYMENTS_API_SECRET;

app.use(cors());

function requireApiAuth(req, res, next) {
  const authHeader = req.headers['x-api-secret'];
  
  if (!PAYMENTS_API_SECRET) {
    console.error('PAYMENTS_API_SECRET not configured');
    return res.status(500).json({ success: false, error: 'Server misconfigured' });
  }
  
  if (!authHeader || authHeader !== PAYMENTS_API_SECRET) {
    console.warn('Unauthorized API request from:', req.ip);
    return res.status(401).json({ success: false, error: 'Unauthorized' });
  }
  
  next();
}

app.post('/api/stripe/webhook', express.raw({ type: 'application/json' }), async (req, res) => {
  if (!stripe) {
    console.error('Webhook received but Stripe not initialized yet');
    return res.status(503).json({ error: 'Service not ready, retry later' });
  }
  
  const sig = req.headers['stripe-signature'];
  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;

  console.log(`Webhook received at ${new Date().toISOString()}`);
  console.log(`Webhook secret configured: ${webhookSecret ? 'YES' : 'NO'}`);
  console.log(`Signature header present: ${sig ? 'YES' : 'NO'}`);

  let event;
  try {
    event = stripe.webhooks.constructEvent(req.body, sig, webhookSecret);
  } catch (err) {
    console.error('Webhook signature verification failed:', err.message);
    console.error('This usually means STRIPE_WEBHOOK_SECRET does not match the webhook signing secret in your Stripe Dashboard');
    return res.status(400).send(`Webhook Error: ${err.message}`);
  }

  console.log(`✅ Received Stripe event: ${event.type}`);

  try {
    switch (event.type) {
      case 'checkout.session.completed':
        await handleCheckoutCompleted(event.data.object);
        break;
      case 'customer.subscription.created':
      case 'customer.subscription.updated':
        await handleSubscriptionUpdated(event.data.object);
        break;
      case 'customer.subscription.deleted':
        await handleSubscriptionDeleted(event.data.object);
        break;
      case 'invoice.payment_failed':
        await handlePaymentFailed(event.data.object);
        break;
      default:
        console.log(`Unhandled event type: ${event.type}`);
    }
  } catch (err) {
    console.error(`Error handling ${event.type}:`, err);
  }

  res.json({ received: true });
});

app.use(express.json());

app.get('/health', (req, res) => {
  const stripeReady = stripe !== null;
  const status = stripeReady ? 'healthy' : 'initializing';
  
  res.status(stripeReady ? 200 : 503).json({
    status,
    service: 'Guide Payments Service',
    stripeReady,
    resendReady: resendClient !== null,
    timestamp: new Date().toISOString()
  });
});

app.get('/api/products', async (req, res) => {
  try {
    const products = await stripe.products.list({ active: true });
    const prices = await stripe.prices.list({ active: true });
    
    const productsWithPrices = products.data.map(product => ({
      ...product,
      prices: prices.data.filter(price => price.product === product.id)
    }));
    
    res.json({ success: true, data: productsWithPrices });
  } catch (error) {
    console.error('Error fetching products:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

app.post('/api/create-checkout-session', requireApiAuth, async (req, res) => {
  try {
    const { priceId, educatorId, email } = req.body;
    
    if (!priceId || !educatorId) {
      return res.status(400).json({ success: false, error: 'priceId and educatorId are required' });
    }

    const existingCustomer = await db.query(
      'SELECT stripe_customer_id FROM users WHERE id = $1',
      [educatorId]
    );
    
    let customerId = existingCustomer.rows[0]?.stripe_customer_id;
    
    if (!customerId && email) {
      const customer = await stripe.customers.create({
        email,
        metadata: { educatorId: String(educatorId) }
      });
      customerId = customer.id;
      
      await db.query(
        'UPDATE users SET stripe_customer_id = $1 WHERE id = $2',
        [customerId, educatorId]
      );
    }

    const sessionParams = {
      mode: 'subscription',
      line_items: [{ price: priceId, quantity: 1 }],
      success_url: `${BASE_URL}/?subscription=success`,
      cancel_url: `${BASE_URL}/?subscription=cancelled`,
      metadata: { educatorId: String(educatorId) },
      allow_promotion_codes: true
    };

    if (customerId) {
      sessionParams.customer = customerId;
    } else if (email) {
      sessionParams.customer_email = email;
    }

    const session = await stripe.checkout.sessions.create(sessionParams);
    
    res.json({ success: true, url: session.url });
  } catch (error) {
    console.error('Error creating checkout session:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

app.post('/api/public/create-checkout-session', async (req, res) => {
  try {
    const { priceId, email } = req.body;
    
    if (!priceId || !email) {
      return res.status(400).json({ success: false, error: 'priceId and email are required' });
    }
    
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      return res.status(400).json({ success: false, error: 'Invalid email format' });
    }

    const inviteToken = generateInviteToken();
    
    const customer = await stripe.customers.create({
      email,
      metadata: { inviteToken }
    });

    await db.query(
      `INSERT INTO pending_subscriptions (invite_token, email, stripe_customer_id)
       VALUES ($1, $2, $3)`,
      [inviteToken, email.toLowerCase(), customer.id]
    );

    const session = await stripe.checkout.sessions.create({
      mode: 'subscription',
      customer: customer.id,
      line_items: [{ price: priceId, quantity: 1 }],
      success_url: `${GUIDE_APP_URL}/?signup_token=${inviteToken}`,
      cancel_url: `${req.headers.referer || 'https://www.auxpery.com.au'}?checkout=cancelled`,
      metadata: { inviteToken, source: 'marketing_site' },
      allow_promotion_codes: true
    });
    
    console.log(`Created public checkout for ${email} with token ${inviteToken.substring(0, 8)}...`);
    
    res.json({ success: true, url: session.url });
  } catch (error) {
    console.error('Error creating public checkout session:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

app.post('/api/public/create-school-checkout', async (req, res) => {
  try {
    const { schoolName, email, seats } = req.body;
    
    if (!schoolName || !email || !seats) {
      return res.status(400).json({ 
        success: false, 
        error: 'schoolName, email, and seats are required' 
      });
    }
    
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      return res.status(400).json({ success: false, error: 'Invalid email format' });
    }
    
    const seatCount = parseInt(seats, 10);
    if (isNaN(seatCount) || seatCount < 5) {
      return res.status(400).json({ 
        success: false, 
        error: 'Minimum 5 seats required for school subscriptions' 
      });
    }
    
    if (seatCount > 500) {
      return res.status(400).json({ 
        success: false, 
        error: 'For subscriptions over 500 seats, please contact us directly' 
      });
    }
    
    const schoolPriceId = process.env.STRIPE_SCHOOL_SEAT_PRICE_ID;
    if (!schoolPriceId) {
      console.error('STRIPE_SCHOOL_SEAT_PRICE_ID not configured');
      return res.status(500).json({ success: false, error: 'School pricing not configured' });
    }
    
    const schoolSetupToken = generateInviteToken();
    
    const customer = await stripe.customers.create({
      email,
      metadata: { 
        schoolSetupToken,
        schoolName,
        type: 'school_admin'
      }
    });
    
    await db.query(
      `INSERT INTO pending_subscriptions 
        (invite_token, email, stripe_customer_id, subscription_plan, expires_at)
       VALUES ($1, $2, $3, $4, NOW() + INTERVAL '7 days')`,
      [schoolSetupToken, email.toLowerCase(), customer.id, 'school']
    );
    
    const session = await stripe.checkout.sessions.create({
      mode: 'subscription',
      customer: customer.id,
      line_items: [{ 
        price: schoolPriceId, 
        quantity: seatCount 
      }],
      success_url: `${GUIDE_APP_URL}/?school_setup=${schoolSetupToken}`,
      cancel_url: `${req.headers.referer || 'https://www.auxpery.com.au'}?checkout=cancelled`,
      metadata: { 
        schoolSetupToken,
        schoolName,
        seats: seatCount.toString(),
        type: 'school',
        source: 'marketing_site'
      },
      allow_promotion_codes: true,
      subscription_data: {
        metadata: {
          type: 'school',
          schoolName,
          seats: seatCount.toString()
        }
      }
    });
    
    console.log(`Created school checkout for ${schoolName} (${email}) - ${seatCount} seats, token ${schoolSetupToken.substring(0, 8)}...`);
    
    res.json({ success: true, url: session.url });
  } catch (error) {
    console.error('Error creating school checkout session:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

app.get('/api/public/validate-school-token/:token', async (req, res) => {
  try {
    const { token } = req.params;
    
    if (!token || token.length !== 64) {
      return res.status(400).json({ success: false, error: 'Invalid token format' });
    }

    const result = await db.query(
      `SELECT id, email, subscription_status, subscription_plan, redeemed, expires_at,
              stripe_customer_id, stripe_subscription_id
       FROM pending_subscriptions
       WHERE invite_token = $1 AND subscription_plan = 'school'`,
      [token]
    );
    
    if (!result.rows[0]) {
      return res.status(404).json({ success: false, error: 'Token not found or not a school subscription' });
    }
    
    const pending = result.rows[0];
    
    if (pending.redeemed) {
      return res.status(400).json({ success: false, error: 'This school has already been set up' });
    }
    
    if (new Date(pending.expires_at) < new Date()) {
      return res.status(400).json({ success: false, error: 'Setup link expired. Please contact support.' });
    }
    
    if (pending.subscription_status !== 'active' && pending.subscription_status !== 'trialing') {
      return res.status(400).json({ 
        success: false, 
        error: 'Payment not yet completed. Please wait a moment and refresh.',
        status: pending.subscription_status
      });
    }
    
    // Get subscription details from Stripe to get school name and seats
    let schoolName = 'Your School';
    let seats = 5;
    
    if (pending.stripe_subscription_id && stripe) {
      try {
        const subscription = await stripe.subscriptions.retrieve(pending.stripe_subscription_id);
        schoolName = subscription.metadata?.schoolName || 'Your School';
        seats = parseInt(subscription.metadata?.seats, 10) || subscription.items?.data[0]?.quantity || 5;
      } catch (e) {
        console.warn('Could not fetch subscription details:', e.message);
      }
    }
    
    res.json({
      success: true,
      data: {
        email: pending.email,
        school_name: schoolName,
        seats: seats,
        subscriptionStatus: pending.subscription_status
      }
    });
  } catch (error) {
    console.error('Error validating school token:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

app.post('/api/public/complete-school-setup', async (req, res) => {
  try {
    const { token, fullName, password } = req.body;
    
    if (!token || !fullName || !password) {
      return res.status(400).json({ success: false, error: 'token, fullName, and password are required' });
    }
    
    if (token.length !== 64) {
      return res.status(400).json({ success: false, error: 'Invalid token format' });
    }
    
    // Fetch pending subscription
    const pendingResult = await db.query(
      `SELECT id, email, subscription_status, stripe_customer_id, stripe_subscription_id, redeemed, expires_at
       FROM pending_subscriptions
       WHERE invite_token = $1 AND subscription_plan = 'school'`,
      [token]
    );
    
    if (!pendingResult.rows[0]) {
      return res.status(404).json({ success: false, error: 'Token not found' });
    }
    
    const pending = pendingResult.rows[0];
    
    if (pending.redeemed) {
      return res.status(400).json({ success: false, error: 'This school has already been set up' });
    }
    
    if (new Date(pending.expires_at) < new Date()) {
      return res.status(400).json({ success: false, error: 'Setup link expired' });
    }
    
    if (pending.subscription_status !== 'active' && pending.subscription_status !== 'trialing') {
      return res.status(400).json({ success: false, error: 'Payment not completed' });
    }
    
    // Get subscription details from Stripe
    let schoolName = 'School';
    let seats = 5;
    let subscriptionEnd = null;
    
    if (pending.stripe_subscription_id && stripe) {
      const subscription = await stripe.subscriptions.retrieve(pending.stripe_subscription_id);
      schoolName = subscription.metadata?.schoolName || 'School';
      seats = parseInt(subscription.metadata?.seats, 10) || subscription.items?.data[0]?.quantity || 5;
      subscriptionEnd = subscription.current_period_end ? new Date(subscription.current_period_end * 1000) : null;
    }
    
    // Generate unique invite code for school (with collision check)
    let inviteCode;
    let codeExists = true;
    let attempts = 0;
    while (codeExists && attempts < 10) {
      inviteCode = crypto.randomBytes(4).toString('hex').toUpperCase();
      const existingCode = await db.query(
        'SELECT id FROM schools WHERE invite_code = $1',
        [inviteCode]
      );
      codeExists = existingCode.rows.length > 0;
      attempts++;
    }
    if (codeExists) {
      return res.status(500).json({ success: false, error: 'Unable to generate unique school code. Please try again.' });
    }
    
    // Hash password using bcrypt (same as Python app)
    const bcrypt = require('bcryptjs');
    const passwordHash = bcrypt.hashSync(password, 12);
    
    // Start transaction
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      
      // Create school
      const schoolResult = await client.query(
        `INSERT INTO schools (name, invite_code, license_count, stripe_customer_id, stripe_subscription_id, subscription_status, subscription_end, contact_email, created_at)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
         RETURNING id`,
        [schoolName, inviteCode, seats, pending.stripe_customer_id, pending.stripe_subscription_id, pending.subscription_status, subscriptionEnd, pending.email]
      );
      const schoolId = schoolResult.rows[0].id;
      
      // Check if user already exists
      const existingUser = await client.query(
        'SELECT id, school_id, role FROM users WHERE LOWER(email) = LOWER($1)',
        [pending.email]
      );
      
      let userId;
      if (existingUser.rows[0]) {
        // Check if user already belongs to another school
        if (existingUser.rows[0].school_id) {
          await client.query('ROLLBACK');
          client.release();
          return res.status(400).json({ 
            success: false, 
            error: 'This email is already associated with a school. Please use a different email or contact support.' 
          });
        }
        
        // Update existing user to be school admin
        userId = existingUser.rows[0].id;
        await client.query(
          `UPDATE users SET 
            school_id = $1, 
            role = 'school_admin',
            password_hash = $2,
            full_name = COALESCE(NULLIF($3, ''), full_name)
           WHERE id = $4`,
          [schoolId, passwordHash, fullName, userId]
        );
      } else {
        // Create new user
        const userResult = await client.query(
          `INSERT INTO users (email, password_hash, full_name, user_type, school_id, role, subscription_status, subscription_plan)
           VALUES ($1, $2, $3, 'educator', $4, 'school_admin', $5, 'school')
           RETURNING id`,
          [pending.email.toLowerCase(), passwordHash, fullName, schoolId, pending.subscription_status]
        );
        userId = userResult.rows[0].id;
      }
      
      // Mark pending subscription as redeemed
      await client.query(
        `UPDATE pending_subscriptions SET redeemed = true, redeemed_at = NOW(), redeemed_by_user_id = $1 WHERE id = $2`,
        [userId, pending.id]
      );
      
      await client.query('COMMIT');
      
      console.log(`School setup completed: ${schoolName} (ID: ${schoolId}) with admin ${pending.email} (ID: ${userId})`);
      
      res.json({
        success: true,
        userId: userId,
        schoolId: schoolId,
        schoolName: schoolName,
        inviteCode: inviteCode,
        seats: seats
      });
    } catch (txError) {
      await client.query('ROLLBACK');
      throw txError;
    } finally {
      client.release();
    }
  } catch (error) {
    console.error('Error completing school setup:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

app.get('/api/public/validate-token/:token', async (req, res) => {
  try {
    const { token } = req.params;
    
    if (!token || token.length !== 64) {
      return res.status(400).json({ success: false, error: 'Invalid token format' });
    }

    const result = await db.query(
      `SELECT id, email, subscription_status, subscription_plan, redeemed, expires_at
       FROM pending_subscriptions
       WHERE invite_token = $1`,
      [token]
    );
    
    if (!result.rows[0]) {
      return res.status(404).json({ success: false, error: 'Token not found' });
    }
    
    const pending = result.rows[0];
    
    if (pending.redeemed) {
      return res.status(400).json({ success: false, error: 'Token already redeemed' });
    }
    
    if (new Date(pending.expires_at) < new Date()) {
      return res.status(400).json({ success: false, error: 'Token expired' });
    }
    
    if (pending.subscription_status !== 'active' && pending.subscription_status !== 'trialing') {
      return res.status(400).json({ 
        success: false, 
        error: 'Payment not yet completed. Please complete checkout first.',
        status: pending.subscription_status
      });
    }
    
    res.json({
      success: true,
      data: {
        email: pending.email,
        subscriptionStatus: pending.subscription_status,
        subscriptionPlan: pending.subscription_plan
      }
    });
  } catch (error) {
    console.error('Error validating token:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

app.post('/api/redeem-token', requireApiAuth, async (req, res) => {
  try {
    const { token, userId, email } = req.body;
    
    if (!token || !userId || !email) {
      return res.status(400).json({ success: false, error: 'token, userId, and email are required' });
    }

    const pendingResult = await db.query(
      `SELECT * FROM pending_subscriptions
       WHERE invite_token = $1 AND redeemed = FALSE AND expires_at > NOW()
         AND subscription_status IN ('active', 'trialing')`,
      [token]
    );
    
    if (!pendingResult.rows[0]) {
      return res.status(400).json({ success: false, error: 'Invalid, expired, or already redeemed token' });
    }
    
    const pending = pendingResult.rows[0];
    
    if (pending.email.toLowerCase() !== email.toLowerCase()) {
      console.warn(`Token redemption email mismatch: token=${token.substring(0, 8)}..., expected=${pending.email}, got=${email}`);
      return res.status(403).json({ 
        success: false, 
        error: 'Email does not match the subscription. You must use the same email address used for payment.' 
      });
    }

    await db.query(
      `UPDATE users SET 
        stripe_customer_id = $1,
        stripe_subscription_id = $2,
        subscription_status = $3,
        subscription_plan = $4,
        trial_ends_at = $5,
        subscription_ends_at = $6
       WHERE id = $7`,
      [
        pending.stripe_customer_id,
        pending.stripe_subscription_id,
        pending.subscription_status,
        pending.subscription_plan,
        pending.trial_ends_at,
        pending.subscription_ends_at,
        userId
      ]
    );

    await db.query(
      `UPDATE pending_subscriptions SET 
        redeemed = TRUE, 
        redeemed_at = NOW(), 
        redeemed_by_user_id = $1
       WHERE id = $2`,
      [userId, pending.id]
    );

    await stripe.customers.update(pending.stripe_customer_id, {
      metadata: { educatorId: String(userId), inviteToken: null }
    });
    
    console.log(`Redeemed token for user ${userId}, email ${pending.email}`);
    
    res.json({ 
      success: true, 
      data: {
        subscriptionStatus: pending.subscription_status,
        subscriptionPlan: pending.subscription_plan
      }
    });
  } catch (error) {
    console.error('Error redeeming token:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

app.post('/api/create-portal-session', requireApiAuth, async (req, res) => {
  try {
    const { educatorId } = req.body;
    
    if (!educatorId) {
      return res.status(400).json({ success: false, error: 'educatorId is required' });
    }

    const result = await db.query(
      'SELECT stripe_customer_id FROM users WHERE id = $1',
      [educatorId]
    );
    
    const customerId = result.rows[0]?.stripe_customer_id;
    
    if (!customerId) {
      return res.status(400).json({ success: false, error: 'No subscription found for this educator' });
    }

    const session = await stripe.billingPortal.sessions.create({
      customer: customerId,
      return_url: `${BASE_URL}/`
    });
    
    res.json({ success: true, url: session.url });
  } catch (error) {
    console.error('Error creating portal session:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

app.get('/api/subscription-status/:educatorId', requireApiAuth, async (req, res) => {
  try {
    const { educatorId } = req.params;
    
    const result = await db.query(
      `SELECT stripe_customer_id, stripe_subscription_id, subscription_status, 
              subscription_plan, trial_ends_at, subscription_ends_at,
              cancel_at_period_end, current_period_end, deactivation_requested_at
       FROM users WHERE id = $1`,
      [educatorId]
    );
    
    if (!result.rows[0]) {
      return res.status(404).json({ success: false, error: 'Educator not found' });
    }
    
    const educator = result.rows[0];
    const isActive = ['active', 'trialing'].includes(educator.subscription_status);
    
    res.json({
      success: true,
      data: {
        isActive,
        status: educator.subscription_status || 'none',
        plan: educator.subscription_plan,
        trialEndsAt: educator.trial_ends_at,
        subscriptionEndsAt: educator.subscription_ends_at,
        cancelAtPeriodEnd: educator.cancel_at_period_end || false,
        currentPeriodEnd: educator.current_period_end,
        deactivationRequestedAt: educator.deactivation_requested_at
      }
    });
  } catch (error) {
    console.error('Error checking subscription status:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

app.post('/api/subscription/cancel', requireApiAuth, async (req, res) => {
  try {
    const { educatorId } = req.body;
    
    if (!educatorId) {
      return res.status(400).json({ success: false, error: 'educatorId is required' });
    }

    const result = await db.query(
      'SELECT stripe_subscription_id FROM users WHERE id = $1',
      [educatorId]
    );
    
    const subscriptionId = result.rows[0]?.stripe_subscription_id;
    
    if (!subscriptionId) {
      return res.status(400).json({ success: false, error: 'No active subscription found' });
    }

    const subscription = await stripe.subscriptions.update(subscriptionId, {
      cancel_at_period_end: true
    });
    
    const currentPeriodEnd = subscription.current_period_end 
      ? new Date(subscription.current_period_end * 1000) 
      : null;

    await db.query(
      `UPDATE users SET 
        cancel_at_period_end = TRUE,
        current_period_end = $1,
        deactivation_requested_at = NOW()
       WHERE id = $2`,
      [currentPeriodEnd, educatorId]
    );
    
    console.log(`Subscription ${subscriptionId} set to cancel at period end for educator ${educatorId}`);
    
    res.json({ 
      success: true, 
      data: { 
        cancelAtPeriodEnd: true,
        currentPeriodEnd 
      }
    });
  } catch (error) {
    console.error('Error cancelling subscription:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

app.post('/api/subscription/reactivate', requireApiAuth, async (req, res) => {
  try {
    const { educatorId } = req.body;
    
    if (!educatorId) {
      return res.status(400).json({ success: false, error: 'educatorId is required' });
    }

    const result = await db.query(
      'SELECT stripe_subscription_id FROM users WHERE id = $1',
      [educatorId]
    );
    
    const subscriptionId = result.rows[0]?.stripe_subscription_id;
    
    if (!subscriptionId) {
      return res.status(400).json({ success: false, error: 'No subscription found' });
    }

    await stripe.subscriptions.update(subscriptionId, {
      cancel_at_period_end: false
    });

    await db.query(
      `UPDATE users SET 
        cancel_at_period_end = FALSE,
        deactivation_requested_at = NULL
       WHERE id = $1`,
      [educatorId]
    );
    
    console.log(`Subscription ${subscriptionId} reactivated for educator ${educatorId}`);
    
    res.json({ success: true, data: { cancelAtPeriodEnd: false } });
  } catch (error) {
    console.error('Error reactivating subscription:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

app.post('/api/admin/sync-by-email', requireApiAuth, async (req, res) => {
  try {
    const { email } = req.body;
    if (!email) {
      return res.status(400).json({ success: false, error: 'email is required' });
    }

    const customers = await stripe.customers.list({ email, limit: 1 });
    if (!customers.data[0]) {
      return res.status(404).json({ success: false, error: 'Customer not found in Stripe' });
    }

    const customerId = customers.data[0].id;
    const subscriptions = await stripe.subscriptions.list({ customer: customerId, limit: 1 });
    
    if (!subscriptions.data[0]) {
      return res.status(404).json({ success: false, error: 'No subscription found' });
    }

    const subscription = subscriptions.data[0];
    const userResult = await db.query('SELECT id FROM users WHERE email = $1', [email]);
    
    if (!userResult.rows[0]) {
      return res.status(404).json({ success: false, error: 'User account not found' });
    }

    const userId = userResult.rows[0].id;
    const plan = subscription.items?.data[0]?.price?.recurring?.interval === 'year' ? 'annual' : 'monthly';
    const trialEnd = subscription.trial_end ? new Date(subscription.trial_end * 1000) : null;
    const currentPeriodEnd = subscription.current_period_end ? new Date(subscription.current_period_end * 1000) : null;
    const cancelAtPeriodEnd = subscription.cancel_at_period_end || false;

    await db.query(
      `UPDATE users SET 
        stripe_customer_id = $1,
        stripe_subscription_id = $2,
        subscription_status = $3,
        subscription_plan = $4,
        trial_ends_at = $5,
        current_period_end = $6,
        subscription_ends_at = $6,
        cancel_at_period_end = $7
       WHERE id = $8`,
      [customerId, subscription.id, subscription.status, plan, trialEnd, currentPeriodEnd, cancelAtPeriodEnd, userId]
    );

    console.log(`Synced full subscription for ${email}: ${subscription.id} (${plan})`);
    res.json({ success: true, data: { customerId, subscriptionId: subscription.id, status: subscription.status, plan } });
  } catch (error) {
    console.error('Error syncing subscription:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

async function handleCheckoutCompleted(session) {
  console.log('Checkout completed:', session.id);
  
  const educatorId = session.metadata?.educatorId;
  const inviteToken = session.metadata?.inviteToken;
  const customerId = session.customer;
  const subscriptionId = session.subscription;
  
  // Handle school checkout (existing school)
  const schoolId = session.metadata?.schoolId;
  const isSchool = session.metadata?.type === 'school';
  const schoolSetupToken = session.metadata?.schoolSetupToken;
  const schoolName = session.metadata?.schoolName;
  
  // Handle self-service school signup from marketing site
  if (isSchool && schoolSetupToken && !schoolId && customerId && subscriptionId) {
    const subscription = await stripe.subscriptions.retrieve(subscriptionId);
    const seatCount = subscription.items?.data[0]?.quantity || 5;
    const currentPeriodEnd = subscription.current_period_end ? new Date(subscription.current_period_end * 1000) : null;
    const trialEnd = subscription.trial_end ? new Date(subscription.trial_end * 1000) : null;
    
    // Update pending_subscription with subscription details
    await db.query(
      `UPDATE pending_subscriptions SET 
        stripe_subscription_id = $1,
        stripe_checkout_session_id = $2,
        subscription_status = $3,
        subscription_plan = 'school',
        trial_ends_at = $4,
        subscription_ends_at = $5
       WHERE invite_token = $6`,
      [subscriptionId, session.id, subscription.status, trialEnd, currentPeriodEnd, schoolSetupToken]
    );
    
    console.log(`School checkout completed for ${schoolName} - ${seatCount} seats, token ${schoolSetupToken.substring(0, 8)}...`);
    console.log(`Admin will complete setup at /school-setup?token=${schoolSetupToken}`);
    return;
  }
  
  // Handle existing school checkout (from in-app purchase)
  if (isSchool && schoolId && customerId && subscriptionId) {
    const subscription = await stripe.subscriptions.retrieve(subscriptionId);
    const seatCount = subscription.items?.data[0]?.quantity || 10;
    const currentPeriodEnd = subscription.current_period_end ? new Date(subscription.current_period_end * 1000) : null;
    
    await db.query(
      `UPDATE schools SET 
        stripe_customer_id = $1,
        stripe_subscription_id = $2,
        subscription_status = $3,
        license_count = $4,
        subscription_end = $5
       WHERE id = $6`,
      [customerId, subscriptionId, subscription.status, seatCount, currentPeriodEnd, schoolId]
    );
    console.log(`Updated school ${schoolId} with subscription ${subscriptionId} (${seatCount} seats)`);
    return;
  }
  
  if (educatorId && customerId && subscriptionId) {
    const subscription = await stripe.subscriptions.retrieve(subscriptionId);
    const plan = subscription.items?.data[0]?.price?.recurring?.interval === 'year' ? 'annual' : 'monthly';
    const trialEnd = subscription.trial_end ? new Date(subscription.trial_end * 1000) : null;
    const currentPeriodEnd = subscription.current_period_end ? new Date(subscription.current_period_end * 1000) : null;
    
    await db.query(
      `UPDATE users SET 
        stripe_customer_id = $1,
        stripe_subscription_id = $2,
        subscription_status = $3,
        subscription_plan = $4,
        trial_ends_at = $5,
        current_period_end = $6,
        subscription_ends_at = $6
       WHERE id = $7`,
      [customerId, subscriptionId, subscription.status, plan, trialEnd, currentPeriodEnd, educatorId]
    );
    console.log(`Updated educator ${educatorId} with subscription ${subscriptionId} (${plan})`);
    
    // Send welcome email if not already sent
    const userResult = await db.query(
      'SELECT email, full_name, welcome_email_sent_at FROM users WHERE id = $1',
      [educatorId]
    );
    
    if (userResult.rows.length > 0 && !userResult.rows[0].welcome_email_sent_at) {
      const { email, full_name } = userResult.rows[0];
      const emailSent = await sendWelcomeEmail(email, full_name);
      
      if (emailSent) {
        await db.query(
          'UPDATE users SET welcome_email_sent_at = NOW() WHERE id = $1',
          [educatorId]
        );
      }
    }
  }
  
  if (inviteToken) {
    const subscription = await stripe.subscriptions.retrieve(subscriptionId);
    const plan = subscription.items?.data[0]?.price?.recurring?.interval === 'year' ? 'annual' : 'monthly';
    const trialEnd = subscription.trial_end ? new Date(subscription.trial_end * 1000) : null;
    const currentPeriodEnd = subscription.current_period_end ? new Date(subscription.current_period_end * 1000) : null;
    
    await db.query(
      `UPDATE pending_subscriptions SET 
        stripe_subscription_id = $1,
        stripe_checkout_session_id = $2,
        subscription_status = $3,
        subscription_plan = $4,
        trial_ends_at = $5,
        subscription_ends_at = $6
       WHERE invite_token = $7`,
      [subscriptionId, session.id, subscription.status, plan, trialEnd, currentPeriodEnd, inviteToken]
    );
    console.log(`Updated pending subscription for token ${inviteToken.substring(0, 8)}...`);
  }
}

async function handleSubscriptionUpdated(subscription) {
  console.log('Subscription updated:', subscription.id, 'Status:', subscription.status, 'Cancel at period end:', subscription.cancel_at_period_end);
  
  const customerId = subscription.customer;
  const status = subscription.status;
  const currentPeriodEnd = subscription.current_period_end ? new Date(subscription.current_period_end * 1000) : null;
  
  // Check if this is a school subscription (by metadata OR by checking schools table)
  let isSchool = subscription.metadata?.type === 'school';
  let schoolId = subscription.metadata?.schoolId;
  
  // Fallback: check schools table by customer_id if metadata is missing
  if (!isSchool && !schoolId) {
    const schoolCheck = await db.query(
      'SELECT id FROM schools WHERE stripe_customer_id = $1',
      [customerId]
    );
    if (schoolCheck.rows.length > 0) {
      isSchool = true;
      schoolId = schoolCheck.rows[0].id;
    }
  }
  
  if (isSchool || schoolId) {
    const seatCount = subscription.items?.data[0]?.quantity || 10;
    await db.query(
      `UPDATE schools SET 
        stripe_subscription_id = $1,
        subscription_status = $2,
        license_count = $3,
        subscription_end = $4
       WHERE stripe_customer_id = $5`,
      [subscription.id, status, seatCount, currentPeriodEnd, customerId]
    );
    console.log(`Updated school subscription for customer ${customerId} (${seatCount} seats)`);
    return;
  }
  
  // Handle individual user subscription
  const plan = subscription.items?.data[0]?.price?.nickname || 
               (subscription.items?.data[0]?.price?.recurring?.interval === 'year' ? 'annual' : 'monthly');
  
  const trialEnd = subscription.trial_end ? new Date(subscription.trial_end * 1000) : null;
  const cancelAtPeriodEnd = subscription.cancel_at_period_end || false;
  
  await db.query(
    `UPDATE users SET 
      stripe_subscription_id = $1,
      subscription_status = $2,
      subscription_plan = $3,
      trial_ends_at = $4,
      subscription_ends_at = $5,
      cancel_at_period_end = $6,
      current_period_end = $7
     WHERE stripe_customer_id = $8`,
    [subscription.id, status, plan, trialEnd, currentPeriodEnd, cancelAtPeriodEnd, currentPeriodEnd, customerId]
  );
  console.log(`Updated subscription for customer ${customerId}`);
}

async function handleSubscriptionDeleted(subscription) {
  console.log('Subscription deleted:', subscription.id);
  
  const customerId = subscription.customer;
  
  // Check if this is a school subscription (by metadata OR by checking schools table)
  let isSchool = subscription.metadata?.type === 'school';
  let schoolId = subscription.metadata?.schoolId;
  
  // Fallback: check schools table by customer_id if metadata is missing
  if (!isSchool && !schoolId) {
    const schoolCheck = await db.query(
      'SELECT id FROM schools WHERE stripe_customer_id = $1',
      [customerId]
    );
    if (schoolCheck.rows.length > 0) {
      isSchool = true;
      schoolId = schoolCheck.rows[0].id;
    }
  }
  
  if (isSchool || schoolId) {
    await db.query(
      `UPDATE schools SET 
        subscription_status = 'canceled',
        subscription_end = NOW()
       WHERE stripe_customer_id = $1`,
      [customerId]
    );
    console.log(`Cancelled school subscription for customer ${customerId}`);
    return;
  }
  
  await db.query(
    `UPDATE users SET 
      subscription_status = 'cancelled',
      subscription_ends_at = NOW(),
      cancel_at_period_end = FALSE,
      current_period_end = NULL
     WHERE stripe_customer_id = $1`,
    [customerId]
  );
  console.log(`Cancelled subscription for customer ${customerId}`);
}

async function handlePaymentFailed(invoice) {
  console.log('Payment failed for invoice:', invoice.id);
  
  const customerId = invoice.customer;
  
  // Check if this is a school subscription
  const schoolCheck = await db.query(
    'SELECT id FROM schools WHERE stripe_customer_id = $1',
    [customerId]
  );
  
  if (schoolCheck.rows.length > 0) {
    // Update school subscription status
    await db.query(
      `UPDATE schools SET subscription_status = 'past_due' WHERE stripe_customer_id = $1`,
      [customerId]
    );
    console.log(`Marked school subscription as past_due for customer ${customerId}`);
  } else {
    // Update individual user subscription status
    await db.query(
      `UPDATE users SET subscription_status = 'past_due' WHERE stripe_customer_id = $1`,
      [customerId]
    );
    console.log(`Marked user subscription as past_due for customer ${customerId}`);
  }
}

async function initDatabase() {
  try {
    await db.query(`
      ALTER TABLE users 
      ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT,
      ADD COLUMN IF NOT EXISTS stripe_subscription_id TEXT,
      ADD COLUMN IF NOT EXISTS subscription_status TEXT DEFAULT 'none',
      ADD COLUMN IF NOT EXISTS subscription_plan TEXT,
      ADD COLUMN IF NOT EXISTS trial_ends_at TIMESTAMP,
      ADD COLUMN IF NOT EXISTS subscription_ends_at TIMESTAMP,
      ADD COLUMN IF NOT EXISTS cancel_at_period_end BOOLEAN DEFAULT FALSE,
      ADD COLUMN IF NOT EXISTS current_period_end TIMESTAMP,
      ADD COLUMN IF NOT EXISTS deactivation_requested_at TIMESTAMP
    `);
    
    await db.query(`
      CREATE TABLE IF NOT EXISTS pending_subscriptions (
        id SERIAL PRIMARY KEY,
        invite_token VARCHAR(64) UNIQUE NOT NULL,
        email VARCHAR(255) NOT NULL,
        stripe_customer_id TEXT,
        stripe_subscription_id TEXT,
        stripe_checkout_session_id TEXT,
        subscription_status TEXT DEFAULT 'pending',
        subscription_plan TEXT,
        trial_ends_at TIMESTAMP,
        subscription_ends_at TIMESTAMP,
        redeemed BOOLEAN DEFAULT FALSE,
        redeemed_at TIMESTAMP,
        redeemed_by_user_id INTEGER,
        created_at TIMESTAMP DEFAULT NOW(),
        expires_at TIMESTAMP DEFAULT (NOW() + INTERVAL '7 days')
      )
    `);
    
    await db.query(`
      CREATE INDEX IF NOT EXISTS idx_pending_subscriptions_token ON pending_subscriptions(invite_token);
      CREATE INDEX IF NOT EXISTS idx_pending_subscriptions_email ON pending_subscriptions(email);
    `);
    
    await db.query(`
      CREATE TABLE IF NOT EXISTS password_reset_tokens (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id),
        token_hash VARCHAR(64) NOT NULL,
        created_at TIMESTAMP DEFAULT NOW(),
        expires_at TIMESTAMP NOT NULL,
        used_at TIMESTAMP,
        is_valid BOOLEAN DEFAULT TRUE
      )
    `);
    
    await db.query(`
      CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_hash ON password_reset_tokens(token_hash);
      CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_user ON password_reset_tokens(user_id);
    `);
    
    console.log('Database columns and pending_subscriptions table initialized successfully');
  } catch (error) {
    console.error('Error initializing database:', error.message);
  }
}

app.post('/api/email/send-contact-autoreply', express.json(), requireApiAuth, async (req, res) => {
  try {
    const { email, userName, subject } = req.body;
    
    if (!email) {
      return res.status(400).json({ success: false, error: 'Email is required' });
    }
    
    if (!resendClient) {
      console.log('⚠️ Resend not configured - contact auto-reply skipped');
      return res.status(500).json({ success: false, error: 'Email service not configured' });
    }
    
    const result = await resendClient.emails.send({
      from: resendFromEmail,
      to: email,
      subject: 'Thank you for contacting Guide',
      html: `
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
          <div style="background: linear-gradient(135deg, #4a6741 0%, #5d7a52 100%); padding: 30px; border-radius: 12px 12px 0 0; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 28px;">Guide</h1>
            <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0; font-size: 14px;">by AUXPERY</p>
          </div>
          
          <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 12px 12px;">
            <p style="font-size: 16px;">Dear${userName ? ` ${userName}` : ''},</p>
            
            <h2 style="color: #4a6741; margin-top: 20px;">Thank you for reaching out!</h2>
            
            <p>We've received your message${subject ? ` regarding "<strong>${subject}</strong>"` : ''} and wanted to let you know that it's in safe hands.</p>
            
            <p>As a small team dedicated to supporting educators, we do our very best to respond to every message thoughtfully. Please allow <strong>up to 3 business days</strong> for us to get back to you with a personal response.</p>
            
            <p>We truly appreciate your patience and are grateful that you've taken the time to connect with us.</p>
            
            <div style="background: #fff; border-left: 4px solid #4a6741; padding: 15px 20px; margin: 25px 0; border-radius: 0 8px 8px 0;">
              <p style="margin: 0; font-style: italic; color: #666;">"The greatest sign of success for a teacher is to be able to say, 'The children are now working as if I did not exist.'"</p>
              <p style="margin: 10px 0 0 0; font-size: 0.9em; color: #888;">— Maria Montessori</p>
            </div>
            
            <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
            
            <p style="margin-bottom: 5px;">With warmth,</p>
            <p style="margin-top: 5px;"><strong>The Guide Team</strong><br><em>Auxpery</em></p>
          </div>
          
          <div style="text-align: center; padding: 20px; color: #999; font-size: 12px;">
            <p>Guide by AUXPERY - Cosmic Curriculum Companion</p>
          </div>
        </body>
        </html>
      `
    });
    
    console.log(`✉️ Contact auto-reply sent to ${email}`);
    res.json({ success: true });
  } catch (error) {
    console.error('Error sending contact auto-reply:', error);
    res.status(500).json({ success: false, error: 'Failed to send email' });
  }
});

app.post('/api/email/send-welcome', express.json(), requireApiAuth, async (req, res) => {
  try {
    const { email, userName } = req.body;
    
    if (!email) {
      return res.status(400).json({ success: false, error: 'Email is required' });
    }
    
    const sent = await sendWelcomeEmail(email, userName);
    
    if (sent) {
      res.json({ success: true });
    } else {
      res.status(500).json({ success: false, error: 'Failed to send welcome email' });
    }
  } catch (error) {
    console.error('Error sending welcome email:', error);
    res.status(500).json({ success: false, error: 'Failed to send email' });
  }
});

app.post('/api/email/send-password-reset', express.json(), requireApiAuth, async (req, res) => {
  try {
    const { email, resetUrl, userName } = req.body;
    
    if (!email || !resetUrl) {
      return res.status(400).json({ success: false, error: 'Email and resetUrl are required' });
    }
    
    if (!resendClient) {
      console.error('Resend client not initialized');
      return res.status(500).json({ success: false, error: 'Email service not available' });
    }
    
    const result = await resendClient.emails.send({
      from: resendFromEmail,
      to: email,
      subject: 'Reset Your Guide Password',
      html: `
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
          <div style="background: linear-gradient(135deg, #4a6741 0%, #5d7a52 100%); padding: 30px; border-radius: 12px 12px 0 0; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 28px;">Guide</h1>
            <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0; font-size: 14px;">by AUXPERY</p>
          </div>
          
          <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 12px 12px;">
            <h2 style="color: #4a6741; margin-top: 0;">Password Reset Request</h2>
            
            <p>Hello${userName ? ` ${userName}` : ''},</p>
            
            <p>We received a request to reset your password for your Guide account. Click the button below to create a new password:</p>
            
            <div style="text-align: center; margin: 30px 0;">
              <a href="${resetUrl}" style="background: #4a6741; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; display: inline-block;">Reset My Password</a>
            </div>
            
            <p style="color: #666; font-size: 14px;">This link will expire in 1 hour for security reasons.</p>
            
            <p style="color: #666; font-size: 14px;">If you didn't request this password reset, you can safely ignore this email. Your password will remain unchanged.</p>
            
            <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
            
            <p style="color: #999; font-size: 12px; text-align: center;">
              If the button doesn't work, copy and paste this link into your browser:<br>
              <a href="${resetUrl}" style="color: #4a6741; word-break: break-all;">${resetUrl}</a>
            </p>
          </div>
          
          <div style="text-align: center; padding: 20px; color: #999; font-size: 12px;">
            <p>Guide by AUXPERY - Cosmic Curriculum Companion</p>
            <p>This is an automated message. Please do not reply.</p>
          </div>
        </body>
        </html>
      `
    });
    
    console.log(`Password reset email sent to ${email}`);
    res.json({ success: true, messageId: result.id });
    
  } catch (error) {
    console.error('Error sending password reset email:', error);
    res.status(500).json({ success: false, error: 'Failed to send email' });
  }
});

async function sendWelcomeEmail(email, userName) {
  if (!resendClient) {
    console.log('⚠️ Resend not configured - welcome email skipped');
    return false;
  }
  
  try {
    const result = await resendClient.emails.send({
      from: resendFromEmail,
      to: email,
      subject: 'Welcome to Guide - Your Cosmic Curriculum Companion 🌍',
      html: `
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
          <div style="background: linear-gradient(135deg, #4a6741 0%, #5d7a52 100%); padding: 30px; border-radius: 12px 12px 0 0; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 28px;">Guide</h1>
            <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0; font-size: 14px;">by AUXPERY</p>
          </div>
          
          <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 12px 12px;">
            <p style="font-size: 16px;">Dear${userName ? ` ${userName}` : ''},</p>
            
            <h2 style="color: #4a6741; margin-top: 20px;">Thank you for joining Guide!</h2>
            
            <p>We're thrilled to have you as part of our community of educators who believe in the power of interconnected learning.</p>
            
            <h3 style="color: #4a6741; margin-top: 25px;">What is Guide?</h3>
            
            <p>Guide is your cosmic curriculum companion - bridging Montessori's Cosmic Education with modern curriculum frameworks like the Australian Curriculum V9. We help you create meaningful, interconnected learning experiences that show children their place in the story of the universe.</p>
            
            <h3 style="color: #4a6741; margin-top: 25px;">Getting Started</h3>
            
            <ul style="padding-left: 20px;">
              <li style="margin-bottom: 10px;">Explore the <strong>Lesson Planning Assistant</strong> for age-appropriate, cross-curricular lesson ideas</li>
              <li style="margin-bottom: 10px;">Try the <strong>Great Story Creator</strong> to craft cosmic narratives for your classroom</li>
              <li style="margin-bottom: 10px;">Use the <strong>Montessori Companion</strong> for professional development</li>
              <li style="margin-bottom: 10px;">Try the <strong>Imaginarium</strong> for anything and everything else!</li>
            </ul>
            
            <p style="margin-top: 25px;">If you ever need help, just reach out - we're here to support you on this journey.</p>
            
            <div style="text-align: center; margin: 30px 0;">
              <a href="https://guide.auxpery.com.au" style="background: #4a6741; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; display: inline-block;">Go to Guide</a>
            </div>
            
            <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
            
            <p style="margin-bottom: 5px;">With gratitude,</p>
            <p style="margin-top: 5px;"><strong>Ben Noble</strong><br><em>Founder, Auxpery</em></p>
          </div>
          
          <div style="text-align: center; padding: 20px; color: #999; font-size: 12px;">
            <p>Guide by AUXPERY - Cosmic Curriculum Companion</p>
          </div>
        </body>
        </html>
      `
    });
    
    console.log(`✉️ Welcome email sent to ${email}`);
    return true;
  } catch (error) {
    console.error('Error sending welcome email:', error);
    return false;
  }
}

async function startServer() {
  // Initialize Stripe client
  try {
    const { secretKey } = await getStripeCredentials();
    stripe = new Stripe(secretKey);
    console.log('✅ Stripe client initialized');
  } catch (err) {
    console.error('❌ Failed to initialize Stripe:', err.message);
    process.exit(1);
  }
  
  // Initialize Resend client for email
  try {
    const resendCreds = await getResendCredentials();
    if (resendCreds) {
      resendClient = new Resend(resendCreds.apiKey);
      resendFromEmail = resendCreds.fromEmail;
      console.log('✅ Resend client initialized (from:', resendFromEmail, ')');
    } else {
      console.log('⚠️ Resend not configured - password reset emails disabled');
    }
  } catch (err) {
    console.error('⚠️ Failed to initialize Resend:', err.message);
  }
  
  await initDatabase();
  
  // Schedule cleanup of expired pending subscriptions (runs every 6 hours)
  async function cleanupExpiredPendingSubscriptions() {
    try {
      const result = await db.query(
        `DELETE FROM pending_subscriptions 
         WHERE (expires_at < NOW() AND redeemed = FALSE)
         OR (redeemed = TRUE AND redeemed_at < NOW() - INTERVAL '30 days')
         RETURNING id`
      );
      if (result.rowCount > 0) {
        console.log(`🧹 Cleaned up ${result.rowCount} expired/old pending subscription records`);
      }
    } catch (err) {
      console.error('Error cleaning up pending subscriptions:', err.message);
    }
  }
  
  // Run cleanup on startup and every 6 hours
  cleanupExpiredPendingSubscriptions();
  setInterval(cleanupExpiredPendingSubscriptions, 6 * 60 * 60 * 1000);
  
  app.listen(PORT, '0.0.0.0', () => {
    console.log(`💳 Guide Payments Service running on port ${PORT}`);
    console.log(`📊 Health check: http://localhost:${PORT}/health`);
    console.log(`🔗 Webhook endpoint: ${BASE_URL}/api/stripe/webhook`);
  });
}

startServer();
