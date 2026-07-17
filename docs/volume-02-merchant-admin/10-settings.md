# 2.10 Settings

## Purpose
Store-wide configuration: general info, users/roles/permissions, domains, checkout behavior, shipping/tax defaults, and notification templates — the control room underlying every other module's behavior.

## Navigation
Sidebar `Settings` (bottom of sidebar, separate from primary nav). Sub-sections: General, Users & Permissions, Billing (CommerceOS subscription), Domains, Checkout, Shipping & Delivery, Taxes, Notifications (templates), Locations, Legal/Policies.

## User roles
Owner: full access to every setting including billing/domain/role-management. Manager: most settings except billing and Owner-role reassignment. Staff: no access by default (occasionally granted narrow settings like Notifications templates for Marketing role).

## Permissions
`settings.view`, `settings.edit_general`, `settings.manage_users`, `settings.manage_billing` (Owner-only), `settings.manage_domains`, `settings.edit_checkout`, `settings.edit_shipping_tax`, `settings.manage_locations`.

## Fields
General: store name, legal name, address, currency, timezone, order ID format. Users: name, email, role, status (Active/Invited/Suspended), 2FA status. Domains: primary domain, redirects, SSL status. Checkout: guest checkout toggle, required fields, abandoned checkout recovery, terms-acceptance requirement. Shipping: zones, rates, carriers connected. Taxes: tax-inclusive/exclusive pricing, nexus/jurisdictions, tax provider integration.

## Buttons
Save, Invite user, Suspend/Reactivate user, Change role, Add domain, Verify domain, Connect carrier, Connect tax provider, Add location, Export settings (for backup/migration).

## Tables
Users list: name, email, role, status, last login. Domains list: domain, type (primary/redirect), SSL status. Locations list: name, address, fulfills-online-orders (yes/no), is-retail (yes/no).

## Filters
Users: role, status. Locations: type.

## Search
User name/email; setting search (⌘K-style "find a setting" within Settings itself).

## Bulk actions
Bulk-invite users (CSV), bulk role reassignment (rare, Owner-only, heavily audited).

## Workflows
1. Owner invites staff → email invite → staff accepts, sets password/2FA → role determines module access thereafter (governs every other volume's permission checks).
2. Custom role creation: Owner defines a named role with per-module permission matrix (view/create/edit/delete per module) → assignable to future users.
3. Domain connection: merchant adds custom domain → DNS verification (TXT/CNAME) → SSL auto-provisioned → domain goes live, old domain auto-redirects.
4. Tax provider connection (e.g., Avalara/TaxJar) → nexus configuration synced → tax calculation at checkout delegates to provider instead of static rate tables.

## Business rules
- There must always be ≥1 Owner; the last Owner cannot demote themselves or be removed until another Owner is designated.
- Role permission changes take effect immediately for that user's active session (not just next login) — enforced via permission re-check on each request, not cached client-side only.
- Suspending a user immediately revokes all active sessions and API keys tied to that user.
- Checkout setting changes (e.g., disabling guest checkout) apply prospectively only — do not affect orders already in progress.

## Validation
Custom domain must pass DNS verification before activation; user invite requires valid email, cannot invite an email already active on the store; tax nexus requires valid jurisdiction codes.

## Notifications
User invited/accepted, role changed (to the affected user, security-relevant), domain SSL provisioning complete/failed, domain expiring soon, tax provider sync failure.

## Audit logs
`user.invited/role_changed/suspended/removed` (high sensitivity, always logged), `settings.checkout_changed`, `settings.tax_changed`, `domain.added/removed`, `role.created/permissions_changed`.

## Database schema
```
stores(id, name, legal_name, currency, timezone, order_number_format, created_at)
users(id, email, name, status, created_at)
store_users(store_id, user_id, role_id, invited_at, joined_at, status)
roles(id, store_id null, name, is_system_role, permissions jsonb)  -- store_id null = system default roles
domains(id, store_id, domain, type, ssl_status, verified_at)
locations(id, store_id, name, address, fulfills_online, is_retail)
checkout_settings(store_id PK, guest_checkout_enabled, required_fields jsonb,
                   terms_required, abandoned_recovery_enabled)
tax_settings(store_id PK, pricing_mode[inclusive|exclusive], provider, nexus jsonb)
```

## APIs
`GET/PATCH /api/v1/settings/general`, `GET/POST /api/v1/settings/users`, `PATCH /api/v1/settings/users/{id}`, `GET/POST /api/v1/settings/roles`, `GET/POST /api/v1/settings/domains`, `GET/PATCH /api/v1/settings/checkout`, `GET/PATCH /api/v1/settings/tax`.

## Events
`user.role_changed`, `user.suspended`, `domain.verified`, `checkout_settings.changed`, `tax_settings.changed` — consumed platform-wide since these gate permission checks everywhere else.

## Edge cases
Role permission matrix changed while a user is mid-action (e.g., editing a product) — in-flight save is validated against permissions at save-time, not just page-load-time; domain DNS verification stuck (TTL delays) — clear "pending, may take up to 48h" messaging instead of implying failure; last-Owner-leaving edge case (blocked with explicit error, not silent no-op).

## Error handling
Domain SSL provisioning failure → automatic retry + clear remediation steps (DNS record examples) shown inline; tax provider connection failure → checkout falls back to last-known static rates rather than failing checkout entirely, with a merchant alert.

## Performance
Permission checks (role → module → action) must be cached in-memory per-request but invalidated instantly platform-wide on role change (pub/sub invalidation, not TTL-only).

## Security
This is the highest-sensitivity module in Merchant Admin: all user/role/domain/billing changes require step-up auth; permission matrix changes are the most heavily audited event type in the system; API keys and OAuth app scopes (Vol 2.9) are enforced against the same underlying role/permission engine defined here.

## AI opportunities
AI-suggested role setups for common team structures ("set up roles for a 5-person team"); anomaly detection on permission changes (unusual escalation pattern); AI-assisted DNS troubleshooting for domain setup.

## UX improvements
Visual permission matrix editor (grid of modules × actions) instead of raw JSON; settings search that jumps directly to the relevant field; guided setup checklist for new stores.

## Estimated scope
~10 sub-views, ~14 API endpoints, 8 DB tables, ~45 functional requirements.
