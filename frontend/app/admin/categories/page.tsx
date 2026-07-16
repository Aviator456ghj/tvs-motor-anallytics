"use client";

import { useEffect, useState } from "react";
import { PageHeader, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { CategoryTree } from "@/lib/types";

export default function CategoriesAdminPage() {
  const [tree, setTree] = useState<CategoryTree[] | null>(null);
  const [form, setForm] = useState({ name: "", slug: "", parent_id: "" });

  function refresh() {
    api.get<CategoryTree[]>("/categories/tree").then(setTree);
  }

  useEffect(refresh, []);

  async function addCategory(e: React.FormEvent) {
    e.preventDefault();
    await api.post("/categories", { name: form.name, slug: form.slug, parent_id: form.parent_id || undefined });
    setForm({ name: "", slug: "", parent_id: "" });
    refresh();
  }

  async function remove(id: string) {
    await api.del(`/categories/${id}`);
    refresh();
  }

  if (!tree) return <Spinner />;

  return (
    <div>
      <PageHeader title="Categories" description={`${tree.length} main verticals, ${tree.reduce((s, c) => s + c.children.length, 0)} subcategories.`} />
      <form onSubmit={addCategory} className="card mb-6 grid grid-cols-1 gap-3 sm:grid-cols-4">
        <input className="input" placeholder="Name" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        <input className="input" placeholder="Slug" required value={form.slug} onChange={(e) => setForm({ ...form, slug: e.target.value })} />
        <select className="input" value={form.parent_id} onChange={(e) => setForm({ ...form, parent_id: e.target.value })}>
          <option value="">Main category (no parent)</option>
          {tree.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <button className="btn-primary">Add category</button>
      </form>
      <div className="space-y-3">
        {tree.map((main) => (
          <div key={main.id} className="card">
            <div className="mb-2 flex items-center justify-between">
              <h3 className="font-semibold text-slate-900">{main.name}</h3>
              <button onClick={() => remove(main.id)} className="text-xs font-medium text-red-600 hover:underline">
                Deactivate
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {main.children.map((sub) => (
                <span key={sub.id} className="badge bg-slate-100 text-slate-600">
                  {sub.name}
                  <button onClick={() => remove(sub.id)} className="ml-1.5 text-slate-400 hover:text-red-600">
                    ×
                  </button>
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
