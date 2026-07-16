"use client";

import { useEffect, useState } from "react";
import { PageHeader, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { Business } from "@/lib/types";

const PLANS = [
  { id: "free", name: "Free", price: "₹0/mo", features: ["Up to 3 active services", "Standard listing placement", "Basic analytics"] },
  { id: "starter", name: "Starter", price: "₹999/mo", features: ["Unlimited services", "Priority listing", "Instant booking enabled"] },
  { id: "pro", name: "Pro", price: "₹2,499/mo", features: ["Featured placement", "AI pricing suggestions", "Lower commission rate"] },
  { id: "enterprise", name: "Enterprise", price: "Talk to us", features: ["Multi-location support", "Dedicated account manager", "Custom integrations"] },
];

export default function SubscriptionPage() {
  const [business, setBusiness] = useState<Business | null>(null);

  useEffect(() => {
    api.get<Business>("/businesses/me").then(setBusiness);
  }, []);

  if (!business) return <Spinner />;

  return (
    <div>
      <PageHeader title="Subscription" description="Upgrade your plan to unlock premium placement and lower commission." />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {PLANS.map((plan) => (
          <div key={plan.id} className={`card ${business.subscription_plan === plan.id ? "ring-2 ring-brand-600" : ""}`}>
            <h3 className="font-semibold text-slate-900">{plan.name}</h3>
            <p className="mt-1 text-xl font-bold text-brand-700">{plan.price}</p>
            <ul className="mt-3 space-y-1 text-sm text-slate-600">
              {plan.features.map((f) => (
                <li key={f}>• {f}</li>
              ))}
            </ul>
            {business.subscription_plan === plan.id ? (
              <p className="mt-4 text-xs font-medium text-brand-700">Current plan</p>
            ) : (
              <button className="btn-secondary mt-4 w-full" disabled>
                Contact sales
              </button>
            )}
          </div>
        ))}
      </div>
      <p className="mt-4 text-xs text-slate-400">
        Self-serve plan upgrades and billing aren&apos;t wired to a payment gateway yet — see docs/ROADMAP.md.
      </p>
    </div>
  );
}
