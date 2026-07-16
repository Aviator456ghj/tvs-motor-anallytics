"use client";

import { useEffect, useState } from "react";
import { PageHeader, Spinner, EmptyState } from "@/components/ui";
import { api } from "@/lib/api";

interface CmsPageItem {
  id: string;
  slug: string;
  title: string;
  content: string;
  is_published: boolean;
}

export default function CmsAdminPage() {
  const [pages, setPages] = useState<CmsPageItem[] | null>(null);
  const [form, setForm] = useState({ slug: "", title: "", content: "" });

  function refresh() {
    api.get<CmsPageItem[]>("/admin/cms").then(setPages);
  }

  useEffect(refresh, []);

  async function addPage(e: React.FormEvent) {
    e.preventDefault();
    await api.post("/admin/cms", { ...form, is_published: true });
    setForm({ slug: "", title: "", content: "" });
    refresh();
  }

  if (!pages) return <Spinner />;

  return (
    <div>
      <PageHeader title="CMS" description="Manage static content pages (About, Terms, Privacy, FAQs…)." />
      <form onSubmit={addPage} className="card mb-6 space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <input className="input" placeholder="Slug (e.g. terms-of-service)" required value={form.slug} onChange={(e) => setForm({ ...form, slug: e.target.value })} />
          <input className="input" placeholder="Title" required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
        </div>
        <textarea className="input" rows={4} placeholder="Content (markdown/HTML)" required value={form.content} onChange={(e) => setForm({ ...form, content: e.target.value })} />
        <button className="btn-primary">Create page</button>
      </form>
      {pages.length === 0 ? (
        <EmptyState message="No CMS pages yet." />
      ) : (
        <div className="space-y-2">
          {pages.map((p) => (
            <div key={p.id} className="card">
              <p className="font-medium text-slate-800">{p.title}</p>
              <p className="text-xs text-slate-400">/{p.slug}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
