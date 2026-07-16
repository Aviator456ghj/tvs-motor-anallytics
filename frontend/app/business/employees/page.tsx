"use client";

import { useEffect, useState } from "react";
import { PageHeader, Spinner, EmptyState } from "@/components/ui";
import { api } from "@/lib/api";

interface Employee {
  id: string;
  name: string;
  role_title: string | null;
  phone: string | null;
  email: string | null;
}

export default function EmployeesPage() {
  const [employees, setEmployees] = useState<Employee[] | null>(null);
  const [form, setForm] = useState({ name: "", role_title: "", phone: "", email: "" });

  function refresh() {
    api.get<Employee[]>("/businesses/me/employees").then(setEmployees);
  }

  useEffect(refresh, []);

  async function addEmployee(e: React.FormEvent) {
    e.preventDefault();
    await api.post("/businesses/me/employees", form);
    setForm({ name: "", role_title: "", phone: "", email: "" });
    refresh();
  }

  async function remove(id: string) {
    await api.del(`/businesses/me/employees/${id}`);
    refresh();
  }

  if (!employees) return <Spinner />;

  return (
    <div>
      <PageHeader title="Employees" description="Team members who help deliver your services." />
      <form onSubmit={addEmployee} className="card mb-6 grid grid-cols-1 gap-3 sm:grid-cols-5">
        <input className="input" placeholder="Name" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        <input className="input" placeholder="Role" value={form.role_title} onChange={(e) => setForm({ ...form, role_title: e.target.value })} />
        <input className="input" placeholder="Phone" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
        <input className="input" placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        <button className="btn-primary">Add employee</button>
      </form>
      {employees.length === 0 ? (
        <EmptyState message="No employees added yet." />
      ) : (
        <div className="space-y-2">
          {employees.map((e) => (
            <div key={e.id} className="card flex items-center justify-between">
              <div>
                <p className="font-medium text-slate-800">{e.name}</p>
                <p className="text-sm text-slate-500">
                  {e.role_title} {e.phone && `· ${e.phone}`}
                </p>
              </div>
              <button onClick={() => remove(e.id)} className="text-sm font-medium text-red-600 hover:underline">
                Remove
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
