import {
  Tag,
  Package,
  Percent,
  UserPlus,
  Upload,
  Download,
  Send,
  BarChart3,
  type LucideIcon,
} from "lucide-react";
import { Card, CardHeader } from "@/components/ui/Card";
import { quickActions } from "@/lib/dashboard-data";

const iconMap: Record<string, LucideIcon> = {
  tag: Tag,
  package: Package,
  percent: Percent,
  "user-plus": UserPlus,
  upload: Upload,
  download: Download,
  send: Send,
  "bar-chart": BarChart3,
};

export default function QuickActionsCard() {
  return (
    <Card>
      <CardHeader title="Quick Actions" />
      <div className="px-5 pb-5 pt-2 grid grid-cols-4 gap-3">
        {quickActions.map((action) => {
          const Icon = iconMap[action.icon];
          return (
            <button
              key={action.id}
              className="flex flex-col items-center gap-2 rounded-lg py-3 px-1 hover:bg-background/80 transition-colors"
            >
              <span className={`w-9 h-9 rounded-full flex items-center justify-center ${action.bg} ${action.color}`}>
                <Icon size={16} />
              </span>
              <span className="text-[11px] font-medium text-muted text-center leading-tight">{action.label}</span>
            </button>
          );
        })}
      </div>
    </Card>
  );
}
