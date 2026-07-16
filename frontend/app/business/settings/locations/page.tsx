"use client";

import { useEffect, useState } from "react";
import { PageHeader, Spinner, EmptyState } from "@/components/ui";
import { useToast } from "@/components/Toast";
import { api, ApiError } from "@/lib/api";

interface Location {
  id: string;
  label: string;
  address: string;
  city: string;
  is_primary: boolean;
  service_radius_km: number | null;
}

export default function LocationsPage() {
  const toast = useToast();
  const [locations, setLocations] = useState<Location[] | null>(null);
  const [form, setForm] = useState({ label: "", address: "", city: "", is_primary: false, service_radius_km: "" });
  const [busy, setBusy] = useState(false);

  function refresh() {
    api.get<Location[]>("/businesses/me/locations").then(setLocations);
  }
  useEffect(refresh, []);

  async function addLocation(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api.post("/businesses/me/locations", {
        ...form,
        service_radius_km: form.service_radius_km ? Number(form.service_radius_km) : null,
      });
      setForm({ label: "", address: "", city: "", is_primary: false, service_radius_km: "" });
      refresh();
      toast("Location added", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Could not add location", "error");
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    await api.del(`/businesses/me/locations/${id}`);
    refresh();
    toast("Location removed");
  }

  if (!locations) return <Spinner />;

  return (
    <div className="max-w-2xl">
      <PageHeader title="Locations" description="Studios you operate from, or the radius you'll travel for home service." />
      <form onSubmit={addLocation} className="card mb-6 space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Label</label>
            <input className="input" required placeholder="Main Studio" value={form.label} onChange={(e) => setForm({ ...form, label: e.target.value })} />
          </div>
          <div>
            <label className="label">City</label>
            <input className="input" required value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} />
          </div>
        </div>
        <div>
          <label className="label">Address</label>
          <input className="input" required value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
        </div>
        <div className="flex items-end gap-4">
          <div>
            <label className="label">Home-service radius (km)</label>
            <input className="input w-40" type="number" value={form.service_radius_km} onChange={(e) => setForm({ ...form, service_radius_km: e.target.value })} />
          </div>
          <label className="mb-2 flex items-center gap-2 text-sm text-slate-600">
            <input type="checkbox" checked={form.is_primary} onChange={(e) => setForm({ ...form, is_primary: e.target.checked })} /> Primary location
          </label>
        </div>
        <button className="btn-primary" disabled={busy}>{busy ? "Adding…" : "Add location"}</button>
      </form>

      {locations.length === 0 ? (
        <EmptyState message="No locations added yet." />
      ) : (
        <div className="space-y-2">
          {locations.map((l) => (
            <div key={l.id} className="card flex items-center justify-between">
              <div>
                <p className="font-medium text-slate-800">
                  {l.label} {l.is_primary && <span className="badge bg-brand-100 text-brand-700 ml-1">Primary</span>}
                </p>
                <p className="text-sm text-slate-500">{l.address}, {l.city}</p>
                {l.service_radius_km && <p className="text-xs text-slate-400">Serves within {l.service_radius_km} km</p>}
              </div>
              <button onClick={() => remove(l.id)} className="text-xs font-medium text-red-600 hover:underline">Remove</button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
