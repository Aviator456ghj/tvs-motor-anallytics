export type StatCard = {
  id: string;
  label: string;
  value: string;
  delta: string;
  deltaDirection: "up" | "down";
  compareLabel: string;
  icon:
    | "cart"
    | "bag"
    | "users"
    | "filter"
    | "chart"
    | "dollar"
    | "calendar"
    | "trending-up"
    | "clock"
    | "repeat"
    | "package"
    | "rotate-ccw"
    | "alert-triangle";
  iconBg: string;
  iconColor: string;
  sparkline: number[];
  sparklineColor: string;
};

export const statCards: StatCard[] = [
  {
    id: "todays-sales",
    label: "Today's Sales",
    value: "$3,842.10",
    delta: "12.4%",
    deltaDirection: "up",
    compareLabel: "vs yesterday",
    icon: "cart",
    iconBg: "bg-blue-50",
    iconColor: "text-blue-500",
    sparkline: [12, 18, 14, 22, 19, 26, 24, 30],
    sparklineColor: "#3b82f6",
  },
  {
    id: "yesterdays-sales",
    label: "Yesterday's Sales",
    value: "$3,418.60",
    delta: "4.1%",
    deltaDirection: "down",
    compareLabel: "vs day before",
    icon: "calendar",
    iconBg: "bg-slate-100",
    iconColor: "text-slate-500",
    sparkline: [20, 18, 19, 17, 18, 16, 17, 15],
    sparklineColor: "#64748b",
  },
  {
    id: "monthly-revenue",
    label: "Monthly Revenue",
    value: "$24,560.90",
    delta: "18.6%",
    deltaDirection: "up",
    compareLabel: "vs last month",
    icon: "trending-up",
    iconBg: "bg-indigo-50",
    iconColor: "text-indigo-500",
    sparkline: [10, 14, 13, 19, 18, 24, 23, 29],
    sparklineColor: "#6366f1",
  },
  {
    id: "orders-today",
    label: "Orders Today",
    value: "27",
    delta: "9.3%",
    deltaDirection: "up",
    compareLabel: "vs yesterday",
    icon: "bag",
    iconBg: "bg-emerald-50",
    iconColor: "text-emerald-500",
    sparkline: [8, 12, 10, 16, 14, 18, 20, 19],
    sparklineColor: "#10b981",
  },
  {
    id: "pending-orders",
    label: "Pending Orders",
    value: "9",
    delta: "2 new",
    deltaDirection: "up",
    compareLabel: "awaiting fulfillment",
    icon: "clock",
    iconBg: "bg-amber-50",
    iconColor: "text-amber-500",
    sparkline: [4, 6, 5, 8, 6, 9, 7, 9],
    sparklineColor: "#f59e0b",
  },
  {
    id: "avg-order-value",
    label: "Avg. Order Value",
    value: "$132.05",
    delta: "6.4%",
    deltaDirection: "up",
    compareLabel: "vs last 7 days",
    icon: "chart",
    iconBg: "bg-amber-50",
    iconColor: "text-amber-500",
    sparkline: [16, 15, 18, 17, 20, 19, 22, 21],
    sparklineColor: "#f59e0b",
  },
  {
    id: "conversion-rate",
    label: "Conversion Rate",
    value: "2.35%",
    delta: "8.7%",
    deltaDirection: "up",
    compareLabel: "vs last 7 days",
    icon: "filter",
    iconBg: "bg-orange-50",
    iconColor: "text-orange-500",
    sparkline: [14, 16, 13, 18, 15, 19, 17, 21],
    sparklineColor: "#f97316",
  },
  {
    id: "returning-customers",
    label: "Returning Customers",
    value: "243",
    delta: "18.7%",
    deltaDirection: "up",
    compareLabel: "vs last 7 days",
    icon: "repeat",
    iconBg: "bg-cyan-50",
    iconColor: "text-cyan-500",
    sparkline: [18, 20, 19, 24, 22, 27, 25, 30],
    sparklineColor: "#06b6d4",
  },
  {
    id: "visitors",
    label: "Visitors",
    value: "8,425",
    delta: "12.5%",
    deltaDirection: "up",
    compareLabel: "vs last 7 days",
    icon: "users",
    iconBg: "bg-violet-50",
    iconColor: "text-violet-500",
    sparkline: [20, 24, 18, 28, 26, 30, 27, 33],
    sparklineColor: "#8b5cf6",
  },
  {
    id: "products-sold",
    label: "Products Sold",
    value: "1,701",
    delta: "11.2%",
    deltaDirection: "up",
    compareLabel: "vs last 7 days",
    icon: "package",
    iconBg: "bg-teal-50",
    iconColor: "text-teal-500",
    sparkline: [22, 25, 21, 28, 26, 31, 29, 34],
    sparklineColor: "#14b8a6",
  },
  {
    id: "refunds",
    label: "Refunds",
    value: "$412.30",
    delta: "3.2%",
    deltaDirection: "down",
    compareLabel: "vs last 7 days",
    icon: "rotate-ccw",
    iconBg: "bg-rose-50",
    iconColor: "text-rose-500",
    sparkline: [9, 8, 10, 7, 9, 6, 8, 6],
    sparklineColor: "#f43f5e",
  },
  {
    id: "profit",
    label: "Profit",
    value: "$6,451.20",
    delta: "21.3%",
    deltaDirection: "up",
    compareLabel: "vs last 7 days",
    icon: "dollar",
    iconBg: "bg-green-50",
    iconColor: "text-green-500",
    sparkline: [10, 14, 12, 19, 16, 24, 21, 28],
    sparklineColor: "#22c55e",
  },
  {
    id: "active-carts",
    label: "Active Carts",
    value: "64",
    delta: "5 in last hour",
    deltaDirection: "up",
    compareLabel: "right now",
    icon: "cart",
    iconBg: "bg-blue-50",
    iconColor: "text-blue-500",
    sparkline: [11, 13, 12, 15, 14, 17, 15, 18],
    sparklineColor: "#3b82f6",
  },
  {
    id: "abandoned-checkouts",
    label: "Abandoned Checkouts",
    value: "38",
    delta: "6.8%",
    deltaDirection: "up",
    compareLabel: "vs last 7 days",
    icon: "alert-triangle",
    iconBg: "bg-red-50",
    iconColor: "text-red-500",
    sparkline: [6, 7, 6, 9, 8, 10, 9, 11],
    sparklineColor: "#ef4444",
  },
];

