import Image from "next/image";
import { notFound } from "next/navigation";
import Navbar from "@/components/Navbar";
import BookingWidget from "@/components/BookingWidget";
import { api } from "@/lib/api";
import { BusinessDetail, Review } from "@/lib/types";

async function getBusiness(slug: string): Promise<BusinessDetail | null> {
  try {
    return await api.get<BusinessDetail>(`/businesses/${slug}`);
  } catch {
    return null;
  }
}

async function getReviews(businessId: string): Promise<Review[]> {
  try {
    return await api.get<Review[]>(`/reviews/business/${businessId}`);
  } catch {
    return [];
  }
}

export default async function ProviderPage({ params }: { params: { slug: string } }) {
  const business = await getBusiness(params.slug);
  if (!business) notFound();
  const reviews = await getReviews(business.id);

  return (
    <div>
      <Navbar />
      <div className="h-48 w-full bg-gradient-to-r from-brand-600 to-brand-800" />
      <div className="mx-auto max-w-6xl px-4 pb-16 sm:px-6">
        <div className="-mt-12 flex flex-col gap-6 lg:flex-row">
          <div className="min-w-0 flex-1">
            <div className="card">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <h1 className="text-2xl font-bold text-slate-900">{business.company_name}</h1>
                  <p className="text-slate-500">{business.tagline}</p>
                </div>
                <div className="flex gap-2">
                  {business.is_verified && <span className="badge bg-emerald-100 text-emerald-700">Verified</span>}
                  {business.offers_instant_booking && <span className="badge bg-brand-100 text-brand-700">Instant Booking</span>}
                </div>
              </div>
              <div className="mt-4 grid grid-cols-2 gap-4 border-t border-slate-100 pt-4 text-sm sm:grid-cols-4">
                <div>
                  <p className="text-slate-400">Rating</p>
                  <p className="font-semibold text-amber-600">★ {business.rating_avg.toFixed(1)} ({business.rating_count})</p>
                </div>
                <div>
                  <p className="text-slate-400">Experience</p>
                  <p className="font-semibold text-slate-800">{business.experience_years} years</p>
                </div>
                <div>
                  <p className="text-slate-400">Location</p>
                  <p className="font-semibold text-slate-800">{business.city}</p>
                </div>
                <div>
                  <p className="text-slate-400">Home service</p>
                  <p className="font-semibold text-slate-800">{business.offers_home_service ? "Available" : "Studio only"}</p>
                </div>
              </div>
              {business.description && <p className="mt-4 text-sm text-slate-600">{business.description}</p>}
            </div>

            <div className="card mt-6">
              <h2 className="mb-4 font-semibold text-slate-900">Packages</h2>
              <div className="space-y-4">
                {business.services.map((service) => (
                  <div key={service.id}>
                    <h3 className="mb-2 text-sm font-semibold text-slate-700">{service.title}</h3>
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                      {service.packages.map((pkg) => (
                        <div key={pkg.id} className="rounded-lg border border-slate-200 p-3">
                          <div className="flex items-center justify-between">
                            <p className="font-medium text-slate-800">{pkg.name}</p>
                            <p className="font-semibold text-brand-700">₹{pkg.price.toLocaleString()}</p>
                          </div>
                          {pkg.description && <p className="mt-1 text-xs text-slate-500">{pkg.description}</p>}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {business.portfolio_items.length > 0 && (
              <div className="card mt-6">
                <h2 className="mb-4 font-semibold text-slate-900">Portfolio</h2>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  {business.portfolio_items.map((item) => (
                    <div key={item.id} className="relative aspect-square overflow-hidden rounded-lg bg-slate-100">
                      <Image src={item.url} alt={item.caption || business.company_name} fill className="object-cover" unoptimized />
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="card mt-6">
              <h2 className="mb-4 font-semibold text-slate-900">Reviews ({reviews.length})</h2>
              {reviews.length === 0 ? (
                <p className="text-sm text-slate-500">No reviews yet.</p>
              ) : (
                <div className="space-y-4">
                  {reviews.map((r) => (
                    <div key={r.id} className="border-b border-slate-100 pb-4 last:border-0">
                      <p className="text-amber-600">{"★".repeat(r.rating)}{"☆".repeat(5 - r.rating)}</p>
                      {r.comment && <p className="mt-1 text-sm text-slate-600">{r.comment}</p>}
                      {r.provider_response && (
                        <p className="mt-2 rounded-lg bg-slate-50 p-2 text-xs text-slate-500">
                          <span className="font-medium">Provider response:</span> {r.provider_response}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="w-full lg:w-80">
            <div className="lg:sticky lg:top-20">
              <BookingWidget businessId={business.id} services={business.services} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
