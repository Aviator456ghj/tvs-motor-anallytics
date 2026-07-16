"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { PageHeader, Spinner, EmptyState } from "@/components/ui";
import { api } from "@/lib/api";
import { Business } from "@/lib/types";

export default function WishlistPage() {
  const [items, setItems] = useState<Business[] | null>(null);

  function refresh() {
    api.get<Business[]>("/wishlist").then(setItems).catch(() => setItems([]));
  }

  useEffect(refresh, []);

  async function remove(id: string) {
    await api.del(`/wishlist/${id}`);
    refresh();
  }

  if (!items) return <Spinner />;

  return (
    <div>
      <PageHeader title="Saved providers" description="Your wishlist of favorite service providers." />
      {items.length === 0 ? (
        <EmptyState message="You haven't saved any providers yet. Tap the heart icon on a provider profile to save it." />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {items.map((b) => (
            <div key={b.id} className="card">
              <Link href={`/provider/${b.slug}`} className="font-semibold text-slate-900 hover:underline">
                {b.company_name}
              </Link>
              <p className="text-sm text-slate-500">{b.city}</p>
              <p className="mt-2 text-sm text-amber-600">★ {b.rating_avg.toFixed(1)}</p>
              <button onClick={() => remove(b.id)} className="mt-3 text-xs font-medium text-red-600 hover:underline">
                Remove
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
