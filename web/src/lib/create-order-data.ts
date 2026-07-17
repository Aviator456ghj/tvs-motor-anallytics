export type Address = {
  name: string;
  company?: string;
  line1: string;
  line2?: string;
  city: string;
  state: string;
  country: string;
  postalCode: string;
  phone: string;
};

export type CustomerLite = {
  id: string;
  name: string;
  email: string;
  phone: string;
  registered: boolean;
  since: string;
  totalOrders: number;
  lifetimeSpend: number;
  outstandingBalance: number;
  tags: string[];
  billingAddress: Address;
  shippingAddress: Address;
};

export const customers: CustomerLite[] = [
  {
    id: "cust-1",
    name: "Jane Smith",
    email: "jane.smith@email.com",
    phone: "+1 555-123-4567",
    registered: true,
    since: "Jan 2023",
    totalOrders: 24,
    lifetimeSpend: 4560.9,
    outstandingBalance: 120.0,
    tags: ["VIP"],
    billingAddress: {
      name: "Jane Smith",
      line1: "123 Main Street",
      city: "New York",
      state: "NY",
      country: "United States",
      postalCode: "10001",
      phone: "+1 555-123-4567",
    },
    shippingAddress: {
      name: "Jane Smith",
      line1: "456 Park Avenue",
      city: "New York",
      state: "NY",
      country: "United States",
      postalCode: "10022",
      phone: "+1 555-123-4567",
    },
  },
  {
    id: "cust-2",
    name: "Robert Brown",
    email: "robert.brown@email.com",
    phone: "+1 555-345-6789",
    registered: true,
    since: "Aug 2024",
    totalOrders: 5,
    lifetimeSpend: 620.5,
    outstandingBalance: 0,
    tags: [],
    billingAddress: {
      name: "Robert Brown",
      line1: "88 Amazon Way",
      city: "Seattle",
      state: "WA",
      country: "United States",
      postalCode: "98101",
      phone: "+1 555-345-6789",
    },
    shippingAddress: {
      name: "Robert Brown",
      line1: "88 Amazon Way",
      city: "Seattle",
      state: "WA",
      country: "United States",
      postalCode: "98101",
      phone: "+1 555-345-6789",
    },
  },
  {
    id: "cust-3",
    name: "Emily Wilson",
    email: "emily.wilson@email.com",
    phone: "+1 555-456-7890",
    registered: false,
    since: "New",
    totalOrders: 0,
    lifetimeSpend: 0,
    outstandingBalance: 0,
    tags: ["gift"],
    billingAddress: {
      name: "Emily Wilson",
      line1: "12 Birch Lane",
      city: "Austin",
      state: "TX",
      country: "United States",
      postalCode: "73301",
      phone: "+1 555-456-7890",
    },
    shippingAddress: {
      name: "Emily Wilson",
      line1: "12 Birch Lane",
      city: "Austin",
      state: "TX",
      country: "United States",
      postalCode: "73301",
      phone: "+1 555-456-7890",
    },
  },
];

export const customerRecentOrders: Record<string, { id: string; date: string; total: string; status: string }[]> = {
  "cust-1": [
    { id: "#ORD-2841", date: "May 15, 2025", total: "$299.00", status: "Completed" },
    { id: "#ORD-2810", date: "May 10, 2025", total: "$159.00", status: "Completed" },
    { id: "#ORD-2765", date: "Apr 28, 2025", total: "$89.00", status: "Processing" },
  ],
  "cust-2": [{ id: "#ORD-2841", date: "May 15, 2025", total: "$89.00", status: "Completed" }],
  "cust-3": [],
};

export const customerNotes: Record<string, { title: string; body: string; author: string; date: string }[]> = {
  "cust-1": [
    {
      title: "VIP Customer",
      body: "Prefers express shipping. Sensitive about delivery timing. Always inform before shipping.",
      author: "John Doe",
      date: "May 10, 2025",
    },
  ],
  "cust-2": [],
  "cust-3": [],
};

export const customerHistory: Record<string, { purchaseFrequency: string; avgOrderValue: string; favoriteProducts: string[]; returns: string }> = {
  "cust-1": { purchaseFrequency: "Every 12 days", avgOrderValue: "$190.04", favoriteProducts: ["Wireless Headphones", "Smart Watch Series 8"], returns: "1 return (Apr 2025)" },
  "cust-2": { purchaseFrequency: "Every 45 days", avgOrderValue: "$124.10", favoriteProducts: ["Running Shoes Pro"], returns: "No returns" },
  "cust-3": { purchaseFrequency: "New customer", avgOrderValue: "—", favoriteProducts: [], returns: "No returns" },
};

export type OrderableProduct = {
  id: string;
  name: string;
  variant: string;
  sku: string;
  price: number;
  stock: number;
};

