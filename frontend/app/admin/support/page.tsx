"use client";

import { useEffect, useState } from "react";
import { PageHeader, Spinner, EmptyState, StatusBadge } from "@/components/ui";
import { api } from "@/lib/api";

interface Ticket {
  id: string;
  subject: string;
  message: string;
  status: string;
  priority: string;
  created_at: string;
}

const STATUSES = ["open", "in_progress", "resolved", "closed"];

export default function SupportPage() {
  const [tickets, setTickets] = useState<Ticket[] | null>(null);

  function refresh() {
    api.get<Ticket[]>("/admin/support-tickets").then(setTickets);
  }

  useEffect(refresh, []);

  async function updateStatus(id: string, status: string) {
    await api.patch(`/admin/support-tickets/${id}/status?new_status=${status}`);
    refresh();
  }

  if (!tickets) return <Spinner />;

  return (
    <div>
      <PageHeader title="Support" description="Customer and business support tickets." />
      {tickets.length === 0 ? (
        <EmptyState message="No support tickets." />
      ) : (
        <div className="space-y-3">
          {tickets.map((t) => (
            <div key={t.id} className="card">
              <div className="flex items-center justify-between">
                <p className="font-medium text-slate-800">{t.subject}</p>
                <StatusBadge status={t.status} />
              </div>
              <p className="mt-1 text-sm text-slate-600">{t.message}</p>
              <div className="mt-3 flex gap-2">
                {STATUSES.map((s) => (
                  <button
                    key={s}
                    onClick={() => updateStatus(t.id, s)}
                    className={`badge ${t.status === s ? "bg-brand-100 text-brand-700" : "bg-slate-100 text-slate-500"}`}
                  >
                    {s.replace("_", " ")}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
