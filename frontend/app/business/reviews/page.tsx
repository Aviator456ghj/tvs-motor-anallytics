"use client";

import { useEffect, useState } from "react";
import { PageHeader, Spinner, EmptyState } from "@/components/ui";
import { api } from "@/lib/api";
import { Business, Review } from "@/lib/types";

export default function BusinessReviewsPage() {
  const [reviews, setReviews] = useState<Review[] | null>(null);
  const [businessId, setBusinessId] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});

  function refresh(id: string) {
    api.get<Review[]>(`/reviews/business/${id}`).then(setReviews);
  }

  useEffect(() => {
    api.get<Business>("/businesses/me").then((b) => {
      setBusinessId(b.id);
      refresh(b.id);
    });
  }, []);

  async function respond(reviewId: string) {
    const response = drafts[reviewId];
    if (!response) return;
    await api.post(`/reviews/${reviewId}/respond?response=${encodeURIComponent(response)}`);
    if (businessId) refresh(businessId);
  }

  if (!reviews) return <Spinner />;

  return (
    <div>
      <PageHeader title="Customer reviews" description="Respond to reviews to build trust with future customers." />
      {reviews.length === 0 ? (
        <EmptyState message="No reviews yet." />
      ) : (
        <div className="space-y-4">
          {reviews.map((r) => (
            <div key={r.id} className="card">
              <p className="text-amber-600">{"★".repeat(r.rating)}{"☆".repeat(5 - r.rating)}</p>
              {r.comment && <p className="mt-1 text-sm text-slate-600">{r.comment}</p>}
              {r.provider_response ? (
                <p className="mt-3 rounded-lg bg-slate-50 p-2 text-xs text-slate-500">
                  <span className="font-medium">Your response:</span> {r.provider_response}
                </p>
              ) : (
                <div className="mt-3 flex gap-2">
                  <input
                    className="input flex-1"
                    placeholder="Write a response…"
                    value={drafts[r.id] || ""}
                    onChange={(e) => setDrafts({ ...drafts, [r.id]: e.target.value })}
                  />
                  <button className="btn-secondary text-xs" onClick={() => respond(r.id)}>
                    Reply
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