export type SalesRange = "Hourly" | "Daily" | "Weekly" | "Monthly" | "Yearly" | "Custom Range";

export const salesRangeOptions: SalesRange[] = ["Hourly", "Daily", "Weekly", "Monthly", "Yearly", "Custom Range"];

export const salesOverviewByRange: Record<Exclude<SalesRange, "Custom Range">, { label: string; sales: number; orders: number }[]> = {
  Hourly: [
    { label: "6am", sales: 180, orders: 2 },
    { label: "8am", sales: 420, orders: 4 },
    { label: "10am", sales: 860, orders: 7 },
    { label: "12pm", sales: 1240, orders: 11 },
    { label: "2pm", sales: 980, orders: 9 },
    { label: "4pm", sales: 1360, orders: 13 },
    { label: "6pm", sales: 1580, orders: 15 },
    { label: "8pm", sales: 1120, orders: 10 },
  ],
  Daily: [
    { label: "May 10", sales: 5200, orders: 22 },
    { label: "May 11", sales: 4600, orders: 18 },
    { label: "May 12", sales: 6100, orders: 26 },
    { label: "May 13", sales: 5400, orders: 21 },
    { label: "May 14", sales: 6800, orders: 30 },
    { label: "May 15", sales: 6200, orders: 27 },
    { label: "May 16", sales: 7300, orders: 34 },
  ],
  Weekly: [
    { label: "Wk 1", sales: 28400, orders: 132 },
    { label: "Wk 2", sales: 31200, orders: 145 },
    { label: "Wk 3", sales: 26800, orders: 121 },
    { label: "Wk 4", sales: 34600, orders: 158 },
    { label: "Wk 5", sales: 33100, orders: 150 },
    { label: "Wk 6", sales: 37900, orders: 171 },
    { label: "Wk 7", sales: 39500, orders: 179 },
  ],
  Monthly: [
    { label: "Jan", sales: 118000, orders: 540 },
    { label: "Feb", sales: 109500, orders: 502 },
    { label: "Mar", sales: 132400, orders: 601 },
    { label: "Apr", sales: 126800, orders: 578 },
    { label: "May", sales: 145200, orders: 662 },
    { label: "Jun", sales: 138900, orders: 631 },
  ],
  Yearly: [
    { label: "2021", sales: 980000, orders: 4200 },
    { label: "2022", sales: 1240000, orders: 5300 },
    { label: "2023", sales: 1510000, orders: 6400 },
    { label: "2024", sales: 1820000, orders: 7600 },
    { label: "2025", sales: 2140000, orders: 8900 },
  ],
};

