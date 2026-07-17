export type ReturnStatus = "Requested" | "Approved" | "In Transit" | "Received" | "Inspection" | "Refund Pending" | "Refunded" | "Rejected";
export type ReturnBucket = "all" | "requested" | "approved" | "in_transit" | "received" | "refund_pending" | "refunded" | "rejected";
export type ReturnType = "Refund" | "Replacement" | "Exchange" | "Store Credit" | "Repair";
export type ReturnReason =
  | "Wrong Size"
  | "Wrong Product"
  | "Defective"
  | "Damaged"
  | "Missing Item"
  | "Changed Mind"
  | "Late Delivery"
  | "Quality Issue"
  | "Not as Described";

export const statusStyle: Record<ReturnStatus, string> = {
  Requested: "bg-info-bg text-info",
  Approved: "bg-success-bg text-success",
  "In Transit": "bg-warning-bg text-warning",
  Received: "bg-violet-50 text-violet-600",
  Inspection: "bg-orange-50 text-orange-600",
  "Refund Pending": "bg-warning-bg text-warning",
  Refunded: "bg-success-bg text-success",
  Rejected: "bg-danger-bg text-danger",
};

export const reasonStyle: Record<ReturnReason, string> = {
  "Wrong Size": "bg-blue-50 text-blue-600",
  "Wrong Product": "bg-blue-50 text-blue-600",
  Defective: "bg-danger-bg text-danger",
  Damaged: "bg-danger-bg text-danger",
  "Missing Item": "bg-orange-50 text-orange-600",
  "Changed Mind": "bg-warning-bg text-warning",
  "Late Delivery": "bg-card-border/60 text-muted",
  "Quality Issue": "bg-danger-bg text-danger",
  "Not as Described": "bg-orange-50 text-orange-600",
};

export type ReturnRequest = {
  id: string;
  orderId: string;
  customer: string;
  email: string;
  items: number;
  sku: number;
  reason: ReturnReason;
  status: ReturnStatus;
  returnType: ReturnType;
  warehouse: string;
  requestedOn: string;
  bucket: ReturnBucket;
};

export const returnRequests: ReturnRequest[] = [
  { id: "#RMA-10098", orderId: "#ORD-2843", customer: "John Doe", email: "john.doe@email.com", items: 2, sku: 2, reason: "Wrong Size", status: "Approved", returnType: "Replacement", warehouse: "New York Warehouse", requestedOn: "May 17, 2025 10:23 AM", bucket: "approved" },
  { id: "#RMA-10097", orderId: "#ORD-2841", customer: "Jane Smith", email: "jane.smith@email.com", items: 3, sku: 3, reason: "Defective", status: "In Transit", returnType: "Replacement", warehouse: "Los Angeles WH", requestedOn: "May 17, 2025 09:50 AM", bucket: "in_transit" },
  { id: "#RMA-10096", orderId: "#ORD-2838", customer: "Robert Johnson", email: "robert.email@email.com", items: 1, sku: 1, reason: "Not as Described", status: "Received", returnType: "Refund", warehouse: "Chicago Warehouse", requestedOn: "May 16, 2025 08:11 AM", bucket: "received" },
  { id: "#RMA-10095", orderId: "#ORD-2835", customer: "Emily Davis", email: "emily.davis@email.com", items: 2, sku: 2, reason: "Changed Mind", status: "Refund Pending", returnType: "Refund", warehouse: "New York Warehouse", requestedOn: "May 16, 2025 07:45 PM", bucket: "refund_pending" },
  { id: "#RMA-10094", orderId: "#ORD-2831", customer: "Michael Brown", email: "michael.brown@email.com", items: 4, sku: 4, reason: "Damaged", status: "Refunded", returnType: "Refund", warehouse: "Dallas Warehouse", requestedOn: "May 16, 2025 06:30 PM", bucket: "refunded" },
  { id: "#RMA-10093", orderId: "#ORD-2829", customer: "Sarah Wilson", email: "sarah.wilson@email.com", items: 1, sku: 1, reason: "Quality Issue", status: "Requested", returnType: "Refund", warehouse: "New York Warehouse", requestedOn: "May 16, 2025 03:10 PM", bucket: "requested" },
  { id: "#RMA-10092", orderId: "#ORD-2820", customer: "David Lee", email: "david.lee@email.com", items: 2, sku: 2, reason: "Late Delivery", status: "Rejected", returnType: "Refund", warehouse: "Los Angeles WH", requestedOn: "May 15, 2025 11:05 AM", bucket: "rejected" },
];

