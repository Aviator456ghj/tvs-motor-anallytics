"use client";

import { useEffect, useState } from "react";
import { PageHeader, Spinner } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { BusinessStaffRole, StaffMember } from "@/lib/types";

const ROLE_STYLES: Record<BusinessStaffRole, string> = {
  owner: "bg-brand-100 text-brand-700",
  manager: "bg-amber-100 text-amber-700",
  staff: "bg-slate-100 text-slate-600",
};

export default function StaffPage() {
  const [staff, setStaff] = useState<StaffMember[] | null>(null);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<BusinessStaffRole>("staff");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function refresh() {
    api.get<StaffMember[]>("/businesses/me/staff").then(setStaff).catch(() => setStaff([]));
  }
  useEffect(refresh, []);

  async function invite(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.post("/businesses/me/staff", { email, role });
      setEmail("");
      refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not add staff member");
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    await api.del(`/businesses/me/staff/${id}`);
    refresh();
  }

  if (!staff) return <Spinner />;

  return (
    <div>
      <PageHeader
        title="Staff accounts"
        description="Give teammates access to this business. They log in with their own account — no shared passwords."
      />

      <form onSubmit={invite} className="card mb-6 flex flex-wrap items-end gap-3">
        <div>
          <label className="label">Teammate's email</label>
          <input className="input w-64" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="teammate@example.com" />
        </div>
        <div>
          <label className="label">Role</label>
          <select className="input w-40" value={role} onChange={(e) => setRole(e.target.value as BusinessStaffRole)}>
            <option value="staff">Staff — bookings & catalog</option>
            <option value="manager">Manager — + earnings & customers</option>
          </select>
        </div>
        <button className="btn-primary" disabled={busy}>
          {busy ? "Adding…" : "Add to team"}
        </button>
      </form>
      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
      <p className="mb-6 text-xs text-slate-400">
        The teammate must already have a Business account (they can register at /register and pick "Business") before you can add them.
      </p>

      <div className="space-y-2">
        {staff.map((s) => (
          <div key={s.id} className="card flex items-center justify-between">
            <div>
              <p className="font-medium text-slate-800">{s.full_name}</p>
              <p className="text-sm text-slate-500">{s.email}</p>
            </div>
            <div className="flex items-center gap-3">
              <span className={`badge ${ROLE_STYLES[s.role]}`}>{s.role}</span>
              {s.role !== "owner" && (
                <button onClick={() => remove(s.id)} className="text-xs font-medium text-red-600 hover:underline">
                  Remove
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="card mt-6 text-xs text-slate-500">
        <p className="mb-1 font-semibold text-slate-700">What each role can do</p>
        <p>
          <b>Staff:</b> manage bookings, catalog, availability, portfolio.<br />
          <b>Manager:</b> everything Staff can, plus earnings, analytics, customers, and reviews.<br />
          <b>Owner:</b> everything, plus company profile, KYC documents, payouts, and staff management.
        </p>
      </div>
    </div>
  );
}
