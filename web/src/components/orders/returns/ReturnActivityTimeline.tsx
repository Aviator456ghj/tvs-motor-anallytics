import { CheckCircle2, Circle } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { returnTimeline } from "@/lib/returns-data";

export default function ReturnActivityTimeline() {
  return (
    <Card className="p-5">
      <h3 className="text-[14.5px] font-semibold text-foreground mb-3">Return Activity Timeline</h3>
      <div className="flex flex-col">
        {returnTimeline.map((step, i) => (
          <div key={step.label} className="flex gap-3">
            <div className="flex flex-col items-center">
              {step.done ? (
                <CheckCircle2 size={16} className="text-success shrink-0" />
              ) : (
                <Circle size={16} className="text-card-border shrink-0" />
              )}
              {i < returnTimeline.length - 1 && <span className="w-px flex-1 bg-card-border my-1" />}
            </div>
            <div className="pb-4 min-w-0">
              <div className={`text-[12.5px] font-medium ${step.done ? "text-foreground" : "text-muted-light"}`}>{step.label}</div>
              {step.time ? (
                <div className="text-[11px] text-muted-light">
                  {step.time} {step.user && `${step.user}`}
                </div>
              ) : (
                <div className="text-[11px] text-muted-light italic">Pending</div>
              )}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
