# 2.7 Analytics

## Purpose
Deeper, customizable reporting beyond the Dashboard's fixed widgets — standard report library, custom report builder, and scheduled exports, for merchants who need to go past the at-a-glance view.

## Navigation
Sidebar `Analytics`. Sub-tabs: Overview, Reports (library), Custom Reports, Live View (real-time visitors), Exports.

## User roles
Owner/Manager: full access. Finance: full access to financial reports, restricted from marketing-spend detail if desired. Marketing: marketing/traffic reports. Staff: none by default (opt-in permission).

## Permissions
`analytics.view`, `analytics.view_financial` (margin/cost-sensitive reports), `analytics.create_custom_report`, `analytics.export`, `analytics.schedule_report`.

## Fields
Report: name, type (Sales/Traffic/Products/Customers/Marketing/Finance), dimensions, metrics, date range, comparison period, filters, visualization type (table/line/bar/pie), schedule (frequency, recipients, format).

## Buttons
New custom report, Save report, Duplicate, Schedule, Export (CSV/PDF/XLSX), Share (internal link), Pin to Dashboard.

## Tables
Standard reports rendered as sortable/filterable tables with inline charts; report library list: name, type, owner, last run, scheduled (yes/no).

## Filters
Date range + comparison period, channel, product/collection, customer segment, location — availability depends on report type.

## Search
Report name/description within the library.

## Bulk actions
Bulk delete custom reports, bulk export selected reports.

## Workflows
1. Select a standard report (e.g., "Sales by product") → adjust date range/filters → view → export or schedule.
2. Build custom report → pick dimensions + metrics from the semantic layer → preview → save to library → optionally pin key metric to Dashboard.
3. Scheduled report runs (e.g., weekly Monday 8am) → generates PDF/CSV → emails to configured recipients automatically.

## Business rules
- Financial reports (margin, COGS, net profit) require `analytics.view_financial`; the underlying query still executes with row-level cost visibility applied even if a broader report is shared with a non-financial role (redaction happens at the data layer, not the UI).
- Custom report dimension/metric combinations are validated against a semantic model to prevent invalid joins (e.g., can't cross marketing spend with warehouse pick-time without a defined relationship).
- Data freshness: real-time metrics (Live View) vs. rollup-based standard reports (updated hourly) are explicitly labeled so merchants don't mistake staleness for a bug.

## Validation
Custom report requires ≥1 metric; date range required; scheduled report requires ≥1 valid recipient email.

## Notifications
Scheduled report delivered, scheduled report failed to generate, anomaly detected in a pinned metric (see AI opportunities).

## Audit logs
`report.created/edited/deleted/exported/scheduled`, `report.shared` (with whom).

## Database schema
```
analytics_reports(id, store_id, name, type, definition jsonb, owner_id, created_at, updated_at)
analytics_report_schedules(id, report_id, frequency, recipients jsonb, format, next_run_at)
analytics_report_runs(id, report_id, status, started_at, completed_at, output_url)
```
Underlying query engine reads from rollup tables (`analytics_daily_rollup` — Vol 2.1, plus product/customer/marketing rollups) rather than OLTP tables directly, to keep reporting from impacting transactional performance.

## APIs
`GET /api/v1/analytics/reports` (standard + custom library), `POST /api/v1/analytics/reports` (create custom), `POST /api/v1/analytics/reports/{id}/run`, `POST /api/v1/analytics/reports/{id}/schedule`, `GET /api/v1/analytics/live-view`.

## Events
`report.scheduled_run_completed`, `report.scheduled_run_failed`, `analytics.anomaly_detected`.

## Edge cases
Report spanning a period before the store existed (empty state, not error); comparison period with different day-count (e.g., comparing a 31-day month to a 28-day month) — normalize or clearly label as non-like-for-like; extremely large custom report result sets (pagination/streaming export rather than in-memory generation).

## Error handling
Scheduled report generation failure → retried once, then merchant notified with the option to run manually; custom report with an invalid/broken definition (e.g., referencing a deleted custom metric) flagged in the library with a "needs attention" badge rather than silently failing on next scheduled run.

## Performance
All standard/custom reports query pre-aggregated rollups, target p95 < 2s even for year-long ranges; exports >50MB generated async with download-when-ready notification.

## Security
Financial report access enforced server-side; exported files link-expire and are access-logged; shared internal report links respect the recipient's own permission level (not the creator's) when viewed.

## AI opportunities
Natural-language report building ("show me margin by category last quarter"); automatic anomaly detection with root-cause suggestions; AI-written executive summary atop any report; forecasting overlays on trend reports.

## UX improvements
Drag-and-drop custom report builder; report templates gallery; inline annotation on charts (mark "ran a promo here"); comparison mode toggle (period-over-period, YoY).

## Estimated scope
~6 sub-views, ~7 API endpoints, 3 DB tables, ~30 functional requirements.
