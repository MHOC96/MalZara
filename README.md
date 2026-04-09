# MalZara — Online Flower Shop Platform

MalZara is a full-stack e-commerce platform for premium floral gifting, built with Flask, SQLite (PostgreSQL-ready), Bootstrap 5, and session-based authentication. It features a complete customer shopping flow with bouquet customisation, subscription plans, review & rating system, special-day reminders with in-app notifications, admin management, and email/WhatsApp notifications.

## Features

### Customer
- Registration, login, logout with secure `bcrypt` password hashing
- Product browsing, category filtering, and bouquet customisation (flower mix, size, colour theme, personalised card)
- Persistent cart with quantity management
- Checkout with multiple payment options: Stripe (real), simulated card, simulated mobile wallet, and COD
- Discount offer application at checkout
- Preferred delivery date selection with priority delivery for subscribers
- Order history with status tracking
- **Review & rating system** — per-order star ratings (1–5) with optional written feedback
- **In-app notification panel** — upcoming special-day reminders shown on dashboard
- **MySara Subscription** — monthly/yearly plans with auto-reminders, order discounts, and priority delivery
- Special-day management (birthday, anniversary, wedding, etc.)

### Admin
- Full product CRUD with image support (URL or Cloudinary upload)
- Offer/promotion management with optional product attachment
- Customer list with detailed view (orders, special days, targeted offers)
- Order management with delivery date scheduling
- Customer review moderation (view & delete)
- Promotional email campaigns (broadcast to all customers)
- Manual special-day reminder trigger
- Targeted offer emails per customer

### System
- Automated background scheduler (APScheduler) for special-day reminders
- Email service via SMTP (or terminal-mode for local demo)
- WhatsApp notification service (optional)
- Cloudinary integration for product image uploads
- JSON API endpoints for products, cart, admin summary, and order items
- Responsive design across all devices (mobile, tablet, desktop)

## Tech Stack

- **Frontend:** HTML5, CSS3, JavaScript, Bootstrap 5, Google Fonts (DM Serif Display, Plus Jakarta Sans)
- **Backend:** Python 3 + Flask
- **Database:** SQLite (default), PostgreSQL-ready (with `psycopg`)
- **Auth:** Flask session-based + bcrypt password hashing
- **Payments:** Stripe integration (optional) + simulated payment modes
- **Email:** SMTP (configurable, or disabled for local demo)
- **Image Hosting:** Cloudinary (optional)
- **Scheduler:** APScheduler (background daily job)

## Project Structure

```
app.py                     # Flask application factory
config.py                  # Configuration from environment variables
requirements.txt           # Python dependencies
vercel.json                # Vercel deployment config
database/
  db.py                    # Database connection and initialisation
  schema.sql               # SQLite schema with seed data
  schema_postgres.sql      # PostgreSQL schema variant
models/
  user_model.py            # User CRUD
  product_model.py         # Product CRUD
  order_model.py           # Order + order items
  offer_model.py           # Offers/promotions
  specialday_model.py      # Special day events
  review_model.py          # Customer reviews
  subscription_model.py    # Subscription plans
routes/
  auth_routes.py           # Login, register, logout
  user_routes.py           # Dashboard, products, cart, checkout, reviews, subscriptions
  admin_routes.py          # Admin dashboard, CRUD, campaigns, order management
services/
  email_service.py         # SMTP email sending
  reminder_service.py      # Special-day reminder logic
  scheduler_service.py     # APScheduler setup
  stripe_service.py        # Stripe payment integration
  whatsapp_service.py      # WhatsApp notification (optional)
templates/
  base.html                # Base layout with navbar, footer, ambient orbs
  dashboard.html           # Customer dashboard
  products.html            # Product catalog listing
  product_detail.html      # Product detail with bouquet builder
  cart.html                # Shopping cart (desktop table + mobile cards)
  checkout.html            # Checkout with offer/discount application
  login.html               # Customer & admin login
  register.html            # Customer registration
  subscribe.html           # MySara subscription plans
  review_form.html         # Star rating & feedback form
  admin_dashboard.html     # Full admin panel
  admin_customer_detail.html  # Per-customer admin view
  error.html               # Error pages (404, 500)
  emails/                  # Email templates (order confirmation, etc.)
static/
  css/style.css            # Custom responsive stylesheet
  js/app.js                # Client-side JavaScript
```

