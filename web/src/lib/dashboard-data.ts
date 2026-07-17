export type StatCard = {
  id: string;
  label: string;
  value: string;
  delta: string;
  deltaDirection: "up" | "down";
  compareLabel: string;
  icon: "cart" | "bag" | "users" | "filter" | "chart" | "dollar";
  iconBg: string;
  iconColor: string;
  sparkline: number[];
  sparklineColor: string;
};

export const statCards: StatCard[] = [
  {
    id: "total-sales",
    label: "Total Sales",
    value: "$24,560.90",
    delta: "18.6%",
    deltaDirection: "up",
    compareLabel: "vs last 7 days",
    icon: "cart",
    iconBg: "bg-blue-50",
    iconColor: "text-blue-500",
    sparkline: [12, 18, 14, 22, 19, 26, 24, 30],
    sparklineColor: "#3b82f6",
  },
  {
    id: "orders",
    label: "Orders",
    value: "186",
    delta: "14.2%",
    deltaDirection: "up",
    compareLabel: "vs last 7 days",
    icon: "bag",
    iconBg: "bg-emerald-50",
    iconColor: "text-emerald-500",
    sparkline: [8, 12, 10, 16, 14, 18, 20, 19],
    sparklineColor: "#10b981",
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
    id: "net-profit",
    label: "Net Profit",
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
];

export const salesOverview = [
  { day: "May 10", sales: 5200, orders: 22 },
  { day: "May 11", sales: 4600, orders: 18 },
  { day: "May 12", sales: 6100, orders: 26 },
  { day: "May 13", sales: 5400, orders: 21 },
  { day: "May 14", sales: 6800, orders: 30 },
  { day: "May 15", sales: 6200, orders: 27 },
  { day: "May 16", sales: 7300, orders: 34 },
];

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

export const recentOrders = [
  { id: "#1059", customer: "Sarah Johnson", total: "$189.99", status: "Paid", date: "May 16, 10:24 AM" },
  { id: "#1058", customer: "Mike Davis", total: "$79.50", status: "Paid", date: "May 16, 09:58 AM" },
  { id: "#1057", customer: "Emily Wilson", total: "$239.00", status: "Paid", date: "May 16, 09:32 AM" },
  { id: "#1056", customer: "James Brown", total: "$129.90", status: "Pending", date: "May 16, 09:15 AM" },
  { id: "#1055", customer: "Jessica Taylor", total: "$59.99", status: "Paid", date: "May 16, 08:47 AM" },
];

export const inventoryAlerts = [
  { id: 1, name: "Wireless Headphones", status: "Only 5 left in stock", level: "low", count: 5 },
  { id: 2, name: "Smart Watch Series 5", status: "Only 8 left in stock", level: "low", count: 8 },
  { id: 3, name: "Bluetooth Speaker", status: "Out of stock", level: "out", count: 0 },
  { id: 4, name: "Leather Backpack", status: "Low stock", level: "low", count: 12 },
  { id: 5, name: "Phone Case", status: "Low stock", level: "low", count: 15 },
];

export const customerInsights = [
  { id: 1, label: "New Customers", value: "+128", delta: "15.4%", direction: "up" as const, color: "text-blue-500", bg: "bg-blue-50" },
  { id: 2, label: "Returning Customers", value: "+243", delta: "18.7%", direction: "up" as const, color: "text-cyan-500", bg: "bg-cyan-50" },
  { id: 3, label: "Repeat Purchase Rate", value: "32.6%", delta: "6.2%", direction: "up" as const, color: "text-indigo-500", bg: "bg-indigo-50" },
  { id: 4, label: "Customer Lifetime Value", value: "$278.42", delta: "12.3%", direction: "up" as const, color: "text-emerald-500", bg: "bg-emerald-50" },
  { id: 5, label: "Churn Risk Customers", value: "23", delta: "4.1%", direction: "up" as const, color: "text-red-500", bg: "bg-red-50" },
];

export const marketingPerformance = [
  { id: 1, name: "Email Campaign", metric: "Open Rate", value: "45.6%", delta: "8.2%", icon: "mail", color: "text-blue-500", bg: "bg-blue-50" },
  { id: 2, name: "SMS Campaign", metric: "Click Rate", value: "12.3%", delta: "3.1%", icon: "sms", color: "text-emerald-500", bg: "bg-emerald-50" },
  { id: 3, name: "Facebook Ads", metric: "ROAS", value: "4.6x", delta: "12.7%", icon: "facebook", color: "text-blue-600", bg: "bg-blue-50" },
  { id: 4, name: "Google Ads", metric: "ROAS", value: "3.2x", delta: "8.4%", icon: "google", color: "text-amber-500", bg: "bg-amber-50" },
];

export const storeHealth = [
  { id: 1, label: "Store Uptime", value: "100%", status: "Healthy", level: "good" as const },
  { id: 2, label: "Checkout", value: "Working", status: "Healthy", level: "good" as const },
  { id: 3, label: "Payment Gateway", value: "All systems operational", status: "Healthy", level: "good" as const },
  { id: 4, label: "Shipping Providers", value: "2 issues detected", status: "Warning", level: "warn" as const },
  { id: 5, label: "SSL Certificate", value: "Valid", status: "Healthy", level: "good" as const },
];

export const topProducts = [
  { id: 1, name: "Wireless Headphones", sold: 432, revenue: "$12,960.00" },
  { id: 2, name: "Smart Watch Series 5", sold: 312, revenue: "$15,600.00" },
  { id: 3, name: "Bluetooth Speaker", sold: 289, revenue: "$7,225.00" },
  { id: 4, name: "Leather Backpack", sold: 156, revenue: "$4,680.00" },
  { id: 5, name: "Phone Case", sold: 512, revenue: "$3,584.00" },
];

export const aiSuggestions = [
  "Why did sales increase yesterday?",
  "What products are low in stock?",
  "Show me top selling products",
  "Forecast sales for next 7 days",
];

export const quickActions = [
  { id: 1, label: "Add Product", icon: "tag", color: "text-red-500", bg: "bg-red-50" },
  { id: 2, label: "Create Order", icon: "package", color: "text-emerald-500", bg: "bg-emerald-50" },
  { id: 3, label: "Create Discount", icon: "percent", color: "text-orange-500", bg: "bg-orange-50" },
  { id: 4, label: "Add Customer", icon: "user-plus", color: "text-indigo-500", bg: "bg-indigo-50" },
  { id: 5, label: "Import Products", icon: "upload", color: "text-blue-500", bg: "bg-blue-50" },
  { id: 6, label: "Export Data", icon: "download", color: "text-emerald-500", bg: "bg-emerald-50" },
  { id: 7, label: "Send Email", icon: "send", color: "text-violet-500", bg: "bg-violet-50" },
  { id: 8, label: "View Reports", icon: "bar-chart", color: "text-cyan-500", bg: "bg-cyan-50" },
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
