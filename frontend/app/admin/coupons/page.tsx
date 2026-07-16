"use client";

import { useEffect, useState } from "react";
import { PageHeader, Spinner, EmptyState } from "@/components/ui";
import { api } from "@/lib/api";
import { Coupon } from "@/lib/types";

export default function CouponsPage() {
  const [coupons, setCoupons] = useState<Coupon[] | null>(null);
  const [form, setForm] = useState({ code: "", discount_type: "percent" as "flat" | "percent", discount_value: "", usage_limit: "" });

  function refresh() {
    api.get<Coupon[]>("/coupons").then(setCoupons);
  }

  useEffect(refresh, []);

  async function addCoupon(e: React.FormEvent) {
    e.preventDefault();
    await api.post("/coupons", {
      code: form.code.toUpperCase(),
      discount_type: form.discount_type,
      discount_value: Number(form.discount_value),
      usage_limit: form.usage_limit ? Number(form.usage_limit) : undefined,
    });
    setForm({ code: "", discount_type: "percent", discount_value: "", usage_limit: "" });
    refresh();
  }

  async function deactivate(id: string) {
    await api.patch(`/coupons/${id}/deactivate`);
    refresh();
  }

  if (!coupons) return <Spinner />;

  return (
    <div>
      <PageHeader title="Coupons" description="Create and manage platform-wide discount codes." />
      <form onSubmit={addCoupon} className="card mb-6 grid grid-cols-1 gap-3 sm:grid-cols-5">
        <input className="input" placeholder="CODE" required value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} />
        <select className="input" value={form.discount_type} onChange={(e) => setForm({ ...form, discount_type: e.target.value as "flat" | "percent" })}>
          <option value="percent">Percent off</option>
          <option value="flat">Flat amount off</option>
        </select>
        <input className="input" placeholder="Value" type="number" required value={form.discount_value} onChange={(e) => setForm({ ...form, discount_value: e.target.value })} />
        <input className="input" placeholder="Usage limit" type="number" value={form.usage_limit} onChange={(e) => setForm({ ...form, usage_limit: e.target.value })} />
        <button className="btn-primary">Create coupon</button>
      </form>
      {coupons.length === 0 ? (
        <EmptyState message="No coupons created yet." />
      ) : (
        <div className="space-y-2">
          {coupons.map((c) => (
            <div key={c.id} className="card flex items-center justify-between">
              <div>
                <p className="font-mono font-semibold text-slate-800">{c.code}</p>
                <p className="text-sm text-slate-500">
                  {c.discount_type === "percent" ? `${c.discount_value}% off` : `₹${c.discount_value} off`} · used {c.usage_count}
                  {c.usage_limit ? `/${c.usage_limit}` : ""}
                </p>
              </div>
              {c.is_active ? (
                <button onClick={() => deactivate(c.id)} className="text-xs font-medium text-red-600 hover:underline">
                  Deactivate
                </button>
              ) : (
                <span className="badge bg-slate-200 text-slate-600">Inactive</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
