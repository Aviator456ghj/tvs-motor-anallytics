"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { PageHeader, Spinner, EmptyState } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import { Business } from "@/lib/types";

export default function NearbyProvidersPage() {
  const { user } = useAuth();
  const [businesses, setBusinesses] = useState<Business[] | null>(null);

  useEffect(() => {
    if (!user?.city) {
      setBusinesses([]);
      return;
    }
    api
      .get<Business[]>(`/businesses/search?city=${encodeURIComponent(user.city)}&sort=rating`)
      .then(setBusinesses)
      .catch(() => setBusinesses([]));
  }, [user]);

  if (!businesses) return <Spinner />;

  return (
    <div>
      <PageHeader title="Nearby providers" description={user?.city ? `Top-rated providers in ${user.city}.` : "Set your city in your profile to see nearby providers."} />
      {businesses.length === 0 ? (
        <EmptyState message="No providers found near you yet. Try browsing all categories." />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {businesses.map((b) => (
            <Link key={b.id} href={`/provider/${b.slug}`} className="card block hover:shadow-md">
              <p className="font-semibold text-slate-900">{b.company_name}</p>
              <p className="text-sm text-slate-500">{b.tagline}</p>
              <p className="mt-2 text-sm text-amber-600">★ {b.rating_avg.toFixed(1)}</p>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
