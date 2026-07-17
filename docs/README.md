# CommerceOS Master Documentation

CommerceOS is an AI-first commerce platform designed to compete with and surpass Shopify, with future integration support for WooCommerce, Magento, BigCommerce, Amazon, Etsy, and more.

This directory is the complete product blueprint: ~20 volumes covering every module from first line of code through production deployment. Each page-level spec documents: Purpose, Navigation, User Roles, Permissions, Fields, Buttons, Tables, Filters, Search, Bulk Actions, Workflows, Business Rules, Validation, Notifications, Audit Logs, Database Schema, APIs, Events, Edge Cases, Error Handling, Performance, Security, AI Opportunities, UX Improvements.

## Status legend
- ✅ Full depth — every page documented against the full template
- 🚧 Skeleton — structure and scope defined, detailed content pending
- ⬜ Not started

## Volumes

| # | Volume | Status | Notes |
|---|--------|--------|-------|
| 1 | [Foundation](./volume-01-foundation/README.md) | 🚧 Skeleton | Vision, BRD, PRD, Business Model, Personas, Market & Competitor Research |
| 2 | [Merchant Admin](./volume-02-merchant-admin/README.md) | ✅ Full depth | Dashboard, Orders, Products, Customers, Marketing, Discounts, Analytics, Finance, Apps, Settings, Markets, Content, B2B — matches the implemented UI in `/web` |
| 3 | Storefront | ⬜ Not started | Customer-facing themed storefront, PDP/PLP/cart/checkout |
| 4 | Customer Portal | ⬜ Not started | Order history, account, returns, loyalty |
| 5 | Vendor Portal | ⬜ Not started | Multi-vendor marketplace seller console |
| 6 | Marketplace | ⬜ Not started | Multi-vendor marketplace core (listings, commissions, payouts) |
| 7 | OMS (Order Management) | ⬜ Not started | Order lifecycle, fulfillment orchestration, returns/RMA |
| 8 | WMS (Warehouse) | ⬜ Not started | Bin/pick/pack/ship, warehouse ops |
| 9 | Inventory | ⬜ Not started | Stock, reservations, transfers, forecasting |
| 10 | CRM | ⬜ Not started | Customer 360, segmentation, support |
| 11 | ERP | ⬜ Not started | Procurement, suppliers, accounting integration |
| 12 | Finance | ⬜ Not started | Payments, ledger, tax, payouts, reconciliation |
| 13 | AI Platform | ⬜ Not started | Forecasting, recommendations, copilots, agentic workflows |
| 14 | Automation Engine | ⬜ Not started | Rules, triggers, workflow builder |
| 15 | APIs | ⬜ Not started | REST/GraphQL/webhooks, public API surface |
| 16 | Database | ⬜ Not started | Schema, ERDs, partitioning, multi-tenancy |
| 17 | Microservices | ⬜ Not started | Service boundaries, messaging, deployment topology |
| 18 | UI Design System | ⬜ Not started | Tokens, components, patterns (the `/web` app is the first implementation) |
| 19 | DevOps | ⬜ Not started | CI/CD, environments, observability, IaC |
| 20 | Testing | ⬜ Not started | Test strategy, QA, coverage, release gates |

## Estimated scope (target)
- 50+ modules · 500+ screens · 2,000+ functional requirements
- 300+ database tables/entities · 800+ APIs · 500+ workflows

## Reference implementation

`/web` contains a working Next.js implementation of the **Volume 2 → Dashboard** page, built to match the approved visual reference. It is the pattern other Merchant Admin pages should follow as they move from spec to code.