export const salesByChannel = [
  { channel: "Online Store", pct: 72.4, amount: "$17,778.20", color: "#4f46e5" },
  { channel: "Mobile App", pct: 12.6, amount: "$3,098.40", color: "#f97316" },
  { channel: "Amazon", pct: 6.8, amount: "$1,672.60", color: "#10b981" },
  { channel: "Facebook", pct: 4.2, amount: "$1,031.40", color: "#94a3b8" },
  { channel: "Other", pct: 4.0, amount: "$980.30", color: "#3b82f6" },
];

export const tasks = [
  { id: 1, label: "50+ orders to fulfill", priority: "High priority", color: "text-red-500", dot: "bg-red-500" },
  { id: 2, label: "3 low stock products", priority: "Medium", color: "text-orange-500", dot: "bg-orange-400" },
  { id: 3, label: "2 refund requests", priority: "Medium", color: "text-orange-500", dot: "bg-orange-400" },
  { id: 4, label: "Update shipping rates", priority: "Low", color: "text-gray-400", dot: "bg-gray-300" },
  { id: 5, label: "Complete store setup", priority: "Low", color: "text-gray-400", dot: "bg-gray-300" },
];

export type OrderActionKey = "view" | "edit" | "refund" | "print" | "archive";

export const orderActions: { key: OrderActionKey; label: string }[] = [
  { key: "view", label: "View" },
  { key: "edit", label: "Edit" },
  { key: "refund", label: "Refund" },
  { key: "print", label: "Print" },
  { key: "archive", label: "Archive" },
];

export const recentOrders = [
  { id: "#1059", customer: "Sarah Johnson", total: "$189.99", payment: "Paid", fulfillment: "Fulfilled", date: "May 16, 10:24 AM" },
  { id: "#1058", customer: "Mike Davis", total: "$79.50", payment: "Paid", fulfillment: "Unfulfilled", date: "May 16, 09:58 AM" },
  { id: "#1057", customer: "Emily Wilson", total: "$239.00", payment: "Paid", fulfillment: "Partial", date: "May 16, 09:32 AM" },
  { id: "#1056", customer: "James Brown", total: "$129.90", payment: "Pending", fulfillment: "Unfulfilled", date: "May 16, 09:15 AM" },
  { id: "#1055", customer: "Jessica Taylor", total: "$59.99", payment: "Refunded", fulfillment: "Fulfilled", date: "May 16, 08:47 AM" },
];

export type InventoryAlertType = "low" | "out" | "overstock" | "incoming";

export const inventoryAlerts: { id: number; name: string; status: string; type: InventoryAlertType; count: number }[] = [
  { id: 1, name: "Wireless Headphones", status: "Only 5 left in stock", type: "low", count: 5 },
  { id: 2, name: "Smart Watch Series 5", status: "Only 8 left in stock", type: "low", count: 8 },
  { id: 3, name: "Bluetooth Speaker", status: "Out of stock", type: "out", count: 0 },
  { id: 4, name: "Canvas Tote Bag", status: "128 units, slow turnover", type: "overstock", count: 128 },
  { id: 5, name: "Phone Case (restock)", status: "Arriving May 20", type: "incoming", count: 200 },
];

export const inventoryAlertMeta: Record<InventoryAlertType, { label: string; textClass: string; bgClass: string }> = {
  low: { label: "Low stock", textClass: "text-warning", bgClass: "bg-warning-bg" },
  out: { label: "Out of stock", textClass: "text-danger", bgClass: "bg-danger-bg" },
  overstock: { label: "Overstock", textClass: "text-violet-600", bgClass: "bg-violet-50" },
  incoming: { label: "Incoming stock", textClass: "text-info", bgClass: "bg-info-bg" },
};

export const customerInsights = [
  { id: 1, label: "New Customers", value: "+128", delta: "15.4%", direction: "up" as const, color: "text-blue-500", bg: "bg-blue-50" },
  { id: 2, label: "Returning Customers", value: "+243", delta: "18.7%", direction: "up" as const, color: "text-cyan-500", bg: "bg-cyan-50" },
  { id: 3, label: "VIP Customers", value: "36", delta: "2 new", direction: "up" as const, color: "text-amber-500", bg: "bg-amber-50" },
  { id: 4, label: "Customer Lifetime Value", value: "$278.42", delta: "12.3%", direction: "up" as const, color: "text-emerald-500", bg: "bg-emerald-50" },
  { id: 5, label: "Churn Risk Customers", value: "23", delta: "4.1%", direction: "up" as const, color: "text-red-500", bg: "bg-red-50" },
];

