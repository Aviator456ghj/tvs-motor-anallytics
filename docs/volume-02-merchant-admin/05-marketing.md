# 2.5 Marketing

## Purpose
Plan, launch, and measure campaigns across email, SMS, and paid ad channels (Facebook/Google) directly from Admin, with performance rolled up to the Dashboard's Marketing Performance widget.

## Navigation
Sidebar `Marketing`. Sub-tabs: Campaigns, Automations (welcome series, abandoned cart — cross-links Volume 14), Audiences/Segments (shared with Customers Vol 2.4), Ad Channels (connected accounts), Templates.

## User roles
Owner/Manager: full access + budget approval. Marketing: full campaign CRUD, cannot change store-level ad account billing. Support/Finance: read-only.

## Permissions
`marketing.view`, `marketing.create_campaign`, `marketing.send`, `marketing.manage_automations`, `marketing.manage_ad_accounts`, `marketing.view_spend` (separate from general view, since budget is sensitive).

## Fields
Campaign name, type (Email/SMS/Ad), status (Draft/Scheduled/Sending/Sent/Active/Paused), audience/segment, subject line + content (email), message body (SMS, char-count/segment indicator), send time (immediate/scheduled), budget + bid strategy (ads), UTM parameters, A/B test variants.

## Buttons
Create campaign, Duplicate, Schedule, Send test, Send now, Pause/Resume (ads), Archive, Connect channel (OAuth to Facebook/Google), Import template, Preview (desktop/mobile).

## Tables
Campaign list: name, type/channel icon, status, audience size, send date, key metric (open rate/click rate/ROAS depending on type), performance sparkline.

## Filters
Channel, status, date range, audience/segment.

## Search
Campaign name.

## Bulk actions
Bulk archive, bulk pause (ads), bulk export performance data.

## Workflows
1. Create campaign → select audience (static list or dynamic segment from Vol 2.4) → build content (or AI-draft) → send test → schedule/send.
2. Connect ad account (OAuth) → sync existing campaigns read-only, or create new campaigns pushed to the platform via API.
3. Automation trigger (e.g., abandoned cart) configured once, runs continuously — see Volume 14 for the rule engine itself; this page is the marketing-specific UI on top of it.

## Business rules
- Cannot send to a segment with 0 marketing-consented members; system blocks send and shows the consent gap.
- SMS campaigns require the recipient to have explicit SMS consent, separate from email consent (per TCPA/regional law).
- Ad spend requires a connected, verified billing method on the ad platform — CommerceOS never holds ad budget itself, it orchestrates the connected account.
- A/B test winner auto-selection (if enabled) requires a minimum sample size before declaring a winner.

## Validation
Subject line required for email; SMS body ≤ configured max segments (warn beyond 1 segment due to cost); scheduled send time must be in the future; budget must be > 0 for ad campaigns.

## Notifications
Campaign sent confirmation with initial metrics, scheduled campaign reminder, ad account disconnected/token-expired alert, budget threshold reached alert, A/B test winner declared.

## Audit logs
`campaign.created/edited/sent/paused/deleted`, `ad_account.connected/disconnected`, `automation.enabled/disabled`.

## Database schema
```
marketing_campaigns(id, store_id, name, type, channel, status, segment_id,
                     content jsonb, scheduled_at, sent_at, created_by, created_at)
campaign_recipients(id, campaign_id, customer_id, status[queued|sent|delivered|opened|clicked|bounced|failed])
campaign_metrics_rollup(campaign_id, sent, delivered, opened, clicked, unsubscribed,
                         revenue_attributed, spend, roas, updated_at)
connected_ad_accounts(id, store_id, platform, external_account_id, access_token_ref,
                       status, connected_at)
```

## APIs
`GET/POST /api/v1/marketing/campaigns`, `GET/PATCH/DELETE /api/v1/marketing/campaigns/{id}`, `POST /api/v1/marketing/campaigns/{id}/send`, `POST /api/v1/marketing/ad-accounts/connect`, `GET /api/v1/marketing/campaigns/{id}/metrics`. Webhooks (inbound from ad platforms): spend/performance sync.

## Events
`campaign.sent`, `campaign.metrics_updated`, `ad_account.connected`, `automation.triggered` — consumed by Dashboard Marketing Performance widget, Analytics.

## Edge cases
Ad platform API outage during sync (show stale-data banner with last-synced timestamp); segment shrinks to 0 between creation and scheduled send (block send, alert creator); customer unsubscribes mid-campaign-send (must not receive remaining sends, checked at send-time not just campaign-creation-time).

## Error handling
Partial send failures (some recipients bounce/fail) tracked per-recipient, not campaign-wide failure; retriable failures (transient SMTP error) auto-retried with backoff; permanent failures (invalid email) surfaced in a bounce report.

## Performance
Large-segment sends (>100k) processed via queued batch jobs with rate limiting to respect ESP/SMS provider limits; metrics rollup updated asynchronously, not computed live per page view.

## Security
Ad platform OAuth tokens stored encrypted, never exposed to frontend; unsubscribe/consent state checked server-side at send time as the final gate regardless of what the segment definition says at creation time.

## AI opportunities
AI-drafted subject lines/content with predicted performance; send-time optimization per recipient (send when they're most likely to open); auto-generated audience suggestions; anomaly alerts on underperforming live ad campaigns with suggested budget reallocation.

## UX improvements
Visual campaign calendar view; side-by-side A/B variant comparison; template library with drag-and-drop editor; one-click "duplicate last month's winning campaign."

## Estimated scope
~8 sub-views, ~8 API endpoints, 4 DB tables, ~30 functional requirements.
