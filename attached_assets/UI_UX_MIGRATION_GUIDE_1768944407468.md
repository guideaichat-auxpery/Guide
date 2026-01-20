# Guide UI/UX Migration Reference

A comprehensive guide for applying all UI/UX changes from this sandbox to the original Guide project.

---

## Table of Contents
1. [Color Palette](#1-color-palette)
2. [Login Page Layout](#2-login-page-layout)
3. [Sidebar Navigation Structure](#3-sidebar-navigation-structure)
4. [Quick Guide Cards (Companion)](#4-quick-guide-cards-companion)
5. [Button Styling System](#5-button-styling-system)
6. [CSS Files to Update](#6-css-files-to-update)
7. [Streamlit CSS Targeting Techniques](#7-streamlit-css-targeting-techniques)
8. [Search & Replace Checklist](#8-search--replace-checklist)

---

## 1. Color Palette

### Primary Colors (use these everywhere)

| Variable | Value | Purpose |
|----------|-------|---------|
| `--ux-accent` | `#789A76` | Primary accent, links, active states |
| `--ux-accent-hover` | `#5a7a58` or `#6A8A68` | Hover states |
| `--ux-accent-light` | `rgba(120, 154, 118, 0.08)` | Subtle backgrounds |
| `--ux-bg` | `#FAF9F6` | Page background, card backgrounds |
| `--ux-surface` | `#FFFFFF` | Elevated surfaces |
| `--ux-text` | `#2E2E2B` | Primary text |
| `--ux-text-muted` | `rgba(46, 46, 43, 0.65)` | Secondary text |
| `--ux-border` | `#E4E1DC` | Visible borders |
| `--ux-border-subtle` | `rgba(228, 225, 220, 0.5)` | Subtle dividers |

### Shadow Scale

```css
--shadow-xs: 0 1px 2px rgba(46, 46, 43, 0.04);
--shadow-sm: 0 2px 8px rgba(46, 46, 43, 0.06);
--shadow-md: 0 4px 16px rgba(46, 46, 43, 0.08);
--shadow-lg: 0 8px 32px rgba(46, 46, 43, 0.12);
```

### Colors to REMOVE (Search & Replace)

| Remove This | Replace With |
|-------------|--------------|
| `#3d5a3d` (dark green) | `#789A76` |
| `#2d4a2d` | `#5a7a58` |
| Any dark green gradient | Light accent or transparent |

---

## 2. Login Page Layout

### Location: `auth.py` → `login_page()` function

### Structure

```python
def login_page():
    """Display login page for educators and students"""
    
    # Page-specific CSS
    st.markdown("""
    <style>
    /* Auth page breathing room */
    .main .block-container {
        padding-top: 2.5rem !important;
        max-width: 560px !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }
    /* Center tabs */
    div[data-testid="stTabs"] [data-baseweb="tab-list"] {
        justify-content: center !important;
    }
    /* Forgot password link - borderless, link-style */
    .forgot-password-link .stButton > button,
    .forgot-password-link .stButton > button[kind="secondary"] {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: #789A76 !important;
        text-decoration: underline !important;
        padding: 0.5rem !important;
    }
    .forgot-password-link .stButton > button:hover,
    .forgot-password-link .stButton > button[kind="secondary"]:hover {
        background: transparent !important;
        color: #5a7a58 !important;
        border: none !important;
        box-shadow: none !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<h2 style="text-align: center; color: var(--ux-accent, #789A76); margin-bottom: 1.5rem;">🔐 Login to Your Account</h2>', unsafe_allow_html=True)
    
    # Tab-based separation
    educator_tab, student_tab, signup_tab, terms_tab = st.tabs(["👩‍🏫 Educator Login", "🎒 Student Login", "📝 Sign Up", "📋 T&Cs"])
    
    with educator_tab:
        # Forgot password - WRAPPED for CSS targeting
        st.markdown('<div class="forgot-password-link">', unsafe_allow_html=True)
        if st.button("Forgot your password?", key="forgot_pwd_link", use_container_width=True, type="secondary"):
            st.session_state.auth_mode = 'forgot_password'
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        with st.form("educator_login"):
            email = st.text_input("Email", placeholder="your.email@example.com")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", use_container_width=True)
            # ... rest of form handling
```

### Key Points
- Max width 560px, centered
- Tabs centered with CSS
- "Forgot password?" button wrapped in div for borderless styling
- Uses `type="secondary"` on the button

---

## 3. Sidebar Navigation Structure

### Location: `auth.py` → `show_user_info()` function

### Full Implementation

```python
def show_user_info():
    """Display current user information with enhanced sidebar navigation"""
    if st.session_state.get('authenticated'):
        # Sidebar styling
        st.sidebar.markdown("""
        <style>
        [data-testid="stSidebar"] {
            background-color: #FAF9F6;
        }
        [data-testid="stSidebar"] .stButton > button {
            border-radius: 8px;
            transition: all 0.2s ease;
        }
        [data-testid="stSidebar"] .stButton > button:hover {
            background-color: rgba(120, 154, 118, 0.1);
            border-color: #789A76;
        }
        .sidebar-user-card {
            background: white;
            border-radius: 12px;
            padding: 1rem;
            margin-bottom: 1rem;
            box-shadow: 0 2px 8px rgba(46, 46, 43, 0.06);
        }
        .sidebar-user-name {
            font-weight: 600;
            font-size: 1rem;
            color: #2E2E2B;
            margin-bottom: 0.25rem;
        }
        .sidebar-user-email {
            font-size: 0.85rem;
            color: rgba(46, 46, 43, 0.65);
        }
        .sidebar-plan-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
            font-size: 0.75rem;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            margin-top: 0.5rem;
        }
        .sidebar-plan-active {
            background: rgba(120, 154, 118, 0.15);
            color: #5a7a58;
        }
        .sidebar-plan-inactive {
            background: rgba(220, 53, 69, 0.1);
            color: #c82333;
        }
        .sidebar-section-title {
            font-size: 0.65rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: rgba(46, 46, 43, 0.45);
            margin: 1.75rem 0 0.75rem 0;
            padding-top: 1rem;
            border-top: 1px solid rgba(120, 154, 118, 0.12);
        }
        .sidebar-section-title:first-of-type {
            margin-top: 1rem;
            border-top: none;
            padding-top: 0;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Student sidebar - compact
        if st.session_state.get('is_student'):
            st.sidebar.markdown(f'''
            <div class="sidebar-user-card">
                <div class="sidebar-user-name">👤 {st.session_state.user_name}</div>
                <div class="sidebar-user-email">@{st.session_state.username}</div>
            </div>
            ''', unsafe_allow_html=True)
        else:
            # Educator sidebar - enhanced with subscription badge
            sub_status = st.session_state.get('subscription_status', 'none')
            is_active = st.session_state.get('subscription_active', False)
            plan = (st.session_state.get('subscription_plan') or 'monthly').capitalize()
            
            if is_active:
                badge_html = f'<span class="sidebar-plan-badge sidebar-plan-active">✓ {plan}</span>'
            else:
                badge_html = '<span class="sidebar-plan-badge sidebar-plan-inactive">No plan</span>'
            
            st.sidebar.markdown(f'''
            <div class="sidebar-user-card">
                <div class="sidebar-user-name">{st.session_state.user_name or 'Educator'}</div>
                <div class="sidebar-user-email">{st.session_state.user_email}</div>
                {badge_html}
            </div>
            ''', unsafe_allow_html=True)
            
            # TOOLS Section
            st.sidebar.markdown('<div style="height: 1rem;"></div>', unsafe_allow_html=True)
            st.sidebar.markdown('<div class="sidebar-section-title">Tools</div>', unsafe_allow_html=True)
            
            nav_items = [
                {"icon": "🏠", "label": "Dashboard", "mode": "dashboard_home"},
                {"icon": "📚", "label": "Lesson Planning", "mode": "lesson_planning"},
                {"icon": "🌱", "label": "Companion", "mode": "companion"},
                {"icon": "👥", "label": "Students", "mode": "student_dashboard"},
                {"icon": "📝", "label": "Planning Notes", "mode": "planning_notes"},
                {"icon": "📖", "label": "Great Stories", "mode": "great_stories"},
                {"icon": "✨", "label": "Imaginarium", "mode": "imaginarium"},
            ]
            
            current_mode = st.session_state.get('auth_mode', 'dashboard_home')
            
            for item in nav_items:
                is_current = current_mode == item["mode"]
                btn_type = "primary" if is_current else "secondary"
                if st.sidebar.button(
                    f"{item['icon']} {item['label']}", 
                    key=f"nav_{item['mode']}", 
                    use_container_width=True,
                    type=btn_type
                ):
                    st.session_state.auth_mode = item["mode"]
                    st.rerun()
            
            # ACCOUNT Section
            st.sidebar.markdown('<div style="height: 0.75rem; border-top: 1px solid rgba(120, 154, 118, 0.15); margin-top: 1rem;"></div>', unsafe_allow_html=True)
            st.sidebar.markdown('<div class="sidebar-section-title">Account</div>', unsafe_allow_html=True)
            
            # Subscription expander
            with st.sidebar.expander("🔄 Subscription"):
                # ... subscription verification buttons
                pass
        
        st.sidebar.divider()
        
        if st.sidebar.button("🚪 Logout", key="logout_btn", use_container_width=True):
            logout()
        
        with st.sidebar.expander("⬇️ Export Data"):
            # ... GDPR export functionality
            pass
```

### Section Headers Pattern

Use explicit spacer divs and markdown for section titles:

```python
# Add spacer with subtle separator line
st.sidebar.markdown('<div style="height: 0.75rem; border-top: 1px solid rgba(120, 154, 118, 0.15); margin-top: 1rem;"></div>', unsafe_allow_html=True)
# Add section title
st.sidebar.markdown('<div class="sidebar-section-title">Account</div>', unsafe_allow_html=True)
```

---

## 4. Quick Guide Cards (Companion)

### Location: `interfaces.py` → companion interface function

### Structure

```python
# Quick conversation starters
st.markdown('<h4 style="color: var(--ux-text, #2E2E2B); margin-top: 1.5rem; margin-bottom: 0.5rem;">📚 Montessori Quick Guides</h4>', unsafe_allow_html=True)
st.caption("Click any topic to explore authentic Montessori wisdom from Dr. Montessori's foundational texts")

quick_prompts = [
    "🌌 What is cosmic education and how do I implement it?",
    "🎯 Explain the sensitive periods in child development",
    "🏛️ What is the prepared environment?",
    # ... more prompts
]

# Custom Grid for Symmetrical Cards - WRAPPER PATTERN
st.markdown('<div class="quick-guide-grid">', unsafe_allow_html=True)
cols = st.columns(3)
for idx, prompt_text in enumerate(quick_prompts):
    with cols[idx % 3]:
        st.markdown(f'<div class="companion-card-container" id="companion_card_{idx}">', unsafe_allow_html=True)
        if st.button(prompt_text, key=f"quick_{idx}", use_container_width=True):
            st.session_state.companion_messages.append({"role": "user", "content": prompt_text})
            # ... save to database
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# Inline CSS for cards
st.markdown("""
    <style>
    /* Target the quick-guide-grid area and set uniform gaps */
    .quick-guide-grid [data-testid="stHorizontalBlock"] {
        gap: 1rem !important;
    }
    .quick-guide-grid [data-testid="stVerticalBlockBorderWrapper"],
    .quick-guide-grid [data-testid="stVerticalBlock"] {
        gap: 1rem !important;
    }
    /* Also target columns directly */
    .quick-guide-grid [data-testid="column"] {
        padding: 0 !important;
    }
    div.companion-card-container {
        margin-bottom: 1rem !important;
        padding: 0 !important;
    }
    div.companion-card-container > div.stButton {
        margin: 0 !important;
    }
    div.companion-card-container > div.stButton > button {
        height: 120px !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
        padding: 1rem !important;
        margin: 0 !important;
        background: #FAF9F6 !important;
        border: none !important;
        color: #2E2E2B !important;
        white-space: normal !important;
        word-wrap: break-word !important;
        line-height: 1.4 !important;
        border-radius: 12px !important;
        box-shadow: 0 2px 8px rgba(46, 46, 43, 0.04) !important;
    }
    div.companion-card-container > div.stButton > button:hover {
        background: rgba(120, 154, 118, 0.12) !important;
        color: #5a7a58 !important;
        border-color: #789A76 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 16px rgba(46, 46, 43, 0.08) !important;
    }
    </style>
""", unsafe_allow_html=True)
```

### Key Points
- Outer wrapper: `<div class="quick-guide-grid">`
- Per-card wrapper: `<div class="companion-card-container">`
- 120px fixed height cards
- Cream background (`#FAF9F6`)
- NO borders (`border: none`)
- Subtle shadow
- Hover: slight lift + green tint

---

## 5. Button Styling System

### Location: `static/css/montessori-theme.css`

### Primary Buttons (with gradient)

```css
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, var(--color-leaf), var(--color-sky)) !important;
  color: white !important;
  border: none !important;
  border-radius: var(--radius-medium) !important;
  padding: 0.5rem 1.5rem !important;
  font-weight: 500 !important;
  box-shadow: var(--shadow-soft) !important;
  transition: var(--transition-smooth) !important;
}

.stButton > button[kind="primary"]:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 8px 24px rgba(20, 20, 20, 0.12) !important;
}
```

### Secondary Buttons (clean, no gradient)

```css
.stButton > button[kind="secondary"],
.stButton > button:not([kind="primary"]) {
  background: rgba(250, 249, 246, 0.95) !important;
  color: var(--color-ink) !important;
  border: 1px solid var(--color-clay) !important;
  border-radius: var(--radius-medium) !important;
  padding: 0.5rem 1.5rem !important;
  font-weight: 500 !important;
  box-shadow: var(--shadow-soft) !important;
  transition: var(--transition-smooth) !important;
}

.stButton > button[kind="secondary"]:hover,
.stButton > button:not([kind="primary"]):hover {
  background: rgba(155, 191, 155, 0.15) !important;
  border-color: var(--color-leaf) !important;
  color: #5a7a58 !important;
}
```

---

## 6. CSS Files to Update

### `static/css/unified-ux.css`

Key variables at the top:
```css
:root {
  --ux-bg: #FAF9F6;
  --ux-surface: #FFFFFF;
  --ux-accent: #789A76;
  --ux-accent-hover: #6A8A68;
  --ux-accent-light: rgba(120, 154, 118, 0.08);
  --ux-text: #2E2E2B;
  --ux-text-muted: rgba(46, 46, 43, 0.65);
  --ux-border: #E4E1DC;
  --ux-border-subtle: rgba(228, 225, 220, 0.5);
}
```

### `static/css/montessori-theme.css`

Key variables:
```css
:root {
  --color-sand: #f5f1e6;
  --color-clay: #d9c2a3;
  --color-sky: #cce3de;
  --color-leaf: #9bbf9b;
  --color-ink: #2f3e46;
  --color-paper: #fffdf8;
}
```

---

## 7. Streamlit CSS Targeting Techniques

### The Wrapper Div Pattern

**Problem:** Streamlit doesn't let you add classes to widgets directly.

**Solution:** Wrap widgets in custom divs, then target with CSS.

```python
# Python
st.markdown('<div class="my-wrapper">', unsafe_allow_html=True)
if st.button("Click me", key="my_btn"):
    pass
st.markdown('</div>', unsafe_allow_html=True)
```

```css
/* CSS */
.my-wrapper .stButton > button {
    /* Your styles */
}
```

### Common Streamlit Selectors

| What you want | CSS Selector |
|---------------|--------------|
| Any button | `.stButton > button` |
| Primary button | `.stButton > button[kind="primary"]` |
| Secondary button | `.stButton > button[kind="secondary"]` |
| Sidebar | `[data-testid="stSidebar"]` |
| Sidebar buttons | `[data-testid="stSidebar"] .stButton > button` |
| Columns row | `[data-testid="stHorizontalBlock"]` |
| Single column | `[data-testid="column"]` |
| Tabs container | `div[data-testid="stTabs"]` |
| Tab list | `[data-baseweb="tab-list"]` |
| Expander | `[data-testid="stExpander"]` |
| Expander header | `.streamlit-expanderHeader` |

### What DOESN'T Work in Streamlit

- `:has()` pseudo-selector
- `:contains()` pseudo-selector
- Complex sibling selectors with dynamic content

---

## 8. Search & Replace Checklist

### Colors to Find & Replace

```
Find: #3d5a3d → Replace: #789A76
Find: #2d4a2d → Replace: #5a7a58
Find: rgb(61, 90, 61) → Replace: rgb(120, 154, 118)
```

### Borders to Remove

Look for these patterns and evaluate if `border: none` is appropriate:

```css
/* Before */
border: 1px solid #something;

/* After (for cards/containers) */
border: none;
```

### Key Files to Check

1. `auth.py` - Login page, sidebar navigation
2. `interfaces.py` - Companion cards, other interfaces
3. `app.py` - Main app structure, header
4. `static/css/montessori-theme.css` - Global theme
5. `static/css/unified-ux.css` - UX design system
6. `static/css/danish-eco-theme.css` - Dashboard theme (if used)

---

## Summary of Changes Made

| Area | Change | File |
|------|--------|------|
| Login page | Centered, narrower (560px), breathing room | `auth.py` |
| Forgot password | Borderless, underlined link style | `auth.py` |
| Sidebar nav | User card + Tools/Account sections with buttons | `auth.py` |
| Section headers | Explicit spacer divs with subtle borders | `auth.py` |
| Quick Guide cards | Wrapper divs, 120px height, borderless, cream bg | `interfaces.py` |
| Card spacing | 1rem uniform gaps via grid CSS | `interfaces.py` |
| Primary buttons | Keep gradient | `montessori-theme.css` |
| Secondary buttons | No gradient, subtle border | `montessori-theme.css` |
| Dark green | Removed entirely | All files |

---

## Quick Start

1. Copy the CSS variables from Section 1 into your theme files
2. Update `auth.py` with the login page and sidebar navigation code from Sections 2-3
3. Update `interfaces.py` with the Quick Guide cards pattern from Section 4
4. Update `montessori-theme.css` button rules from Section 5
5. Search for and remove all instances of `#3d5a3d` dark green
6. Test each page after changes
