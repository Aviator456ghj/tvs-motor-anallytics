export type DetailPaymentStatus = "Pending" | "Authorized" | "Paid" | "Partially Paid" | "Refunded" | "Voided" | "Failed";
export type DetailFulfillmentStatus =
  | "Unfulfilled"
  | "Processing"
  | "Picking"
  | "Packing"
  | "Ready to Ship"
  | "Partially Fulfilled"
  | "Shipped"
  | "Delivered"
  | "Completed";
export type DetailOrderStatus = "Draft" | "Confirmed" | "On Hold" | "Cancelled" | "Archived";

export const paymentStatusStyle: Record<DetailPaymentStatus, string> = {
  Pending: "bg-warning-bg text-warning",
  Authorized: "bg-info-bg text-info",
  Paid: "bg-success-bg text-success",
  "Partially Paid": "bg-orange-50 text-orange-600",
  Refunded: "bg-info-bg text-info",
  Voided: "bg-card-border/60 text-muted",
  Failed: "bg-danger-bg text-danger",
};

export const fulfillmentStatusStyle: Partial<Record<DetailFulfillmentStatus, string>> = {
  Unfulfilled: "bg-warning-bg text-warning",
  Processing: "bg-orange-50 text-orange-600",
  "Partially Fulfilled": "bg-violet-50 text-violet-600",
  Shipped: "bg-info-bg text-info",
  Delivered: "bg-success-bg text-success",
  Completed: "bg-success-bg text-success",
};

export const orderStatusStyle: Record<DetailOrderStatus, string> = {
  Draft: "bg-card-border/60 text-muted",
  Confirmed: "bg-info-bg text-info",
  "On Hold": "bg-warning-bg text-warning",
  Cancelled: "bg-danger-bg text-danger",
  Archived: "bg-card-border/60 text-muted",
};

export type OrderDetail = typeof orderDetail;

