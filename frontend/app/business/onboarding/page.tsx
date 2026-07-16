"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { PageHeader } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { Business, CategoryTree } from "@/lib/types";

export default function BusinessOnboardingPage() {
  const router = useRouter();
  const [categories, setCategories] = useState<CategoryTree[]>([]);
  const [form, setForm] = useState({
    company_name: "",
    tagline: "",
    description: "",
    city: "",
    state: "",
    experience_years: 0,
    offers_home_service: false,
    offers_instant_booking: false,
  });
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.get<CategoryTree[]>("/categories/tree").then(setCategories);
    api
      .get<Business>("/businesses/me")
      .then(() => router.push("/business"))
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await api.post("/businesses", { ...form, category_ids: selectedCategories });
      router.push("/business");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create business profile");
    } finally {
      setLoading(false);
    }
  }

  function toggleCategory(id: string) {
    setSelectedCategories((prev) => (prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id]));
  }

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader title="Set up your business" description="Tell customers about your business — you can add services and pricing next." />
      <form onSubmit={submit} className="card space-y-4">
        <div>
          <label className="label">Company name</label>
          <input className="input" required value={form.company_name} onChange={(e) => setForm({ ...form, company_name: e.target.value })} />
        </div>
        <div>
          <label className="label">Tagline</label>
          <input className="input" value={form.tagline} onChange={(e) => setForm({ ...form, tagline: e.target.value })} />
        </div>
        <div>
          <label className="label">Description</label>
          <textarea className="input" rows={3} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">City</label>
            <input className="input" value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} />
          </div>
          <div>
            <label className="label">State</label>
            <input className="input" value={form.state} onChange={(e) => setForm({ ...form, state: e.target.value })} />
          </div>
        </div>
        <div>
          <label className="label">Years of experience</label>
          <input
            className="input"
            type="number"
            min={0}
            value={form.experience_years}
            onChange={(e) => setForm({ ...form, experience_years: Number(e.target.value) })}
          />
        </div>
        <div className="flex gap-6">
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input type="checkbox" checked={form.offers_home_service} onChange={(e) => setForm({ ...form, offers_home_service: e.target.checked })} />
            Offers home service
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={form.offers_instant_booking}
              onChange={(e) => setForm({ ...form, offers_instant_booking: e.target.checked })}
            />
            Offers instant booking
          </label>
        </div>
        <div>
          <label className="label">Categories you serve</label>
          <div className="max-h-56 space-y-2 overflow-y-auto rounded-lg border border-slate-200 p-3">
            {categories.map((main) => (
              <div key={main.id}>
                <p className="text-xs font-semibold uppercase text-slate-400">{main.name}</p>
                <div className="mt-1 flex flex-wrap gap-2">
                  {main.children.map((sub) => (
                    <label
                      key={sub.id}
                      className={`cursor-pointer rounded-full border px-2.5 py-1 text-xs ${
                        selectedCategories.includes(sub.id) ? "border-brand-600 bg-brand-50 text-brand-700" : "border-slate-300 text-slate-600"
                      }`}
                    >
                      <input type="checkbox" className="hidden" checked={selectedCategories.includes(sub.id)} onChange={() => toggleCategory(sub.id)} />
                      {sub.name}
                    </label>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button className="btn-primary w-full" disabled={loading}>
          {loading ? "Creating…" : "Create business profile"}
        </button>
      </form>
    </div>
  );
}
