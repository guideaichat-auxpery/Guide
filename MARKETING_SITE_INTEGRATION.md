# Guide Payment Integration for Marketing Site (www.auxpery.com.au)

## Overview

This document explains how to integrate your marketing site at www.auxpery.com.au with the Guide payment system. When users want to subscribe to Guide, they will:

1. Enter their email on your marketing site
2. Choose a subscription plan (Monthly or Annual)
3. Click "Subscribe" and be redirected to Stripe Checkout
4. After successful payment, be redirected to guide.auxpery.com.au to complete their account setup

## API Endpoint

**Base URL:** `https://guide.auxpery.com.au` (or your Guide app's deployed URL)

### Create Checkout Session

**POST** `/api/public/create-checkout-session`

This endpoint is **public** and does not require authentication.

#### Request Body

```json
{
  "email": "user@example.com",
  "priceId": "price_1Sd7RX8PGiRAuUvfzibxCNLV"
}
```

#### Price IDs

| Plan | Price | Price ID |
|------|-------|----------|
| Monthly | $15/month (14-day free trial) | `price_1Sd7RX8PGiRAuUvfzibxCNLV` |
| Annual | $150/year (2 months free) | `price_1Sd7RX8PGiRAuUvfxnQgzmy1` |

#### Response

**Success (200):**
```json
{
  "success": true,
  "url": "https://checkout.stripe.com/c/pay/cs_live_..."
}
```

**Error (400):**
```json
{
  "success": false,
  "error": "priceId and email are required"
}
```

## Frontend Implementation Example

### HTML Form

```html
<form id="subscribe-form">
  <h2>Start Your Guide Journey</h2>
  
  <div class="form-group">
    <label for="email">Email Address</label>
    <input type="email" id="email" name="email" required placeholder="your.email@example.com">
  </div>
  
  <div class="plan-options">
    <label class="plan-card">
      <input type="radio" name="plan" value="monthly" checked>
      <div class="plan-content">
        <h3>Monthly</h3>
        <p class="price">$15/month</p>
        <p class="trial">14-day free trial</p>
      </div>
    </label>
    
    <label class="plan-card">
      <input type="radio" name="plan" value="annual">
      <div class="plan-content">
        <h3>Annual</h3>
        <p class="price">$150/year</p>
        <p class="savings">Save $30 (2 months free!)</p>
      </div>
    </label>
  </div>
  
  <button type="submit" id="subscribe-btn">Start Free Trial</button>
</form>

<div id="error-message" style="display: none; color: red;"></div>
```

### JavaScript

```javascript
const GUIDE_API_URL = 'https://guide.auxpery.com.au';

const PRICE_IDS = {
  monthly: 'price_1Sd7RX8PGiRAuUvfzibxCNLV',
  annual: 'price_1Sd7RX8PGiRAuUvfxnQgzmy1'
};

document.getElementById('subscribe-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  
  const email = document.getElementById('email').value;
  const plan = document.querySelector('input[name="plan"]:checked').value;
  const button = document.getElementById('subscribe-btn');
  const errorDiv = document.getElementById('error-message');
  
  // Validate email
  if (!email || !email.includes('@')) {
    errorDiv.textContent = 'Please enter a valid email address';
    errorDiv.style.display = 'block';
    return;
  }
  
  // Disable button and show loading state
  button.disabled = true;
  button.textContent = 'Redirecting to checkout...';
  errorDiv.style.display = 'none';
  
  try {
    const response = await fetch(`${GUIDE_API_URL}/api/public/create-checkout-session`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        email: email,
        priceId: PRICE_IDS[plan]
      })
    });
    
    const data = await response.json();
    
    if (data.success && data.url) {
      // Redirect to Stripe Checkout
      window.location.href = data.url;
    } else {
      throw new Error(data.error || 'Failed to create checkout session');
    }
  } catch (error) {
    console.error('Checkout error:', error);
    errorDiv.textContent = error.message || 'Something went wrong. Please try again.';
    errorDiv.style.display = 'block';
    button.disabled = false;
    button.textContent = 'Start Free Trial';
  }
});
```

## What Happens After Payment

1. **Stripe Checkout Completion**: User completes payment on Stripe
2. **Redirect to Guide**: User is redirected to `https://guide.auxpery.com.au/?signup_token=<token>`
3. **Account Setup**: Guide shows a simplified signup form with:
   - Email pre-filled and locked (must match the email used for payment)
   - User enters their name and password
4. **Subscription Activated**: The subscription is automatically linked to their new account
5. **Access Granted**: User has immediate access to all Guide features

## Replit Agent Prompt

If you're building the marketing site in Replit, you can copy this prompt to your Replit Agent:

---

**Prompt for Replit Agent:**

Build a pricing/subscription section for my marketing website that integrates with the Guide payment system. 

Requirements:
1. Create a clean, professional pricing section with two plan options:
   - Monthly: $15/month with 14-day free trial
   - Annual: $150/year (save $30 - 2 months free)

2. Include an email input field and plan selection

3. When the user clicks "Subscribe" or "Start Free Trial":
   - Make a POST request to `https://guide.auxpery.com.au/api/public/create-checkout-session`
   - Send JSON body: `{ "email": "<user email>", "priceId": "<selected price id>" }`
   - Price IDs:
     - Monthly: `price_1Sd7RX8PGiRAuUvfzibxCNLV`
     - Annual: `price_1Sd7RX8PGiRAuUvfxnQgzmy1`
   - On success, redirect the user to the `url` returned in the response
   - On error, show an error message

4. Style it to match the Auxpery brand with earth tones and professional design

5. Add proper error handling for invalid emails and network errors

---

## CORS Configuration

The Guide payments API is configured to accept cross-origin requests from any domain, so your marketing site can make requests directly from the browser without any additional configuration.

## Testing

For testing, you can use Stripe's test card numbers:
- **Card Number:** 4242 4242 4242 4242
- **Expiry:** Any future date
- **CVC:** Any 3 digits

## Support

If you encounter any issues with the integration, please contact the Guide development team.
