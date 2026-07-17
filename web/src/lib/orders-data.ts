export type PaymentStatus = "Paid" | "Pending" | "Partially Paid" | "Refunded" | "Voided";
export type FulfillmentStatus =
  | "Unfulfilled"
  | "Partially Fulfilled"
  | "Fulfilled"
  | "Backordered";
export type OrderStatus = "Draft" | "Open" | "Confirmed" | "Completed" | "Cancelled" | "Archived";

export type OrderBucket =
  | "all"
  | "unfulfilled"
  | "unpaid"
  | "open"
  | "closed"
  | "cancelled"
  | "refunded"
  | "return_requested";

export type Order = {
  id: string;
  date: string;
  customer: string;
  email: string;
  phone: string;
  channel: string;
  items: number;
  subtotal: number;
  discount: number;
  shipping: number;
  tax: number;
  total: number;
  payment: PaymentStatus;
  fulfillment: FulfillmentStatus;
  orderStatus: OrderStatus;
  risk: "Low" | "Medium" | "High";
  tags: string[];
  buckets: OrderBucket[];
};

function makeOrders(): Order[] {
  const base: Omit<Order, "id" | "date">[] = [
    { customer: "John Doe", email: "john.doe@email.com", phone: "+1 555-123-4567", channel: "Online Store", items: 2, subtotal: 220, discount: 0, shipping: 10, tax: 19, total: 249, payment: "Paid", fulfillment: "Fulfilled", orderStatus: "Completed", risk: "Low", tags: ["VIP"], buckets: ["all", "closed"] },
    { customer: "Jane Smith", email: "jane.smith@email.com", phone: "+1 555-234-5678", channel: "Mobile App", items: 1, subtotal: 149, discount: 0, shipping: 0, tax: 10, total: 159, payment: "Paid", fulfillment: "Unfulfilled", orderStatus: "Open", risk: "Low", tags: [], buckets: ["all", "unfulfilled", "open"] },
    { customer: "Robert Brown", email: "robert.brown@email.com", phone: "+1 555-345-6789", channel: "Amazon", items: 3, subtotal: 79, discount: 5, shipping: 8, tax: 7, total: 89, payment: "Paid", fulfillment: "Partially Fulfilled", orderStatus: "Open", risk: "Low", tags: [], buckets: ["all", "unfulfilled", "open"] },
    { customer: "Emily Wilson", email: "emily.wilson@email.com", phone: "+1 555-456-7890", channel: "Online Store", items: 2, subtotal: 270, discount: 10, shipping: 12, tax: 27, total: 299, payment: "Pending", fulfillment: "Unfulfilled", orderStatus: "Open", risk: "Medium", tags: ["gift"], buckets: ["all", "unfulfilled", "unpaid", "open"] },
    { customer: "Michael Johnson", email: "michael.j@email.com", phone: "+1 555-567-8901", channel: "eBay", items: 1, subtotal: 105, discount: 0, shipping: 5, tax: 10, total: 120, payment: "Paid", fulfillment: "Fulfilled", orderStatus: "Completed", risk: "Low", tags: [], buckets: ["all", "closed"] },
    { customer: "Sarah Davis", email: "sarah.davis@email.com", phone: "+1 555-678-9012", channel: "Online Store", items: 1, subtotal: 68, discount: 0, shipping: 0, tax: 7, total: 75, payment: "Refunded", fulfillment: "Backordered", orderStatus: "Cancelled", risk: "Low", tags: ["refund"], buckets: ["all", "cancelled", "refunded", "return_requested"] },
    { customer: "David Lee", email: "david.lee@email.com", phone: "+1 555-789-0123", channel: "Walmart", items: 4, subtotal: 280, discount: 0, shipping: 15, tax: 15, total: 310, payment: "Paid", fulfillment: "Unfulfilled", orderStatus: "Open", risk: "High", tags: ["risk"], buckets: ["all", "unfulfilled", "open"] },
    { customer: "Linda Martin", email: "linda.martin@email.com", phone: "+1 555-890-1234", channel: "Shopify POS", items: 1, subtotal: 40, discount: 0, shipping: 0, tax: 5, total: 45, payment: "Paid", fulfillment: "Fulfilled", orderStatus: "Completed", risk: "Low", tags: [], buckets: ["all", "closed"] },
  ];

  const dates = [
    "May 16, 2025 10:23 AM",
    "May 16, 2025 09:15 AM",
    "May 15, 2025 08:45 PM",
    "May 15, 2025 07:30 PM",
    "May 15, 2025 06:20 PM",
    "May 15, 2025 05:10 PM",
    "May 15, 2025 04:05 PM",
    "May 15, 2025 03:45 PM",
  ];

  return base.map((o, i) => ({
    id: `#ORD-${2843 - i}`,
    date: dates[i],
    ...o,
  }));
}

