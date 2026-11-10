# E-Commerce Admin & SuperAdmin Backend Service Roadmap

## 1. System Vision & Overview
A high-performance, enterprise-grade, asynchronous backend service built with **FastAPI** and **MongoDB (Motor)** dedicated to e-commerce administration. The system implements a hierarchical Role-Based Access Control (RBAC) architecture with granular permissions, separating the **SuperAdmin** (platform owner, admin manager, audit overseer, global configurer) from specialized **Admin** roles (Product Managers, Order Processors, Support Staff, Inventory Leads, and Finance Managers).

---

## 2. Core Functional Requirements & Analysis

### A. SuperAdmin Capabilities (Platform Management)
1. **Admin Lifecycle & Governance**:
   - Create, update, suspend, activate, and delete Admin accounts.
   - Assign built-in roles (`SUPERADMIN`, `ADMIN`, `CATALOG_MANAGER`, `ORDER_MANAGER`, `FINANCE`, `SUPPORT`) or custom granular permission scopes.
   - Force password resets, revoke tokens, and manage multi-factor authentication (MFA) settings.
2. **Audit Logging & Security Surveillance**:
   - Append-only immutable activity log recording all administrative actions (actor, role, IP, action, target resource, diff payload, timestamp).
   - Filtering and exportable logs for compliance.
3. **Global System & Store Configuration**:
   - Store identity, currency defaults, internationalization settings.
   - Tax rate configurations (regional tax percentages, compound taxes).
   - Shipping methods, flat rates, and free shipping thresholds.
   - Maintenance mode toggles and API rate-limiting policies.

### B. Admin Capabilities (Store Operations)
1. **Catalog & Product Management**:
   - **Categories**: Hierarchical category tree (parent-child), slugs, metadata, active/inactive toggles.
   - **Brands**: Brand registry, logos, website links, SEO metadata.
   - **Products**: Full CRUD with Title, SKU, Barcode, Slugs, Status (`DRAFT`, `PUBLISHED`, `ARCHIVED`), Descriptions, Media galleries.
   - **Variants & Attributes**: Dynamic attribute combinations (Size, Color, Material), variant-specific pricing, SKUs, and inventory.
   - **Search & Filtering**: Full-text search, category facets, price range, and status filters.
2. **Inventory & Warehouse Management**:
   - Real-time stock tracking across products and variants.
   - Stock adjustments with audit reason codes (`PURCHASE_RECEIPT`, `CORRECTION`, `DAMAGED`, `CUSTOMER_RETURN`, `ORDER_FULFILLMENT`).
   - Low-stock threshold alerts with rapid restocking flags.
3. **Order & Fulfillment Pipeline**:
   - Centralized order dashboard with comprehensive state-machine validation (`PENDING` -> `CONFIRMED` -> `PROCESSING` -> `SHIPPED` -> `DELIVERED` / `CANCELLED` / `REFUNDED`).
   - Payment status tracking (`UNPAID`, `AUTHORIZED`, `PAID`, `REFUNDED`, `FAILED`).
   - Fulfillment & tracking updates (courier, tracking ID, tracking link).
   - Order cancellations and refunds with automatic inventory restock options.
   - Internal staff order notes vs. customer-facing communication logs.
4. **Customer Intelligence & Relationship Management**:
   - Customer registry with lifetime statistics (Total Orders, Lifetime Value - LTV, Average Order Value - AOV, Last Purchase Date).
   - Customer status moderation (Active, Suspended, Flagged for Fraud).
   - Customer addresses, internal admin notes, and VIP tagging.
5. **Marketing, Coupons & Promotions Engine**:
   - Discount types: Percentage discount, Fixed amount, Free shipping.
   - Usage constraints: Minimum order amount, maximum discount cap, overall usage limits, per-customer limits, valid date ranges.
   - Category / Product inclusion & exclusion rules.
   - Promotion performance analytics (redemption counts, discount revenue impact).
