"use client";

import { ReactNode } from "react";
import DashboardShell, { NavSection } from "@/components/DashboardShell";
import { useRequireRole } from "@/lib/auth";
import { Spinner } from "@/components/ui";

const sections: NavSection[] = [
  { label: "Overview", items: [{ href: "/business", label: "Dashboard" }] },
  {
    label: "Profile",
    items: [
      { href: "/business/profile", label: "Company Profile" },
      { href: "/business/employees", label: "Employees" },
      { href: "/business/documents", label: "Documents (KYC)" },
      { href: "/business/portfolio", label: "Portfolio" },
    ],
  },
  {
    label: "Catalog",
    items: [
      { href: "/business/services", label: "Services & Packages" },
      { href: "/business/pricing", label: "Pricing" },
      { href: "/business/calendar", label: "Calendar" },
      { href: "/business/availability", label: "Availability" },
    ],
  },
  {
    label: "Orders",
    items: [
      { href: "/business/bookings", label: "Orders" },
      { href: "/business/customers", label: "Customers" },
      { href: "/business/reviews", label: "Customer Reviews" },
    ],
  },
  {
    label: "Finance",
    items: [
      { href: "/business/payouts", label: "Payouts" },
      { href: "/business/earnings", label: "Earnings" },
      { href: "/business/analytics", label: "Analytics" },
      { href: "/business/invoices", label: "Invoices" },
    ],
  },
  {
    label: "Account",
    items: [
      { href: "/business/staff", label: "Staff Accounts" },
      { href: "/business/chat", label: "Chat" },
      { href: "/business/subscription", label: "Subscription" },
    ],
  },
];

export default function BusinessLayout({ children }: { children: ReactNode }) {
  const { user, loading } = useRequireRole("business");
  if (loading || !user) return <Spinner />;
  return (
    <DashboardShell title="Business Portal" sections={sections}>
      {children}
    </DashboardShell>
  );
}
