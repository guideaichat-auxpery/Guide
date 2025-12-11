# Guide Payment Integration for Marketing Site (www.auxpery.com.au)

## Overview

Guide uses a **sign up first, then pay** model. Users create their account on guide.auxpery.com.au and then complete their subscription payment through the pricing page within the app. 

Optionally, your marketing site can also offer direct checkout links to accelerate the subscription process.

## User Journey

**Recommended Flow:**
1. User creates account on guide.auxpery.com.au
2. After signup, they see the pricing page
3. They choose a plan and complete Stripe Checkout
4. Subscription is activated immediately
5. Full access to Guide features

**Optional Marketing Site Integration:**
Your marketing site can link directly to Guide's checkout flow if desired using the public API endpoint below.

## API Endpoint (Optional)

**Base URL:** `https://guide.auxpery.com.au` (or your Guide app's deployed URL)

### Create Checkout Session

**POST** `/api/public/create-checkout-session`

This endpoint is **public** and does not require authentication. It returns a Stripe Checkout URL that can be used to initiate payments for users who want to pay on your marketing site.

#### Request Body

```json
{
  "email": "user@example.com",
  "priceId": "price_1Sd7RX8PGiRAuUvfzibxCNLV"
}
```

Note: This API is optional. Most users will go directly to guide.auxpery.com.au to sign up and pay within the app.

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

## Simple Redirect Links (Optional)

If you want to offer checkout on your marketing site, you can use simple redirect links to Guide's pricing page:

```html
<a href="https://guide.auxpery.com.au/?utm_source=auxpery&plan=pricing" 
   class="btn btn-primary">
   Start Free Trial
</a>
```

Users will be directed to:
1. Create their Guide account
2. See the pricing page
3. Complete checkout

This is the recommended approach - no API integration needed on your marketing site.

## Replit Agent Prompt (Optional)

If your marketing site wants to offer direct checkout, you can build a simple pricing section. Here's the prompt:

---

**Prompt for Replit Agent:**

Build a pricing section for my marketing website that links to Guide's payment flow. 

Requirements:
1. Create a clean, professional pricing section displaying two plan options:
   - Monthly: $15/month with 14-day free trial
   - Annual: $150/year (save $30 - 2 months free)

2. Add a "Start Free Trial" button that links users to Guide's signup and pricing page

3. Basic implementation:
   - Link to: `https://guide.auxpery.com.au/?utm_source=auxpery`
   - Users create their account on Guide
   - They'll see the pricing page and complete checkout there

4. Style it to match the Auxpery brand with earth tones and professional design

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
