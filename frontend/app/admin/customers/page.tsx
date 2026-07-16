"use client";

import { useEffect, useState } from "react";
import { PageHeader, Spinner } from "@/components/ui";
import { api } from "@/lib/api";

interface AdminCustomer {
  id: string;
  full_name: string;
  email: string;
  city: string | null;
  created_at: string;
  is_active: boolean;
}

export default function AllCustomersPage() {
  const [customers, setCustomers] = useState<AdminCustomer[] | null>(null);

  function refresh() {
    api.get<AdminCustomer[]>("/admin/customers").then(setCustomers);
  }

  useEffect(refresh, []);

  async function deactivate(id: string) {
    await api.patch(`/admin/customers/${id}/deactivate`);
    refresh();
  }

  if (!customers) return <Spinner />;

  return (
    <div>
      <PageHeader title="All customers" description={`${customers.length} registered customers.`} />
      <div className="card overflow-x-auto p-0">
        <table className="w-full text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3">Email</th>
              <th className="px-4 py-3">City</th>
              <th className="px-4 py-3">Joined</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {customers.map((c) => (
              <tr key={c.id}>
                <td className="px-4 py-3 font-medium text-slate-800">{c.full_name}</td>
                <td className="px-4 py-3 text-slate-500">{c.email}</td>
                <td className="px-4 py-3 text-slate-500">{c.city}</td>
                <td className="px-4 py-3 text-slate-500">{new Date(c.created_at).toLocaleDateString()}</td>
                <td className="px-4 py-3">
                  <span className={`badge ${c.is_active ? "bg-emerald-100 text-emerald-700" : "bg-slate-200 text-slate-600"}`}>
                    {c.is_active ? "Active" : "Deactivated"}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  {c.is_active && (
                    <button onClick={() => deactivate(c.id)} className="text-xs font-medium text-red-600 hover:underline">
                      Deactivate
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
