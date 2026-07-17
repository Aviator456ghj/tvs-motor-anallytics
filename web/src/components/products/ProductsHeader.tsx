"use client";

import { useState } from "react";
import { ChevronRight, Download, Upload, ChevronDown, Plus } from "lucide-react";
import { exportFormats, importSources, addProductTypes, addProductTypeLabels, type ProductType } from "@/lib/products-data";

export default function ProductsHeader() {
  const [exportOpen, setExportOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [addOpen, setAddOpen] = useState(false);

  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
      <div>
        <div className="flex items-center gap-1.5 text-[12.5px] text-muted-light mb-1">
          <span>Dashboard</span>
          <ChevronRight size={13} />
          <span className="text-foreground font-medium">Products</span>
        </div>
        <h1 className="text-2xl font-bold text-foreground tracking-tight">Products</h1>
      </div>
      <div className="flex items-center gap-2">
        <div className="relative">
          <button
            onClick={() => setExportOpen((v) => !v)}
            className="flex items-center gap-1.5 text-[13px] font-medium text-foreground border border-card-border rounded-lg px-3 py-2 bg-card-bg hover:bg-background/80"
          >
            <Download size={14} />
            Export
          </button>
          {exportOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setExportOpen(false)} />
              <div className="absolute right-0 top-full mt-1 w-40 bg-card-bg border border-card-border rounded-lg shadow-lg z-20 py-1">
                <div className="px-3 py-1 text-[10.5px] font-semibold uppercase tracking-wider text-muted-light">Format</div>
                {exportFormats.map((f) => (
                  <button key={f} onClick={() => setExportOpen(false)} className="w-full text-left px-3 py-1.5 text-[12.5px] text-foreground hover:bg-background/80">
                    {f}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>

        <div className="relative">
          <button
            onClick={() => setImportOpen((v) => !v)}
            className="flex items-center gap-1.5 text-[13px] font-medium text-foreground border border-card-border rounded-lg px-3 py-2 bg-card-bg hover:bg-background/80"
          >
            <Upload size={14} />
            Import
          </button>
          {importOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setImportOpen(false)} />
              <div className="absolute right-0 top-full mt-1 w-40 bg-card-bg border border-card-border rounded-lg shadow-lg z-20 py-1">
                <div className="px-3 py-1 text-[10.5px] font-semibold uppercase tracking-wider text-muted-light">Source</div>
                {importSources.map((s) => (
                  <button key={s} onClick={() => setImportOpen(false)} className="w-full text-left px-3 py-1.5 text-[12.5px] text-foreground hover:bg-background/80">
                    {s}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>

        <div className="relative">
          <button
            onClick={() => setAddOpen((v) => !v)}
            className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-brand-start to-brand-end text-white text-[13px] font-medium pl-4 pr-3 py-2 shadow-sm hover:opacity-90 transition-opacity"
          >
            <Plus size={14} />
            Add Product
            <ChevronDown size={13} className="ml-1" />
          </button>
          {addOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setAddOpen(false)} />
              <div className="absolute right-0 top-full mt-1 w-48 bg-card-bg border border-card-border rounded-lg shadow-lg z-20 py-1">
                {addProductTypes.map((t: ProductType) => (
                  <button key={t} onClick={() => setAddOpen(false)} className="w-full text-left px-3 py-1.5 text-[12.5px] text-foreground hover:bg-background/80">
                    {addProductTypeLabels[t]}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
