# 2.8 Finance

## Purpose
Merchant-facing view into money movement: payouts, transaction ledger, tax collected, and reconciliation — the Admin surface on top of the deeper Finance/ERP engine in Volumes 11–12.

## Navigation
Sidebar `Finance`. Sub-tabs: Overview (balance, next payout), Payouts, Transactions, Taxes, Billing (CommerceOS subscription/fees — distinct from merchant's own payouts).

## User roles
Owner: full access incl. bank account management. Finance: full access, cannot change payout bank account (Owner-only, step-up auth required). Manager/Staff: no access by default.

## Permissions
`finance.view`, `finance.view_payouts`, `finance.manage_payout_account` (Owner-only), `finance.view_tax`, `finance.export`.

## Fields
Available balance, pending balance, next payout date/amount, payout account (masked), transaction: type (charge/refund/fee/adjustment/payout), amount, currency, related order, date, status. Tax: jurisdiction, collected amount, filing period, remittance status.

## Buttons
Request payout now (if instant payout enabled), Add/change payout account, Export transactions, Export tax report, View transaction detail, Download invoice (CommerceOS billing).

## Tables
Transactions ledger: date, type, order #, gross, fee, net, status. Payouts list: date, amount, status (In transit/Paid/Failed), covering-period, transaction count.

## Filters
Date range, transaction type, status, currency (if multi-currency).

## Search
Order number, payout ID, transaction ID.

## Bulk actions
Bulk export (transactions/tax), none for mutation (financial records are not bulk-editable by design).

## Workflows
1. Order paid → processing fee deducted → net amount accrues to pending balance → moves to available balance per gateway's holding period → included in next scheduled payout.
2. Payout initiated (scheduled or manual) → funds sent to bank account → status tracked (In transit → Paid) → downloadable payout report ties back to underlying transactions.
3. Tax period closes → Tax report generated summarizing collected tax by jurisdiction → merchant remits via their own filing process (CommerceOS does not auto-file in v1) → remittance status manually marked or synced via tax-provider integration (e.g., Avalara).

## Business rules
- Payout account changes require step-up authentication (re-enter password/2FA) and trigger a hold period (e.g., 24–72h) before the new account becomes active, to prevent fraud via account takeover.
- Negative balance (e.g., refunds exceeding recent sales) is carried forward and deducted from the next payout rather than requiring immediate merchant payment, up to a configurable negative-balance ceiling.
- Every transaction row is immutable once created; corrections are made via new adjustment entries, never by editing history (accounting integrity).

## Validation
Payout account must pass bank account validation (routing/account number format, micro-deposit or instant verification) before activation. Manual payout request cannot exceed available balance.

## Notifications
Payout sent/paid/failed, payout account change requested (security alert to Owner via email, separate from in-app), negative balance warning, tax filing period closing reminder.

## Audit logs
`payout_account.changed` (high-sensitivity, always logged with IP/device), `payout.requested`, `transaction.adjusted`, `tax_report.exported`.

## Database schema
```
ledger_transactions(id, store_id, type, order_id null, amount, fee, net, currency,
                     status, created_at)
payouts(id, store_id, amount, currency, status, bank_account_id, period_start,
        period_end, initiated_at, paid_at)
payout_bank_accounts(id, store_id, masked_account_number, routing_number_ref,
                      status, verified_at, created_at)
tax_collected(id, store_id, jurisdiction, period_start, period_end, amount,
              remittance_status)
```
Sensitive bank details are tokenized via a PCI-scope payment/banking provider; CommerceOS stores only references, never raw account numbers (see Security).

## APIs
`GET /api/v1/finance/balance`, `GET /api/v1/finance/transactions`, `GET/POST /api/v1/finance/payouts`, `POST /api/v1/finance/payout-account`, `GET /api/v1/finance/tax-report`.

## Events
`payout.initiated`, `payout.paid`, `payout.failed`, `transaction.recorded`, `tax_period.closed` — consumed by Dashboard (Net Profit), ERP (Vol 11), Analytics.

## Edge cases
Payout fails after being marked "In transit" (bank rejection) — must reverse and retry, clearly communicated; multi-currency stores with per-currency balances and payout schedules; chargeback/dispute creating a negative adjustment after a payout already occurred (net against future payout); store closure with a pending negative balance (collections workflow, out of Admin UI scope).

## Error handling
Payout provider API failure → payout stays queued, retried, merchant sees "processing" not a false failure state; tax report generation failure → retry + fallback to raw transaction export.

## Performance
Transaction ledger paginated/indexed by date; balance calculation served from a maintained running-balance cache updated transactionally, not summed from full history on every page load.

## Security
Bank account numbers never stored in plaintext/tokenized only via PCI-compliant vault; all Finance pages require re-auth if session is older than a configurable threshold (step-up for sensitive views); full audit trail immutable (append-only).

## AI opportunities
Cash-flow forecasting (predicted next payout, predicted month-end balance); anomaly detection on transactions (unusual fee, unexpected chargeback spike); AI-drafted tax filing summary highlighting what changed vs. last period.

## UX improvements
Visual payout calendar; one-click reconciliation matching payouts to bank statement lines (via Plaid-style bank connection); downloadable accountant-ready package (P&L-adjacent export).

## Estimated scope
~5 sub-views, ~7 API endpoints, 4 DB tables, ~30 functional requirements.
