"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { PageHeader, Spinner, StatusBadge } from "@/components/ui";
import { api } from "@/lib/api";
import { Business } from "@/lib/types";

export default function AllBusinessesPage() {
  const [businesses, setBusinesses] = useState<Business[] | null>(null);

  function refresh() {
    api.get<Business[]>("/admin/businesses").then(setBusinesses);
  }

  useEffect(refresh, []);

  async function approve(id: string) {
    await api.patch(`/admin/businesses/${id}/approve`);
    refresh();
  }

  async function suspend(id: string) {
    await api.patch(`/admin/businesses/${id}/suspend`);
    refresh();
  }

  if (!businesses) return <Spinner />;

  return (
    <div>
      <PageHeader title="All businesses" description={`${businesses.length} businesses on the platform.`} />
      <div className="card overflow-x-auto p-0">
        <table className="w-full text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-3">Company</th>
              <th className="px-4 py-3">City</th>
              <th className="px-4 py-3">Rating</th>
              <th className="px-4 py-3">KYC</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {businesses.map((b) => (
              <tr key={b.id}>
                <td className="px-4 py-3 font-medium text-slate-800">
                  <Link href={`/provider/${b.slug}`} className="hover:underline">
                    {b.company_name}
                  </Link>
                </td>
                <td className="px-4 py-3 text-slate-500">{b.city}</td>
                <td className="px-4 py-3 text-amber-600">★ {b.rating_avg.toFixed(1)}</td>
                <td className="px-4 py-3">
                  <StatusBadge status={b.kyc_status} />
                </td>
                <td className="px-4 py-3">
                  <span className={`badge ${b.is_approved ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"}`}>
                    {b.is_approved ? "Approved" : "Pending"}
                  </span>
                </td>
                <td className="space-x-3 px-4 py-3 text-right text-xs">
                  {b.is_approved ? (
                    <button onClick={() => suspend(b.id)} className="font-medium text-red-600 hover:underline">
                      Suspend
                    </button>
                  ) : (
                    <button onClick={() => approve(b.id)} className="font-medium text-emerald-600 hover:underline">
                      Approve
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
