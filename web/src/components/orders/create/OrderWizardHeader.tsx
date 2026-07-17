"use client";

import { ChevronRight, ChevronDown, Check } from "lucide-react";
import { wizardSteps } from "@/lib/create-order-data";

export default function OrderWizardHeader({
  currentStep,
  maxReachedStep,
  onStepClick,
  onCancel,
  onSaveDraft,
  onNextStep,
  isLastStep,
}: {
  currentStep: number;
  maxReachedStep: number;
  onStepClick: (step: number) => void;
  onCancel: () => void;
  onSaveDraft: () => void;
  onNextStep: () => void;
  isLastStep: boolean;
}) {
  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-1.5 text-[12.5px] text-muted-light mb-1">
            <span>Dashboard</span>
            <ChevronRight size={13} />
            <span>Orders</span>
            <ChevronRight size={13} />
            <span className="text-foreground font-medium">Create Order</span>
          </div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">Create Order</h1>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onCancel}
            className="text-[13px] font-medium text-foreground border border-card-border rounded-lg px-3.5 py-2 bg-card-bg hover:bg-background/80"
          >
            Cancel
          </button>
          <button
            onClick={onSaveDraft}
            className="text-[13px] font-medium text-foreground border border-card-border rounded-lg px-3.5 py-2 bg-card-bg hover:bg-background/80"
          >
            Save Draft
          </button>
          <button
            onClick={onNextStep}
            className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-brand-start to-brand-end text-white text-[13px] font-medium pl-4 pr-3 py-2 shadow-sm hover:opacity-90 transition-opacity"
          >
            {isLastStep ? "Create Order" : "Next Step"}
            {!isLastStep && <ChevronDown size={13} className="ml-0.5 -rotate-90" />}
          </button>
        </div>
      </div>

      <div className="bg-card-bg border border-card-border rounded-xl px-5 py-4 flex items-center">
        {wizardSteps.map((s, i) => {
          const state = s.step < currentStep ? "done" : s.step === currentStep ? "active" : "upcoming";
          const clickable = s.step <= maxReachedStep;
          return (
            <div key={s.step} className="flex items-center flex-1 last:flex-none">
              <button
                onClick={() => clickable && onStepClick(s.step)}
                disabled={!clickable}
                className={`flex items-center gap-2.5 text-left ${clickable ? "cursor-pointer" : "cursor-not-allowed"}`}
              >
                <span
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-[13px] font-semibold shrink-0 ${
                    state === "done"
                      ? "bg-brand-start text-white"
                      : state === "active"
                        ? "bg-brand-start text-white"
                        : "bg-background text-muted-light"
                  }`}
                >
                  {state === "done" ? <Check size={15} /> : s.step}
                </span>
                <span className="hidden md:block">
                  <div className={`text-[13px] font-semibold ${state === "upcoming" ? "text-muted-light" : "text-foreground"}`}>{s.label}</div>
                  <div className="text-[11px] text-muted-light">{s.sub}</div>
                </span>
              </button>
              {i < wizardSteps.length - 1 && <div className={`h-px flex-1 mx-3 ${s.step < currentStep ? "bg-brand-start" : "bg-card-border"}`} />}
            </div>
          );
        })}
      </div>
    </div>
  );
}
