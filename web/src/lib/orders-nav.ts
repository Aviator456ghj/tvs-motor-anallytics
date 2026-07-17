export type OrdersNavItem = {
  key: string;
  label: string;
  href: string;
  icon: string;
  built: boolean;
};

export const ordersNavItems: OrdersNavItem[] = [
  { key: "dashboard", label: "Dashboard", href: "/orders", icon: "layout-dashboard", built: true },
  { key: "create", label: "Create Order", href: "/orders/create", icon: "plus-square", built: true },
  { key: "details", label: "Order Details", href: "/orders/ORD-2843", icon: "file-text", built: true },
  { key: "fulfillment", label: "Fulfillment Center", href: "/orders/fulfillment", icon: "truck", built: true },
  { key: "returns", label: "Returns (RMA)", href: "/orders/returns", icon: "rotate-ccw", built: false },
  { key: "refunds", label: "Refund Center", href: "/orders/refunds", icon: "banknote", built: false },
  { key: "drafts", label: "Draft Orders", href: "/orders/drafts", icon: "file-edit", built: false },
  { key: "bulk", label: "Bulk Operations", href: "/orders/bulk", icon: "list-checks", built: false },
  { key: "settings", label: "Order Settings", href: "/orders/settings", icon: "settings", built: false },
];
