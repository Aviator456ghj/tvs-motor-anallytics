export type ProductStatus = "Active" | "Draft" | "Out of Stock" | "Low Stock" | "Discontinued" | "Archived";
export type ProductBucket = "all" | "active" | "draft" | "out_of_stock" | "low_stock" | "discontinued" | "archived";
export type ProductType = "Simple" | "Variant" | "Digital" | "Bundle" | "Subscription" | "Gift Card" | "Service";

export type Product = {
  id: string;
  name: string;
  variant: string;
  sku: string;
  barcode: string;
  category: string;
  brand: string;
  vendor: string;
  price: number;
  compareAtPrice: number;
  costPrice: number;
  currency: string;
  taxClass: string;
  stock: number;
  reserved: number;
  warehouse: string;
  lowStockThreshold: number;
  status: ProductStatus;
  type: ProductType;
  channels: string[];
  created: string;
  updated: string;
  buckets: ProductBucket[];
};

function makeProducts(): Product[] {
  const rows: Omit<Product, "buckets">[] = [
    {
      id: "1", name: "Wireless Headphones", variant: "Over-ear, Black", sku: "WH-1000XM5-BLK", barcode: "8901234567890",
      category: "Electronics > Audio > Headphones", brand: "Sony", vendor: "Sony Electronics", price: 199, compareAtPrice: 249, costPrice: 120,
      currency: "USD", taxClass: "Standard", stock: 128, reserved: 12, warehouse: "Main Warehouse", lowStockThreshold: 20,
      status: "Active", type: "Simple", channels: ["online-store", "amazon", "facebook", "tiktok"], created: "May 10, 2025 10:23 AM", updated: "May 16, 2025 09:15 AM",
    },
    {
      id: "2", name: "Smart Watch Series 8", variant: "45mm, GPS", sku: "SW-8-45-GPS", barcode: "8901234567891",
      category: "Electronics > Wearables", brand: "Apple", vendor: "Apple Inc.", price: 399, compareAtPrice: 429, costPrice: 240,
      currency: "USD", taxClass: "Standard", stock: 64, reserved: 4, warehouse: "Main Warehouse", lowStockThreshold: 20,
      status: "Active", type: "Simple", channels: ["online-store", "amazon", "facebook", "tiktok"], created: "May 9, 2025 02:10 PM", updated: "May 15, 2025 11:40 AM",
    },
    {
      id: "3", name: "Classic Cotton T-Shirt", variant: "Blue / L", sku: "CT-TSHIRT-BLU-L", barcode: "8901234567892",
      category: "Apparel > T-Shirts", brand: "Everlane", vendor: "Everlane Basics", price: 29, compareAtPrice: 35, costPrice: 9,
      currency: "USD", taxClass: "Standard", stock: 0, reserved: 0, warehouse: "Main Warehouse", lowStockThreshold: 15,
      status: "Out of Stock", type: "Variant", channels: ["online-store", "amazon", "facebook", "tiktok"], created: "Apr 28, 2025 09:00 AM", updated: "May 14, 2025 08:12 AM",
    },
    {
      id: "4", name: "Leather Backpack", variant: "Brown", sku: "LB-BRN-01", barcode: "8901234567893",
      category: "Bags > Backpacks", brand: "Fossil", vendor: "Fossil Group", price: 129, compareAtPrice: 159, costPrice: 62,
      currency: "USD", taxClass: "Standard", stock: 18, reserved: 2, warehouse: "Main Warehouse", lowStockThreshold: 20,
      status: "Low Stock", type: "Simple", channels: ["online-store", "amazon", "facebook", "tiktok"], created: "Apr 20, 2025 04:30 PM", updated: "May 13, 2025 03:05 PM",
    },
    {
      id: "5", name: "Running Shoes Pro", variant: "Black / 42", sku: "RS-PRO-BLK-42", barcode: "8901234567894",
      category: "Footwear > Running", brand: "Nike", vendor: "Nike Inc.", price: 89, compareAtPrice: 110, costPrice: 41,
      currency: "USD", taxClass: "Standard", stock: 256, reserved: 30, warehouse: "Main Warehouse", lowStockThreshold: 25,
      status: "Active", type: "Simple", channels: ["online-store", "amazon", "facebook", "tiktok"], created: "Apr 12, 2025 11:20 AM", updated: "May 12, 2025 01:45 PM",
    },
    {
      id: "6", name: "Modern Sofa Set", variant: "3 Seater, Gray", sku: "SOFA-3S-GRY", barcode: "8901234567895",
      category: "Furniture > Living Room", brand: "IKEA", vendor: "IKEA Home", price: 899, compareAtPrice: 1099, costPrice: 520,
      currency: "USD", taxClass: "Standard", stock: 42, reserved: 5, warehouse: "Main Warehouse", lowStockThreshold: 10,
      status: "Active", type: "Variant", channels: ["online-store", "amazon", "facebook", "tiktok"], created: "Mar 30, 2025 09:50 AM", updated: "May 11, 2025 10:30 AM",
    },
  ];

  const bucketOf = (status: ProductStatus): ProductBucket[] => {
    const map: Record<ProductStatus, ProductBucket> = {
      Active: "active",
      Draft: "draft",
      "Out of Stock": "out_of_stock",
      "Low Stock": "low_stock",
      Discontinued: "discontinued",
      Archived: "archived",
    };
    return ["all", map[status]];
  };

  return rows.map((r) => ({ ...r, buckets: bucketOf(r.status) }));
}

