# MalZara - Online Flower Shop Platform

MalZara is a full-stack university project built with Flask, SQLite/MySQL-ready schema, Bootstrap 5, and session-based authentication. It includes customer shopping flow, flower customization, special day reminders, admin management, and email notifications.

## Features

- Customer registration, login, logout
- Secure password hashing with `bcrypt`
- Product browsing, filtering, and customization
- Persistent cart system
- Simulated payment checkout with order confirmation
- Special day management (birthday, anniversary, wedding, etc.)
- Automated reminder emails 3 days before special events
- Admin panel for products, offers, customer/order visibility
- Product image support via image URL or local file upload from admin dashboard
- Promotional offer email broadcast and manual campaign email
- Special-day reminder emails include relevant active offers when available
- Basic JSON API endpoints for products/cart/admin summary

## Tech Stack

- Frontend: HTML5, CSS3, JavaScript, Bootstrap 5
- Backend: Python + Flask
- Database: SQLite (default) with SQL schema compatible for MySQL adaptation
- Auth: Flask session-based + bcrypt password hashing
- Email: SMTP (or disabled mode for local demo)

## Project Structure

- app.py
- config.py
- requirements.txt
- models/
- routes/
- templates/
- static/
- database/schema.sql

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

5. Run the app:

```bash
python app.py
```

6. Open in browser:

- http://127.0.0.1:5000

## Default Admin Login

- Email: `admin@malzara.com`
- Password: `Admin@123`

This admin is auto-created the first time the app initializes the database.

## Email Behavior

- If `ENABLE_EMAIL=false`, emails are printed in terminal logs (safe for demo).
- If enabled, order confirmations, promotional campaigns, and special-day reminders send via SMTP.

## Scheduler

- A background scheduler runs daily at 08:00 server time to send special day reminders for events happening in 3 days.

## JSON API Endpoints

- `GET /api/products?category=<name>`
- `GET /api/cart`
- `GET /admin/api/summary` (admin session required)

## Demo Flow

1. Register as a customer and login.
2. Browse products and customize a bouquet.
3. Add to cart, checkout, and place simulated payment.
4. Add special days from dashboard.
5. Login as admin and manage products/offers.
6. Trigger promotional email by creating a new offer.

## Notes for MySQL Usage

- Replace SQLite connection logic with MySQL connector in `database/db.py`.
- Reuse `database/schema.sql` structure with minor SQL dialect adjustments if needed.
