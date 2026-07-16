"use client";

import Link from "next/link";
import { PageHeader } from "@/components/ui";

const GROUPS: { title: string; items: { href: string; label: string; desc: string }[] }[] = [
  {
    title: "Business",
    items: [
      { href: "/business/profile", label: "Company profile", desc: "Name, tagline, description, and public details" },
      { href: "/business/settings/locations", label: "Locations", desc: "Studio addresses and home-service radius" },
      { href: "/business/settings/policies", label: "Policies", desc: "Cancellation and refund policy shown to customers" },
    ],
  },
  {
    title: "Payments",
    items: [
      { href: "/business/settings/payout-account", label: "Payout account", desc: "Bank account payouts are sent to" },
      { href: "/business/subscription", label: "Plan & billing", desc: "Your subscription tier and commission rate" },
    ],
  },
  {
    title: "Team",
    items: [
      { href: "/business/staff", label: "Staff accounts", desc: "Teammates with their own login and permission tier" },
      { href: "/business/employees", label: "Team roster", desc: "A simple directory of who works here" },
    ],
  },
  {
    title: "Compliance & notifications",
    items: [
      { href: "/business/documents", label: "KYC documents", desc: "Verification documents for admin review" },
      { href: "/business/settings/notifications", label: "Notifications", desc: "What we email you about" },
    ],
  },
];

export default function SettingsHubPage() {
  return (
    <div>
      <PageHeader title="Settings" description="Everything that configures how your business runs on ServicesOS." />
      <div className="space-y-8">
        {GROUPS.map((group) => (
          <div key={group.title}>
            <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400">{group.title}</h2>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {group.items.map((item) => (
                <Link key={item.href} href={item.href} className="card block hover:border-brand-300 hover:shadow-md">
                  <p className="font-medium text-slate-900">{item.label}</p>
                  <p className="mt-1 text-xs text-slate-500">{item.desc}</p>
                </Link>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
