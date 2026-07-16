"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { PageHeader, StatCard, Spinner } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { Business } from "@/lib/types";

interface Analytics {
  total_bookings: number;
  completed_bookings: number;
  gross_earnings: number;
  net_earnings: number;
  rating_avg: number;
  rating_count: number;
}

export default function BusinessOverview() {
  const router = useRouter();
  const [business, setBusiness] = useState<Business | null>(null);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [notFoundYet, setNotFoundYet] = useState(false);

  useEffect(() => {
    api
      .get<Business>("/businesses/me")
      .then((b) => {
        setBusiness(b);
        api.get<Analytics>("/analytics/business/me").then(setAnalytics);
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 404) setNotFoundYet(true);
      });
  }, []);

  if (notFoundYet) {
    return (
      <div className="card text-center">
        <h2 className="mb-2 font-semibold text-slate-900">Finish setting up your business</h2>
        <p className="mb-4 text-sm text-slate-500">Create your business profile to start receiving bookings.</p>
        <button className="btn-primary" onClick={() => router.push("/business/onboarding")}>
          Set up business profile
        </button>
      </div>
    );
  }

  if (!business || !analytics) return <Spinner />;

  return (
    <div>
      <PageHeader
        title={business.company_name}
        description={business.is_approved ? "Your business is live and visible to customers." : "Your profile is pending admin approval."}
      />
      {!business.is_approved && (
        <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-700">
          Your business is awaiting Super Admin approval. Complete KYC in Documents to speed this up.
        </div>
      )}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="Total bookings" value={analytics.total_bookings} />
        <StatCard label="Completed" value={analytics.completed_bookings} />
        <StatCard label="Gross earnings" value={`₹${analytics.gross_earnings.toLocaleString()}`} />
        <StatCard label="Rating" value={`${analytics.rating_avg.toFixed(1)} ★`} sub={`${analytics.rating_count} reviews`} />
      </div>
    </div>
  );
}
