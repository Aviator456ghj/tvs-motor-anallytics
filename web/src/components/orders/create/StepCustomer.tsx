"use client";

import { useState } from "react";
import { Search, Plus, Pencil, ChevronDown, ShieldCheck, Bell } from "lucide-react";
import { Card } from "@/components/ui/Card";
import {
  customers,
  customerRecentOrders,
  customerNotes,
  suggestedTags,
  salesChannels,
  warehouses,
  currencies,
  languages,
  orderPriorities,
  fraudChecks,
  type CustomerLite,
  type Address,
  type OrderPriority,
} from "@/lib/create-order-data";

export type CustomerStepState = {
  mode: "existing" | "new";
  customerId: string | null;
  billingAddress: Address | null;
  shippingAddress: Address | null;
  salesChannel: string;
  warehouse: string;
  currency: string;
  priority: OrderPriority;
  tags: string[];
  internalNotes: string;
};

export default function StepCustomer({
  state,
  onChange,
}: {
  state: CustomerStepState;
  onChange: (patch: Partial<CustomerStepState>) => void;
}) {
  const [query, setQuery] = useState("");
  const [tagInput, setTagInput] = useState("");

  const selectedCustomer = customers.find((c) => c.id === state.customerId) ?? null;
  const matches = query.trim()
    ? customers.filter(
        (c) => c.name.toLowerCase().includes(query.toLowerCase()) || c.email.toLowerCase().includes(query.toLowerCase())
      )
    : customers;

  function selectCustomer(c: CustomerLite) {
    onChange({ customerId: c.id, billingAddress: c.billingAddress, shippingAddress: c.shippingAddress });
    setQuery("");
  }

  function addTag(t: string) {
    const tag = t.trim();
    if (tag && !state.tags.includes(tag)) onChange({ tags: [...state.tags, tag] });
    setTagInput("");
  }

  return (
    <div className="flex flex-col gap-4">
      <Card className="p-5">
        <h3 className="text-[14.5px] font-semibold text-foreground mb-3">Customer Information</h3>
        <div className="flex items-center gap-5 mb-4">
          <label className="flex items-center gap-2 text-[13px] font-medium text-foreground cursor-pointer">
            <input
              type="radio"
              checked={state.mode === "existing"}
              onChange={() => onChange({ mode: "existing" })}
              className="accent-brand-start"
            />
            Existing Customer
          </label>
          <label className="flex items-center gap-2 text-[13px] font-medium text-foreground cursor-pointer">
            <input type="radio" checked={state.mode === "new"} onChange={() => onChange({ mode: "new" })} className="accent-brand-start" />
            New Customer
          </label>
        </div>

        {state.mode === "existing" ? (
          <>
            <div className="flex items-center gap-2 mb-3">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-light" size={15} />
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search customer by name, email, phone..."
                  className="w-full pl-9 pr-8 py-2.5 rounded-lg border border-card-border bg-background/60 text-[13px] placeholder:text-muted-light focus:outline-none focus:ring-2 focus:ring-brand-start/30"
                />
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-light" size={14} />
                {query && (
                  <div className="absolute left-0 right-0 top-full mt-1 bg-card-bg border border-card-border rounded-lg shadow-lg z-20 max-h-56 overflow-y-auto">
                    {matches.length === 0 && <div className="px-3 py-2 text-[12.5px] text-muted-light">No customers found</div>}
                    {matches.map((c) => (
                      <button
                        key={c.id}
                        onClick={() => selectCustomer(c)}
                        className="w-full text-left px-3 py-2 hover:bg-background/80 flex items-center justify-between"
                      >
                        <span>
                          <div className="text-[12.5px] font-medium text-foreground">{c.name}</div>
                          <div className="text-[11px] text-muted-light">{c.email}</div>
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <button className="flex items-center gap-1.5 text-[13px] font-medium text-white bg-brand-start rounded-lg px-3.5 py-2.5 hover:opacity-90 whitespace-nowrap">
                <Plus size={14} /> Add New Customer
              </button>
            </div>

            {selectedCustomer && (
              <div className="flex flex-wrap items-center gap-4 rounded-lg border border-card-border p-4">
                <span className="w-11 h-11 rounded-full bg-gradient-to-br from-brand-start to-brand-end flex items-center justify-center text-white text-[13px] font-semibold shrink-0">
                  {selectedCustomer.name.split(" ").map((n) => n[0]).join("")}
                </span>
                <div className="min-w-[160px]">
                  <div className="flex items-center gap-2">
                    <span className="text-[13.5px] font-semibold text-foreground">{selectedCustomer.name}</span>
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10.5px] font-medium ${
                        selectedCustomer.registered ? "bg-success-bg text-success" : "bg-card-border/60 text-muted"
                      }`}
                    >
                      {selectedCustomer.registered ? "Registered" : "Guest"}
                    </span>
                  </div>
                  <div className="text-[12px] text-muted-light">
                    {selectedCustomer.email} · {selectedCustomer.phone}
                  </div>
                </div>
                <Stat label="Total Orders" value={String(selectedCustomer.totalOrders)} />
                <Stat label="Total Spent" value={`$${selectedCustomer.lifetimeSpend.toFixed(2)}`} />
                <Stat
                  label="Outstanding"
                  value={`$${selectedCustomer.outstandingBalance.toFixed(2)}`}
                  valueClass={selectedCustomer.outstandingBalance > 0 ? "text-danger" : undefined}
                />
              </div>
            )}
          </>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <TextField label="First Name" />
            <TextField label="Last Name" />
            <TextField label="Email" type="email" required />
            <TextField label="Phone" />
            <TextField label="Company" />
            <TextField label="GST Number" />
            <TextField label="Tax ID" />
          </div>
        )}
      </Card>

      {state.mode === "existing" && selectedCustomer && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <AddressCard
            title="Billing Address"
            address={state.billingAddress}
            checkboxLabel="Use Shipping"
            checked={state.shippingAddress !== null && state.billingAddress === state.shippingAddress}
            onCheck={() => onChange({ billingAddress: state.shippingAddress })}
          />
          <AddressCard
            title="Shipping Address"
            address={state.shippingAddress}
            checkboxLabel="Use Billing"
            checked={state.billingAddress !== null && state.shippingAddress === state.billingAddress}
            onCheck={() => onChange({ shippingAddress: state.billingAddress })}
          />
        </div>
      )}

      <Card className="p-5">
        <h3 className="text-[14.5px] font-semibold text-foreground mb-3">Order Settings</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <SelectField label="Sales Channel" value={state.salesChannel} options={salesChannels} onChange={(v) => onChange({ salesChannel: v })} />
          <SelectField label="Warehouse" value={state.warehouse} options={warehouses} onChange={(v) => onChange({ warehouse: v })} />
          <div>
            <label className="text-[11.5px] font-medium text-muted mb-1 block">Order Date</label>
            <input
              readOnly
              value="May 17, 2025 10:30 AM"
              className="w-full rounded-lg border border-card-border bg-background/60 text-[13px] px-3 py-2"
            />
          </div>
          <SelectField label="Currency" value={state.currency} options={currencies} onChange={(v) => onChange({ currency: v })} />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3">
          <div>
            <label className="text-[11.5px] font-medium text-muted mb-1 block">Order Priority</label>
            <div className="flex items-center gap-2">
              {orderPriorities.map((p) => (
                <button
                  key={p}
                  onClick={() => onChange({ priority: p })}
                  className={`px-3 py-1.5 rounded-lg text-[12px] font-medium border ${
                    state.priority === p ? "bg-brand-start text-white border-brand-start" : "border-card-border text-muted hover:bg-background/80"
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
          <SelectField label="Language" value={languages[0]} options={languages} onChange={() => {}} />
        </div>
      </Card>

      <Card className="p-5">
        <h3 className="text-[14.5px] font-semibold text-foreground mb-2">Tags</h3>
        <div className="flex flex-wrap items-center gap-1.5 mb-2">
          {state.tags.map((t) => (
            <span key={t} className="flex items-center gap-1 px-2 py-1 rounded-full bg-background text-[11.5px] text-foreground">
              {t}
              <button onClick={() => onChange({ tags: state.tags.filter((x) => x !== t) })} className="text-muted-light hover:text-danger">
                ×
              </button>
            </span>
          ))}
          <input
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addTag(tagInput)}
            placeholder="Select or type tags..."
            className="flex-1 min-w-[140px] text-[12.5px] px-2 py-1 focus:outline-none"
          />
        </div>
        <div className="flex flex-wrap gap-1.5">
          {suggestedTags
            .filter((t) => !state.tags.includes(t))
            .map((t) => (
              <button
                key={t}
                onClick={() => addTag(t)}
                className="px-2 py-1 rounded-full border border-card-border text-[11px] text-muted hover:bg-background/80"
              >
                + {t}
              </button>
            ))}
        </div>
      </Card>

      <Card className="p-5">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-[14.5px] font-semibold text-foreground">Internal Notes</h3>
          <span className="text-[11px] text-muted-light">{state.internalNotes.length}/500</span>
        </div>
        <textarea
          value={state.internalNotes}
          onChange={(e) => onChange({ internalNotes: e.target.value.slice(0, 500) })}
          rows={2}
          placeholder="Add internal note..."
          className="w-full rounded-lg border border-card-border bg-background/60 text-[13px] px-3 py-2 placeholder:text-muted-light focus:outline-none focus:ring-2 focus:ring-brand-start/30"
        />
      </Card>

      {state.mode === "existing" && selectedCustomer && (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          <Card className="p-4">
            <div className="flex items-center justify-between mb-2.5">
              <h4 className="text-[13px] font-semibold text-foreground">Customer Recent Orders</h4>
              <a href="#" className="text-[11.5px] font-medium text-brand-start hover:underline">View all</a>
            </div>
            <div className="flex flex-col gap-2">
              {(customerRecentOrders[selectedCustomer.id] ?? []).map((o) => (
                <div key={o.id} className="flex items-center justify-between text-[12px]">
                  <span className="text-brand-start font-medium">{o.id}</span>
                  <span className="text-muted-light">{o.date}</span>
                  <span className="text-foreground">{o.total}</span>
                  <span className={o.status === "Completed" ? "text-success" : "text-warning"}>{o.status}</span>
                </div>
              ))}
              {(customerRecentOrders[selectedCustomer.id] ?? []).length === 0 && (
                <span className="text-[12px] text-muted-light">No previous orders</span>
              )}
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center justify-between mb-2.5">
              <h4 className="text-[13px] font-semibold text-foreground">Customer Notes</h4>
              <a href="#" className="text-[11.5px] font-medium text-brand-start hover:underline">View all</a>
            </div>
            {(customerNotes[selectedCustomer.id] ?? []).map((n, i) => (
              <div key={i} className="rounded-lg bg-warning-bg p-2.5">
                <div className="flex items-center gap-1.5 text-[12px] font-semibold text-warning">
                  <Bell size={12} /> {n.title}
                </div>
                <p className="text-[11.5px] text-foreground mt-1 leading-snug">{n.body}</p>
                <div className="text-[10.5px] text-muted-light mt-1">
                  Added by {n.author} on {n.date}
                </div>
              </div>
            ))}
            {(customerNotes[selectedCustomer.id] ?? []).length === 0 && <span className="text-[12px] text-muted-light">No notes</span>}
          </Card>

          <Card className="p-4">
            <h4 className="text-[13px] font-semibold text-foreground mb-2.5">Inventory Status</h4>
            <p className="text-[11.5px] text-muted-light mb-2">All items will be validated in next step.</p>
            <div className="flex flex-col gap-1.5">
              <StatusDot color="bg-success" label="In Stock" desc="Enough stock available" />
              <StatusDot color="bg-warning" label="Low Stock" desc="Some items are low in stock" />
              <StatusDot color="bg-danger" label="Out of Stock" desc="Item not available" />
            </div>
          </Card>

          <Card className="p-4">
            <h4 className="text-[13px] font-semibold text-foreground mb-2.5">Fraud Check</h4>
            <p className="text-[11.5px] text-muted-light mb-2">Will be performed after order review.</p>
            <div className="rounded-lg bg-success-bg p-3 flex items-center gap-2.5">
              <ShieldCheck size={18} className="text-success shrink-0" />
              <span className="text-[11.5px] text-success">
                This order will be screened for fraud before confirmation. Checks: {fraudChecks.slice(0, 3).join(", ")}, and more.
              </span>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, valueClass }: { label: string; value: string; valueClass?: string }) {
  return (
    <div className="ml-auto sm:ml-0">
      <div className="text-[10.5px] text-muted-light">{label}</div>
      <div className={`text-[13px] font-semibold ${valueClass ?? "text-foreground"}`}>{value}</div>
    </div>
  );
}

function TextField({ label, type = "text", required }: { label: string; type?: string; required?: boolean }) {
  return (
    <div>
      <label className="text-[11.5px] font-medium text-muted mb-1 block">
        {label} {required && <span className="text-danger">*</span>}
      </label>
      <input type={type} className="w-full rounded-lg border border-card-border bg-background/60 text-[13px] px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-start/30" />
    </div>
  );
}

function SelectField({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (v: string) => void }) {
  return (
    <div>
      <label className="text-[11.5px] font-medium text-muted mb-1 block">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-card-border bg-background/60 text-[13px] px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-start/30"
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </div>
  );
}

function AddressCard({
  title,
  address,
  checkboxLabel,
  checked,
  onCheck,
}: {
  title: string;
  address: Address | null;
  checkboxLabel: string;
  checked: boolean;
  onCheck: () => void;
}) {
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[14.5px] font-semibold text-foreground">{title}</h3>
        <label className="flex items-center gap-1.5 text-[12px] text-muted cursor-pointer">
          <input type="checkbox" checked={checked} onChange={onCheck} className="accent-brand-start" />
          {checkboxLabel}
        </label>
      </div>
      <select className="w-full rounded-lg border border-card-border bg-background/60 text-[13px] px-3 py-2 mb-3">
        <option>Select saved address</option>
      </select>
      {address ? (
        <div className="rounded-lg border border-card-border p-3 flex items-start justify-between gap-3">
          <div className="text-[12.5px] text-foreground leading-snug">
            {address.name}
            <br />
            {address.line1}
            <br />
            {address.city}, {address.state} {address.postalCode}
            <br />
            {address.country}
            <br />
            {address.phone}
          </div>
          <button className="flex items-center gap-1 text-[12px] font-medium text-brand-start hover:underline shrink-0">
            <Pencil size={12} /> Edit
          </button>
        </div>
      ) : (
        <div className="rounded-lg border border-dashed border-card-border p-4 text-center text-[12.5px] text-muted-light">No address selected</div>
      )}
      <button className="flex items-center gap-1.5 text-[12.5px] font-medium text-brand-start hover:underline mt-2.5">
        <Plus size={13} /> Add New Address
      </button>
    </Card>
  );
}

function StatusDot({ color, label, desc }: { color: string; label: string; desc: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className={`w-2 h-2 rounded-full shrink-0 ${color}`} />
      <span className="text-[11.5px] font-medium text-foreground w-[76px] shrink-0">{label}</span>
      <span className="text-[11px] text-muted-light">{desc}</span>
    </div>
  );
}
