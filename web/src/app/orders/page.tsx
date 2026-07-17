"use client";

import { useMemo, useState } from "react";
import OrdersHeader from "@/components/orders/OrdersHeader";
import OrdersKpiRow from "@/components/orders/OrdersKpiRow";
import OrdersToolbar from "@/components/orders/OrdersToolbar";
import OrdersStatusTabs from "@/components/orders/OrdersStatusTabs";
import OrdersTable from "@/components/orders/OrdersTable";
import OrderDetailPanel from "@/components/orders/OrderDetailPanel";
import OrdersRightSidebar from "@/components/orders/OrdersRightSidebar";
import {
  orders,
  statusTabs,
  orderColumns,
  type OrderBucket,
  type OrderColumnKey,
  type BulkActionKey,
} from "@/lib/orders-data";

const defaultVisibleColumns = new Set<OrderColumnKey>(
  orderColumns.filter((c) => c.defaultVisible).map((c) => c.key)
);

export default function OrdersPage() {
  const [search, setSearch] = useState("");
  const [activeTab, setActiveTab] = useState<OrderBucket>("all");
  const [visibleColumns, setVisibleColumns] = useState<Set<OrderColumnKey>>(defaultVisibleColumns);
  const [sort, setSort] = useState("Date (Newest)");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [selectedOrderId, setSelectedOrderId] = useState<string>(orders[0].id);
  const [currentPage, setCurrentPage] = useState(1);

  const filtered = useMemo(() => {
    return orders.filter((o) => {
      const inBucket = activeTab === "all" || o.buckets.includes(activeTab);
      const q = search.trim().toLowerCase();
      const matchesSearch =
        q === "" ||
        o.id.toLowerCase().includes(q) ||
        o.customer.toLowerCase().includes(q) ||
        o.email.toLowerCase().includes(q);
      return inBucket && matchesSearch;
    });
  }, [activeTab, search]);

  const totalCount = statusTabs.find((t) => t.key === activeTab)?.count ?? filtered.length;
  const totalPages = Math.max(1, Math.ceil(totalCount / 8));
  const selectedOrder = orders.find((o) => o.id === selectedOrderId) ?? orders[0];

  function toggleSelect(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleSelectAll() {
    setSelectedIds((prev) => {
      if (filtered.every((o) => prev.has(o.id))) return new Set();
      return new Set(filtered.map((o) => o.id));
    });
  }

  function toggleColumn(key: OrderColumnKey) {
    setVisibleColumns((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function handleBulkAction(key: BulkActionKey) {
    console.log("bulk action", key, Array.from(selectedIds));
    setSelectedIds(new Set());
  }

  return (
    <div className="flex flex-col gap-5 max-w-[1600px] mx-auto">
      <OrdersHeader />
      <OrdersKpiRow />

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_280px] gap-5 items-start">
        <div className="flex flex-col gap-4 min-w-0">
          <div className="bg-card-bg border border-card-border rounded-xl p-4 flex flex-col gap-4">
            <OrdersToolbar
              search={search}
              onSearchChange={setSearch}
              visibleColumns={visibleColumns}
              onToggleColumn={toggleColumn}
              sort={sort}
              onSortChange={setSort}
              selectedCount={selectedIds.size}
              onBulkAction={handleBulkAction}
            />
            <OrdersStatusTabs active={activeTab} onChange={setActiveTab} />
          </div>

          <OrdersTable
            rows={filtered}
            visibleColumns={visibleColumns}
            selectedIds={selectedIds}
            onToggleSelect={toggleSelect}
            onToggleSelectAll={toggleSelectAll}
            onView={setSelectedOrderId}
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={setCurrentPage}
            totalCount={totalCount}
          />

          <OrderDetailPanel order={selectedOrder} />
        </div>

        <OrdersRightSidebar />
      </div>
    </div>
  );
}