export const products: Product[] = makeProducts();

export const productTabs: { key: ProductBucket; label: string; count: number }[] = [
  { key: "all", label: "All", count: 5324 },
  { key: "active", label: "Active", count: 4832 },
  { key: "draft", label: "Draft", count: 112 },
  { key: "out_of_stock", label: "Out of Stock", count: 286 },
  { key: "low_stock", label: "Low Stock", count: 542 },
  { key: "discontinued", label: "Discontinued", count: 76 },
  { key: "archived", label: "Archived", count: 34 },
];

export type ProductsKpi = {
  id: string;
  label: string;
  value: string;
  delta: string;
  direction: "up" | "down";
  compareLabel: string;
  breakdown: { label: string; value: string }[];
  icon: "boxes" | "check" | "package-x" | "alert-triangle" | "dollar";
  iconBg: string;
  iconColor: string;
};

export const productsKpis: ProductsKpi[] = [
  {
    id: "total-products",
    label: "Total Products",
    value: "5,324",
    delta: "14.2%",
    direction: "up",
    compareLabel: "vs last 7 days",
    breakdown: [
      { label: "Today's added", value: "12" },
      { label: "This month", value: "186" },
      { label: "Growth %", value: "14.2%" },
    ],
    icon: "boxes",
    iconBg: "bg-indigo-50",
    iconColor: "text-indigo-500",
  },
  {
    id: "active-products",
    label: "Active Products",
    value: "4,832",
    delta: "16.7%",
    direction: "up",
    compareLabel: "vs last 7 days",
    breakdown: [
      { label: "Published", value: "4,832" },
      { label: "Draft", value: "112" },
      { label: "Archived", value: "34" },
    ],
    icon: "check",
    iconBg: "bg-emerald-50",
    iconColor: "text-emerald-500",
  },
  {
    id: "out-of-stock",
    label: "Out of Stock",
    value: "286",
    delta: "8.3%",
    direction: "down",
    compareLabel: "vs last 7 days",
    breakdown: [
      { label: "Out of stock", value: "286" },
      { label: "Need purchase", value: "198" },
      { label: "Critical products", value: "34" },
    ],
    icon: "package-x",
    iconBg: "bg-red-50",
    iconColor: "text-red-500",
  },
  {
    id: "low-stock",
    label: "Low Stock",
    value: "542",
    delta: "3.6%",
    direction: "up",
    compareLabel: "vs last 7 days",
    breakdown: [
      { label: "Low inventory", value: "542" },
      { label: "Warning products", value: "310" },
      { label: "Forecasted shortage", value: "48" },
    ],
    icon: "alert-triangle",
    iconBg: "bg-amber-50",
    iconColor: "text-amber-500",
  },
  {
    id: "inventory-value",
    label: "Total Value",
    value: "$1,245,780",
    delta: "21.4%",
    direction: "up",
    compareLabel: "vs last 7 days",
    breakdown: [
      { label: "Cost value", value: "$742,300" },
      { label: "Selling value", value: "$1,245,780" },
      { label: "Profit margin", value: "40.4%" },
    ],
    icon: "dollar",
    iconBg: "bg-green-50",
    iconColor: "text-green-500",
  },
];

