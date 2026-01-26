# Guide Payment Integration for Marketing Site (www.auxpery.com.au)

## Overview

Guide uses a **pay first, then create account** model for the marketing site. This provides a streamlined experience where users pay via Stripe first, then are redirected to Guide to create their account with their payment already linked.

## User Journey (Pay First Flow)

1. User visits www.auxpery.com.au and sees pricing
2. User enters their email and clicks "Start Free Trial" or "Choose Annual"
3. Marketing site calls Guide's API to create a Stripe checkout session
4. User is redirected to Stripe Checkout (14-day trial, card collected but not charged)
5. After payment, user is redirected to guide.auxpery.com.au with a signup token
6. User creates their password → account is automatically linked to their payment
7. Full access to Guide features

## API Endpoint

**Base URL:** `https://guide.auxpery.com.au`

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
| Annual | $150/year (14-day free trial, 2 months free) | `price_1Sd7RX8PGiRAuUvfxnQgzmy1` |

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

#### After receiving the response, redirect the user to the `url` provided.

---

## Implementation Guide for www.auxpery.com.au

### What to Build

Create a pricing section with:
1. An email input field
2. Three pricing cards: Monthly, Annual, and Schools
3. Buttons that call the API and redirect to Stripe

### Example HTML Structure

```html
<section class="pricing">
  <h2>Start Your Guide Journey</h2>
  <p>AI-powered Montessori curriculum companion. Start your 14-day free trial today.</p>
  
  <div class="email-input">
    <input type="email" id="userEmail" placeholder="Enter your email" required>
  </div>
  
  <div class="pricing-cards">
    <!-- Monthly -->
    <div class="card">
      <h3>Monthly</h3>
      <div class="price">$15<span>/month</span></div>
      <p>14-day free trial included</p>
      <button onclick="startCheckout('monthly')">Start Free Trial</button>
    </div>
    
    <!-- Annual -->
    <div class="card recommended">
      <span class="badge">2 Months Free</span>
      <h3>Annual</h3>
      <div class="price">$150<span>/year</span></div>
      <p>Best value - save $30/year</p>
      <button onclick="startCheckout('annual')">Choose Annual</button>
    </div>
    
    <!-- Schools -->
    <div class="card">
      <span class="badge">Schools</span>
      <h3>School Plan</h3>
      <div class="price">$10<span>/seat/month</span></div>
      <p>Minimum 5 seats</p>
      <button onclick="showSchoolForm()">Get Started</button>
    </div>
  </div>
  
  <!-- School Signup Modal -->
  <div id="schoolModal" class="modal" style="display: none;">
    <div class="modal-content">
      <h3>School Subscription</h3>
      <input type="text" id="schoolName" placeholder="School Name" required>
      <input type="email" id="schoolEmail" placeholder="Admin Email" required>
      <div class="seat-selector">
        <label>Number of Educator Seats:</label>
        <input type="number" id="seatCount" min="5" max="500" value="10">
        <p class="hint">Minimum 5 seats. Price: $10/seat/month</p>
      </div>
      <p id="schoolTotal">Total: $100/month</p>
      <button onclick="startSchoolCheckout()">Proceed to Payment</button>
      <button onclick="closeSchoolModal()">Cancel</button>
    </div>
  </div>
</section>
```

### Example JavaScript

```javascript
const PRICE_IDS = {
  monthly: 'price_1Sd7RX8PGiRAuUvfzibxCNLV',
  annual: 'price_1Sd7RX8PGiRAuUvfxnQgzmy1'
};

const SCHOOL_SEAT_PRICE = 10; // $10 per seat per month

async function startCheckout(plan) {
  const email = document.getElementById('userEmail').value;
  
  // Validate email
  if (!email || !email.includes('@')) {
    alert('Please enter a valid email address');
    return;
  }
  
  try {
    const response = await fetch('https://guide.auxpery.com.au/api/public/create-checkout-session', {
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
      alert('Error: ' + (data.error || 'Unable to start checkout'));
    }
  } catch (error) {
    console.error('Checkout error:', error);
    alert('Unable to connect to payment service. Please try again.');
  }
}

// School subscription functions
function showSchoolForm() {
  document.getElementById('schoolModal').style.display = 'flex';
  updateSchoolTotal();
}

function closeSchoolModal() {
  document.getElementById('schoolModal').style.display = 'none';
}

function updateSchoolTotal() {
  const seats = parseInt(document.getElementById('seatCount').value) || 5;
  const total = seats * SCHOOL_SEAT_PRICE;
  document.getElementById('schoolTotal').textContent = `Total: $${total}/month`;
}

// Add event listener for seat count changes
document.getElementById('seatCount')?.addEventListener('input', updateSchoolTotal);

async function startSchoolCheckout() {
  const schoolName = document.getElementById('schoolName').value;
  const email = document.getElementById('schoolEmail').value;
  const seats = parseInt(document.getElementById('seatCount').value);
  
  // Validation
  if (!schoolName) {
    alert('Please enter your school name');
    return;
  }
  if (!email || !email.includes('@')) {
    alert('Please enter a valid email address');
    return;
  }
  if (seats < 5) {
    alert('Minimum 5 seats required');
    return;
  }
  if (seats > 500) {
    alert('For subscriptions over 500 seats, please contact us directly');
    return;
  }
  
  try {
    const response = await fetch('https://guide.auxpery.com.au/api/public/create-school-checkout', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        schoolName: schoolName,
        email: email,
        seats: seats
      })
    });
    
    const data = await response.json();
    
    if (data.success && data.url) {
      // Redirect to Stripe Checkout
      window.location.href = data.url;
    } else {
      alert('Error: ' + (data.error || 'Unable to start checkout'));
    }
  } catch (error) {
    console.error('School checkout error:', error);
    alert('Unable to connect to payment service. Please try again.');
  }
}
```