export const statusTabs: { key: ReturnBucket; label: string; count: number }[] = [
  { key: "all", label: "All Returns", count: 98 },
  { key: "requested", label: "Requested", count: 20 },
  { key: "approved", label: "Approved", count: 64 },
  { key: "in_transit", label: "In Transit", count: 27 },
  { key: "received", label: "Received", count: 19 },
  { key: "refund_pending", label: "Refund Pending", count: 13 },
  { key: "refunded", label: "Refunded", count: 42 },
  { key: "rejected", label: "Rejected", count: 15 },
];

export type ReturnsKpi = {
  id: string;
  label: string;
  value: string;
  sub: string;
  icon: "shopping-bag" | "shield-check" | "shuffle" | "package-open" | "wallet";
  iconBg: string;
  iconColor: string;
  breakdown: { label: string; value: string }[];
};

export const returnsKpis: ReturnsKpi[] = [
  {
    id: "return-requests", label: "Return Requests", value: "98", sub: "+12 this week",
    icon: "shopping-bag", iconBg: "bg-blue-50", iconColor: "text-blue-500",
    breakdown: [{ label: "Today's requests", value: "6" }, { label: "Weekly requests", value: "20" }, { label: "Monthly requests", value: "98" }, { label: "Growth %", value: "18.4%" }],
  },
  {
    id: "approved", label: "Approved", value: "64", sub: "65.3%",
    icon: "shield-check", iconBg: "bg-emerald-50", iconColor: "text-emerald-500",
    breakdown: [{ label: "Approved returns", value: "64" }, { label: "Approval rate", value: "65.3%" }, { label: "Pending approval", value: "20" }],
  },
  {
    id: "in-transit", label: "In Transit", value: "27", sub: "+5 today",
    icon: "shuffle", iconBg: "bg-orange-50", iconColor: "text-orange-500",
    breakdown: [{ label: "Customer shipped", value: "18" }, { label: "Courier pickup", value: "9" }, { label: "Expected arrival", value: "May 20, 2025" }],
  },
  {
    id: "received", label: "Received", value: "19", sub: "+3 today",
    icon: "package-open", iconBg: "bg-violet-50", iconColor: "text-violet-500",
    breakdown: [{ label: "Packages received", value: "19" }, { label: "Inspection pending", value: "11" }, { label: "Inspection complete", value: "8" }],
  },
  {
    id: "refund-issued", label: "Refund Issued", value: "42", sub: "45.3%",
    icon: "wallet", iconBg: "bg-green-50", iconColor: "text-green-500",
    breakdown: [{ label: "Refund amount", value: "$8,240.50" }, { label: "Completed refunds", value: "42" }, { label: "Replacement orders", value: "22" }],
  },
];

export const statusOptions = ["All Statuses", "Requested", "Approved", "In Transit", "Received", "Inspection", "Refund Pending", "Refunded", "Rejected"];
export const reasonOptions = ["All Reasons", "Wrong Size", "Wrong Product", "Defective", "Damaged", "Missing Item", "Changed Mind", "Late Delivery", "Quality Issue", "Not as Described"];
export const warehouseOptions = ["All Warehouses", "New York Warehouse", "Los Angeles WH", "Chicago Warehouse", "Dallas Warehouse"];
export const returnTypeOptions = ["All Types", "Refund", "Replacement", "Exchange", "Store Credit", "Repair"];
export const filterGroups = ["Status", "Reason", "Warehouse", "Return Type", "Courier", "Requested Date", "Received Date", "Refund Status", "Customer Group"];