## Local Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy environment config:

```bash
copy .env.example .env
```

4. Update `.env` values:

- Set `SECRET_KEY`.
- Keep `ENABLE_EMAIL=false` for local testing, or set SMTP credentials and `ENABLE_EMAIL=true`.
- Set Cloudinary values if using image uploads: `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`.
- (Optional) Set Stripe keys if using real payments.

5. Run the app:

```bash
python app.py
```

6. Open in browser:

- http://127.0.0.1:5000

## Default Admin Login

- Email: `admin@malzara.com`
- Password: `Admin@123`

This admin is auto-created the first time the app initialises the database.

## Email Behaviour

- If `ENABLE_EMAIL=false`, emails are printed in terminal logs (safe for demo).
- If enabled, order confirmations, promotional campaigns, and special-day reminders send via SMTP.

## Scheduler

- A background scheduler runs daily at 08:00 server time.
- Sends special-day reminder emails for events happening in **1 day** and **3 days**.
- Includes relevant active offers in reminder emails when available.
- Disabled on Vercel serverless (`ENABLE_SCHEDULER=false`). Use Vercel Cron + HTTP endpoint for production.

## Deploy on Vercel

1. Push the project to GitHub.
2. In Vercel, create a new project and import this repository.
3. Vercel detects `vercel.json` and runs the Flask app from `app.py`.
4. Add environment variables in Vercel Project Settings → Environment Variables:

- `SECRET_KEY`
- `DATABASE_URL` (for Vercel demo mode, use `/tmp/malzara.db`)
- `ENABLE_EMAIL`, `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_FROM`
- `APP_BASE_URL` (set to your Vercel domain, e.g. `https://your-app.vercel.app`)
- `OFFERS_PAGE_URL`
- `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`, `CLOUDINARY_UPLOAD_FOLDER`
- `ENABLE_SCHEDULER=false`

5. Deploy.

Important notes:

- SQLite on Vercel is ephemeral. Data can reset across cold starts and redeploys.
- For production, migrate to a managed database (e.g. Neon/Postgres, Supabase, PlanetScale, or Turso).
- APScheduler background jobs are disabled on Vercel serverless runtime. Use Vercel Cron + an HTTP endpoint if you need scheduled reminders in production.

## JSON API Endpoints

- `GET /api/products?category=<name>` — List products (optional category filter)
- `GET /api/cart` — Current user's cart items
- `GET /admin/api/summary` — Admin dashboard summary (admin session required)
- `GET /admin/api/orders/<id>/items` — Order items for a specific order (admin session required)

## Demo Flow

1. Register as a customer and login.
2. Browse products, filter by category, and customise a bouquet.
3. Add to cart, adjust quantities, then proceed to checkout.
4. Apply a discount offer, choose delivery date, and place order (simulated or Stripe).
5. View order status and submit a review with star rating.
6. Add special days from the dashboard and receive in-app notifications.
7. Subscribe to a MySara plan for auto-reminders and discounts.
8. Login as admin and manage products, offers, orders, and reviews.
9. Send promotional emails or targeted offers to individual customers.

## Notes for PostgreSQL Usage

- The project ships with `schema_postgres.sql` for PostgreSQL compatibility.
- Set `DATABASE_URL` to a PostgreSQL connection string (e.g. from Neon, Supabase, etc.).
- Replace SQLite connection logic with the PostgreSQL adapter in `database/db.py` (already supports `psycopg`).
