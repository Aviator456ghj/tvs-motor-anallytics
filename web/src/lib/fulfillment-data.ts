export type FulfillmentStatus = "Pending Pick" | "Picking" | "Packing" | "Ready to Ship" | "Shipped" | "Exception" | "On Hold";
export type FulfillmentBucket = "all" | "pending_pick" | "picking" | "packing" | "ready_to_ship" | "shipped" | "exception" | "on_hold";
export type Priority = "High" | "Medium" | "Low";

export const statusStyle: Record<FulfillmentStatus, string> = {
  "Pending Pick": "bg-warning-bg text-warning",
  Picking: "bg-orange-50 text-orange-600",
  Packing: "bg-violet-50 text-violet-600",
  "Ready to Ship": "bg-info-bg text-info",
  Shipped: "bg-success-bg text-success",
  Exception: "bg-danger-bg text-danger",
  "On Hold": "bg-card-border/60 text-muted",
};

export const priorityStyle: Record<Priority, string> = {
  High: "text-danger",
  Medium: "text-warning",
  Low: "text-success",
};

export type FulfillmentOrder = {
  id: string;
  customer: string;
  email: string;
  items: number;
  sku: number;
  warehouse: string;
  warehouseCode: string;
  status: FulfillmentStatus;
  priority: Priority;
  shippingMethod: string;
  expedited: boolean;
  shipBy: string;
  picker: string | null;
  packer: string | null;
  bucket: FulfillmentBucket;
};

export const fulfillmentOrders: FulfillmentOrder[] = [
  {
    id: "#ORD-2843", customer: "John Doe", email: "john.doe@email.com", items: 2, sku: 2,
    warehouse: "New York Warehouse", warehouseCode: "NY", status: "Pending Pick", priority: "High",
    shippingMethod: "FedEx Expedited", expedited: true, shipBy: "May 17, 2025 11:59 PM", picker: null, packer: null, bucket: "pending_pick",
  },
  {
    id: "#ORD-2841", customer: "Jane Smith", email: "jane.smith@email.com", items: 3, sku: 3,
    warehouse: "Los Angeles WH", warehouseCode: "LA", status: "Picking", priority: "Medium",
    shippingMethod: "UPS Ground", expedited: false, shipBy: "May 17, 2025 11:59 PM", picker: "Mike Williams", packer: null, bucket: "picking",
  },
  {
    id: "#ORD-2838", customer: "Robert Johnson", email: "robert.email@email.com", items: 1, sku: 1,
    warehouse: "Chicago Warehouse", warehouseCode: "CHI", status: "Packing", priority: "High",
    shippingMethod: "DHL Express", expedited: false, shipBy: "May 16, 2025 11:59 PM", picker: "Tom Harris", packer: "Tom Harris", bucket: "packing",
  },
  {
    id: "#ORD-2835", customer: "Emily Davis", email: "emily.davis@email.com", items: 2, sku: 2,
    warehouse: "New York Warehouse", warehouseCode: "NY", status: "Ready to Ship", priority: "Medium",
    shippingMethod: "FedEx Ground", expedited: false, shipBy: "May 16, 2025 05:00 PM", picker: "Sarah Johnson", packer: "Sarah Johnson", bucket: "ready_to_ship",
  },
  {
    id: "#ORD-2831", customer: "Michael Brown", email: "michael.brown@email.com", items: 4, sku: 4,
    warehouse: "Dallas Warehouse", warehouseCode: "DAL", status: "Shipped", priority: "Low",
    shippingMethod: "FedEx Expedited", expedited: true, shipBy: "May 15, 2025 04:15 PM", picker: "Jane Cooper", packer: "Jane Cooper", bucket: "shipped",
  },
  {
    id: "#ORD-2829", customer: "Sarah Wilson", email: "sarah.wilson@email.com", items: 1, sku: 1,
    warehouse: "New York Warehouse", warehouseCode: "NY", status: "Exception", priority: "High",
    shippingMethod: "UPS Ground", expedited: false, shipBy: "May 16, 2025 11:59 PM", picker: null, packer: null, bucket: "exception",
  },
  {
    id: "#ORD-2820", customer: "David Lee", email: "david.lee@email.com", items: 2, sku: 2,
    warehouse: "Los Angeles WH", warehouseCode: "LA", status: "On Hold", priority: "Medium",
    shippingMethod: "DHL Express", expedited: false, shipBy: "May 18, 2025 11:59 PM", picker: null, packer: null, bucket: "on_hold",
  },
];

