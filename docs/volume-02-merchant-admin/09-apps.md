# 2.9 Apps

## Purpose
Extend CommerceOS via first-party and third-party apps — the marketplace/ecosystem layer that lets merchants add functionality without core platform changes, mirroring Shopify's App Store as a key competitive surface.

## Navigation
Sidebar `Apps`. Sub-tabs: Installed Apps, App Store (browse/search), Custom Apps (private, store-specific integrations), Developer settings (API keys, webhooks — cross-links Volume 15).

## User roles
Owner: full access incl. install/uninstall/billing approval for paid apps. Manager: install/configure free apps, cannot approve paid app billing. Staff: view installed apps relevant to their permitted modules only.

## Permissions
`apps.view`, `apps.install`, `apps.uninstall`, `apps.approve_billing`, `apps.manage_api_keys`, `apps.manage_webhooks`.

## Fields
App: name, developer, category, pricing model (free/paid/usage-based), permissions requested (scopes), rating/reviews, install count. Installed app: status (Active/Needs attention/Suspended), granted scopes, install date, billing (if paid).

## Buttons
Install, Uninstall, Configure, Approve billing, Revoke access, Regenerate API key, Create custom app, Add webhook.

## Tables
App Store grid/list: icon, name, developer, category, rating, pricing. Installed Apps list: icon, name, status, scopes summary, last active.

## Filters
Category, pricing model, rating, "built by CommerceOS" (first-party) vs. third-party.

## Search
App name, category, developer name.

## Bulk actions
None typical for install (deliberate one-at-a-time review of permissions); bulk-revoke for security incident response (Owner-only, emergency action).

## Workflows
1. Browse App Store → select app → review requested scopes (e.g., `read_orders, write_discounts`) → approve → OAuth-style install → app appears in Installed Apps, gains scoped API access.
2. Paid app install → billing approval screen (price, billing cycle) → Owner approves → charge added to CommerceOS invoice (or app's own billing, depending on model) → activated.
3. Uninstall → scopes revoked immediately, app's webhooks disabled, any app-created data (e.g., custom fields) either retained or purged per the app's uninstall policy (disclosed at install time).
4. Custom app: merchant/developer creates a private app scoped to their own store → generates API credentials → used for bespoke integrations without App Store review.

## Business rules
- An app can only access the scopes it was explicitly granted at install; scope changes on app update require re-approval (no silent privilege escalation).
- Uninstalling an app does not retroactively undo actions it already performed (e.g., discounts it created remain unless the merchant removes them).
- Paid app charges flow through CommerceOS billing and appear on the merchant's CommerceOS invoice, with CommerceOS taking a platform revenue share (business model — Vol 1.4).

## Validation
Custom app requires a name and at least one requested scope; webhook URL must be HTTPS and pass a verification handshake before activation.

## Notifications
App requesting new scopes on update (requires re-approval), app billing charge upcoming, app flagged/suspended by platform review, webhook delivery failures exceeding threshold.

## Audit logs
`app.installed/uninstalled/scopes_changed`, `app.billing_approved`, `api_key.created/revoked`, `webhook.created/deleted`.

## Database schema
```
apps(id, name, developer_id, category, pricing_model, scopes_available jsonb,
     status[listed|unlisted|suspended], created_at)
store_app_installs(id, store_id, app_id, granted_scopes jsonb, status,
                    installed_at, uninstalled_at)
store_app_billing(id, install_id, plan, amount, cycle, status)
api_keys(id, store_id, app_id null, key_hash, scopes jsonb, created_at, revoked_at)
webhooks(id, store_id, app_id null, topic, target_url, status, created_at)
```

## APIs
`GET /api/v1/apps` (store listing), `POST /api/v1/apps/{id}/install`, `DELETE /api/v1/apps/{id}/uninstall`, `GET /api/v1/apps/installed`, `POST /api/v1/api-keys`, `DELETE /api/v1/api-keys/{id}`, `POST /api/v1/webhooks`. (This is the Admin-side management surface; the public developer-facing API is documented fully in Volume 15.)

## Events
`app.installed`, `app.uninstalled`, `app.scope_changed`, `app.billing_charged`, `webhook.delivery_failed` — consumed by Settings (permission surface), Finance (billing).

## Edge cases
App requests a scope the installing user's own role doesn't have (block — can't grant more than you hold); app removed from App Store while still installed on a store (grandfathered but flagged, no new installs); two apps with conflicting webhook subscriptions on the same topic (both fire independently, no conflict by design — apps are isolated).

## Error handling
Webhook delivery failure → retried with exponential backoff up to a cap, then marked failed and surfaced to the merchant with a "reconnect app" prompt; app OAuth install flow interrupted → no partial-scope grant left behind (transactional).

## Performance
App Store listing cached/CDN-served (mostly-static catalog data); scope checks on every API request must be low-latency (<5ms) since they gate all app API traffic.

## Security
Scopes are the sole access boundary for third-party code — reviewed rigorously in App Store submission (Volume 15/20 testing); API keys shown once at creation, stored hashed; webhook payloads signed (HMAC) so receivers can verify authenticity.

## AI opportunities
AI-recommended apps based on store profile/gaps ("stores like yours use X for returns"); anomaly detection on app API usage (sudden spike suggesting compromised key); AI-assisted custom app scaffolding.

## UX improvements
Scope explanations in plain language (not just technical scope names) at install time; sandbox/test mode for custom apps before going live; visual dependency map of which apps touch which data.

## Estimated scope
~6 sub-views, ~9 API endpoints, 5 DB tables, ~30 functional requirements.
