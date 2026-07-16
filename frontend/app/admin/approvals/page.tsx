"use client";

import { useEffect, useState } from "react";
import { PageHeader, Spinner, EmptyState } from "@/components/ui";
import { api } from "@/lib/api";
import { Business } from "@/lib/types";

export default function ApprovalsPage() {
  const [pending, setPending] = useState<Business[] | null>(null);

  function refresh() {
    api.get<Business[]>("/admin/businesses?pending_only=true").then(setPending);
  }

  useEffect(refresh, []);

  async function approve(id: string) {
    await api.patch(`/admin/businesses/${id}/approve`);
    refresh();
  }

  if (!pending) return <Spinner />;

  return (
    <div>
      <PageHeader title="Pending approvals" description="New businesses waiting to go live on the marketplace." />
      {pending.length === 0 ? (
        <EmptyState message="No pending approvals. You're all caught up." />
      ) : (
        <div className="space-y-3">
          {pending.map((b) => (
            <div key={b.id} className="card flex items-center justify-between">
              <div>
                <p className="font-medium text-slate-800">{b.company_name}</p>
                <p className="text-sm text-slate-500">{b.city} · KYC: {b.kyc_status}</p>
              </div>
              <button onClick={() => approve(b.id)} className="btn-primary text-sm">
                Approve
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
