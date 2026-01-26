"""
Python Stripe Client for Guide
Handles all Stripe operations directly without relying on external payments service.
Webhooks are still handled by the Node.js service for reliability.
"""
import os
import stripe
from datetime import datetime, timedelta
from sqlalchemy import text
from typing import Optional
from database import get_db

STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
stripe.api_key = STRIPE_SECRET_KEY

MONTHLY_PRICE_ID = os.getenv('STRIPE_MONTHLY_PRICE_ID', 'price_1Sd7RX8PGiRAuUvfzibxCNLV')
ANNUAL_PRICE_ID = os.getenv('STRIPE_ANNUAL_PRICE_ID', 'price_1SeSbY8PGiRAuUvf0xjZmMXK')
SCHOOL_SEAT_PRICE_ID = os.getenv('STRIPE_SCHOOL_SEAT_PRICE_ID')  # Per-seat annual price for schools

GUIDE_APP_URL = os.getenv('GUIDE_APP_URL', 'https://guide.auxpery.com.au')

SUBSCRIPTION_CACHE_TTL = timedelta(seconds=30)


def get_subscription_from_stripe(email: str, user_id: Optional[int] = None) -> dict:
    """Fetch subscription status directly from Stripe.
    
    IMPORTANT: Uses stored customer ID first to avoid wrong-customer bug.
    Only falls back to email search if no customer ID is stored.
    """
    if not STRIPE_SECRET_KEY:
        print("[STRIPE] No API key configured")
        return {'isActive': False, 'status': 'error', 'error': 'Stripe not configured'}
    
    try:
        customer = None
        stored_customer_id = None
        
        # FIRST: Try to get stored customer ID from database (prevents wrong-customer bug)
        if user_id:
            db = get_db()
            if db:
                try:
                    result = db.execute(
                        text("SELECT stripe_customer_id FROM users WHERE id = :user_id"),
                        {'user_id': user_id}
                    ).fetchone()
                    stored_customer_id = result[0] if result and result[0] else None
                finally:
                    db.close()
        
        # Use stored customer ID if available
        if stored_customer_id:
            try:
                customer = stripe.Customer.retrieve(stored_customer_id)
                print(f"[STRIPE] Using stored customer ID: {stored_customer_id}")
            except Exception as e:
                print(f"[STRIPE] Stored customer ID invalid, falling back to email: {e}")
                customer = None
        
        # FALLBACK: Search by email if no stored ID
        if not customer:
            customers = stripe.Customer.list(email=email, limit=10)  # Get more to check for subscriptions
            if not customers.data:
                print(f"[STRIPE] No customer found for {email}")
                return {'isActive': False, 'status': 'none'}
            
            # Check ALL customers for this email to find one with subscription
            for c in customers.data:
                subs = stripe.Subscription.list(customer=c.id, limit=1)
                if subs.data:
                    customer = c
                    print(f"[STRIPE] Found customer with subscription: {c.id}")
                    break
            
            # If no customer has subscription, use the first one
            if not customer:
                customer = customers.data[0]
                print(f"[STRIPE] No subscription found, using first customer: {customer.id}")
        
        # Now check for subscriptions on the selected customer
        subscriptions = stripe.Subscription.list(customer=customer.id, limit=1)
        
        if not subscriptions.data:
            print(f"[STRIPE] No subscription found for customer {customer.id}")
            return {'isActive': False, 'status': 'none', 'customerId': customer.id}
        
        sub = subscriptions.data[0]
        is_active = sub.status in ['active', 'trialing']
        
        interval = sub.items.data[0].price.recurring.interval if sub.items.data[0].price.recurring else 'month'
        plan = 'annual' if interval == 'year' else 'monthly'
        
        trial_end = datetime.fromtimestamp(sub.trial_end) if sub.trial_end else None
        period_end_ts = getattr(sub, 'current_period_end', None)
        current_period_end = datetime.fromtimestamp(period_end_ts) if period_end_ts else None
        
        result = {
            'isActive': is_active,
            'status': sub.status,
            'plan': plan,
            'subscriptionId': sub.id,
            'customerId': customer.id,
            'trialEndsAt': trial_end.isoformat() if trial_end else None,
            'currentPeriodEnd': current_period_end.isoformat() if current_period_end else None,
            'cancelAtPeriodEnd': getattr(sub, 'cancel_at_period_end', False)
        }
        print(f"[STRIPE] Found subscription for {email}: {sub.status} ({plan})")
        return result
        
    except Exception as e:
        print(f"[STRIPE] Error fetching subscription: {e}")
        return {'isActive': False, 'status': 'error', 'error': str(e)}


