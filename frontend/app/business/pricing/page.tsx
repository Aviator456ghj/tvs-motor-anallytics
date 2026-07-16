"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { PageHeader, Spinner, EmptyState } from "@/components/ui";
import { api } from "@/lib/api";
import { Service } from "@/lib/types";

export default function PricingPage() {
  const [services, setServices] = useState<Service[] | null>(null);

  useEffect(() => {
    api.get<Service[]>("/services/me").then(setServices);
  }, []);

  if (!services) return <Spinner />;

  const packages = services.flatMap((s) => s.packages.map((p) => ({ ...p, serviceTitle: s.title })));

  return (
    <div>
      <PageHeader title="Pricing" description="Every package price across your services, at a glance." />
      {packages.length === 0 ? (
        <EmptyState message="No packages yet." />
      ) : (
        <div className="card overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">Service</th>
                <th className="px-4 py-3">Package</th>
                <th className="px-4 py-3">Price</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {packages.map((p) => (
                <tr key={p.id}>
                  <td className="px-4 py-3 text-slate-600">{p.serviceTitle}</td>
                  <td className="px-4 py-3 font-medium text-slate-800">{p.name}</td>
                  <td className="px-4 py-3 font-semibold text-brand-700">₹{p.price.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="mt-4 text-sm text-slate-500">
        Need to change a price?{" "}
        <Link href="/business/services" className="font-medium text-brand-700 hover:underline">
          Edit in Services & Packages
        </Link>
        .
      </p>
    </div>
  );
}
