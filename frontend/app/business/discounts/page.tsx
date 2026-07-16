"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { PageHeader, Spinner, EmptyState } from "@/components/ui";
import { useToast } from "@/components/Toast";
import { api, ApiError } from "@/lib/api";
import { Coupon } from "@/lib/types";

export default function DiscountsPage() {
  return (
    <Suspense>
      <DiscountsContent />
    </Suspense>
  );
}

function DiscountsContent() {
  const toast = useToast();
  const params = useSearchParams();
  const [coupons, setCoupons] = useState<Coupon[] | null>(null);
  const [showForm, setShowForm] = useState(params.get("create") === "1");
  const [form, setForm] = useState({ code: "", discount_type: "percent" as "flat" | "percent", discount_value: "", usage_limit: "", min_order_value: "" });
  const [busy, setBusy] = useState(false);

  function refresh() {
    api.get<Coupon[]>("/businesses/me/discounts").then(setCoupons);
  }
  useEffect(refresh, []);

  useEffect(() => {
    if (params.get("create") === "1") setShowForm(true);
  }, [params]);

  async function addDiscount(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api.post("/businesses/me/discounts", {
        code: form.code.toUpperCase(),
        discount_type: form.discount_type,
        discount_value: Number(form.discount_value),
        usage_limit: form.usage_limit ? Number(form.usage_limit) : undefined,
        min_order_value: form.min_order_value ? Number(form.min_order_value) : 0,
      });
      setForm({ code: "", discount_type: "percent", discount_value: "", usage_limit: "", min_order_value: "" });
      setShowForm(false);
      refresh();
      toast("Discount created", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Could not create discount", "error");
    } finally {
      setBusy(false);
    }
  }

  async function deactivate(id: string) {
    await api.patch(`/businesses/me/discounts/${id}/deactivate`);
    refresh();
    toast("Discount deactivated");
  }

  if (!coupons) return <Spinner />;

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <PageHeader title="Discounts" description="Codes customers can apply at checkout — valid only for your business." />
        <button className="btn-primary" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cancel" : "Create discount"}
        </button>
      </div>

      {showForm && (
        <form onSubmit={addDiscount} className="card mb-6 grid grid-cols-1 gap-3 sm:grid-cols-5">
          <input className="input" placeholder="CODE" required value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} />
          <select className="input" value={form.discount_type} onChange={(e) => setForm({ ...form, discount_type: e.target.value as "flat" | "percent" })}>
            <option value="percent">Percent off</option>
            <option value="flat">Flat amount off</option>
          </select>
          <input className="input" placeholder="Value" type="number" required value={form.discount_value} onChange={(e) => setForm({ ...form, discount_value: e.target.value })} />
          <input className="input" placeholder="Min order ₹" type="number" value={form.min_order_value} onChange={(e) => setForm({ ...form, min_order_value: e.target.value })} />
          <input className="input" placeholder="Usage limit" type="number" value={form.usage_limit} onChange={(e) => setForm({ ...form, usage_limit: e.target.value })} />
          <button className="btn-primary sm:col-span-5" disabled={busy}>{busy ? "Creating…" : "Create"}</button>
        </form>
      )}

      {coupons.length === 0 ? (
        <EmptyState message="No discount codes yet. Create one to run a promotion for your services." />
      ) : (
        <div className="space-y-2">
          {coupons.map((c) => (
            <div key={c.id} className="card flex items-center justify-between">
              <div>
                <p className="font-mono font-semibold text-slate-800">{c.code}</p>
                <p className="text-sm text-slate-500">
                  {c.discount_type === "percent" ? `${c.discount_value}% off` : `₹${c.discount_value} off`}
                  {c.min_order_value ? ` · min order ₹${c.min_order_value.toLocaleString()}` : ""} · used {c.usage_count}
                  {c.usage_limit ? `/${c.usage_limit}` : ""}
                </p>
              </div>
              {c.is_active ? (
                <button onClick={() => deactivate(c.id)} className="text-xs font-medium text-red-600 hover:underline">Deactivate</button>
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
