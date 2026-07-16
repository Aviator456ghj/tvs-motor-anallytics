"use client";

import { useEffect, useState } from "react";
import { PageHeader, Spinner, EmptyState, StatusBadge } from "@/components/ui";
import { api } from "@/lib/api";
import { CustomerDetail, CustomerSummary } from "@/lib/types";

export default function CustomersPage() {
  const [customers, setCustomers] = useState<CustomerSummary[] | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [detail, setDetail] = useState<CustomerDetail | null>(null);

  useEffect(() => {
    api.get<CustomerSummary[]>("/businesses/me/customers").then(setCustomers);
  }, []);

  useEffect(() => {
    if (!activeId) {
      setDetail(null);
      return;
    }
    api.get<CustomerDetail>(`/businesses/me/customers/${activeId}`).then(setDetail);
  }, [activeId]);

  if (!customers) return <Spinner />;

  return (
    <div>
      <PageHeader title="Customers" description="Everyone who has booked your services, ranked by most recent order." />
      {customers.length === 0 ? (
        <EmptyState message="No customers yet." />
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_360px]">
          <div className="card overflow-x-auto p-0">
            <table className="w-full text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-4 py-3">Customer</th>
                  <th className="px-4 py-3">Orders</th>
                  <th className="px-4 py-3">Lifetime spend</th>
                  <th className="px-4 py-3">Last order</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {customers.map((c) => (
                  <tr key={c.customer_id} className="cursor-pointer hover:bg-slate-50" onClick={() => setActiveId(c.customer_id)}>
                    <td className="px-4 py-3">
                      <div className="font-medium text-slate-800">{c.full_name}</div>
                      <div className="text-xs text-slate-400">{c.email}</div>
                    </td>
                    <td className="px-4 py-3 text-slate-600">{c.order_count}</td>
                    <td className="px-4 py-3 font-medium text-slate-800">₹{c.total_spent.toLocaleString()}</td>
                    <td className="px-4 py-3 text-slate-500">{new Date(c.last_order_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="card">
            {!activeId ? (
              <p className="text-sm text-slate-400">Select a customer to see their order history.</p>
            ) : !detail ? (
              <Spinner />
            ) : (
              <div>
                <p className="font-semibold text-slate-900">{detail.full_name}</p>
                <p className="text-sm text-slate-500">{detail.email}</p>
                <p className="text-sm text-slate-500">{detail.city}</p>
                <div className="my-3 grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <p className="text-slate-400">Orders</p>
                    <p className="font-semibold">{detail.order_count}</p>
                  </div>
                  <div>
                    <p className="text-slate-400">Lifetime spend</p>
                    <p className="font-semibold">₹{detail.total_spent.toLocaleString()}</p>
                  </div>
                </div>
                <p className="mb-2 text-xs font-semibold uppercase text-slate-400">Order history</p>
                <div className="space-y-2">
                  {detail.bookings.map((b) => (
                    <div key={b.id} className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2 text-xs">
                      <div>
                        <p className="font-medium text-slate-700">{b.service_title}</p>
                        <p className="text-slate-400">{new Date(b.created_at).toLocaleDateString()}</p>
                      </div>
                      <div className="text-right">
                        <p className="font-medium text-slate-700">₹{b.amount_total.toLocaleString()}</p>
                        <StatusBadge status={b.status} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