6. **Analytics & BI Dashboard**:
   - Executive KPIs: Total Revenue, Gross Merchandise Value (GMV), Total Orders, Pending Shipments, New Customers.
   - Time-series aggregations (daily, weekly, monthly sales and order trends).
   - Top-selling products and categories by volume and margin.
   - Real-time alerts for low inventory and pending orders.

---

## 3. Scalable Production Architecture

```
                                  [ Client Requests ]
                                           │
                                  [ Reverse Proxy ]
                              (Nginx / Traefik / Envoy)
                                           │
                      ┌────────────────────┴────────────────────┐
                      ▼                                         ▼
            [ FastAPI Worker 1 ]                      [ FastAPI Worker 2 ]
          (Gunicorn + UvicornWorker)                (Gunicorn + UvicornWorker)
                      │                                         │
        ┌─────────────┼─────────────────────────────────────────┼─────────────┐
        ▼             ▼                                         ▼             ▼
   [ Auth / RBAC ] [ Rate Limiter ]                       [ Request Tracing ] [ CORS & Compress ]
        │             │                                         │             │
        └─────────────┴────────────────────┬────────────────────┴─────────────┘
                                           │
                                  [ API Routers v1 ]
             (Auth, SuperAdmin, Products, Orders, Customers, Coupons, Analytics)
                                           │
                                  [ Service Layer ]
           (Business Logic, State Machine, Discount Engine, Audit Event Dispatch)
                                           │
                                 [ Repository Layer ]
          (Motor Async Driver, Aggregations, Projections, Atomic Updates)
                                           │
                      ┌────────────────────┴────────────────────┐
                      ▼                                         ▼
          [ MongoDB Replica Set ]                         [ Redis Cache ]
    (Compound Indexes, Sharding-ready)              (Session store & Stats cache)
```

### Architectural Pillars:
1. **Asynchronous Non-Blocking I/O**:
   - End-to-end async/await pipeline using `FastAPI` and `Motor` (official async MongoDB driver).
   - Minimized latency via connection pooling (`minPoolSize=10`, `maxPoolSize=100`, `maxIdleTimeMS=45000`).
2. **Layered Separation of Concerns**:
   - `api/`: Route definitions, request parsing, response formatting, status codes.
   - `services/`: Domain business logic, state machines, validation rules.
   - `repositories/`: Database queries, aggregation pipelines, projections, index hints.
   - `models/` & `schemas/`: Pydantic V2 models for strict type safety and serialization.
   - `core/`: Config (`pydantic-settings`), Security (JWT + bcrypt), Database lifecycle, Exceptions.
3. **Database Optimization & Indexes**:
   - Text indexing on product titles, descriptions, and SKUs.
   - Compound indexes on orders (`status`, `created_at`), products (`category_id`, `status`), audit logs (`actor_id`, `created_at`).
   - Lean query projections excluding heavy fields when listing entities.
4. **Security & Auditing**:
   - JWT tokens with short expiry (e.g. 15-30m) + Refresh tokens.
   - Cryptographic password hashing with bcrypt (cost factor 12).
   - Declarative permission dependency injection (`require_permissions("products:write")`).
   - Automatic audit logging middleware / hook.

---

## 4. Permission Matrix

