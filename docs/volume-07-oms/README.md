# Volume 7 — OMS (Order Management)

Status: ⬜ Not started (skeleton).

The order lifecycle engine underlying Merchant Admin's Orders page (Vol 2.2): orchestration across payment, inventory allocation, fulfillment routing, and returns — the "backend" to Volume 2.2's "frontend."

## Planned modules/pages
- Order orchestration state machine (created → paid → allocated → fulfilled → delivered → closed)
- Fulfillment routing logic (which warehouse/location fulfills which line, split-shipment rules — ties to WMS Vol 8)
- Returns / RMA engine (initiation, inspection, restock vs. dispose, refund trigger)
- Order allocation & inventory reservation (ties to Inventory Vol 9)
- Exception handling (backorders, partial availability, substitutions)
- Multi-channel order ingestion (online, POS, marketplace, social — normalization layer)

## Dependencies
Inventory (Vol 9) for allocation, WMS (Vol 8) for physical fulfillment, Finance (Vol 12) for payment/refund settlement, Merchant Admin Orders (Vol 2.2) as the primary UI.

## Next steps
Document the order state machine and allocation algorithm in full depth first — every other OMS capability builds on those two.
