"""
Stripe Webhook Handler for Guide Platform
Receives webhook events from Stripe and updates user subscription status
"""

import os
import json
import stripe
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Get Stripe API key from environment
# This will be set by the Stripe connector
def get_stripe_key():
    """Get Stripe secret key from Replit connector"""
    import requests
    
    hostname = os.environ.get('REPLIT_CONNECTORS_HOSTNAME')
    x_replit_token = os.environ.get('REPL_IDENTITY')
    
    if x_replit_token:
        x_replit_token = 'repl ' + x_replit_token
    else:
        web_repl = os.environ.get('WEB_REPL_RENEWAL')
        if web_repl:
            x_replit_token = 'depl ' + web_repl
    
    if not x_replit_token or not hostname:
        # Fallback to direct environment variable
        return os.environ.get('STRIPE_SECRET_KEY')
    
    try:
        is_production = os.environ.get('REPLIT_DEPLOYMENT') == '1'
        target_env = 'production' if is_production else 'development'
        
        url = f"https://{hostname}/api/v2/connection"
        params = {
            'include_secrets': 'true',
            'connector_names': 'stripe',
            'environment': target_env
        }
        
        response = requests.get(url, params=params, headers={
            'Accept': 'application/json',
            'X_REPLIT_TOKEN': x_replit_token
        })
        
        data = response.json()
        connection = data.get('items', [{}])[0]
        return connection.get('settings', {}).get('secret')
    except Exception as e:
        logger.error(f"Error getting Stripe key: {e}")
        return os.environ.get('STRIPE_SECRET_KEY')

# Initialize Stripe
stripe_key = get_stripe_key()
if stripe_key:
    stripe.api_key = stripe_key
    logger.info("Stripe API key configured")
else:
    logger.warning("No Stripe API key found")

def get_database_session():
    """Get database session"""
    from database import get_db
    return get_db()

def update_user_subscription_from_event(customer_email: str, customer_id: str, 
                                         status: str, end_date: datetime = None, 
                                         plan: str = None):
    """Update user subscription in database"""
    from database import update_user_subscription
    
    db = get_database_session()
    if not db:
        logger.error("Could not get database session")
        return False
    
    try:
        user = update_user_subscription(
            db=db,
            email=customer_email,
            stripe_customer_id=customer_id,
            subscription_status=status,
            subscription_end_date=end_date,
            subscription_plan=plan
        )
        
        if user:
            logger.info(f"Updated subscription for {customer_email}: status={status}")
            return True
        else:
            logger.warning(f"User not found for email: {customer_email}")
            return False
    except Exception as e:
        logger.error(f"Error updating subscription: {e}")
        return False
    finally:
        db.close()

def update_subscription_by_customer(customer_id: str, status: str, 
                                     end_date: datetime = None, plan: str = None):
    """Update subscription by Stripe customer ID"""
    from database import update_subscription_by_customer_id
    
    db = get_database_session()
    if not db:
        logger.error("Could not get database session")
        return False
    
    try:
        user = update_subscription_by_customer_id(
            db=db,
            stripe_customer_id=customer_id,
            subscription_status=status,
            subscription_end_date=end_date,
            subscription_plan=plan
        )
        
        if user:
            logger.info(f"Updated subscription for customer {customer_id}: status={status}")
            return True
        else:
            logger.warning(f"User not found for customer ID: {customer_id}")
            return False
    except Exception as e:
        logger.error(f"Error updating subscription: {e}")
        return False
    finally:
        db.close()

