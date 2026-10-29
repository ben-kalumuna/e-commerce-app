# Alesi Grocery Store (Django)

Static W3layouts grocery template converted to a Django e-commerce storefront with a custom admin dashboard, role-based access, customer accounts, cart, and Cash on Delivery checkout.

## Setup

```bash
cd web   # project root (this folder)
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_catalog
python manage.py createsuperuser
python manage.py runserver
```

Demo admin: **admin** / **admin123** (change this password).

- Storefront: http://127.0.0.1:8000/
- Admin dashboard: http://127.0.0.1:8000/dashboard/
- Django Admin (advanced): http://127.0.0.1:8000/admin/

## Roles

| Role | Who | After login |
|------|-----|-------------|
| **Admin** | Users with `is_staff` | `/dashboard/` |
| **Customer** | Regular registered users | Storefront `/` |

Login/register share `/accounts/login/`. Registration always creates a customer (never staff).

## What you can do

**As admin (`/dashboard/`):**
- Overview KPIs, 7-day sales chart, top products, offers snapshot
- Products CRUD (create / edit / delete, images, prices, featured)
- Categories CRUD
- Offers & featured products
- Inventory stock updates
- Orders: filter, detail, status workflow (Pending → Confirmed → Out for delivery → Delivered / Cancelled)
- Sales summary
- Customers list & detail
- Newsletter subscribers & contact messages
- Settings overview

**As customer:**
- Browse, search, product detail
- Register / login
- Cart (guests OK); login required to checkout
- COD orders, order history, cancel pending orders

## Project layout

```
manage.py
config/
apps/
  accounts/       # auth + role redirects
  catalog/
  cart/
  orders/
  pages/
  dashboard/      # custom admin UI
templates/
  dashboard/      # admin dashboard templates
static/dashboard/ # dashboard CSS
css/ js/ images/ fonts/
media/
```
