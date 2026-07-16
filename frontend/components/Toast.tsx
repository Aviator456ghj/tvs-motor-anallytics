"use client";

import { createContext, useCallback, useContext, useRef, useState, ReactNode } from "react";

interface ToastItem {
  id: number;
  message: string;
  tone: "default" | "success" | "error";
}

interface ToastContextValue {
  toast: (message: string, tone?: ToastItem["tone"]) => void;
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const counter = useRef(0);

  const toast = useCallback((message: string, tone: ToastItem["tone"] = "default") => {
    const id = ++counter.current;
    setItems((prev) => [...prev, { id, message, tone }]);
    setTimeout(() => setItems((prev) => prev.filter((i) => i.id !== id)), 3200);
  }, []);

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 bottom-5 z-[100] flex flex-col items-center gap-2">
        {items.map((item) => (
          <div
            key={item.id}
            className={`pointer-events-auto rounded-lg px-4 py-2.5 text-sm font-medium shadow-lg transition ${
              item.tone === "error"
                ? "bg-red-600 text-white"
                : item.tone === "success"
                  ? "bg-emerald-600 text-white"
                  : "bg-slate-900 text-white"
            }`}
          >
            {item.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx.toast;
}