@app.route('/stripe/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events"""
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    
    # Get webhook secret from environment
    webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
    
    try:
        if not webhook_secret:
            logger.error("STRIPE_WEBHOOK_SECRET not configured - rejecting webhook")
            return jsonify({'error': 'Webhook secret not configured'}), 500
        
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        return jsonify({'error': 'Invalid signature'}), 400
    
    event_type = event.get('type', event.get('event_type', ''))
    data = event.get('data', {}).get('object', {})
    
    logger.info(f"Received webhook event: {event_type}")
    
    # Handle checkout session completed (new subscription)
    if event_type == 'checkout.session.completed':
        handle_checkout_completed(data)
    
    # Handle subscription updated
    elif event_type == 'customer.subscription.updated':
        handle_subscription_updated(data)
    
    # Handle subscription deleted/cancelled
    elif event_type == 'customer.subscription.deleted':
        handle_subscription_deleted(data)
    
    # Handle invoice paid (subscription renewal)
    elif event_type == 'invoice.paid':
        handle_invoice_paid(data)
    
    # Handle invoice payment failed
    elif event_type == 'invoice.payment_failed':
        handle_payment_failed(data)
    
    return jsonify({'received': True}), 200

def handle_checkout_completed(session):
    """Handle successful checkout session"""
    customer_id = session.get('customer')
    customer_email = session.get('customer_email') or session.get('customer_details', {}).get('email')
    subscription_id = session.get('subscription')
    
    if not customer_email:
        try:
            customer = stripe.Customer.retrieve(customer_id)
            customer_email = customer.get('email')
        except Exception as e:
            logger.error(f"Could not retrieve customer email: {e}")
            return
    
    # Get subscription details from Stripe for accurate end date and plan
    plan = 'monthly'
    end_date = None
    
    if subscription_id:
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            
            # Get accurate end date from Stripe
            current_period_end = subscription.get('current_period_end')
            if current_period_end:
                end_date = datetime.fromtimestamp(current_period_end)
            
            # Get plan from subscription items
            items = subscription.get('items', {}).get('data', [])
            if items:
                interval = items[0].get('price', {}).get('recurring', {}).get('interval')
                if interval == 'year':
                    plan = 'yearly'
        except Exception as e:
            logger.error(f"Could not retrieve subscription details: {e}")
            # Fallback to metadata-based plan detection
            metadata = session.get('metadata', {})
            if metadata.get('plan'):
                plan = metadata.get('plan')
            if not end_date:
                end_date = datetime.utcnow() + timedelta(days=365 if plan == 'yearly' else 30)
    
    logger.info(f"Checkout completed for {customer_email}, plan: {plan}")
    
    update_user_subscription_from_event(
        customer_email=customer_email,
        customer_id=customer_id,
        status='active',
        end_date=end_date,
        plan=plan
    )

def handle_subscription_updated(subscription):
    """Handle subscription update"""
    customer_id = subscription.get('customer')
    status = subscription.get('status')
    
    # Map Stripe status to our status
    status_map = {
        'active': 'active',
        'past_due': 'past_due',
        'canceled': 'cancelled',
        'unpaid': 'inactive',
        'incomplete': 'inactive',
        'incomplete_expired': 'inactive',
        'trialing': 'active'
    }
    
    mapped_status = status_map.get(status, 'inactive')
    
    # Get subscription end date
    current_period_end = subscription.get('current_period_end')
    end_date = None
    if current_period_end:
        end_date = datetime.fromtimestamp(current_period_end)
    
    # Determine plan from interval
    plan = 'monthly'
    items = subscription.get('items', {}).get('data', [])
    if items:
        interval = items[0].get('price', {}).get('recurring', {}).get('interval')
        if interval == 'year':
            plan = 'yearly'
    
    logger.info(f"Subscription updated for customer {customer_id}: {mapped_status}")
    
    update_subscription_by_customer(
        customer_id=customer_id,
        status=mapped_status,
        end_date=end_date,
        plan=plan
    )

def handle_subscription_deleted(subscription):
    """Handle subscription cancellation - honor already-paid access"""
    customer_id = subscription.get('customer')
    
    # Use current_period_end to honor already-paid access
    current_period_end = subscription.get('current_period_end')
    end_date = datetime.fromtimestamp(current_period_end) if current_period_end else datetime.utcnow()
    
    logger.info(f"Subscription deleted for customer {customer_id}, access until {end_date}")
    
    update_subscription_by_customer(
        customer_id=customer_id,
        status='cancelled',
        end_date=end_date
    )

def handle_invoice_paid(invoice):
    """Handle successful invoice payment (renewal)"""
    customer_id = invoice.get('customer')
    subscription_id = invoice.get('subscription')
    
    if not subscription_id:
        return  # Not a subscription invoice
    
    # Get subscription details
    try:
        subscription = stripe.Subscription.retrieve(subscription_id)
        handle_subscription_updated(subscription)
    except Exception as e:
        logger.error(f"Error retrieving subscription: {e}")

def handle_payment_failed(invoice):
    """Handle failed payment"""
    customer_id = invoice.get('customer')
    
    logger.warning(f"Payment failed for customer {customer_id}")
    
    update_subscription_by_customer(
        customer_id=customer_id,
        status='past_due'
    )

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'stripe-webhook',
        'stripe_configured': bool(stripe.api_key)
    }), 200

if __name__ == '__main__':
    port = int(os.environ.get('STRIPE_WEBHOOK_PORT', 8000))
    logger.info(f"Starting Stripe webhook server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