| Resource | Scope | SuperAdmin | Admin | Catalog Mgr | Order Mgr | Support | Finance |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| Admins | `admins:read` / `write` / `delete` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Audit Logs | `audit:read` | ✅ | ✅ (view) | ❌ | ❌ | ❌ | ❌ |
| Store Settings| `settings:read` / `write` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Products | `products:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Products | `products:write` / `delete` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Inventory | `inventory:read` / `write` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Orders | `orders:read` | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ |
| Orders | `orders:write` / `status` | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| Orders | `orders:refund` | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ |
| Customers | `customers:read` | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ |
| Customers | `customers:write` / `ban` | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ |
| Coupons | `coupons:read` / `write` | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| Analytics | `analytics:read` | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ |

---

## 5. Implementation Roadmap & Milestones

- [x] **Milestone 1: Architecture & Technical Design (Roadmap & Specifications)**
- [x] **Milestone 2: Core Infrastructure & Configuration**
  - Project structure setup.
  - Configuration management via `pydantic-settings` (.env support).
  - MongoDB async client lifecycle management & connection pool configuration.
  - Index bootstrap service (ensures indexes on startup).
  - Centralized error handling, standardized JSON error responses, and logging.
  - Maintenance mode enforcement middleware (blocks non-SuperAdmins with 503).
- [x] **Milestone 3: Authentication, Security & RBAC Engine**
  - Password hashing (bcrypt cost 12), JWT access & refresh token generation/validation.
  - Granular permission decorator & dependency injection (`get_current_admin`, `require_permissions`, `require_superadmin`).
  - Active session revocation & token versioning (`token_version` tracking).
  - Initial SuperAdmin auto-seeding on first startup.
- [x] **Milestone 4: SuperAdmin Module**
  - Admin management CRUD (create admin, change roles/permissions, activate/deactivate, delete).
  - Force password resets & instant token revocation.
  - System Audit Log engine, querying, and CSV compliance export endpoint (`/superadmin/audit-logs/export`).
  - Store configuration endpoints (store profile, currency, tax rates, shipping methods).
- [x] **Milestone 5: Product & Catalog Management Module**
  - Categories (hierarchical parent-child support, slugs, ordering, delete protection).
  - Brands management (slug uniqueness, website, active toggles).
  - Products with variants, dynamic attributes, SKUs, pricing, stock levels.
  - Fast pagination, filtering, price range facets, and text search.
  - Bulk product status updating.
- [x] **Milestone 6: Inventory & Stock Movement Module**
  - Atomic stock adjustment records (reasons, references, delta changes).
  - Protection against reducing stock below zero.
  - Real-time low stock detection and alert lists.
- [x] **Milestone 7: Order Management & State Machine Module**
  - Order creation for manual/phone staff provisioning (`POST /api/v1/orders`).
  - Order listing with filters (status, payment status, customer, date range, amounts).
  - Order details with line items, tax, shipping, and discounts.
  - Strict order status transitions (prevents illegal state jumps).
  - Fulfillment tracking updates and refund processing with automatic inventory restock.
  - Order cancellation with automatic inventory restock (`POST /api/v1/orders/{id}/cancel`).
  - Internal staff notes with author tracking.
- [x] **Milestone 8: Customer Moderation & CRM Module**
  - Customer directory with calculated metrics (orders count, total spend, LTV).
  - Customer CRUD (`POST`, `GET`, `PUT`, `DELETE` with order history delete protection).
  - Customer status moderation (ACTIVE, SUSPENDED, FLAGGED).
  - Customer internal notes with author tagging.
- [x] **Milestone 9: Discounts, Coupons & Promotions Module**
  - Coupon CRUD (percentage, fixed amount, free shipping).
  - Comprehensive Coupon Validation & Cart Calculation Engine (`POST /api/v1/coupons/validate`): min spend, date windows, overall usage caps, per-customer limits, category/product scope.
  - Promotion performance tracking and statistics (`GET /api/v1/coupons/{id}/stats`).
- [x] **Milestone 10: Analytics & Reporting Aggregation Engine**
  - MongoDB aggregation pipelines for revenue, order trends, AOV, top products.
  - Executive dashboard summary stats endpoint (`GET /api/v1/analytics/dashboard`).
- [x] **Milestone 11: Production Readiness, Tests & Documentation**
  - Comprehensive Pytest test suite (29 tests across all domains, 100% passing).
  - Dockerfile and `docker-compose.yml` (FastAPI + MongoDB + Mongo Express).
  - Seed CLI script for demo data & SuperAdmin provisioning (`python -m app.utils.seed`).
  - Comprehensive API Documentation (OpenAPI / Swagger at `/docs`).