export const statusTabs: { key: FulfillmentBucket; label: string; count: number }[] = [
  { key: "all", label: "All", count: 434 },
  { key: "pending_pick", label: "Pending Pick", count: 142 },
  { key: "picking", label: "Picking", count: 68 },
  { key: "packing", label: "Packing", count: 41 },
  { key: "ready_to_ship", label: "Ready to Ship", count: 37 },
  { key: "shipped", label: "Shipped", count: 128 },
  { key: "exception", label: "Exception", count: 18 },
  { key: "on_hold", label: "On Hold", count: 11 },
];

export type FulfillmentKpi = {
  id: string;
  label: string;
  value: string;
  sub: string;
  icon: "clipboard" | "lock" | "package" | "truck" | "check" | "alert";
  iconBg: string;
  iconColor: string;
  breakdown: { label: string; value: string }[];
};

export const fulfillmentKpis: FulfillmentKpi[] = [
  {
    id: "pending-pick", label: "Pending Pick", value: "142", sub: "Orders to be picked",
    icon: "clipboard", iconBg: "bg-blue-50", iconColor: "text-blue-500",
    breakdown: [{ label: "Today's pick queue", value: "86" }, { label: "Avg. waiting time", value: "2.4 hrs" }],
  },
  {
    id: "picking", label: "Picking", value: "68", sub: "Currently picking",
    icon: "lock", iconBg: "bg-amber-50", iconColor: "text-amber-500",
    breakdown: [{ label: "Assigned employees", value: "14" }, { label: "Avg. pick time", value: "6.2 min" }],
  },
  {
    id: "packing", label: "Packing", value: "41", sub: "Ready to pack",
    icon: "package", iconBg: "bg-violet-50", iconColor: "text-violet-500",
    breakdown: [{ label: "Packed orders", value: "412" }, { label: "Waiting shipment", value: "41" }, { label: "Packing errors", value: "3" }],
  },
  {
    id: "ready-to-ship", label: "Ready to Ship", value: "37", sub: "Ready for pickup",
    icon: "truck", iconBg: "bg-cyan-50", iconColor: "text-cyan-500",
    breakdown: [{ label: "Ready for pickup", value: "37" }, { label: "Courier assigned", value: "29" }, { label: "Awaiting label", value: "8" }],
  },
  {
    id: "shipped-today", label: "Shipped Today", value: "128", sub: "Shipped orders",
    icon: "check", iconBg: "bg-emerald-50", iconColor: "text-emerald-500",
    breakdown: [{ label: "Completed shipments", value: "119" }, { label: "Delayed shipments", value: "9" }],
  },
  {
    id: "exception", label: "Exception", value: "18", sub: "Require attention",
    icon: "alert", iconBg: "bg-red-50", iconColor: "text-red-500",
    breakdown: [{ label: "Inventory issues", value: "7" }, { label: "Address issues", value: "4" }, { label: "Payment hold", value: "3" }, { label: "Carrier errors", value: "4" }],
  },
];

export const warehouseOptions = ["All Warehouses", "New York Warehouse", "Los Angeles WH", "Chicago Warehouse", "Dallas Warehouse"];
export const channelOptions = ["All Channels", "Online Store", "Mobile App", "Amazon", "eBay", "Walmart"];
export const priorityOptions = ["All Priorities", "High", "Medium", "Low"];
export const methodOptions = ["All Methods", "FedEx Expedited", "FedEx Ground", "UPS Ground", "DHL Express"];
export const statusOptions = ["All Status", "Pending Pick", "Picking", "Packing", "Ready to Ship", "Shipped", "Exception", "On Hold"];

