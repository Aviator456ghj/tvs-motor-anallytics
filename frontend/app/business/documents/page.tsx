"use client";

import { useEffect, useState } from "react";
import { PageHeader, Spinner, EmptyState, StatusBadge } from "@/components/ui";
import { api } from "@/lib/api";

interface Document {
  id: string;
  doc_type: string;
  file_url: string;
  status: string;
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[] | null>(null);
  const [form, setForm] = useState({ doc_type: "GST Certificate", file_url: "" });

  function refresh() {
    api.get<Document[]>("/businesses/me/documents").then(setDocuments);
  }

  useEffect(refresh, []);

  async function upload(e: React.FormEvent) {
    e.preventDefault();
    await api.post("/businesses/me/documents", form);
    setForm({ ...form, file_url: "" });
    refresh();
  }

  if (!documents) return <Spinner />;

  return (
    <div>
      <PageHeader title="KYC Documents" description="Upload business documents for admin verification." />
      <form onSubmit={upload} className="card mb-6 grid grid-cols-1 gap-3 sm:grid-cols-[200px_1fr_auto]">
        <select className="input" value={form.doc_type} onChange={(e) => setForm({ ...form, doc_type: e.target.value })}>
          {["GST Certificate", "PAN Card", "Aadhaar Card", "Trade License", "Bank Proof"].map((t) => (
            <option key={t}>{t}</option>
          ))}
        </select>
        <input
          className="input"
          placeholder="File URL (upload to storage, paste link here)"
          required
          value={form.file_url}
          onChange={(e) => setForm({ ...form, file_url: e.target.value })}
        />
        <button className="btn-primary">Submit</button>
      </form>
      {documents.length === 0 ? (
        <EmptyState message="No documents submitted yet." />
      ) : (
        <div className="space-y-2">
          {documents.map((d) => (
            <div key={d.id} className="card flex items-center justify-between">
              <div>
                <p className="font-medium text-slate-800">{d.doc_type}</p>
                <a href={d.file_url} className="text-xs text-brand-700 hover:underline" target="_blank" rel="noreferrer">
                  View file
                </a>
              </div>
              <StatusBadge status={d.status} />
            </div>
          ))}
        </div>
      )}
      <p className="mt-4 text-xs text-slate-400">
        File storage isn&apos;t wired up yet — paste a hosted URL for now. See docs/ROADMAP.md for the S3 upload flow.
      </p>
    </div>
  );
}
