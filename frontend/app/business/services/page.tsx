"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { PageHeader, StatCard, Spinner, EmptyState } from "@/components/ui";
import { useToast } from "@/components/Toast";
import { api, ApiError } from "@/lib/api";
import { CategoryTree, Service } from "@/lib/types";

export default function ServicesPage() {
  return (
    <Suspense>
      <ServicesContent />
    </Suspense>
  );
}

function ServicesContent() {
  const toast = useToast();
  const params = useSearchParams();
  const [services, setServices] = useState<Service[] | null>(null);
  const [categories, setCategories] = useState<CategoryTree[]>([]);
  const [showForm, setShowForm] = useState(params.get("create") === "1");
  const [serviceForm, setServiceForm] = useState({ title: "", category_id: "", description: "" });
  const [packageForms, setPackageForms] = useState<Record<string, { name: string; price: string; description: string }>>({});

  useEffect(() => {
    if (params.get("create") === "1") setShowForm(true);
  }, [params]);

  function refresh() {
    api.get<Service[]>("/services/me").then(setServices);
  }

  useEffect(() => {
    refresh();
    api.get<CategoryTree[]>("/categories/tree").then(setCategories);
  }, []);

  async function addService(e: React.FormEvent) {
    e.preventDefault();
    if (!serviceForm.category_id) return;
    try {
      await api.post("/services", serviceForm);
      setServiceForm({ title: "", category_id: "", description: "" });
      setShowForm(false);
      refresh();
      toast("Service added", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Could not add service", "error");
    }
  }

  async function removeService(id: string) {
    await api.del(`/services/${id}`);
    refresh();
    toast("Service removed");
  }

  async function addPackage(serviceId: string) {
    const draft = packageForms[serviceId];
    if (!draft?.name || !draft?.price) return;
    await api.post(`/services/${serviceId}/packages`, { name: draft.name, price: Number(draft.price), description: draft.description });
    setPackageForms({ ...packageForms, [serviceId]: { name: "", price: "", description: "" } });
    refresh();
    toast("Package added", "success");
  }

  async function removePackage(id: string) {
    await api.del(`/packages/${id}`);
    refresh();
    toast("Package removed");
  }

  if (!services) return <Spinner />;

  const totalPackages = services.reduce((sum, s) => sum + s.packages.length, 0);
  const allPrices = services.flatMap((s) => s.packages.map((p) => p.price));
  const priceRange = allPrices.length ? `₹${Math.min(...allPrices).toLocaleString()} – ₹${Math.max(...allPrices).toLocaleString()}` : "—";

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <PageHeader title="Products" description="Services and packages customers can book." />
        <button className="btn-primary text-sm" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cancel" : "Add service"}
        </button>
      </div>

      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard label="Services" value={services.length} />
        <StatCard label="Packages" value={totalPackages} />
        <StatCard label="Price range" value={priceRange} />
      </div>

      {showForm && (
        <form onSubmit={addService} className="card mb-6 grid grid-cols-1 gap-3 sm:grid-cols-[1fr_1fr_auto]">
          <input className="input" placeholder="Service title (e.g. Wedding Photography)" required value={serviceForm.title} onChange={(e) => setServiceForm({ ...serviceForm, title: e.target.value })} />
          <select className="input" required value={serviceForm.category_id} onChange={(e) => setServiceForm({ ...serviceForm, category_id: e.target.value })}>
            <option value="">Select category…</option>
            {categories.map((main) => (
              <optgroup key={main.id} label={main.name}>
                {main.children.map((sub) => (
                  <option key={sub.id} value={sub.id}>
                    {sub.name}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
          <button className="btn-primary">Add service</button>
        </form>
      )}

      {services.length === 0 ? (
        <EmptyState message="No services yet. Add your first service to start taking bookings." />
      ) : (
        <div className="space-y-4">
          {services.map((s) => (
            <div key={s.id} className="card">
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold text-slate-900">{s.title}</h3>
                  <span className={`badge ${s.is_active ? "bg-emerald-100 text-emerald-700" : "bg-slate-200 text-slate-600"}`}>
                    {s.is_active ? "Active" : "Inactive"}
                  </span>
                  <span className="badge bg-slate-100 text-slate-500">{s.packages.length} package{s.packages.length === 1 ? "" : "s"}</span>
                  {s.is_instant_booking && <span className="badge bg-brand-100 text-brand-700">Instant</span>}
                  {s.is_home_service && <span className="badge bg-amber-100 text-amber-700">Home service</span>}
                </div>
                <button onClick={() => removeService(s.id)} className="text-xs font-medium text-red-600 hover:underline">
                  Remove service
                </button>
              </div>
              <div className="space-y-2">
                {s.packages.map((p) => (
                  <div key={p.id} className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2 text-sm">
                    <div>
                      <p className="font-medium text-slate-800">{p.name}</p>
                      <p className="text-slate-500">{p.description}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <p className="font-semibold text-brand-700">₹{p.price.toLocaleString()}</p>
                      <button onClick={() => removePackage(p.id)} className="text-xs text-red-600 hover:underline">
                        Remove
                      </button>
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-[1fr_120px_1fr_auto]">
                <input
                  className="input"
                  placeholder="Package name"
                  value={packageForms[s.id]?.name || ""}
                  onChange={(e) => setPackageForms({ ...packageForms, [s.id]: { ...packageForms[s.id], name: e.target.value, price: packageForms[s.id]?.price || "", description: packageForms[s.id]?.description || "" } })}
                />
                <input
                  className="input"
                  placeholder="Price ₹"
                  type="number"
                  value={packageForms[s.id]?.price || ""}
                  onChange={(e) => setPackageForms({ ...packageForms, [s.id]: { ...packageForms[s.id], price: e.target.value, name: packageForms[s.id]?.name || "", description: packageForms[s.id]?.description || "" } })}
                />
                <input
                  className="input"
                  placeholder="Description"
                  value={packageForms[s.id]?.description || ""}
                  onChange={(e) => setPackageForms({ ...packageForms, [s.id]: { ...packageForms[s.id], description: e.target.value, name: packageForms[s.id]?.name || "", price: packageForms[s.id]?.price || "" } })}
                />
                <button className="btn-secondary" onClick={() => addPackage(s.id)}>
                  Add package
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
