"use client";

import { PageHeader, StatCard } from "@/components/ui";
import { useAuth } from "@/lib/auth";

export default function WalletPage() {
  const { user } = useAuth();

  return (
    <div>
      <PageHeader title="Wallet" description="Refunds and cashback are credited here for faster future bookings." />
      <div className="max-w-xs">
        <StatCard label="Wallet balance" value={`₹${(user?.wallet_balance ?? 0).toLocaleString()}`} />
      </div>
      <p className="mt-6 text-sm text-slate-400">
        Wallet top-up and UPI/card auto-load are on the roadmap — see docs/ROADMAP.md. Balance today accrues from
        refunds processed by the platform.
      </p>
    </div>
  );
}