export const marketingPerformance = [
  { id: 1, name: "Email Campaign", metric: "Open Rate", value: "45.6%", delta: "8.2%", icon: "mail", color: "text-blue-500", bg: "bg-blue-50" },
  { id: 2, name: "SMS Campaign", metric: "Click Rate", value: "12.3%", delta: "3.1%", icon: "sms", color: "text-emerald-500", bg: "bg-emerald-50" },
  { id: 3, name: "Facebook Ads", metric: "ROAS", value: "4.6x", delta: "12.7%", icon: "facebook", color: "text-blue-600", bg: "bg-blue-50" },
  { id: 4, name: "Google Ads", metric: "ROAS", value: "3.2x", delta: "8.4%", icon: "google", color: "text-amber-500", bg: "bg-amber-50" },
  { id: 5, name: "Ad Spend (MTD)", metric: "Total spend", value: "$2,140", delta: "6.1%", icon: "spend", color: "text-rose-500", bg: "bg-rose-50" },
];

export const storeHealth = [
  { id: 1, label: "Website Uptime", value: "100%", status: "Healthy", level: "good" as const },
  { id: 2, label: "Checkout", value: "Working", status: "Healthy", level: "good" as const },
  { id: 3, label: "Payment Gateway", value: "All systems operational", status: "Healthy", level: "good" as const },
  { id: 4, label: "Shipping Providers", value: "2 issues detected", status: "Warning", level: "warn" as const },
  { id: 5, label: "App Errors", value: "1 app degraded", status: "Warning", level: "warn" as const },
  { id: 6, label: "Security Alerts", value: "No threats detected", status: "Healthy", level: "good" as const },
];

export const topProducts = [
  { id: 1, name: "Wireless Headphones", sold: 432, revenue: "$12,960.00" },
  { id: 2, name: "Smart Watch Series 5", sold: 312, revenue: "$15,600.00" },
  { id: 3, name: "Bluetooth Speaker", sold: 289, revenue: "$7,225.00" },
  { id: 4, name: "Leather Backpack", sold: 156, revenue: "$4,680.00" },
  { id: 5, name: "Phone Case", sold: 512, revenue: "$3,584.00" },
];

export const aiCapabilities = [
  "Summarize today's business",
  "Explain revenue changes",
  "Forecast inventory shortages",
  "Recommend discounts",
  "Predict churn",
  "Suggest marketing actions",
  "Generate reports",
  "Answer natural-language questions",
];

export const quickActions = [
  { id: 1, label: "Add Product", icon: "tag", color: "text-red-500", bg: "bg-red-50" },
  { id: 2, label: "Create Order", icon: "package", color: "text-emerald-500", bg: "bg-emerald-50" },
  { id: 3, label: "Create Discount", icon: "percent", color: "text-orange-500", bg: "bg-orange-50" },
  { id: 4, label: "Add Customer", icon: "user-plus", color: "text-indigo-500", bg: "bg-indigo-50" },
  { id: 5, label: "Import Products", icon: "upload", color: "text-blue-500", bg: "bg-blue-50" },
  { id: 6, label: "Export Data", icon: "download", color: "text-emerald-500", bg: "bg-emerald-50" },
  { id: 7, label: "Send Campaign", icon: "send", color: "text-violet-500", bg: "bg-violet-50" },
  { id: 8, label: "View Reports", icon: "bar-chart", color: "text-cyan-500", bg: "bg-cyan-50" },
];

export type NotificationType =
  | "order"
  | "payment-failed"
  | "refund"
  | "chargeback"
  | "inventory"
  | "shipping"
  | "app"
  | "mention";

