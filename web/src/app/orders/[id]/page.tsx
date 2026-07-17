"use client";

import { useState } from "react";
import OrderDetailHeader from "@/components/orders/detail/OrderDetailHeader";
import OrderKpiStrip from "@/components/orders/detail/OrderKpiStrip";
import OverviewTab from "@/components/orders/detail/OverviewTab";
import ItemsTable from "@/components/orders/detail/ItemsTable";
import OrderDetailSidebar from "@/components/orders/detail/OrderDetailSidebar";
import {
  PaymentsTab,
  ShipmentsTab,
  InvoicesTab,
  ReturnsTab,
  NotesTab,
  TimelineTab,
  ActivityTab,
  LogsTab,
} from "@/components/orders/detail/SecondaryTabs";
import { orderDetail, detailTabs, type OrderDetailTab } from "@/lib/order-detail-data";

const tabCounts: Partial<Record<OrderDetailTab, number>> = {
  Items: orderDetail.items.length,
  Payments: orderDetail.payments.length,
  Shipments: orderDetail.shipments.length,
  Invoices: orderDetail.invoices.length,
  Returns: orderDetail.returns.length,
  Notes: orderDetail.notes.length,
};

export default function OrderDetailPage() {
  const [tab, setTab] = useState<OrderDetailTab>("Overview");

  return (
    <div className="flex flex-col gap-5 max-w-[1600px] mx-auto">
      <OrderDetailHeader />
      <OrderKpiStrip />

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_280px] gap-5 items-start">
        <div className="flex flex-col gap-4 min-w-0">
          <div className="bg-card-bg border border-card-border rounded-xl px-4 pt-1 flex items-center gap-1 overflow-x-auto">
            {detailTabs.map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`whitespace-nowrap px-2.5 py-3 text-[13px] font-medium border-b-2 -mb-px transition-colors ${
                  tab === t ? "border-brand-start text-brand-start" : "border-transparent text-muted hover:text-foreground"
                }`}
              >
                {t}
                {tabCounts[t] !== undefined && <span className="ml-1 text-[11px] text-muted-light">({tabCounts[t]})</span>}
              </button>
            ))}
          </div>

          {tab === "Overview" && <OverviewTab />}
          {tab === "Items" && <ItemsTable extended />}
          {tab === "Payments" && <PaymentsTab />}
          {tab === "Shipments" && <ShipmentsTab />}
          {tab === "Invoices" && <InvoicesTab />}
          {tab === "Returns" && <ReturnsTab />}
          {tab === "Notes" && <NotesTab />}
          {tab === "Timeline" && <TimelineTab />}
          {tab === "Activity" && <ActivityTab />}
          {tab === "Logs" && <LogsTab />}
        </div>

        <OrderDetailSidebar />
      </div>
    </div>
  );
}
