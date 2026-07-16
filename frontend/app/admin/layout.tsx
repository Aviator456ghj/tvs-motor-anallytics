"use client";

import { ReactNode } from "react";
import DashboardShell, { NavSection } from "@/components/DashboardShell";
import { useRequireRole } from "@/lib/auth";
import { Spinner } from "@/components/ui";

const sections: NavSection[] = [
  { label: "Overview", items: [{ href: "/admin", label: "Dashboard" }] },
  {
    label: "Marketplace",
    items: [
      { href: "/admin/orders", label: "All Orders" },
      { href: "/admin/businesses", label: "All Businesses" },
      { href: "/admin/customers", label: "All Customers" },
      { href: "/admin/categories", label: "Categories" },
      { href: "/admin/approvals", label: "Approvals" },
      { href: "/admin/kyc", label: "KYC" },
    ],
  },
  {
    label: "Revenue",
    items: [
      { href: "/admin/revenue", label: "Revenue" },
      { href: "/admin/payouts", label: "Payouts" },
      { href: "/admin/commission", label: "Commission" },
      { href: "/admin/coupons", label: "Coupons" },
    ],
  },
  {
    label: "Operations",
    items: [
      { href: "/admin/support", label: "Support" },
      { href: "/admin/cms", label: "CMS" },
      { href: "/admin/reports", label: "Reports" },
      { href: "/admin/analytics", label: "Analytics" },
      { href: "/admin/ai-insights", label: "AI Insights" },
    ],
  },
];

export default function AdminLayout({ children }: { children: ReactNode }) {
  const { user, loading } = useRequireRole("admin");
  if (loading || !user) return <Spinner />;
  return (
    <DashboardShell title="Super Admin" sections={sections}>
      {children}
    </DashboardShell>
  );
}