export const fulfillmentProgress = [
  { label: "Pending Pick", pct: 32.7, count: 142, color: "#3b82f6" },
  { label: "Picking", pct: 15.7, count: 68, color: "#f59e0b" },
  { label: "Packing", pct: 9.4, count: 41, color: "#8b5cf6" },
  { label: "Ready to Ship", pct: 8.5, count: 37, color: "#06b6d4" },
  { label: "Shipped", pct: 29.5, count: 128, color: "#10b981" },
  { label: "Exception", pct: 4.2, count: 18, color: "#ef4444" },
];

export const warehouseCapacity = [
  { name: "New York Warehouse", used: 780, max: 1000 },
  { name: "Los Angeles Warehouse", used: 620, max: 1000 },
  { name: "Chicago Warehouse", used: 550, max: 1000 },
  { name: "Dallas Warehouse", used: 400, max: 1000 },
];

export const quickActions = [
  { id: 1, label: "Create Fulfillment", icon: "plus-square" },
  { id: 2, label: "Print Pick List", icon: "clipboard" },
  { id: 3, label: "Print Packing Slip", icon: "file-text" },
  { id: 4, label: "Create Shipping Label", icon: "tag" },
  { id: 5, label: "Bulk Fulfill Orders", icon: "list-checks" },
];

export const aiInsights = [
  { id: 1, tone: "success" as const, text: "37 orders ready to ship today" },
  { id: 2, tone: "warning" as const, text: "18 exception orders require attention" },
  { id: 3, tone: "info" as const, text: "New York Warehouse capacity will reach 90% tomorrow" },
];

export const workflowSteps = [
  { key: "pending_pick", label: "Pending Pick", desc: "Order received and waiting for pick list", icon: "clipboard" },
  { key: "picking", label: "Picking", desc: "Items are being picked from inventory", icon: "shopping-cart" },
  { key: "packing", label: "Packing", desc: "Items are packed and verified", icon: "package" },
  { key: "ready_to_ship", label: "Ready to Ship", desc: "Packed items ready for pickup", icon: "truck" },
  { key: "shipped", label: "Shipped", desc: "Order shipped to customer", icon: "truck" },
  { key: "delivered", label: "Delivered", desc: "Order delivered successfully", icon: "check" },
] as const;

export const recentActivity = [
  { id: 1, time: "10:25 AM", text: 'Order #ORD-2843 moved to Pending Pick', actor: "Sarah Johnson" },
  { id: 2, time: "10:20 AM", text: "Order #ORD-2841 picking started", actor: "Mike Williams" },
  { id: 3, time: "09:45 AM", text: "Order #ORD-2838 packed and verified", actor: "Tom Harris" },
  { id: 4, time: "08:30 AM", text: "Order #ORD-2831 shipped via FedEx", actor: "System" },
  { id: 5, time: "08:15 AM", text: "Order #ORD-2829 exception updated", actor: "Jane Cooper" },
];

export const exceptionOrders: { id: string; reason: string; date: string; severity: Priority }[] = [
  { id: "#ORD-2829", reason: "Payment failed", date: "May 16, 2025", severity: "High" },
  { id: "#ORD-2818", reason: "Address verification failed", date: "May 16, 2025", severity: "High" },
  { id: "#ORD-2812", reason: "Item out of stock", date: "May 15, 2025", severity: "Medium" },
  { id: "#ORD-2805", reason: "Carrier pickup delay", date: "May 15, 2025", severity: "Medium" },
  { id: "#ORD-2799", reason: "Weight mismatch", date: "May 15, 2025", severity: "Low" },
];

export const filterGroups = ["Warehouse", "Sales Channel", "Priority", "Shipping Method", "Status", "Assigned Picker", "Assigned Packer", "Carrier", "Delivery Date"];
