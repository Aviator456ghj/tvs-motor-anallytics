"use client";

import { Sparkles, ArrowUp } from "lucide-react";
import { aiCapabilities } from "@/lib/dashboard-data";

export default function AIAssistantCard() {
  return (
    <div className="rounded-xl p-5 flex flex-col gap-4 text-white bg-gradient-to-br from-brand-start to-brand-end relative overflow-hidden">
      <div className="flex items-center gap-2">
        <Sparkles size={17} className="shrink-0" />
        <h3 className="text-[14px] font-semibold whitespace-nowrap">AI Business Assistant</h3>
      </div>

      <div className="relative">
        <input
          type="text"
          placeholder="Ask anything about your business..."
          className="w-full rounded-lg bg-white/15 placeholder:text-white/70 text-white text-[12px] pl-3 pr-9 py-2.5 border border-white/20 focus:outline-none focus:bg-white/20"
        />
        <button className="absolute right-1.5 top-1/2 -translate-y-1/2 w-6 h-6 rounded-md bg-white/20 flex items-center justify-center hover:bg-white/30">
          <ArrowUp size={13} />
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        {aiCapabilities.map((s) => (
          <button
            key={s}
            className="text-[11.5px] px-3 py-1.5 rounded-full bg-white/15 hover:bg-white/25 transition-colors leading-tight"
          >
            {s}
          </button>
        ))}
      </div>

      <button className="mt-auto flex items-center justify-center gap-2 rounded-lg bg-white text-brand-start text-[13px] font-semibold py-2.5 hover:opacity-90 transition-opacity">
        <Sparkles size={14} />
        Ask AI Assistant
      </button>
    </div>
  );
}
