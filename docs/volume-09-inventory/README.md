# Volume 9 — Inventory

Status: ⬜ Not started (skeleton).

Stock-level source of truth across all locations/channels — referenced by Products (Vol 2.3), OMS (Vol 7), WMS (Vol 8), and the Dashboard's Inventory Alerts widget (Vol 2.1).

## Planned modules/pages
- Stock levels by location (on-hand, reserved, available-to-sell, incoming)
- Inventory adjustments (manual counts, damage, shrinkage — audited)
- Transfers between locations
- Reorder points & purchase order suggestions
- Demand forecasting (ties to AI Platform Vol 13)
- Multi-channel inventory sync (prevent overselling across storefront/POS/marketplace)
- Backorder & preorder handling

## Dependencies
Products (Vol 2.3) for the SKU/variant dimension, WMS (Vol 8) for physical counts, OMS (Vol 7) for reservation/allocation consumption, AI Platform (Vol 13) for forecasting.

## Next steps
Document the reservation model (on-hand vs. available-to-sell vs. reserved) precisely first — overselling prevention depends on getting this state machine right across every consuming volume.