def sync_subscription_to_db(user_id: int, email: str) -> dict:
    """Sync subscription from Stripe to database and return status"""
    stripe_data = get_subscription_from_stripe(email, user_id=user_id)
    
    if stripe_data.get('status') == 'error':
        return stripe_data
    
    if stripe_data.get('subscriptionId'):
        db = get_db()
        if db:
            try:
                db.execute(
                    text("""UPDATE users SET 
                        stripe_customer_id = :customer_id,
                        stripe_subscription_id = :sub_id,
                        subscription_status = :status,
                        subscription_plan = :plan,
                        trial_ends_at = :trial_end,
                        current_period_end = :period_end,
                        cancel_at_period_end = :cancel_at_end
                    WHERE id = :user_id"""),
                    {
                        'customer_id': stripe_data.get('customerId'),
                        'sub_id': stripe_data.get('subscriptionId'),
                        'status': stripe_data.get('status'),
                        'plan': stripe_data.get('plan'),
                        'trial_end': stripe_data.get('trialEndsAt'),
                        'period_end': stripe_data.get('currentPeriodEnd'),
                        'cancel_at_end': stripe_data.get('cancelAtPeriodEnd', False),
                        'user_id': user_id
                    }
                )
                db.commit()
                print(f"[STRIPE] Synced subscription to DB for user {user_id}")
            except Exception as e:
                print(f"[STRIPE] Error syncing to DB: {e}")
            finally:
                db.close()
    
    return stripe_data


def get_subscription_from_db(user_id: int) -> dict:
    """Get subscription status from database (fast local check)"""
    db = get_db()
    if not db:
        return {'isActive': False, 'status': 'error'}
    
    try:
        result = db.execute(
            text("""SELECT subscription_status, subscription_plan, stripe_customer_id,
                      trial_ends_at, current_period_end, cancel_at_period_end
               FROM users WHERE id = :user_id"""),
            {'user_id': user_id}
        ).fetchone()
        
        if not result:
            return {'isActive': False, 'status': 'none'}
        
        status = result[0] or 'none'
        is_active = status in ['active', 'trialing']
        
        return {
            'isActive': is_active,
            'status': status,
            'plan': result[1],
            'customerId': result[2],
            'trialEndsAt': result[3].isoformat() if result[3] else None,
            'currentPeriodEnd': result[4].isoformat() if result[4] else None,
            'cancelAtPeriodEnd': result[5] or False
        }
    except Exception as e:
        print(f"[STRIPE] Error reading from DB: {e}")
        return {'isActive': False, 'status': 'error'}
    finally:
        db.close()


def create_checkout_session(user_id: int, email: str, plan: str = 'monthly') -> Optional[str]:
    """Create a Stripe checkout session and return the URL"""
    if not STRIPE_SECRET_KEY:
        return None
    
    price_id = ANNUAL_PRICE_ID if plan == 'annual' else MONTHLY_PRICE_ID
    
    try:
        db = get_db()
        customer_id = None
        has_previous_subscription = False
        if db:
            try:
                result = db.execute(
                    text("SELECT stripe_customer_id, stripe_subscription_id FROM users WHERE id = :user_id"),
                    {'user_id': user_id}
                ).fetchone()
                customer_id = result[0] if result else None
                # Check if user has ever had a subscription (returning customer)
                has_previous_subscription = bool(result[1]) if result else False
            finally:
                db.close()
        
        if not customer_id:
            customer = stripe.Customer.create(
                email=email,
                metadata={'educatorId': str(user_id)}
            )
            customer_id = customer.id
            db = get_db()
            if db:
                try:
                    db.execute(
                        text("UPDATE users SET stripe_customer_id = :cid WHERE id = :uid"),
                        {'cid': customer_id, 'uid': user_id}
                    )
                    db.commit()
                finally:
                    db.close()
        
        # Only offer trial to new customers who have never had a subscription
        subscription_data = {}
        if not has_previous_subscription:
            subscription_data['trial_period_days'] = 14  # 14-day free trial for new subscribers only
            print(f"[STRIPE] New customer {user_id} - offering 14-day trial")
        else:
            print(f"[STRIPE] Returning customer {user_id} - no trial (has previous subscription)")
        
        # Build checkout session params
        checkout_params = {
            'mode': 'subscription',
            'customer': customer_id,
            'line_items': [{'price': price_id, 'quantity': 1}],
            'success_url': f"{GUIDE_APP_URL}/?subscription=success",
            'cancel_url': f"{GUIDE_APP_URL}/?subscription=cancelled",
            'metadata': {'educatorId': str(user_id)},
            'allow_promotion_codes': True
        }
        
        # Only include subscription_data with trial for new customers
        if subscription_data:
            checkout_params['subscription_data'] = subscription_data
        
        session = stripe.checkout.Session.create(**checkout_params)
        
        print(f"[STRIPE] Created checkout session for user {user_id} ({plan})")
        return session.url
        
    except Exception as e:
        print(f"[STRIPE] Error creating checkout: {e}")
        return None


