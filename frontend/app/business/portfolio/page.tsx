"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { PageHeader, Spinner, EmptyState } from "@/components/ui";
import { api } from "@/lib/api";
import { BusinessDetail, PortfolioItem } from "@/lib/types";

export default function PortfolioPage() {
  const [items, setItems] = useState<PortfolioItem[] | null>(null);
  const [form, setForm] = useState({ item_type: "image" as "image" | "video", url: "", caption: "" });

  function refresh() {
    api.get<BusinessDetail>("/businesses/me").then((b) => setItems(b.portfolio_items));
  }

  useEffect(refresh, []);

  async function addItem(e: React.FormEvent) {
    e.preventDefault();
    await api.post("/portfolio", form);
    setForm({ item_type: "image", url: "", caption: "" });
    refresh();
  }

  async function remove(id: string) {
    await api.del(`/portfolio/${id}`);
    refresh();
  }

  if (!items) return <Spinner />;

  return (
    <div>
      <PageHeader title="Portfolio" description="Showcase your best work to win more bookings." />
      <form onSubmit={addItem} className="card mb-6 grid grid-cols-1 gap-3 sm:grid-cols-[120px_1fr_1fr_auto]">
        <select className="input" value={form.item_type} onChange={(e) => setForm({ ...form, item_type: e.target.value as "image" | "video" })}>
          <option value="image">Image</option>
          <option value="video">Video</option>
        </select>
        <input className="input" placeholder="Media URL" required value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} />
        <input className="input" placeholder="Caption" value={form.caption} onChange={(e) => setForm({ ...form, caption: e.target.value })} />
        <button className="btn-primary">Add</button>
      </form>
      {items.length === 0 ? (
        <EmptyState message="No portfolio items yet." />
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {items.map((item) => (
            <div key={item.id} className="card p-2">
              <div className="relative aspect-square overflow-hidden rounded-lg bg-slate-100">
                <Image src={item.url} alt={item.caption || ""} fill className="object-cover" unoptimized />
              </div>
              <div className="mt-2 flex items-center justify-between">
                <p className="truncate text-xs text-slate-500">{item.caption}</p>
                <button onClick={() => remove(item.id)} className="text-xs font-medium text-red-600 hover:underline">
                  Remove
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
