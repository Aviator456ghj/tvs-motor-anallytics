"use client";

import { useEffect, useState } from "react";
import { PageHeader, Spinner, EmptyState } from "@/components/ui";
import { api } from "@/lib/api";

interface KycDocument {
  id: string;
  business_id: string;
  doc_type: string;
  file_url: string;
  status: string;
}

export default function KycPage() {
  const [documents, setDocuments] = useState<KycDocument[] | null>(null);

  function refresh() {
    api.get<KycDocument[]>("/admin/kyc/pending").then(setDocuments);
  }

  useEffect(refresh, []);

  async function approve(id: string) {
    await api.patch(`/admin/kyc/${id}/approve`);
    refresh();
  }

  async function reject(id: string) {
    const reason = window.prompt("Rejection reason?") || "Document unclear";
    await api.patch(`/admin/kyc/${id}/reject?reason=${encodeURIComponent(reason)}`);
    refresh();
  }

  if (!documents) return <Spinner />;

  return (
    <div>
      <PageHeader title="KYC review" description="Verify business documents before approving their profile." />
      {documents.length === 0 ? (
        <EmptyState message="No pending KYC documents." />
      ) : (
        <div className="space-y-3">
          {documents.map((d) => (
            <div key={d.id} className="card flex items-center justify-between">
              <div>
                <p className="font-medium text-slate-800">{d.doc_type}</p>
                <a href={d.file_url} target="_blank" rel="noreferrer" className="text-xs text-brand-700 hover:underline">
                  View document
                </a>
              </div>
              <div className="flex gap-2">
                <button onClick={() => approve(d.id)} className="btn-secondary text-xs text-emerald-700">
                  Approve
                </button>
                <button onClick={() => reject(d.id)} className="btn-secondary text-xs text-red-600">
                  Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