export const orders: Order[] = makeOrders();

export const statusTabs: { key: OrderBucket; label: string; count: number }[] = [
  { key: "all", label: "All", count: 2843 },
  { key: "unfulfilled", label: "Unfulfilled", count: 325 },
  { key: "unpaid", label: "Unpaid", count: 128 },
  { key: "open", label: "Open", count: 412 },
  { key: "closed", label: "Closed", count: 1845 },
  { key: "cancelled", label: "Cancelled", count: 96 },
  { key: "refunded", label: "Refunded", count: 37 },
  { key: "return_requested", label: "Return requested", count: 26 },
];

export type OrdersKpi = {
  id: string;
  label: string;
  value: string;
  delta: string;
  direction: "up" | "down";
  compareLabel: string;
  breakdown: { label: string; value: string }[];
  icon: "cart" | "dollar" | "chart" | "clock" | "rotate";
  iconBg: string;
  iconColor: string;
};

export const ordersKpis: OrdersKpi[] = [
  {
    id: "total-orders",
    label: "Total Orders",
    value: "2,843",
    delta: "18.6%",
    direction: "up",
    compareLabel: "vs last 7 days",
    breakdown: [
      { label: "Today", value: "27" },
      { label: "This week", value: "186" },
      { label: "This month", value: "742" },
      { label: "This year", value: "2,843" },
    ],
    icon: "cart",
    iconBg: "bg-blue-50",
    iconColor: "text-blue-500",
  },
  {
    id: "total-revenue",
    label: "Total Revenue",
    value: "$24,560.90",
    delta: "18.6%",
    direction: "up",
    compareLabel: "vs last 7 days",
    breakdown: [
      { label: "Gross sales", value: "$26,890.10" },
      { label: "Net sales", value: "$24,560.90" },
      { label: "Taxes", value: "$1,842.30" },
      { label: "Shipping", value: "$980.00" },
      { label: "Discounts", value: "$2,329.20" },
    ],
    icon: "dollar",
    iconBg: "bg-green-50",
    iconColor: "text-green-500",
  },
  {
    id: "avg-order-value",
    label: "Average Order Value",
    value: "$132.05",
    delta: "4.3%",
    direction: "down",
    compareLabel: "vs last 7 days",
    breakdown: [{ label: "Formula", value: "Revenue ÷ Total Orders" }],
    icon: "chart",
    iconBg: "bg-amber-50",
    iconColor: "text-amber-500",
  },
  {
    id: "pending-orders",
    label: "Pending Orders",
    value: "128",
    delta: "12.4%",
    direction: "up",
    compareLabel: "vs last 7 days",
    breakdown: [
      { label: "Pending payment", value: "42" },
      { label: "Pending confirmation", value: "18" },
      { label: "Pending fulfillment", value: "51" },
      { label: "Pending shipment", value: "17" },
    ],
    icon: "clock",
    iconBg: "bg-orange-50",
    iconColor: "text-orange-500",
  },
  {
    id: "refunds",
    label: "Refunds",
    value: "$1,235.40",
    delta: "6.8%",
    direction: "up",
    compareLabel: "vs last 7 days",
    breakdown: [
      { label: "Refund amount", value: "$1,235.40" },
      { label: "Refund %", value: "5.0%" },
      { label: "Refund requests", value: "26" },
      { label: "Completed refunds", value: "37" },
    ],
    icon: "rotate",
    iconBg: "bg-rose-50",
    iconColor: "text-rose-500",
  },
];

export type OrderColumnKey =
  | "customer"
  | "channel"
  | "items"
  | "subtotal"
  | "discount"
  | "shipping"
  | "tax"
  | "total"
  | "payment"
  | "fulfillment"
  | "risk"
  | "tags";

export const orderColumns: { key: OrderColumnKey; label: string; defaultVisible: boolean }[] = [
  { key: "customer", label: "Customer", defaultVisible: true },
  { key: "channel", label: "Channel", defaultVisible: true },
  { key: "items", label: "Items", defaultVisible: true },
  { key: "subtotal", label: "Subtotal", defaultVisible: false },
  { key: "discount", label: "Discount", defaultVisible: false },
  { key: "shipping", label: "Shipping", defaultVisible: false },
  { key: "tax", label: "Tax", defaultVisible: false },
  { key: "total", label: "Total", defaultVisible: true },
  { key: "payment", label: "Payment", defaultVisible: true },
  { key: "fulfillment", label: "Fulfillment", defaultVisible: true },
  { key: "risk", label: "Risk", defaultVisible: false },
  { key: "tags", label: "Tags", defaultVisible: false },
];

export const filterGroups = [
  "Date",
  "Store",
  "Marketplace",
  "Country",
  "Currency",
  "Payment Status",
  "Fulfillment Status",
  "Order Status",
  "Sales Channel",
  "Tags",
  "Assigned Staff",
  "Shipping Provider",
];

