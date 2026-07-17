# Volume 8 — WMS (Warehouse Management)

Status: ⬜ Not started (skeleton).

Physical fulfillment operations: receiving, put-away, picking, packing, and shipping — for merchants operating their own warehouse(s) rather than pure dropship/3PL.

## Planned modules/pages
- Receiving (inbound POs → put-away)
- Bin/location management (warehouse map, zone/aisle/bin structure)
- Pick lists & pick paths (wave/batch picking optimization)
- Packing & shipping label generation (carrier integration)
- Cycle counting / stocktake
- Returns processing (inbound inspection, restock decision)
- Mobile/handheld scanner workflows

## Dependencies
Inventory (Vol 9) for stock-level source of truth, OMS (Vol 7) for fulfillment routing input, Products (Vol 2.3) for SKU/barcode data.

## Next steps
Define the bin/location data model and pick-path algorithm first; these anchor every other WMS workflow.
