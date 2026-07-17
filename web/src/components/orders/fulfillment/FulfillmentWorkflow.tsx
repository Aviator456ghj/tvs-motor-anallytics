import { Clipboard, ShoppingCart, Package, Truck, CheckCircle2, ArrowRight, type LucideIcon } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { workflowSteps } from "@/lib/fulfillment-data";

const iconMap: Record<string, LucideIcon> = {
  clipboard: Clipboard,
  "shopping-cart": ShoppingCart,
  package: Package,
  truck: Truck,
  check: CheckCircle2,
};

export default function FulfillmentWorkflow() {
  return (
    <Card className="p-5">
      <h3 className="text-[14.5px] font-semibold text-foreground mb-4">Fulfillment Workflow</h3>
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 sm:gap-2 overflow-x-auto">
        {workflowSteps.map((step, i) => {
          const Icon = iconMap[step.icon];
          return (
            <div key={step.key} className="flex items-center gap-2 shrink-0">
              <div className="flex flex-col items-center gap-1.5 w-[128px] text-center">
                <span className="w-10 h-10 rounded-full bg-background flex items-center justify-center text-brand-start">
                  <Icon size={17} />
                </span>
                <span className="text-[12px] font-semibold text-foreground">{step.label}</span>
                <span className="text-[10.5px] text-muted-light leading-tight">{step.desc}</span>
              </div>
              {i < workflowSteps.length - 1 && <ArrowRight size={16} className="text-card-border shrink-0 hidden sm:block" />}
            </div>
          );
        })}
      </div>
    </Card>
  );
}