export const orderableProducts: OrderableProduct[] = [
  { id: "p1", name: "Wireless Headphones", variant: "Over-ear, Black", sku: "WH-1000XM5-BLK", price: 199, stock: 128 },
  { id: "p2", name: "Smart Watch Series 8", variant: "45mm, GPS", sku: "SW-8-45-GPS", price: 399, stock: 64 },
  { id: "p3", name: "Classic Cotton T-Shirt", variant: "Blue / L", sku: "CT-TSHIRT-BLU-L", price: 29, stock: 0 },
  { id: "p4", name: "Leather Backpack", variant: "Brown", sku: "LB-BRN-01", price: 129, stock: 18 },
  { id: "p5", name: "Running Shoes Pro", variant: "Black / 42", sku: "RS-PRO-BLK-42", price: 89, stock: 256 },
  { id: "p6", name: "Modern Sofa Set", variant: "3 Seater, Gray", sku: "SOFA-3S-GRY", price: 899, stock: 42 },
];

export function inventoryStatusFor(stock: number): "In Stock" | "Low Stock" | "Out of Stock" {
  if (stock === 0) return "Out of Stock";
  if (stock <= 20) return "Low Stock";
  return "In Stock";
}

export const salesChannels = ["Online Store", "Point of Sale", "Mobile App", "Marketplace", "Phone Order"];
export const warehouses = ["Main Warehouse", "New York Warehouse", "West Coast Fulfillment"];
export const currencies = ["USD - US Dollar", "EUR - Euro", "GBP - British Pound", "INR - Indian Rupee"];
export const languages = ["English", "Spanish", "French", "German"];
export const orderPriorities = ["Low", "Medium", "High", "Urgent"] as const;
export type OrderPriority = (typeof orderPriorities)[number];

export const suggestedTags = ["VIP", "Wholesale", "Urgent", "COD", "Corporate", "Gift"];

export type Coupon = { code: string; type: "percent" | "fixed"; value: number; expires: string; usageLimit: number; used: number };

export const coupons: Coupon[] = [
  { code: "WELCOME10", type: "percent", value: 10, expires: "Dec 31, 2025", usageLimit: 500, used: 212 },
  { code: "SAVE20", type: "fixed", value: 20, expires: "Jun 1, 2025", usageLimit: 100, used: 100 },
  { code: "VIP15", type: "percent", value: 15, expires: "Dec 31, 2025", usageLimit: 50, used: 12 },
];

export type ShippingMethod = { id: string; name: string; carrier: string; eta: string; price: number };

export const shippingMethods: ShippingMethod[] = [
  { id: "standard", name: "Standard Shipping", carrier: "USPS", eta: "5–7 business days", price: 0 },
  { id: "express", name: "Express Shipping", carrier: "FedEx", eta: "2–3 business days", price: 15 },
  { id: "overnight", name: "Overnight", carrier: "UPS", eta: "Next business day", price: 35 },
  { id: "pickup", name: "Store Pickup", carrier: "Main Warehouse", eta: "Ready in 2 hours", price: 0 },
];

export type PaymentMethod = { id: string; label: string; description: string };

export const paymentMethods: PaymentMethod[] = [
  { id: "card", label: "Credit / Debit Card", description: "Charge a saved or new card" },
  { id: "cash", label: "Cash", description: "Record a cash payment (POS/phone orders)" },
  { id: "bank-transfer", label: "Bank Transfer", description: "Manual reconciliation required" },
  { id: "pay-later", label: "Pay Later (Net Terms)", description: "B2B customers with approved credit" },
  { id: "split", label: "Split Payment", description: "Combine two or more payment methods" },
];

export const aiCapabilities = [
  "Recommend products",
  "Suggest upsells",
  "Suggest cross-sells",
  "Apply best discount",
  "Check customer history",
  "Detect duplicate orders",
  "Recommend shipping method",
];

export const quickActions = [
  { id: 1, label: "Add Custom Product", icon: "plus" },
  { id: 2, label: "Apply Discount", icon: "percent" },
  { id: 3, label: "Add Gift Card", icon: "gift" },
  { id: 4, label: "Internal Note", icon: "note" },
];

export const fraudChecks = ["Duplicate Orders", "High Refund Customer", "High Risk Address", "Velocity Checks", "Payment Risk", "Blacklist"];

export const wizardSteps = [
  { step: 1, label: "Customer", sub: "Select customer" },
  { step: 2, label: "Products", sub: "Add order items" },
  { step: 3, label: "Shipping", sub: "Shipping details" },
  { step: 4, label: "Payment", sub: "Payment method" },
  { step: 5, label: "Review", sub: "Review & confirm" },
] as const;
