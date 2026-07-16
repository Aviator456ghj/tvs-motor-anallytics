"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import { Spinner, EmptyState } from "@/components/ui";
import { api } from "@/lib/api";

interface SearchResult {
  categories: { id: string; name: string; slug: string; icon: string | null }[];
  businesses: { id: string; slug: string; company_name: string; city: string | null; rating_avg: number }[];
}

export default function SearchPage() {
  return (
    <Suspense>
      <SearchContent />
    </Suspense>
  );
}

function SearchContent() {
  const params = useSearchParams();
  const initialQ = params.get("q") || "";
  const [q, setQ] = useState(initialQ);
  const [results, setResults] = useState<SearchResult | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!initialQ) return;
    runSearch(initialQ);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialQ]);

  function runSearch(query: string) {
    if (!query.trim()) return;
    setLoading(true);
    api
      .get<SearchResult>(`/search?q=${encodeURIComponent(query)}`)
      .then(setResults)
      .finally(() => setLoading(false));
  }

  return (
    <div>
      <Navbar />
      <div className="mx-auto max-w-3xl px-4 py-10 sm:px-6">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            runSearch(q);
          }}
          className="flex gap-2"
        >
          <input className="input flex-1" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search categories or providers…" />
          <button className="btn-primary">Search</button>
        </form>

        {loading && <Spinner />}

        {results && !loading && (
          <div className="mt-8 space-y-8">
            <div>
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Categories</h2>
              {results.categories.length === 0 ? (
                <EmptyState message="No matching categories." />
              ) : (
                <div className="flex flex-wrap gap-2">
                  {results.categories.map((c) => (
                    <Link key={c.id} href={`/browse?category=${c.slug}`} className="badge bg-brand-50 text-brand-700 hover:bg-brand-100">
                      {c.name}
                    </Link>
                  ))}
                </div>
              )}
            </div>
            <div>
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Providers</h2>
              {results.businesses.length === 0 ? (
                <EmptyState message="No matching providers." />
              ) : (
                <div className="space-y-3">
                  {results.businesses.map((b) => (
                    <Link key={b.id} href={`/provider/${b.slug}`} className="card flex items-center justify-between hover:shadow-md">
                      <div>
                        <p className="font-medium text-slate-900">{b.company_name}</p>
                        <p className="text-sm text-slate-500">{b.city}</p>
                      </div>
                      <span className="text-amber-600">★ {b.rating_avg.toFixed(1)}</span>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