export const orderDetail = {
  id: "#ORD-2843",
  placedAt: "May 16, 2025 at 10:23 AM",
  channel: "Online Store",
  source: "Web checkout",
  store: "Main Store",
  currency: "USD",
  paymentStatus: "Paid" as DetailPaymentStatus,
  fulfillmentStatus: "Partially Fulfilled" as DetailFulfillmentStatus,
  orderStatus: "Confirmed" as DetailOrderStatus,
  processingLabel: "Processing" as const,

  customer: {
    name: "Jane Smith",
    email: "jane.smith@email.com",
    phone: "+1 555-123-4567",
    since: "May 10, 2024",
    group: "Retail",
    vip: true,
    totalOrders: 24,
    totalSpent: 4560.9,
    outstanding: 120.0,
  },

  shippingAddress: {
    name: "Jane Smith",
    line1: "456 Park Avenue",
    city: "New York",
    state: "NY",
    postalCode: "10022",
    country: "United States",
    phone: "+1 555-123-4567",
  },
  billingAddress: {
    name: "Jane Smith",
    line1: "123 Main Street",
    city: "New York",
    state: "NY",
    postalCode: "10001",
    country: "United States",
    phone: "+1 555-123-4567",
  },

  shippingMethod: "FedEx Express",
  carrier: "FedEx",
  trackingNumber: "FX123456789US",
  trackingStatus: "In Transit",
  expectedDelivery: "May 21, 2025",
  warehouse: "Main Warehouse",
  packageWeight: "1.2 kg",

  summary: {
    itemsTotal: 220.0,
    discount: 20.0,
    coupon: "SAVE20",
    shipping: 10.0,
    taxLabel: "Tax (8.25%)",
    tax: 19.0,
    grandTotal: 249.0,
    paid: 249.0,
    due: 0.0,
    refunded: 0.0,
  },

  payment: {
    method: "Visa •••• 4242",
    gateway: "Stripe",
    transactionId: "TXN1234567890",
    authorizationId: "AUTH998877",
    capturedOn: "May 16, 2025 10:24 AM",
    status: "Paid" as DetailPaymentStatus,
  },

  items: [
    {
      id: "li-1",
      name: "Nike Air Max 270",
      variant: "Black / 9",
      sku: "NK-AM270-BLK-9",
      price: 150.0,
      qty: 1,
      reserved: 1,
      fulfilled: 1,
      returned: 0,
      total: 150.0,
    },
    {
      id: "li-2",
      name: "Classic Cotton T-Shirt",
      variant: "Blue / L",
      sku: "CT-TSHIRT-BLU-L",
      price: 70.0,
      qty: 1,
      reserved: 1,
      fulfilled: 0,
      returned: 0,
      total: 70.0,
    },
  ],

  statusSteps: [
    { label: "Order Placed", time: "May 16, 10:23 AM", done: true },
    { label: "Payment Captured", time: "May 16, 10:24 AM", done: true },
    { label: "Order Confirmed", time: "May 16, 10:24 AM", done: true },
    { label: "Processing", time: "May 16, 11:15 AM", done: true },
    { label: "Shipped", time: null, done: false },
    { label: "Out for Delivery", time: null, done: false },
    { label: "Delivered", time: null, done: false },
    { label: "Completed", time: null, done: false },
  ],

  tags: ["VIP", "Wholesale", "Urgent"],

  notes: [
    {
      id: 1,
      type: "customer" as const,
      title: "Customer Note",
      body: "Please deliver after 6 PM. Customer will be available.",
      author: "Jane Smith",
      time: "May 16, 10:25 AM",
    },
    {
      id: 2,
      type: "internal" as const,
      title: "Internal Note",
      body: "Customer requested faster delivery.",
      author: "John Doe",
      time: "May 16, 11:10 AM",
    },
  ],

  payments: [
    {
      id: "pay-1",
      type: "Charge",
      method: "Visa •••• 4242",
      gateway: "Stripe",
      transactionId: "TXN1234567890",
      amount: 249.0,
      status: "Paid",
      date: "May 16, 2025 10:24 AM",
    },
  ],

  shipments: [
    {
      id: "shp-1",
      carrier: "FedEx",
      service: "FedEx Express",
      trackingNumber: "FX123456789US",
      status: "In Transit",
      items: "1 of 2 items",
      shippedAt: "May 16, 2025 02:10 PM",
      expectedAt: "May 21, 2025",
      events: [
        { label: "Label created", location: "Main Warehouse", time: "May 16, 01:45 PM" },
        { label: "Picked up by carrier", location: "New York, NY", time: "May 16, 02:10 PM" },
        { label: "In transit", location: "Newark, NJ", time: "May 16, 08:30 PM" },
      ],
    },
  ],

  invoices: [
    { id: "INV-2843-1", type: "Invoice", amount: 249.0, status: "Paid", date: "May 16, 2025", downloadable: true },
  ],

  returns: [] as { id: string; items: string; reason: string; status: string; date: string }[],

  timeline: [
    { label: "Order Created", user: "System", department: "Checkout", time: "May 16, 10:23 AM", note: "Placed via Online Store" },
    { label: "Payment Authorized", user: "Stripe", department: "Payments", time: "May 16, 10:23 AM", note: "Visa •••• 4242" },
    { label: "Payment Captured", user: "Stripe", department: "Payments", time: "May 16, 10:24 AM", note: "TXN1234567890" },
    { label: "Order Confirmed", user: "System", department: "OMS", time: "May 16, 10:24 AM", note: "Auto-confirmed (low risk)" },
    { label: "Inventory Reserved", user: "System", department: "Inventory", time: "May 16, 10:24 AM", note: "2 units reserved at Main Warehouse" },
    { label: "Picking Started", user: "Mike Chen", department: "Warehouse", time: "May 16, 11:15 AM", note: "Wave #45" },
    { label: "Packed", user: "Mike Chen", department: "Warehouse", time: "May 16, 01:30 PM", note: "1 of 2 items — T-shirt backordered" },
    { label: "Shipping Label Created", user: "System", department: "Shipping", time: "May 16, 01:45 PM", note: "FedEx Express" },
    { label: "Shipped", user: "System", department: "Shipping", time: "May 16, 02:10 PM", note: "FX123456789US" },
  ],

  activity: [
    { id: 1, text: "Internal note added", actor: "John Doe", time: "May 16, 11:10 AM" },
    { id: 2, text: "Tag \"Urgent\" added", actor: "John Doe", time: "May 16, 11:05 AM" },
    { id: 3, text: "Customer note added", actor: "Jane Smith", time: "May 16, 10:25 AM" },
    { id: 4, text: "Order confirmation email sent", actor: "System", time: "May 16, 10:24 AM" },
  ],

  auditLogs: [
    { id: 1, action: "order.created", actor: "system", before: "—", after: "status: confirmed", ip: "—", time: "May 16, 10:23 AM" },
    { id: 2, action: "payment.captured", actor: "stripe-webhook", before: "authorized", after: "paid", ip: "—", time: "May 16, 10:24 AM" },
    { id: 3, action: "order.note_added", actor: "jane.smith@email.com", before: "—", after: "customer note", ip: "203.0.113.24", time: "May 16, 10:25 AM" },
    { id: 4, action: "order.tag_added", actor: "john@store.com", before: "[VIP, Wholesale]", after: "[VIP, Wholesale, Urgent]", ip: "198.51.100.7", time: "May 16, 11:05 AM" },
    { id: 5, action: "order.note_added", actor: "john@store.com", before: "—", after: "internal note", ip: "198.51.100.7", time: "May 16, 11:10 AM" },
    { id: 6, action: "shipment.created", actor: "system", before: "—", after: "FX123456789US", ip: "—", time: "May 16, 01:45 PM" },
  ],

  aiInsights: [
    { id: 1, tone: "success" as const, text: "High value customer" },
    { id: 2, tone: "success" as const, text: "Order partially fulfilled" },
    { id: 3, tone: "warning" as const, text: "Suggest upsell: Socks (Frequently bought)" },
  ],
};