export type ProductColumnKey = "category" | "price" | "stock" | "status" | "type" | "channels" | "created" | "updated";

export const productColumns: { key: ProductColumnKey; label: string; defaultVisible: boolean }[] = [
  { key: "category", label: "Category", defaultVisible: true },
  { key: "price", label: "Price", defaultVisible: true },
  { key: "stock", label: "Stock", defaultVisible: true },
  { key: "status", label: "Status", defaultVisible: true },
  { key: "type", label: "Type", defaultVisible: true },
  { key: "channels", label: "Sales Channel", defaultVisible: true },
  { key: "created", label: "Created Date", defaultVisible: false },
  { key: "updated", label: "Updated Date", defaultVisible: false },
];

export const filterGroups = [
  "Status",
  "Brand",
  "Vendor",
  "Collection",
  "Category",
  "Product Type",
  "Sales Channel",
  "Price",
  "Inventory",
  "Created Date",
  "Updated Date",
  "Published",
  "Tags",
];

export const sortOptions = [
  "Date (Newest)",
  "Date (Oldest)",
  "Price (High to Low)",
  "Price (Low to High)",
  "Stock (High to Low)",
  "Name (A–Z)",
];

export type BulkActionKey =
  | "publish"
  | "unpublish"
  | "archive"
  | "delete"
  | "change-category"
  | "change-brand"
  | "update-tags"
  | "update-prices"
  | "inventory-adjustment"
  | "assign-collections"
  | "export"
  | "generate-ai-description";

export const bulkActions: { key: BulkActionKey; label: string; danger?: boolean }[] = [
  { key: "publish", label: "Publish" },
  { key: "unpublish", label: "Unpublish" },
  { key: "archive", label: "Archive" },
  { key: "delete", label: "Delete", danger: true },
  { key: "change-category", label: "Change Category" },
  { key: "change-brand", label: "Change Brand" },
  { key: "update-tags", label: "Update Tags" },
  { key: "update-prices", label: "Update Prices" },
  { key: "inventory-adjustment", label: "Inventory Adjustment" },
  { key: "assign-collections", label: "Assign Collections" },
  { key: "export", label: "Export" },
  { key: "generate-ai-description", label: "Generate AI Description" },
];

export const addProductTypes: ProductType[] = ["Simple", "Variant", "Digital", "Bundle", "Subscription", "Gift Card", "Service"];
export const addProductTypeLabels: Record<ProductType, string> = {
  Simple: "Simple Product",
  Variant: "Variable Product",
  Digital: "Digital Product",
  Bundle: "Bundle Product",
  Subscription: "Subscription Product",
  "Gift Card": "Gift Card",
  Service: "Service Product",
};

export const exportFormats = ["Excel", "CSV", "JSON", "XML"];
export const importSources = ["CSV", "Excel", "Shopify", "WooCommerce", "Magento", "API"];

export const quickActions = [
  { id: 1, label: "Add Product", icon: "plus-square" },
  { id: 2, label: "Import Products", icon: "upload" },
  { id: 3, label: "Export Products", icon: "download" },
  { id: 4, label: "Bulk Edit", icon: "list-checks" },
  { id: 5, label: "Categories", icon: "layers" },
  { id: 6, label: "Brands", icon: "award" },
  { id: 7, label: "Attributes", icon: "list-tree" },
  { id: 8, label: "Reviews", icon: "star" },
  { id: 9, label: "Trash", icon: "trash" },
];

export const productStatusLegend: { label: ProductStatus; description: string; color: string; bg: string; dot: string }[] = [
  { label: "Active", description: "Product is live and available", color: "text-success", bg: "bg-success-bg", dot: "bg-success" },
  { label: "Draft", description: "Product is in draft mode", color: "text-muted", bg: "bg-card-border/60", dot: "bg-slate-500" },
  { label: "Out of Stock", description: "No stock available", color: "text-danger", bg: "bg-danger-bg", dot: "bg-danger" },
  { label: "Low Stock", description: "Stock below threshold", color: "text-warning", bg: "bg-warning-bg", dot: "bg-warning" },
  { label: "Discontinued", description: "Product discontinued", color: "text-muted", bg: "bg-card-border/60", dot: "bg-slate-400" },
  { label: "Archived", description: "Product archived", color: "text-muted", bg: "bg-card-border/60", dot: "bg-slate-400" },
];

