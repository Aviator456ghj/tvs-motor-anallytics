"use client";

import { ReactNode } from "react";
import DashboardShell, { NavSection } from "@/components/DashboardShell";
import { useRequireRole } from "@/lib/auth";
import { Spinner } from "@/components/ui";

const sections: NavSection[] = [
  { label: "Overview", items: [{ href: "/dashboard", label: "Dashboard" }] },
  {
    label: "Discover",
    items: [
      { href: "/browse", label: "Browse Services" },
      { href: "/search", label: "Search" },
      { href: "/dashboard/nearby", label: "Nearby Providers" },
      { href: "/dashboard/recommendations", label: "AI Recommendation" },
    ],
  },
  {
    label: "Bookings",
    items: [
      { href: "/dashboard/bookings", label: "Booking History" },
      { href: "/dashboard/payments", label: "Payments" },
    ],
  },
  {
    label: "Engagement",
    items: [
      { href: "/dashboard/wishlist", label: "Saved Providers" },
      { href: "/dashboard/reviews", label: "Reviews" },
      { href: "/dashboard/chat", label: "Chat" },
      { href: "/dashboard/notifications", label: "Notifications" },
      { href: "/dashboard/wallet", label: "Wallet" },
    ],
  },
];

export default function CustomerLayout({ children }: { children: ReactNode }) {
  const { user, loading } = useRequireRole("customer");
  if (loading || !user) return <Spinner />;
  return (
    <DashboardShell title="Customer Portal" sections={sections}>
      {children}
    </DashboardShell>
  );
}
