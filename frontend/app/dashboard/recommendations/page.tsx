"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { PageHeader, Spinner, EmptyState } from "@/components/ui";
import { api } from "@/lib/api";

interface Recommendation {
  business_id: string;
  company_name: string;
  slug: string;
  score: number;
}

export default function RecommendationsPage() {
  const [items, setItems] = useState<Recommendation[] | null>(null);

  useEffect(() => {
    api.get<Recommendation[]>("/ai/recommendations").then(setItems).catch(() => setItems([]));
  }, []);

  if (!items) return <Spinner />;

  return (
    <div>
      <PageHeader title="AI recommendations" description="Providers picked for you based on your city and top ratings." />
      {items.length === 0 ? (
        <EmptyState message="No recommendations available yet." />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {items.map((r) => (
            <Link key={r.business_id} href={`/provider/${r.slug}`} className="card block hover:shadow-md">
              <p className="font-semibold text-slate-900">{r.company_name}</p>
              <p className="mt-2 text-sm text-amber-600">Match score {r.score.toFixed(1)}</p>
            </Link>
          ))}
        </div>
      )}
      <p className="mt-6 text-xs text-slate-400">
        Powered by a placeholder ranking model today (rating × review volume). See docs/ROADMAP.md for the planned
        learned-to-rank upgrade.
      </p>
    </div>
  );
}
