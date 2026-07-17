"use client";

import { useMemo, useState } from "react";
import ProductsHeader from "@/components/products/ProductsHeader";
import ProductsKpiRow from "@/components/products/ProductsKpiRow";
import ProductsToolbar from "@/components/products/ProductsToolbar";
import ProductsTabs from "@/components/products/ProductsTabs";
import ProductsTable from "@/components/products/ProductsTable";
import ProductDetailPanel from "@/components/products/ProductDetailPanel";
import ProductsRightSidebar from "@/components/products/ProductsRightSidebar";
import {
  products,
  productTabs,
  productColumns,
  type ProductBucket,
  type ProductColumnKey,
  type BulkActionKey,
} from "@/lib/products-data";

const defaultVisibleColumns = new Set<ProductColumnKey>(productColumns.filter((c) => c.defaultVisible).map((c) => c.key));

export default function ProductsPage() {
  const [search, setSearch] = useState("");
  const [activeTab, setActiveTab] = useState<ProductBucket>("all");
  const [visibleColumns, setVisibleColumns] = useState<Set<ProductColumnKey>>(defaultVisibleColumns);
  const [sort, setSort] = useState("Date (Newest)");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [selectedProductId, setSelectedProductId] = useState<string>(products[0].id);
  const [currentPage, setCurrentPage] = useState(1);

  const filtered = useMemo(() => {
    return products.filter((p) => {
      const inBucket = activeTab === "all" || p.buckets.includes(activeTab);
      const q = search.trim().toLowerCase();
      const matchesSearch =
        q === "" ||
        p.name.toLowerCase().includes(q) ||
        p.sku.toLowerCase().includes(q) ||
        p.barcode.toLowerCase().includes(q) ||
        p.category.toLowerCase().includes(q);
      return inBucket && matchesSearch;
    });
  }, [activeTab, search]);

  const totalCount = productTabs.find((t) => t.key === activeTab)?.count ?? filtered.length;
  const totalPages = Math.max(1, Math.ceil(totalCount / 6));
  const selectedProduct = products.find((p) => p.id === selectedProductId) ?? products[0];

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
      if (filtered.every((p) => prev.has(p.id))) return new Set();
      return new Set(filtered.map((p) => p.id));
    });
  }

  function toggleColumn(key: ProductColumnKey) {
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
      <ProductsHeader />
      <ProductsKpiRow />

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_280px] gap-5 items-start">
        <div className="flex flex-col gap-4 min-w-0">
          <div className="bg-card-bg border border-card-border rounded-xl p-4 flex flex-col gap-4">
            <ProductsToolbar
              search={search}
              onSearchChange={setSearch}
              visibleColumns={visibleColumns}
              onToggleColumn={toggleColumn}
              sort={sort}
              onSortChange={setSort}
              selectedCount={selectedIds.size}
              onBulkAction={handleBulkAction}
            />
            <ProductsTabs active={activeTab} onChange={setActiveTab} />
          </div>

          <ProductsTable
            rows={filtered}
            visibleColumns={visibleColumns}
            selectedIds={selectedIds}
            onToggleSelect={toggleSelect}
            onToggleSelectAll={toggleSelectAll}
            onView={setSelectedProductId}
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={setCurrentPage}
            totalCount={totalCount}
          />

          <ProductDetailPanel product={selectedProduct} />
        </div>

        <ProductsRightSidebar />
      </div>
    </div>
  );
}
