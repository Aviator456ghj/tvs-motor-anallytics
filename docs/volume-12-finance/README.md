# Volume 12 — Finance (Platform Engine)

Status: ⬜ Not started (skeleton).

The deep financial engine underlying Merchant Admin's Finance page (Vol 2.8): payment processing orchestration, double-entry ledger, multi-party settlement (marketplace splits, Vol 6), and tax calculation — Vol 2.8 is the merchant-facing view; this volume is the system of record.

## Planned modules/pages
- Payment gateway orchestration (multi-processor routing, retries, 3DS)
- Double-entry ledger (the authoritative accounting core beneath `ledger_transactions` in Vol 2.8)
- Tax calculation engine (rate determination, nexus rules, provider integration)
- Multi-party settlement & split payouts (marketplace commissions, Vol 6)
- Chargebacks & dispute management
- Currency conversion & multi-currency settlement
- Fraud/risk scoring integration

## Dependencies
Orders (Vol 2.2/7) as the primary transaction source, Markets (Vol 2.11) for currency, Marketplace (Vol 6) for split-payment rules, ERP (Vol 11) for accounting sync.

## Next steps
Document the double-entry ledger schema and payment-state machine first — everything else in this volume and in Vol 2.8 depends on getting that foundation right.