export const detailTabs = [
  "Overview",
  "Items",
  "Payments",
  "Shipments",
  "Invoices",
  "Returns",
  "Notes",
  "Timeline",
  "Activity",
  "Logs",
] as const;
export type OrderDetailTab = (typeof detailTabs)[number];

export const moreActions = [
  { key: "edit", label: "Edit Order" },
  { key: "duplicate", label: "Duplicate" },
  { key: "capture", label: "Capture Payment" },
  { key: "refund", label: "Refund" },
  { key: "cancel", label: "Cancel", danger: true },
  { key: "archive", label: "Archive" },
  { key: "delete", label: "Delete", danger: true },
  { key: "invoice", label: "Generate Invoice" },
  { key: "packing-slip", label: "Generate Packing Slip" },
  { key: "shipping-label", label: "Generate Shipping Label" },
  { key: "download-pdf", label: "Download PDF" },
  { key: "audit-logs", label: "Audit Logs" },
] as const;

export const quickActions = [
  { key: "edit", label: "Edit Order", icon: "pencil" },
  { key: "duplicate", label: "Duplicate Order", icon: "copy" },
  { key: "print-invoice", label: "Print Invoice", icon: "receipt" },
  { key: "packing-slip", label: "Print Packing Slip", icon: "file-text" },
  { key: "email", label: "Send Email", icon: "mail" },
  { key: "note", label: "Add Note", icon: "sticky-note" },
  { key: "cancel", label: "Cancel Order", icon: "x-circle", danger: true },
] as const;

export const itemRowActions = ["Edit Quantity", "Replace Product", "Split Item", "Remove Item"] as const;
