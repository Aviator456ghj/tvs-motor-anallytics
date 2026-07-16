"use client";

import { useEffect, useState } from "react";
import { PageHeader, Spinner, EmptyState } from "@/components/ui";
import { api } from "@/lib/api";

interface Slot {
  id: string;
  date: string;
  start_time: string;
  end_time: string;
  capacity: number;
  booked_count: number;
  is_blocked: boolean;
}

export default function AvailabilityPage() {
  const [slots, setSlots] = useState<Slot[] | null>(null);
  const [form, setForm] = useState({ date: "", start_time: "10:00", end_time: "18:00", capacity: 1 });

  function refresh() {
    api.get<Slot[]>("/availability/me").then(setSlots);
  }

  useEffect(refresh, []);

  async function addSlot(e: React.FormEvent) {
    e.preventDefault();
    if (!form.date) return;
    await api.post("/availability", form);
    refresh();
  }

  async function block(id: string) {
    await api.patch(`/availability/${id}/block`);
    refresh();
  }

  async function remove(id: string) {
    await api.del(`/availability/${id}`);
    refresh();
  }

  if (!slots) return <Spinner />;

  return (
    <div>
      <PageHeader title="Availability" description="Open time slots that customers can book." />
      <form onSubmit={addSlot} className="card mb-6 grid grid-cols-1 gap-3 sm:grid-cols-5">
        <input className="input" type="date" required value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} />
        <input className="input" type="time" value={form.start_time} onChange={(e) => setForm({ ...form, start_time: e.target.value })} />
        <input className="input" type="time" value={form.end_time} onChange={(e) => setForm({ ...form, end_time: e.target.value })} />
        <input
          className="input"
          type="number"
          min={1}
          value={form.capacity}
          onChange={(e) => setForm({ ...form, capacity: Number(e.target.value) })}
        />
        <button className="btn-primary">Add slot</button>
      </form>
      {slots.length === 0 ? (
        <EmptyState message="No availability slots yet." />
      ) : (
        <div className="space-y-2">
          {slots.map((s) => (
            <div key={s.id} className="card flex items-center justify-between">
              <div>
                <p className="font-medium text-slate-800">
                  {s.date} · {s.start_time.slice(0, 5)}–{s.end_time.slice(0, 5)}
                </p>
                <p className="text-xs text-slate-500">
                  {s.booked_count}/{s.capacity} booked {s.is_blocked && "· Blocked"}
                </p>
              </div>
              <div className="flex gap-3 text-xs">
                {!s.is_blocked && (
                  <button onClick={() => block(s.id)} className="font-medium text-amber-600 hover:underline">
                    Block
                  </button>
                )}
                <button onClick={() => remove(s.id)} className="font-medium text-red-600 hover:underline">
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
