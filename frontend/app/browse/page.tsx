"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import Navbar from "@/components/Navbar";
import { Spinner, EmptyState } from "@/components/ui";
import { api } from "@/lib/api";
import { Business, CategoryTree } from "@/lib/types";

export default function BrowsePage() {
  return (
    <Suspense>
      <BrowseContent />
    </Suspense>
  );
}

function BrowseContent() {
  const params = useSearchParams();
  const categorySlug = params.get("category") || "";

  const [categories, setCategories] = useState<CategoryTree[]>([]);
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [city, setCity] = useState("");
  const [verifiedOnly, setVerifiedOnly] = useState(false);
  const [instantOnly, setInstantOnly] = useState(false);
  const [sort, setSort] = useState("rating");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<CategoryTree[]>("/categories/tree").then(setCategories).catch(() => setCategories([]));
  }, []);

  useEffect(() => {
    setLoading(true);
    const qs = new URLSearchParams();
    if (categorySlug) qs.set("category_slug", categorySlug);
    if (city) qs.set("city", city);
    if (verifiedOnly) qs.set("verified_only", "true");
    if (instantOnly) qs.set("instant_booking", "true");
    qs.set("sort", sort);
    api
      .get<Business[]>(`/businesses/search?${qs.toString()}`)
      .then(setBusinesses)
      .catch(() => setBusinesses([]))
      .finally(() => setLoading(false));
  }, [categorySlug, city, verifiedOnly, instantOnly, sort]);

  const activeMain = categories.find((c) => c.slug === categorySlug || c.children.some((s) => s.slug === categorySlug));

  return (
    <div>
      <Navbar />
      <div className="mx-auto grid max-w-7xl grid-cols-1 gap-6 px-4 py-8 sm:px-6 lg:grid-cols-[240px_1fr]">
        <aside className="space-y-6">
          <div className="card">
            <h3 className="mb-3 text-sm font-semibold text-slate-700">Categories</h3>
            <div className="max-h-[420px] space-y-1 overflow-y-auto pr-1 text-sm">
              <Link href="/browse" className={`block rounded px-2 py-1 ${!categorySlug ? "bg-brand-50 text-brand-700" : "text-slate-600"}`}>
                All categories
              </Link>
              {categories.map((c) => (
                <details key={c.id} open={activeMain?.id === c.id}>
                  <summary className="cursor-pointer rounded px-2 py-1 font-medium text-slate-700 hover:bg-slate-50">{c.name}</summary>
                  <div className="ml-3 space-y-0.5 border-l border-slate-200 pl-2">
                    {c.children.map((sub) => (
                      <Link
                        key={sub.id}
                        href={`/browse?category=${sub.slug}`}
                        className={`block rounded px-2 py-1 text-slate-500 hover:bg-slate-50 ${
                          categorySlug === sub.slug ? "bg-brand-50 font-medium text-brand-700" : ""
                        }`}
                      >
                        {sub.name}
                      </Link>
                    ))}
                  </div>
                </details>
              ))}
            </div>
          </div>
          <div className="card space-y-3">
            <h3 className="text-sm font-semibold text-slate-700">Filters</h3>
            <div>
              <label className="label">City</label>
              <input className="input" placeholder="e.g. Hyderabad" value={city} onChange={(e) => setCity(e.target.value)} />
            </div>
            <label className="flex items-center gap-2 text-sm text-slate-600">
              <input type="checkbox" checked={verifiedOnly} onChange={(e) => setVerifiedOnly(e.target.checked)} /> Verified only
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-600">
              <input type="checkbox" checked={instantOnly} onChange={(e) => setInstantOnly(e.target.checked)} /> Instant booking
            </label>
            <div>
              <label className="label">Sort by</label>
              <select className="input" value={sort} onChange={(e) => setSort(e.target.value)}>
                <option value="rating">Top rated</option>
                <option value="experience">Most experienced</option>
                <option value="newest">Newest</option>
              </select>
            </div>
          </div>
        </aside>

        <section>
          <h1 className="mb-4 text-xl font-bold text-slate-900">
            {activeMain ? activeMain.name : "All providers"} <span className="font-normal text-slate-400">({businesses.length})</span>
          </h1>
          {loading ? (
            <Spinner />
          ) : businesses.length === 0 ? (
            <EmptyState message="No providers match these filters yet." />
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {businesses.map((b) => (
                <Link key={b.id} href={`/provider/${b.slug}`} className="card block transition hover:-translate-y-0.5 hover:shadow-md">
                  <div className="mb-2 flex items-start justify-between">
                    <h3 className="font-semibold text-slate-900">{b.company_name}</h3>
                    {b.is_verified && <span className="badge bg-emerald-100 text-emerald-700">Verified</span>}
                  </div>
                  <p className="text-sm text-slate-500">{b.tagline}</p>
                  <div className="mt-3 flex items-center justify-between text-sm">
                    <span className="text-amber-600">★ {b.rating_avg.toFixed(1)} ({b.rating_count})</span>
                    <span className="text-slate-500">{b.city}</span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