export const notifications: { id: number; type: NotificationType; title: string; body: string; time: string; read: boolean }[] = [
  { id: 1, type: "order", title: "New order #1059", body: "Sarah Johnson placed an order for $189.99", time: "2m ago", read: false },
  { id: 2, type: "payment-failed", title: "Payment failed", body: "Order #1052 payment declined by gateway", time: "18m ago", read: false },
  { id: 3, type: "refund", title: "Refund requested", body: "James Brown requested a refund for #1041", time: "41m ago", read: false },
  { id: 4, type: "chargeback", title: "Chargeback opened", body: "Chargeback filed on order #1032 by customer's bank", time: "1h ago", read: false },
  { id: 5, type: "inventory", title: "Low inventory", body: "Bluetooth Speaker is out of stock", time: "2h ago", read: true },
  { id: 6, type: "shipping", title: "Shipping delay", body: "Carrier reports delays on 3 outbound shipments", time: "3h ago", read: true },
  { id: 7, type: "app", title: "App update available", body: "Reviews & Ratings app has a new version", time: "5h ago", read: true },
  { id: 8, type: "mention", title: "Staff mention", body: "Mike tagged you in a note on order #1048", time: "Yesterday", read: true },
];

export type ActivityType = "order" | "payment" | "customer" | "product" | "discount" | "inventory" | "system";

export const activityFeed: { id: number; type: ActivityType; text: string; actor: string; time: string }[] = [
  { id: 1, type: "order", text: "Order #1059 placed", actor: "Sarah Johnson", time: "2m ago" },
  { id: 2, type: "payment", text: "Payment captured for #1058", actor: "System", time: "12m ago" },
  { id: 3, type: "customer", text: "New customer account created", actor: "Mike Davis", time: "34m ago" },
  { id: 4, type: "product", text: "Product \"Wireless Headphones\" updated", actor: "John Doe", time: "1h ago" },
  { id: 5, type: "discount", text: "Discount \"SUMMER20\" activated", actor: "John Doe", time: "2h ago" },
  { id: 6, type: "inventory", text: "Inventory adjusted: Bluetooth Speaker → 0", actor: "System", time: "2h ago" },
  { id: 7, type: "order", text: "Order #1041 refunded", actor: "John Doe", time: "3h ago" },
  { id: 8, type: "system", text: "Shipping rates updated for US zone", actor: "John Doe", time: "5h ago" },
];

export const storeSwitcherItems = [
  { id: "main", name: "TVS Motor Store", domain: "tvsmotor.com", active: true },
  { id: "wholesale", name: "TVS Wholesale (B2B)", domain: "wholesale.tvsmotor.com", active: false },
  { id: "outlet", name: "TVS Outlet", domain: "outlet.tvsmotor.com", active: false },
];

export const appSwitcherItems = [
  { id: "admin", label: "Admin", icon: "layout-dashboard" },
  { id: "storefront", label: "Storefront", icon: "monitor" },
  { id: "pos", label: "Point of Sale", icon: "store" },
  { id: "partner", label: "Partner Center", icon: "users" },
  { id: "ai-center", label: "AI Center", icon: "sparkles" },
  { id: "analytics", label: "Analytics", icon: "bar-chart-2" },
];

export const mainNav = [
  { id: "dashboard", label: "Dashboard", icon: "layout-dashboard", href: "/" },
  { id: "orders", label: "Orders", icon: "shopping-bag", href: "/orders", badge: "54" },
  { id: "products", label: "Products", icon: "package", href: "/products" },
  { id: "customers", label: "Customers", icon: "users", href: "/customers" },
  { id: "marketing", label: "Marketing", icon: "megaphone", href: "/marketing" },
  { id: "discounts", label: "Discounts", icon: "percent", href: "/discounts" },
  { id: "content", label: "Content", icon: "file-text", href: "/content" },
  { id: "markets", label: "Markets", icon: "globe", href: "/markets" },
  { id: "analytics", label: "Analytics", icon: "bar-chart-2", href: "/analytics" },
  { id: "finance", label: "Finance", icon: "wallet", href: "/finance" },
  { id: "apps", label: "Apps", icon: "grid", href: "/apps" },
  { id: "automations", label: "Automations", icon: "zap", href: "/automations" },
  { id: "ai-center", label: "AI Center", icon: "sparkles", href: "/ai-center", badge: "New" },
];

export const salesChannels = [
  { id: "online-store", label: "Online Store", icon: "monitor", eye: true },
  { id: "pos", label: "Point of Sale", icon: "store" },
  { id: "mobile-app", label: "Mobile App", icon: "smartphone" },
  { id: "buy-button", label: "Buy Button", icon: "mouse-pointer-click" },
  { id: "facebook", label: "Facebook", icon: "facebook" },
  { id: "amazon", label: "Amazon", icon: "amazon" },
  { id: "tiktok", label: "TikTok Shop", icon: "tiktok" },
];
