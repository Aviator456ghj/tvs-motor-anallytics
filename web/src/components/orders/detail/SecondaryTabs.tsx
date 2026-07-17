"use client";

import { CreditCard, Truck, FileText, Download, RotateCcw, Bell, History, ShieldAlert, CheckCircle2 } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { orderDetail } from "@/lib/order-detail-data";

export function PaymentsTab() {
  const o = orderDetail;
  return (
    <Card className="overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4 border-b border-card-border">
        <h3 className="text-[14px] font-semibold text-foreground">Payments ({o.payments.length})</h3>
        <div className="flex items-center gap-2">
          <button className="text-[12.5px] font-medium text-foreground border border-card-border rounded-lg px-3 py-1.5 hover:bg-background/80">Capture</button>
          <button className="text-[12.5px] font-medium text-foreground border border-card-border rounded-lg px-3 py-1.5 hover:bg-background/80">Void</button>
          <button className="text-[12.5px] font-medium text-foreground border border-card-border rounded-lg px-3 py-1.5 hover:bg-background/80">Refund</button>
          <button className="text-[12.5px] font-medium text-foreground border border-card-border rounded-lg px-3 py-1.5 hover:bg-background/80">Retry Payment</button>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-[12.5px] border-separate border-spacing-0">
          <thead>
            <tr className="text-left text-muted-light font-medium bg-background/60">
              <th className="py-2.5 pl-5 pr-2 font-medium">Type</th>
              <th className="py-2.5 pr-2 font-medium">Method</th>
              <th className="py-2.5 pr-2 font-medium">Gateway</th>
              <th className="py-2.5 pr-2 font-medium">Transaction ID</th>
              <th className="py-2.5 pr-2 font-medium">Amount</th>
              <th className="py-2.5 pr-2 font-medium">Status</th>
              <th className="py-2.5 pr-5 font-medium">Date</th>
            </tr>
          </thead>
          <tbody>
            {o.payments.map((p) => (
              <tr key={p.id} className="border-t border-card-border/70">
                <td className="py-3 pl-5 pr-2">
                  <span className="flex items-center gap-1.5 text-foreground font-medium whitespace-nowrap">
                    <CreditCard size={13} className="text-muted-light" /> {p.type}
                  </span>
                </td>
                <td className="py-3 pr-2 text-muted whitespace-nowrap">{p.method}</td>
                <td className="py-3 pr-2 text-muted whitespace-nowrap">{p.gateway}</td>
                <td className="py-3 pr-2 text-muted whitespace-nowrap">{p.transactionId}</td>
                <td className="py-3 pr-2 text-foreground font-medium whitespace-nowrap">${p.amount.toFixed(2)}</td>
                <td className="py-3 pr-2">
                  <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-success-bg text-success">{p.status}</span>
                </td>
                <td className="py-3 pr-5 text-muted-light whitespace-nowrap">{p.date}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

export function ShipmentsTab() {
  const o = orderDetail;
  return (
    <div className="flex flex-col gap-4">
      {o.shipments.map((s) => (
        <Card key={s.id} className="p-5">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
            <div className="flex items-center gap-3">
              <span className="w-10 h-10 rounded-lg bg-info-bg flex items-center justify-center text-info shrink-0">
                <Truck size={17} />
              </span>
              <div>
                <div className="text-[13.5px] font-semibold text-foreground">
                  {s.service} · {s.trackingNumber}
                </div>
                <div className="text-[12px] text-muted-light">
                  {s.items} · Shipped {s.shippedAt} · Expected {s.expectedAt}
                </div>
              </div>
            </div>
            <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-info-bg text-info">{s.status}</span>
          </div>
          <div className="flex flex-col gap-2 pl-3 border-l-2 border-card-border ml-5">
            {s.events.map((e, i) => (
              <div key={i} className="flex items-center justify-between text-[12.5px]">
                <span className="text-foreground">{e.label}</span>
                <span className="text-muted-light">
                  {e.location} · {e.time}
                </span>
              </div>
            ))}
          </div>
          <button className="mt-3 text-[12.5px] font-medium text-brand-start hover:underline">Track on {s.carrier}</button>
        </Card>
      ))}
    </div>
  );
}

export function InvoicesTab() {
  const o = orderDetail;
  return (
    <Card className="overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4 border-b border-card-border">
        <h3 className="text-[14px] font-semibold text-foreground">Invoices ({o.invoices.length})</h3>
        <button className="text-[12.5px] font-medium text-white bg-brand-start rounded-lg px-3 py-1.5 hover:opacity-90">Generate Invoice</button>
      </div>
      <div className="px-5 py-3 flex flex-col gap-2">
        {o.invoices.map((inv) => (
          <div key={inv.id} className="flex items-center justify-between py-1.5">
            <span className="flex items-center gap-2.5">
              <FileText size={15} className="text-muted-light" />
              <span>
                <div className="text-[13px] font-medium text-foreground">{inv.id}</div>
                <div className="text-[11.5px] text-muted-light">
                  {inv.type} · {inv.date}
                </div>
              </span>
            </span>
            <span className="flex items-center gap-3">
              <span className="text-[13px] font-medium text-foreground">${inv.amount.toFixed(2)}</span>
              <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-success-bg text-success">{inv.status}</span>
              <button className="text-muted-light hover:text-muted" title="Download">
                <Download size={14} />
              </button>
            </span>
          </div>
        ))}
      </div>
    </Card>
  );
}

export function ReturnsTab() {
  const o = orderDetail;
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[14px] font-semibold text-foreground">Returns ({o.returns.length})</h3>
        <button className="text-[12.5px] font-medium text-foreground border border-card-border rounded-lg px-3 py-1.5 hover:bg-background/80">Create Return</button>
      </div>
      {o.returns.length === 0 ? (
        <div className="py-8 text-center">
          <RotateCcw size={22} className="text-muted-light mx-auto mb-2" />
          <div className="text-[13px] text-muted">No returns for this order</div>
          <div className="text-[11.5px] text-muted-light mt-1">Returns become available once the order is delivered.</div>
        </div>
      ) : null}
    </Card>
  );
}

export function NotesTab() {
  const o = orderDetail;
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {(["customer", "internal"] as const).map((type) => {
        const notes = o.notes.filter((n) => n.type === type);
        return (
          <Card key={type} className="p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-[14px] font-semibold text-foreground">{type === "customer" ? "Customer Notes" : "Internal Notes"}</h3>
              <button className="text-[12px] font-medium text-brand-start hover:underline">Add Note</button>
            </div>
            <div className="text-[11px] text-muted-light mb-2.5">
              {type === "customer" ? "Visible to customer" : "Visible only to staff"}
            </div>
            <div className="flex flex-col gap-2.5">
              {notes.map((n) => (
                <div key={n.id} className={`rounded-lg p-3 ${type === "customer" ? "bg-warning-bg" : "bg-background"}`}>
                  <div className="flex items-center gap-1.5 text-[12px] font-semibold text-foreground">
                    <Bell size={12} className={type === "customer" ? "text-warning" : "text-muted-light"} /> {n.title}
                    <span className="ml-auto text-[10.5px] font-normal text-muted-light">{n.time}</span>
                  </div>
                  <p className="text-[12px] text-foreground mt-1 leading-snug">{n.body}</p>
                  <div className="text-[10.5px] text-muted-light mt-1">Added by {n.author}</div>
                </div>
              ))}
              {notes.length === 0 && <span className="text-[12px] text-muted-light">No notes yet</span>}
            </div>
          </Card>
        );
      })}
    </div>
  );
}

export function TimelineTab() {
  const o = orderDetail;
  return (
    <Card className="p-5">
      <h3 className="text-[14px] font-semibold text-foreground mb-4">Order Timeline</h3>
      <div className="flex flex-col">
        {o.timeline.map((t, i) => (
          <div key={i} className="flex gap-3">
            <div className="flex flex-col items-center">
              <span className="w-7 h-7 rounded-full bg-success-bg flex items-center justify-center text-success shrink-0">
                <CheckCircle2 size={13} />
              </span>
              {i < o.timeline.length - 1 && <span className="w-px flex-1 bg-card-border my-1" />}
            </div>
            <div className="pb-5 min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-[13px] font-semibold text-foreground">{t.label}</span>
                <span className="px-1.5 py-0.5 rounded bg-background text-[10.5px] text-muted">{t.department}</span>
              </div>
              <div className="text-[12px] text-muted mt-0.5">{t.note}</div>
              <div className="text-[11px] text-muted-light mt-0.5">
                {t.user} · {t.time}
              </div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

export function ActivityTab() {
  const o = orderDetail;
  return (
    <Card className="p-5">
      <h3 className="text-[14px] font-semibold text-foreground mb-4">Activity</h3>
      <div className="flex flex-col gap-3">
        {o.activity.map((a) => (
          <div key={a.id} className="flex items-start gap-2.5">
            <span className="w-7 h-7 rounded-full bg-background flex items-center justify-center text-muted-light shrink-0">
              <History size={13} />
            </span>
            <div>
              <div className="text-[12.5px] text-foreground">{a.text}</div>
              <div className="text-[11px] text-muted-light">
                {a.actor} · {a.time}
              </div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

export function LogsTab() {
  const o = orderDetail;
  return (
    <Card className="overflow-hidden">
      <div className="flex items-center gap-2 px-5 py-4 border-b border-card-border">
        <ShieldAlert size={15} className="text-muted-light" />
        <h3 className="text-[14px] font-semibold text-foreground">Audit Logs ({o.auditLogs.length})</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-[12px] border-separate border-spacing-0">
          <thead>
            <tr className="text-left text-muted-light font-medium bg-background/60">
              <th className="py-2.5 pl-5 pr-2 font-medium">Action</th>
              <th className="py-2.5 pr-2 font-medium">Actor</th>
              <th className="py-2.5 pr-2 font-medium">Before</th>
              <th className="py-2.5 pr-2 font-medium">After</th>
              <th className="py-2.5 pr-2 font-medium">IP</th>
              <th className="py-2.5 pr-5 font-medium">Time</th>
            </tr>
          </thead>
          <tbody>
            {o.auditLogs.map((log) => (
              <tr key={log.id} className="border-t border-card-border/70">
                <td className="py-2.5 pl-5 pr-2 font-mono text-[11.5px] text-foreground whitespace-nowrap">{log.action}</td>
                <td className="py-2.5 pr-2 text-muted whitespace-nowrap">{log.actor}</td>
                <td className="py-2.5 pr-2 text-muted-light whitespace-nowrap">{log.before}</td>
                <td className="py-2.5 pr-2 text-muted whitespace-nowrap">{log.after}</td>
                <td className="py-2.5 pr-2 text-muted-light whitespace-nowrap">{log.ip}</td>
                <td className="py-2.5 pr-5 text-muted-light whitespace-nowrap">{log.time}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