---

## School Subscription API

### Create School Checkout Session

**POST** `/api/public/create-school-checkout`

This endpoint creates a Stripe checkout session for school subscriptions with seat-based pricing.

#### Request Body

```json
{
  "schoolName": "Springfield Primary School",
  "email": "admin@springfield.edu.au",
  "seats": 10
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| schoolName | string | Yes | Name of the school |
| email | string | Yes | Admin email address |
| seats | number | Yes | Number of educator seats (minimum 5, maximum 500) |

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
  "error": "Minimum 5 seats required for school subscriptions"
}
```

---

## Prompt for www.auxpery.com.au Replit Agent

Copy and paste this prompt into your www.auxpery.com.au Replit project:

---

**Build a pricing section with pay-first checkout flow.**

Requirements:

1. Create a pricing section with an email input field at the top

2. Display THREE pricing cards side by side:
   - **Monthly**: $15/month, "14-day free trial included", button: "Start Free Trial"
   - **Annual**: $150/year, badge "2 Months Free", "Best value - save $30/year", button: "Choose Annual"
   - **Schools**: "$10/seat/month", "Minimum 5 seats", button: "Get Started" (opens modal)

3. When user clicks Monthly or Annual button:
   - Validate email is entered
   - Call this API:
     ```
     POST https://guide.auxpery.com.au/api/public/create-checkout-session
     Content-Type: application/json
     
     {
       "email": "<user's email>",
       "priceId": "<see below>"
     }
     ```
   - Price IDs:
     - Monthly: `price_1Sd7RX8PGiRAuUvfzibxCNLV`
     - Annual: `price_1Sd7RX8PGiRAuUvfxnQgzmy1`
   - Redirect user to the `url` in the response

4. When user clicks Schools button:
   - Show a modal with: School Name input, Admin Email input, Number of Seats selector (min 5)
   - Calculate and display total price ($10 x seats)
   - On submit, call:
     ```
     POST https://guide.auxpery.com.au/api/public/create-school-checkout
     Content-Type: application/json
     
     {
       "schoolName": "<school name>",
       "email": "<admin email>",
       "seats": <number of seats>
     }
     ```
   - Redirect user to the `url` in the response

5. Style with earth tones matching Auxpery brand (greens, warm neutrals)

6. Make it mobile responsive

---

## CORS Configuration

The Guide payments API accepts cross-origin requests from any domain, so your marketing site can make requests directly from the browser.

## Testing

Use Stripe's test card numbers:
- **Card Number:** 4242 4242 4242 4242
- **Expiry:** Any future date
- **CVC:** Any 3 digits

## What Happens After Payment

### Individual Subscriptions
1. Stripe redirects user to `guide.auxpery.com.au/?signup_token=<token>`
2. Guide detects the token and shows a "Complete Your Account" form
3. User enters their password (email is pre-filled from payment)
4. Account is created and linked to their Stripe subscription
5. User is logged in with full access

### School Subscriptions
1. Stripe redirects admin to `guide.auxpery.com.au/?school_setup=<token>`
2. Guide shows "Complete Your School Setup" form
3. Admin enters their name and creates a password
4. School and admin account are created automatically
5. Admin receives an invite link to share with educators
6. Educators join via the invite link (no individual payment required)

## Support

Contact guide@auxpery.com.au for integration questions.
