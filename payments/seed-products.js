const Stripe = require('stripe');
require('dotenv').config();

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);

async function createProducts() {
  console.log('Creating Guide subscription products in Stripe...\n');

  try {
    const existingProducts = await stripe.products.search({
      query: "name:'Guide Pro'"
    });

    if (existingProducts.data.length > 0) {
      console.log('Guide Pro product already exists:', existingProducts.data[0].id);
      
      const prices = await stripe.prices.list({
        product: existingProducts.data[0].id,
        active: true
      });
      
      console.log('\nExisting prices:');
      prices.data.forEach(price => {
        const interval = price.recurring?.interval || 'one-time';
        const amount = (price.unit_amount / 100).toFixed(2);
        console.log(`  - ${price.id}: $${amount} AUD/${interval}`);
        if (price.recurring?.trial_period_days) {
          console.log(`    (includes ${price.recurring.trial_period_days}-day trial)`);
        }
      });
      
      return;
    }

    console.log('Creating Guide Pro product...');
    const product = await stripe.products.create({
      name: 'Guide Pro',
      description: 'Full access to Guide by Auxpery - AI-powered Montessori curriculum companion with Australian Curriculum V9 integration',
      metadata: {
        platform: 'guide',
        target_audience: 'educators_homeschool'
      }
    });
    console.log('Created product:', product.id);

    console.log('\nCreating monthly price ($15/month with 14-day trial)...');
    const monthlyPrice = await stripe.prices.create({
      product: product.id,
      unit_amount: 1500,
      currency: 'aud',
      recurring: {
        interval: 'month',
        trial_period_days: 14
      },
      nickname: 'monthly',
      metadata: {
        plan_type: 'monthly',
        trial_days: '14'
      }
    });
    console.log('Created monthly price:', monthlyPrice.id);

    console.log('\nCreating annual price ($150/year - 2 months free)...');
    const annualPrice = await stripe.prices.create({
      product: product.id,
      unit_amount: 15000,
      currency: 'aud',
      recurring: {
        interval: 'year'
      },
      nickname: 'annual',
      metadata: {
        plan_type: 'annual',
        savings: '2 months free'
      }
    });
    console.log('Created annual price:', annualPrice.id);

    console.log('\n✅ Products created successfully!');
    console.log('\nPrice IDs to use in your application:');
    console.log(`  Monthly: ${monthlyPrice.id}`);
    console.log(`  Annual:  ${annualPrice.id}`);
    
  } catch (error) {
    console.error('Error creating products:', error.message);
    process.exit(1);
  }
}

createProducts();
