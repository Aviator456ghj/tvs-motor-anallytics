"use client";

import { useMemo, useState } from "react";
import ReturnsHeader from "@/components/orders/returns/ReturnsHeader";
import ReturnsKpiRow from "@/components/orders/returns/ReturnsKpiRow";
import ReturnsToolbar from "@/components/orders/returns/ReturnsToolbar";
import ReturnsTabs from "@/components/orders/returns/ReturnsTabs";
import ReturnsTable from "@/components/orders/returns/ReturnsTable";
import ReturnDetailsPanel from "@/components/orders/returns/ReturnDetailsPanel";
import ReturnActivityTimeline from "@/components/orders/returns/ReturnActivityTimeline";
import TopReturnedProducts from "@/components/orders/returns/TopReturnedProducts";
import ReturnsRightSidebar from "@/components/orders/returns/ReturnsRightSidebar";
import {
  returnRequests,
  statusTabs,
  statusOptions,
  reasonOptions,
  warehouseOptions,
  returnTypeOptions,
  type ReturnBucket,
} from "@/lib/returns-data";

export default function ReturnsPage() {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState(statusOptions[0]);
  const [reason, setReason] = useState(reasonOptions[0]);
  const [warehouse, setWarehouse] = useState(warehouseOptions[0]);
  const [returnType, setReturnType] = useState(returnTypeOptions[0]);
  const [activeTab, setActiveTab] = useState<ReturnBucket>("all");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [selectedRmaId, setSelectedRmaId] = useState(returnRequests[0].id);
  const [currentPage, setCurrentPage] = useState(1);

  const filtered = useMemo(() => {
    return returnRequests.filter((r) => {
      const inBucket = activeTab === "all" || r.bucket === activeTab;
      const q = search.trim().toLowerCase();
      const matchesSearch = q === "" || r.id.toLowerCase().includes(q) || r.orderId.toLowerCase().includes(q) || r.customer.toLowerCase().includes(q);
      const matchesStatus = status === statusOptions[0] || r.status === status;
      const matchesReason = reason === reasonOptions[0] || r.reason === reason;
      const matchesWarehouse = warehouse === warehouseOptions[0] || r.warehouse === warehouse;
      const matchesType = returnType === returnTypeOptions[0] || r.returnType === returnType;
      return inBucket && matchesSearch && matchesStatus && matchesReason && matchesWarehouse && matchesType;
    });
  }, [activeTab, search, status, reason, warehouse, returnType]);

  const totalCount = statusTabs.find((t) => t.key === activeTab)?.count ?? filtered.length;
  const totalPages = Math.max(1, Math.ceil(totalCount / 5));
  const selectedReturn = returnRequests.find((r) => r.id === selectedRmaId) ?? returnRequests[0];

  function toggleSelect(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }
  function toggleSelectAll() {
    setSelectedIds((prev) => (filtered.every((r) => prev.has(r.id)) ? new Set() : new Set(filtered.map((r) => r.id))));
  }

  return (
    <div className="flex flex-col gap-5">
      <ReturnsHeader />
      <ReturnsKpiRow />

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_280px] gap-5 items-start">
        <div className="flex flex-col gap-4 min-w-0">
          <div className="bg-card-bg border border-card-border rounded-xl p-4 flex flex-col gap-4">
            <ReturnsToolbar
              search={search}
              onSearchChange={setSearch}
              status={status}
              onStatusChange={setStatus}
              reason={reason}
              onReasonChange={setReason}
              warehouse={warehouse}
              onWarehouseChange={setWarehouse}
              returnType={returnType}
              onReturnTypeChange={setReturnType}
            />
            <ReturnsTabs active={activeTab} onChange={setActiveTab} />
          </div>

          <ReturnsTable
            rows={filtered}
            selectedIds={selectedIds}
            onToggleSelect={toggleSelect}
            onToggleSelectAll={toggleSelectAll}
            onView={setSelectedRmaId}
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={setCurrentPage}
            totalCount={totalCount}
          />

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <ReturnDetailsPanel selected={selectedReturn} />
            <ReturnActivityTimeline />
            <TopReturnedProducts />
          </div>
        </div>

        <ReturnsRightSidebar />
      </div>
    </div>
  );
}