def create_portal_session(user_id: int) -> Optional[str]:
    """Create a Stripe billing portal session and return the URL"""
    if not STRIPE_SECRET_KEY:
        return None
    
    try:
        db = get_db()
        customer_id = None
        if db:
            try:
                result = db.execute(
                    text("SELECT stripe_customer_id FROM users WHERE id = :user_id"),
                    {'user_id': user_id}
                ).fetchone()
                customer_id = result[0] if result else None
            finally:
                db.close()
        
        if not customer_id:
            print(f"[STRIPE] No customer ID for user {user_id}")
            return None
        
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=f"{GUIDE_APP_URL}/"
        )
        
        print(f"[STRIPE] Created portal session for user {user_id}")
        return session.url
        
    except Exception as e:
        print(f"[STRIPE] Error creating portal: {e}")
        return None


def cancel_subscription(user_id: int) -> Optional[dict]:
    """Cancel subscription at end of billing period"""
    if not STRIPE_SECRET_KEY:
        return None
    
    try:
        db = get_db()
        sub_id = None
        if db:
            try:
                result = db.execute(
                    text("SELECT stripe_subscription_id FROM users WHERE id = :user_id"),
                    {'user_id': user_id}
                ).fetchone()
                sub_id = result[0] if result else None
            finally:
                db.close()
        
        if not sub_id:
            return None
        
        subscription = stripe.Subscription.modify(
            sub_id,
            cancel_at_period_end=True
        )
        
        period_end_ts = getattr(subscription, 'current_period_end', None)
        period_end = datetime.fromtimestamp(period_end_ts) if period_end_ts else None
        
        db = get_db()
        if db:
            try:
                db.execute(
                    text("""UPDATE users SET 
                        cancel_at_period_end = TRUE,
                        current_period_end = :period_end
                    WHERE id = :user_id"""),
                    {'period_end': period_end, 'user_id': user_id}
                )
                db.commit()
            finally:
                db.close()
        
        print(f"[STRIPE] Cancelled subscription for user {user_id}")
        return {'cancelAtPeriodEnd': True, 'currentPeriodEnd': period_end.isoformat() if period_end else None}
        
    except Exception as e:
        print(f"[STRIPE] Error cancelling: {e}")
        return None


def reactivate_subscription(user_id: int) -> Optional[dict]:
    """Reactivate a subscription that was set to cancel"""
    if not STRIPE_SECRET_KEY:
        return None
    
    try:
        db = get_db()
        sub_id = None
        if db:
            try:
                result = db.execute(
                    text("SELECT stripe_subscription_id FROM users WHERE id = :user_id"),
                    {'user_id': user_id}
                ).fetchone()
                sub_id = result[0] if result else None
            finally:
                db.close()
        
        if not sub_id:
            return None
        
        stripe.Subscription.modify(
            sub_id,
            cancel_at_period_end=False
        )
        
        db = get_db()
        if db:
            try:
                db.execute(
                    text("UPDATE users SET cancel_at_period_end = FALSE WHERE id = :user_id"),
                    {'user_id': user_id}
                )
                db.commit()
            finally:
                db.close()
        
        print(f"[STRIPE] Reactivated subscription for user {user_id}")
        return {'cancelAtPeriodEnd': False}
        
    except Exception as e:
        print(f"[STRIPE] Error reactivating: {e}")
        return None


# ===================== SCHOOL STRIPE FUNCTIONS =====================

def create_school_checkout_session(school_id: int, school_name: str, contact_email: str, seat_count: int = 10) -> Optional[str]:
    """Create a Stripe checkout session for a school subscription and return the URL"""
    if not STRIPE_SECRET_KEY:
        print("[STRIPE] No API key configured")
        return None
    
    if not SCHOOL_SEAT_PRICE_ID:
        print("[STRIPE] No school seat price ID configured (STRIPE_SCHOOL_SEAT_PRICE_ID)")
        return None
    
    try:
        db = get_db()
        customer_id = None
        if db:
            try:
                result = db.execute(
                    text("SELECT stripe_customer_id FROM schools WHERE id = :school_id"),
                    {'school_id': school_id}
                ).fetchone()
                customer_id = result[0] if result else None
            finally:
                db.close()
        
        if not customer_id:
            customer = stripe.Customer.create(
                email=contact_email,
                name=school_name,
                metadata={'schoolId': str(school_id), 'type': 'school'}
            )
            customer_id = customer.id
            db = get_db()
            if db:
                try:
                    db.execute(
                        text("UPDATE schools SET stripe_customer_id = :cid WHERE id = :sid"),
                        {'cid': customer_id, 'sid': school_id}
                    )
                    db.commit()
                finally:
                    db.close()
        
        session = stripe.checkout.Session.create(
            mode='subscription',
            customer=customer_id,
            line_items=[{
                'price': SCHOOL_SEAT_PRICE_ID,
                'quantity': seat_count
            }],
            success_url=f"{GUIDE_APP_URL}/school/dashboard?subscription=success",
            cancel_url=f"{GUIDE_APP_URL}/school/dashboard?subscription=cancelled",
            metadata={'schoolId': str(school_id), 'type': 'school'},
            allow_promotion_codes=True,
            subscription_data={
                'metadata': {'schoolId': str(school_id), 'type': 'school'}
            }
        )
        
        print(f"[STRIPE] Created school checkout session for school {school_id} ({seat_count} seats)")
        return session.url
        
    except Exception as e:
        print(f"[STRIPE] Error creating school checkout: {e}")
        return None


