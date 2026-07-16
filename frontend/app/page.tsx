import Link from "next/link";
import Navbar from "@/components/Navbar";
import { api } from "@/lib/api";
import { CategoryTree } from "@/lib/types";

async function getCategories(): Promise<CategoryTree[]> {
  try {
    return await api.get<CategoryTree[]>("/categories/tree");
  } catch {
    return [];
  }
}

export default async function HomePage() {
  const categories = await getCategories();

  return (
    <div>
      <Navbar />
      <section className="bg-gradient-to-b from-brand-700 to-brand-600 px-4 py-20 text-center text-white sm:px-6">
        <p className="mb-3 text-sm font-semibold uppercase tracking-widest text-brand-200">
          Amazon + Urban Company + Justdial + Fiverr + Booking.com
        </p>
        <h1 className="mx-auto max-w-3xl text-4xl font-extrabold leading-tight sm:text-5xl">
          One platform to discover, compare, book, pay, and manage any service.
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-brand-100">
          From wedding photographers to plumbers, tutors to travel guides — book verified local & online
          service providers in minutes.
        </p>
        <form action="/search" className="mx-auto mt-8 flex max-w-xl gap-2">
          <input
            name="q"
            placeholder="Search for photographers, electricians, tutors…"
            className="input flex-1 bg-white text-slate-900"
          />
          <button className="btn-primary bg-white text-brand-700 hover:bg-brand-50">Search</button>
        </form>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-14 sm:px-6">
        <div className="mb-8 flex items-end justify-between">
          <h2 className="text-2xl font-bold text-slate-900">Browse by category</h2>
          <Link href="/browse" className="text-sm font-medium text-brand-700 hover:underline">
            View all categories →
          </Link>
        </div>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-8">
          {categories.slice(0, 16).map((cat) => (
            <Link
              key={cat.id}
              href={`/browse?category=${cat.slug}`}
              className="card flex flex-col items-center gap-2 text-center transition hover:-translate-y-0.5 hover:shadow-md"
            >
              <span className="text-2xl">📷</span>
              <span className="text-sm font-medium text-slate-700">{cat.name}</span>
              <span className="text-xs text-slate-400">{cat.children.length} services</span>
            </Link>
          ))}
        </div>
      </section>

      <section className="bg-white py-14">
        <div className="mx-auto max-w-7xl px-4 sm:px-6">
          <h2 className="mb-8 text-center text-2xl font-bold text-slate-900">How it works</h2>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
            {[
              { step: "1. Discover", text: "Browse 100+ categories or search for a provider near you." },
              { step: "2. Book", text: "Compare portfolios, pricing and reviews, then pay a small advance." },
              { step: "3. Get it done", text: "Provider delivers the service — pay the balance and leave a review." },
            ].map((s) => (
              <div key={s.step} className="card text-center">
                <h3 className="mb-2 font-semibold text-brand-700">{s.step}</h3>
                <p className="text-sm text-slate-600">{s.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-14 text-center sm:px-6">
        <h2 className="text-2xl font-bold text-slate-900">Own a service business?</h2>
        <p className="mx-auto mt-2 max-w-xl text-slate-600">
          List your business, manage bookings, get paid on time, and grow with built-in analytics and AI tools.
        </p>
        <Link href="/business/onboarding" className="btn-primary mt-6 inline-flex">
          List your business
        </Link>
      </section>

      <footer className="border-t border-slate-200 bg-white py-8 text-center text-sm text-slate-500">
        © {new Date().getFullYear()} ServicesOS — The Operating System for Local & Online Services.
      </footer>
    </div>
  );
}