export const topCategories = [
  { id: 1, name: "Electronics", count: 1245 },
  { id: 2, name: "Apparel", count: 1023 },
  { id: 3, name: "Footwear", count: 856 },
  { id: 4, name: "Bags", count: 412 },
  { id: 5, name: "Furniture", count: 365 },
];

export const aiInsights = [
  { id: 1, icon: "package-x", text: "12 products are low in stock." },
  { id: 2, icon: "trending-up", text: "6 products have trending sales." },
  { id: 3, icon: "search", text: "3 products need SEO improvement." },
];

export const productAiInsightsDetail = [
  { id: 1, icon: "package-x", text: "12 products running out of stock", tone: "danger" as const },
  { id: 2, icon: "trending-down", text: "8 products have declining sales", tone: "warning" as const },
  { id: 3, icon: "search", text: "4 products need SEO optimization", tone: "info" as const },
  { id: 4, icon: "image", text: "3 products have missing images", tone: "warning" as const },
  { id: 5, icon: "alert-circle", text: "5 products have inconsistent pricing", tone: "danger" as const },
];

export const salesChannelPublishState: { id: string; label: string; status: "Published" | "Hidden" | "Pending Approval" }[] = [
  { id: "online-store", label: "Online Store", status: "Published" },
  { id: "mobile-app", label: "Mobile App", status: "Published" },
  { id: "amazon", label: "Amazon", status: "Published" },
  { id: "facebook", label: "Facebook Shop", status: "Published" },
  { id: "tiktok", label: "TikTok Shop", status: "Published" },
];

export const detailTabs = [
  "Overview",
  "Variants",
  "Inventory",
  "Pricing",
  "Media",
  "SEO",
  "Attributes",
  "Sales",
  "Activity",
  "AI Insights",
] as const;
export type DetailTab = (typeof detailTabs)[number];

export const productVariants = [
  { id: 1, name: "Over-ear, Black", sku: "WH-1000XM5-BLK", price: 199, stock: 128, status: "Active" as ProductStatus },
  { id: 2, name: "Over-ear, Silver", sku: "WH-1000XM5-SLV", price: 199, stock: 42, status: "Active" as ProductStatus },
  { id: 3, name: "Over-ear, Blue", sku: "WH-1000XM5-BLU", price: 209, stock: 0, status: "Out of Stock" as ProductStatus },
];

export const activityLog = [
  { id: 1, text: "Price updated from $189.00 to $199.00", actor: "John Doe", time: "May 16, 09:15 AM" },
  { id: 2, text: "Stock adjusted +40 units (restock)", actor: "System", time: "May 14, 02:20 PM" },
  { id: 3, text: "Published to TikTok Shop", actor: "John Doe", time: "May 12, 11:05 AM" },
  { id: 4, text: "AI description generated", actor: "AI Assistant", time: "May 10, 10:30 AM" },
  { id: 5, text: "Product created", actor: "John Doe", time: "May 10, 10:23 AM" },
];

export const salesStats = [
  { label: "Units sold (30d)", value: "432" },
  { label: "Revenue (30d)", value: "$85,968.00" },
  { label: "Conversion rate", value: "3.8%" },
  { label: "Return rate", value: "1.2%" },
];

export const seoFields = {
  title: "Wireless Headphones – Sony WH-1000XM5 | CommerceOS Store",
  description: "Industry-leading noise cancelling wireless headphones with 30-hour battery life. Free shipping and 30-day returns.",
  handle: "wireless-headphones-sony-wh-1000xm5",
  keywords: ["wireless headphones", "noise cancelling", "sony wh-1000xm5", "bluetooth headphones"],
};

export const productAttributes = [
  { label: "Color", value: "Black" },
  { label: "Connectivity", value: "Bluetooth 5.2" },
  { label: "Battery Life", value: "30 hours" },
  { label: "Weight", value: "250g" },
  { label: "Warranty", value: "1 year" },
];
