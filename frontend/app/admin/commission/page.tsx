"use client";

import { useEffect, useState } from "react";
import { PageHeader, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { Business } from "@/lib/types";

export default function CommissionPage() {
  const [businesses, setBusinesses] = useState<Business[] | null>(null);
  const [rates, setRates] = useState<Record<string, string>>({});
  const [savedId, setSavedId] = useState<string | null>(null);

  useEffect(() => {
    api.get<Business[]>("/admin/businesses").then(setBusinesses);
  }, []);

  async function save(id: string) {
    const rate = Number(rates[id]);
    if (Number.isNaN(rate) || rate < 0 || rate > 1) return;
    await api.patch(`/admin/businesses/${id}/commission?rate=${rate}`);
    setSavedId(id);
    setTimeout(() => setSavedId(null), 1500);
  }

  if (!businesses) return <Spinner />;

  return (
    <div>
      <PageHeader title="Commission settings" description="Set the per-booking commission rate for each business (e.g. 0.12 = 12%)." />
      <div className="card overflow-x-auto p-0">
        <table className="w-full text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-3">Business</th>
              <th className="px-4 py-3">Rate</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {businesses.map((b) => (
              <tr key={b.id}>
                <td className="px-4 py-3 font-medium text-slate-800">{b.company_name}</td>
                <td className="px-4 py-3">
                  <input
                    className="input w-24"
                    type="number"
                    step="0.01"
                    min="0"
                    max="1"
                    placeholder="0.12"
                    defaultValue=""
                    onChange={(e) => setRates({ ...rates, [b.id]: e.target.value })}
                  />
                </td>
                <td className="px-4 py-3">
                  <button onClick={() => save(b.id)} className="btn-secondary text-xs">
                    {savedId === b.id ? "Saved ✓" : "Save"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
