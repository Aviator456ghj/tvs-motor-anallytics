"use client";

import { useMemo, useState } from "react";
import FulfillmentHeader from "@/components/orders/fulfillment/FulfillmentHeader";
import FulfillmentKpiRow from "@/components/orders/fulfillment/FulfillmentKpiRow";
import FulfillmentToolbar from "@/components/orders/fulfillment/FulfillmentToolbar";
import FulfillmentTabs from "@/components/orders/fulfillment/FulfillmentTabs";
import FulfillmentTable from "@/components/orders/fulfillment/FulfillmentTable";
import FulfillmentWorkflow from "@/components/orders/fulfillment/FulfillmentWorkflow";
import ActivityAndExceptions from "@/components/orders/fulfillment/ActivityAndExceptions";
import FulfillmentRightSidebar from "@/components/orders/fulfillment/FulfillmentRightSidebar";
import {
  fulfillmentOrders,
  statusTabs,
  warehouseOptions,
  channelOptions,
  priorityOptions,
  methodOptions,
  statusOptions,
  type FulfillmentBucket,
} from "@/lib/fulfillment-data";

export default function FulfillmentCenterPage() {
  const [search, setSearch] = useState("");
  const [warehouse, setWarehouse] = useState(warehouseOptions[0]);
  const [channel, setChannel] = useState(channelOptions[0]);
  const [priority, setPriority] = useState(priorityOptions[0]);
  const [method, setMethod] = useState(methodOptions[0]);
  const [status, setStatus] = useState(statusOptions[0]);
  const [activeTab, setActiveTab] = useState<FulfillmentBucket>("all");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [currentPage, setCurrentPage] = useState(1);

  const filtered = useMemo(() => {
    return fulfillmentOrders.filter((o) => {
      const inBucket = activeTab === "all" || o.bucket === activeTab;
      const q = search.trim().toLowerCase();
      const matchesSearch = q === "" || o.id.toLowerCase().includes(q) || o.customer.toLowerCase().includes(q) || o.email.toLowerCase().includes(q);
      const matchesWarehouse = warehouse === warehouseOptions[0] || o.warehouse === warehouse;
      const matchesPriority = priority === priorityOptions[0] || o.priority === priority;
      const matchesMethod = method === methodOptions[0] || o.shippingMethod === method;
      const matchesStatus = status === statusOptions[0] || o.status === status;
      return inBucket && matchesSearch && matchesWarehouse && matchesPriority && matchesMethod && matchesStatus;
    });
  }, [activeTab, search, warehouse, priority, method, status]);

  const totalCount = statusTabs.find((t) => t.key === activeTab)?.count ?? filtered.length;
  const totalPages = Math.max(1, Math.ceil(totalCount / 5));

  function toggleSelect(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }
  function toggleSelectAll() {
    setSelectedIds((prev) => (filtered.every((o) => prev.has(o.id)) ? new Set() : new Set(filtered.map((o) => o.id))));
  }

  return (
    <div className="flex flex-col gap-5">
      <FulfillmentHeader />
      <FulfillmentKpiRow />

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_280px] gap-5 items-start">
        <div className="flex flex-col gap-4 min-w-0">
          <div className="bg-card-bg border border-card-border rounded-xl p-4 flex flex-col gap-4">
            <FulfillmentToolbar
              search={search}
              onSearchChange={setSearch}
              warehouse={warehouse}
              onWarehouseChange={setWarehouse}
              channel={channel}
              onChannelChange={setChannel}
              priority={priority}
              onPriorityChange={setPriority}
              method={method}
              onMethodChange={setMethod}
              status={status}
              onStatusChange={setStatus}
            />
            <FulfillmentTabs active={activeTab} onChange={setActiveTab} />
          </div>

          <FulfillmentTable
            rows={filtered}
            selectedIds={selectedIds}
            onToggleSelect={toggleSelect}
            onToggleSelectAll={toggleSelectAll}
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={setCurrentPage}
            totalCount={totalCount}
          />

          <FulfillmentWorkflow />
          <ActivityAndExceptions />
        </div>

        <FulfillmentRightSidebar />
      </div>
    </div>
  );
}
