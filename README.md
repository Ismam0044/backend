# A2i ERP

A Django-based ERP for a multi-warehouse supershop: inventory, sales/POS, purchase, party (customer/supplier) ledgers, and cash book/vouchers.

## Stack
- **Backend:** Django + HTMX (server-rendered, no separate JS frontend)
- **Database:** PostgreSQL — local Postgres via Docker Compose for development, [Neon](https://neon.tech) (managed Postgres, free tier) in production
- **Hosting:** Render (free tier), auto-deployed from this GitHub repo via the Dockerfile
- **Security:** custom role-based access (`core.permissions`), `django-axes` (login brute-force protection), `django-simple-history` (audit trail on financial/inventory models)

## Apps
| App | Responsibility |
|---|---|
| `core` | Warehouses, custom User model with roles (Owner/Manager/Cashier/Stock Keeper) |
| `inventory` | Items, units, per-warehouse stock, stock transfers |
| `parties` | Customers/suppliers and their running ledger balance (khata/baki) |
| `sales` | Sales invoices (POS) |
| `purchase` | Purchase invoices |
| `accounts` | Cash book, payment/receipt vouchers |
| `reports` | Cross-cutting reports (no models) |

## Local development (Docker)

1. Copy the env template and adjust if needed:
   ```
   cp .env.example .env
   ```
   The default values already match `docker-compose.yml`'s local Postgres service.

2. Build and start everything:
   ```
   docker compose up --build
   ```

3. In another terminal, create an admin user:
   ```
   docker compose exec web python manage.py createsuperuser
   ```

4. Visit `http://localhost:8000/admin/` and log in.

## Production deployment (Render + Neon)

1. Create a Neon project, copy its connection string.
2. Create a Render **Web Service** from this GitHub repo, "Docker" runtime (uses the `Dockerfile` as-is).
3. Set these environment variables in Render's dashboard (never commit them):
   - `SECRET_KEY` — a long random string
   - `DEBUG` = `False`
   - `ALLOWED_HOSTS` — your Render domain, e.g. `erp-system.onrender.com`
   - `DATABASE_URL` — the Neon connection string (`postgresql://...?sslmode=require`)
   - `CSRF_TRUSTED_ORIGINS` — `https://erp-system.onrender.com`
4. Push to `main` — Render builds the Docker image and deploys automatically. The container runs migrations on startup.

## Status

Phase 0 (this scaffold): project structure, data model, admin data-entry, Docker, and security foundations are in place.

Next: Phase 1 — Sales/POS screen, Purchase entry screen, Party ledger view, stock auto-updates on sale/purchase.