export const sortOptions = [
  "Date (Newest)",
  "Date (Oldest)",
  "Total (High to Low)",
  "Total (Low to High)",
  "Customer (A–Z)",
  "Risk (High to Low)",
];

export type BulkActionKey =
  | "export"
  | "print-invoice"
  | "print-label"
  | "capture-payment"
  | "refund"
  | "cancel"
  | "archive"
  | "delete"
  | "assign-staff"
  | "add-tag"
  | "remove-tag"
  | "merge"
  | "split"
  | "send-email"
  | "send-sms"
  | "pick-list";

export const bulkActions: { key: BulkActionKey; label: string; danger?: boolean }[] = [
  { key: "export", label: "Export" },
  { key: "print-invoice", label: "Print Invoice" },
  { key: "print-label", label: "Print Label" },
  { key: "capture-payment", label: "Capture Payment" },
  { key: "refund", label: "Refund" },
  { key: "cancel", label: "Cancel", danger: true },
  { key: "archive", label: "Archive" },
  { key: "delete", label: "Delete", danger: true },
  { key: "assign-staff", label: "Assign Staff" },
  { key: "add-tag", label: "Add Tag" },
  { key: "remove-tag", label: "Remove Tag" },
  { key: "merge", label: "Merge Orders" },
  { key: "split", label: "Split Orders" },
  { key: "send-email", label: "Send Email" },
  { key: "send-sms", label: "Send SMS" },
  { key: "pick-list", label: "Generate Pick List" },
];

export type TimelineStep = { label: string; time: string | null };

export const orderTimeline: TimelineStep[] = [
  { label: "Order placed", time: "May 16, 10:23 AM" },
  { label: "Payment captured", time: "May 16, 10:24 AM" },
  { label: "Order confirmed", time: "May 16, 10:24 AM" },
  { label: "Fulfilled", time: "May 16, 11:15 AM" },
  { label: "Delivered", time: "May 17, 02:30 PM" },
];

export const orderDetailItems = [
  { name: "Nike Air Max 270", variant: "Black / 9", sku: "NK-AM270-BLK-9", price: 150, qty: 1, total: 150 },
  { name: "Classic Cotton T-Shirt", variant: "Blue / L", sku: "CT-TSHIRT-BLU-L", price: 70, qty: 1, total: 70 },
];

export const quickActions = [
  { id: 1, label: "Create Order", icon: "plus-square" },
  { id: 2, label: "Import Orders", icon: "upload" },
  { id: 3, label: "Export Orders", icon: "download" },
  { id: 4, label: "Manage Returns", icon: "rotate-ccw" },
  { id: 5, label: "Bulk Update Orders", icon: "list-checks" },
  { id: 6, label: "Print Packing Slips", icon: "file-text" },
  { id: 7, label: "Print Invoices", icon: "receipt" },
];

export const paymentStatusLegend: { label: PaymentStatus; description: string; color: string; bg: string }[] = [
  { label: "Paid", description: "Payment completed", color: "text-success", bg: "bg-success-bg" },
  { label: "Pending", description: "Payment pending", color: "text-warning", bg: "bg-warning-bg" },
  { label: "Partially Paid", description: "Partial payment received", color: "text-orange-600", bg: "bg-orange-50" },
  { label: "Refunded", description: "Payment refunded", color: "text-info", bg: "bg-info-bg" },
  { label: "Voided", description: "Payment voided", color: "text-muted", bg: "bg-card-border/60" },
];

export const fulfillmentStatusLegend: { label: FulfillmentStatus; description: string; color: string; bg: string }[] = [
  { label: "Unfulfilled", description: "Not yet fulfilled", color: "text-warning", bg: "bg-warning-bg" },
  { label: "Partially Fulfilled", description: "Partially shipped", color: "text-orange-600", bg: "bg-orange-50" },
  { label: "Fulfilled", description: "Fully shipped", color: "text-success", bg: "bg-success-bg" },
  { label: "Backordered", description: "Waiting for stock", color: "text-danger", bg: "bg-danger-bg" },
];

export const orderStatusLegend: { label: OrderStatus; description: string; color: string; bg: string }[] = [
  { label: "Draft", description: "Not yet placed", color: "text-muted", bg: "bg-card-border/60" },
  { label: "Open", description: "Order is open", color: "text-info", bg: "bg-info-bg" },
  { label: "Confirmed", description: "Order confirmed", color: "text-indigo-600", bg: "bg-indigo-50" },
  { label: "Completed", description: "Order completed", color: "text-success", bg: "bg-success-bg" },
  { label: "Cancelled", description: "Order cancelled", color: "text-danger", bg: "bg-danger-bg" },
  { label: "Archived", description: "Order archived", color: "text-muted", bg: "bg-card-border/60" },
];