def create_school_portal_session(school_id: int) -> Optional[str]:
    """Create a Stripe billing portal session for a school and return the URL"""
    if not STRIPE_SECRET_KEY:
        return None
    
    try:
        db = get_db()
        customer_id = None
        if db:
            try:
                result = db.execute(
                    text("SELECT stripe_customer_id FROM schools WHERE id = :school_id"),
                    {'school_id': school_id}
                ).fetchone()
                customer_id = result[0] if result else None
            finally:
                db.close()
        
        if not customer_id:
            print(f"[STRIPE] No customer ID for school {school_id}")
            return None
        
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=f"{GUIDE_APP_URL}/school/dashboard"
        )
        
        print(f"[STRIPE] Created portal session for school {school_id}")
        return session.url
        
    except Exception as e:
        print(f"[STRIPE] Error creating school portal: {e}")
        return None


def get_school_subscription_from_stripe(school_id: int) -> dict:
    """Fetch school subscription status directly from Stripe"""
    if not STRIPE_SECRET_KEY:
        return {'isActive': False, 'status': 'error', 'error': 'Stripe not configured'}
    
    try:
        db = get_db()
        customer_id = None
        if db:
            try:
                result = db.execute(
                    text("SELECT stripe_customer_id FROM schools WHERE id = :school_id"),
                    {'school_id': school_id}
                ).fetchone()
                customer_id = result[0] if result else None
            finally:
                db.close()
        
        if not customer_id:
            return {'isActive': False, 'status': 'none'}
        
        subscriptions = stripe.Subscription.list(customer=customer_id, limit=1)
        
        if not subscriptions.data:
            return {'isActive': False, 'status': 'none', 'customerId': customer_id}
        
        sub = subscriptions.data[0]
        is_active = sub.status in ['active', 'trialing', 'past_due']  # Include past_due for grace period
        
        # Get seat count from subscription
        seat_count = sub.items.data[0].quantity if sub.items.data else 1
        
        period_end_ts = getattr(sub, 'current_period_end', None)
        current_period_end = datetime.fromtimestamp(period_end_ts) if period_end_ts else None
        
        return {
            'isActive': is_active,
            'status': sub.status,
            'seatCount': seat_count,
            'customerId': customer_id,
            'subscriptionId': sub.id,
            'currentPeriodEnd': current_period_end.isoformat() if current_period_end else None,
            'cancelAtPeriodEnd': getattr(sub, 'cancel_at_period_end', False)
        }
        
    except Exception as e:
        print(f"[STRIPE] Error fetching school subscription: {e}")
        return {'isActive': False, 'status': 'error', 'error': str(e)}


def update_school_seats(school_id: int, new_seat_count: int) -> Optional[dict]:
    """Update the number of seats for a school subscription"""
    if not STRIPE_SECRET_KEY:
        return None
    
    try:
        db = get_db()
        sub_id = None
        if db:
            try:
                result = db.execute(
                    text("SELECT stripe_subscription_id FROM schools WHERE id = :school_id"),
                    {'school_id': school_id}
                ).fetchone()
                sub_id = result[0] if result else None
            finally:
                db.close()
        
        if not sub_id:
            print(f"[STRIPE] No subscription ID for school {school_id}")
            return None
        
        subscription = stripe.Subscription.retrieve(sub_id)
        item_id = subscription.items.data[0].id
        
        updated_sub = stripe.Subscription.modify(
            sub_id,
            items=[{'id': item_id, 'quantity': new_seat_count}],
            proration_behavior='create_prorations'
        )
        
        # Update license count in database
        db = get_db()
        if db:
            try:
                db.execute(
                    text("UPDATE schools SET license_count = :seats WHERE id = :school_id"),
                    {'seats': new_seat_count, 'school_id': school_id}
                )
                db.commit()
            finally:
                db.close()
        
        print(f"[STRIPE] Updated school {school_id} to {new_seat_count} seats")
        return {'seatCount': new_seat_count, 'success': True}
        
    except Exception as e:
        print(f"[STRIPE] Error updating school seats: {e}")
        return None
