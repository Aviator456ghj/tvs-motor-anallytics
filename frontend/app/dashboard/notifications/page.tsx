"use client";

import { useEffect, useState } from "react";
import { PageHeader, Spinner, EmptyState } from "@/components/ui";
import { api } from "@/lib/api";
import { Notification } from "@/lib/types";

export default function NotificationsPage() {
  const [items, setItems] = useState<Notification[] | null>(null);

  function refresh() {
    api.get<Notification[]>("/notifications").then(setItems).catch(() => setItems([]));
  }

  useEffect(refresh, []);

  async function markRead(id: string) {
    await api.patch(`/notifications/${id}/read`);
    refresh();
  }

  async function markAllRead() {
    await api.post("/notifications/read-all");
    refresh();
  }

  if (!items) return <Spinner />;

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <PageHeader title="Notifications" />
        {items.some((n) => !n.is_read) && (
          <button onClick={markAllRead} className="btn-secondary">
            Mark all read
          </button>
        )}
      </div>
      {items.length === 0 ? (
        <EmptyState message="You're all caught up." />
      ) : (
        <div className="space-y-2">
          {items.map((n) => (
            <button
              key={n.id}
              onClick={() => !n.is_read && markRead(n.id)}
              className={`card block w-full text-left ${!n.is_read ? "border-brand-200 bg-brand-50/40" : ""}`}
            >
              <div className="flex items-center justify-between">
                <p className="font-medium text-slate-800">{n.title}</p>
                <p className="text-xs text-slate-400">{new Date(n.created_at).toLocaleString()}</p>
              </div>
              <p className="mt-1 text-sm text-slate-600">{n.message}</p>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