export const returnsOverview = [
  { label: "Requested", count: 20, pct: 20.4, color: "#3b82f6" },
  { label: "Approved", count: 64, pct: 65.3, color: "#f59e0b" },
  { label: "In Transit", count: 27, pct: 27.6, color: "#8b5cf6" },
  { label: "Received", count: 19, pct: 19.4, color: "#06b6d4" },
  { label: "Refund Pending", count: 13, pct: 13.3, color: "#eab308" },
  { label: "Refunded", count: 42, pct: 42.9, color: "#10b981" },
  { label: "Rejected", count: 15, pct: 15.3, color: "#ef4444" },
];

export const reasonsSummary = [
  { label: "Wrong Size", count: 32, pct: 32.7 },
  { label: "Defective", count: 24, pct: 24.5 },
  { label: "Not as Described", count: 16, pct: 16.3 },
  { label: "Changed Mind", count: 12, pct: 12.2 },
  { label: "Damaged", count: 9, pct: 9.2 },
  { label: "Other", count: 5, pct: 5.1 },
];

export const quickActions = [
  { id: 1, label: "Create RMA", icon: "plus-square" },
  { id: 2, label: "Approve Return", icon: "shield-check" },
  { id: 3, label: "Print Return Label", icon: "tag" },
  { id: 4, label: "Print RMA List", icon: "file-text" },
  { id: 5, label: "Bulk Process Returns", icon: "list-checks" },
];

export const aiInsights = [
  { id: 1, tone: "warning" as const, text: "32 returns are awaiting approval." },
  { id: 2, tone: "danger" as const, text: "Defective returns increased by 18% this week." },
  { id: 3, tone: "danger" as const, text: "High-value returns detected. Review recommended." },
];

export const returnActionsRow = ["View Details", "Approve", "Reject", "Generate Label", "Mark Received", "Send to Inspection"] as const;

export const selectedReturnDetail = {
  id: "#RMA-10098",
  status: "Approved" as ReturnStatus,
  orderId: "#ORD-2843",
  customer: "John Doe",
  requestedOn: "May 17, 2025 10:23 AM",
  returnType: "Return",
  reason: "Wrong Size",
  notes: "Item size is smaller than expected.",
  totalRefund: 220.0,
  items: [
    { name: "Nike Air Max 270", variant: "Black / 9", sku: "NK-AM270-BLK-9", price: 150.0, qty: 1 },
    { name: "Classic Cotton T-Shirt", variant: "Blue / L", sku: "CT-TSHIRT-BLU-L", price: 70.0, qty: 1 },
  ],
};

export const returnTimeline: { label: string; time: string | null; user: string | null; done: boolean }[] = [
  { label: "Return request submitted", time: "May 17, 2025 10:23 AM", user: "John Doe", done: true },
  { label: "Return approved", time: "May 17, 2025 10:30 AM", user: "by Admin", done: true },
  { label: "Return label generated", time: "May 17, 2025 10:35 AM", user: "by System", done: true },
  { label: "Package shipped by customer", time: "May 18, 2025 02:15 PM", user: "via FedEx", done: true },
  { label: "Package in transit", time: "May 18, 2025 05:40 PM", user: "via FedEx", done: true },
  { label: "Package received at warehouse", time: "May 19, 2025 09:12 AM", user: "by System", done: true },
  { label: "Return inspection", time: null, user: null, done: false },
  { label: "Refund processing", time: null, user: null, done: false },
];

export const topReturnedProducts = [
  { id: 1, name: "Nike Air Max 270", returns: 24 },
  { id: 2, name: "Classic Cotton T-Shirt", returns: 18 },
  { id: 3, name: "Wireless Headphones", returns: 12 },
  { id: 4, name: "Denim Jacket", returns: 9 },
  { id: 5, name: "Smart Watch Series 5", returns: 7 },
];

export const returnRowActions = [
  { key: "view", label: "View Details" },
  { key: "approve", label: "Approve" },
  { key: "reject", label: "Reject", danger: true },
  { key: "label", label: "Generate Return Label" },
  { key: "received", label: "Mark Received" },
  { key: "inspection", label: "Send to Inspection" },
] as const;
