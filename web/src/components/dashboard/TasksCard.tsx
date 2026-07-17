import { Card, CardHeader, ViewAllLink } from "@/components/ui/Card";
import { tasks } from "@/lib/dashboard-data";

export default function TasksCard() {
  return (
    <Card>
      <CardHeader title="Tasks & To-Dos" action={<ViewAllLink />} />
      <div className="px-5 pb-4 pt-2 flex flex-col gap-3.5">
        {tasks.map((task) => (
          <div key={task.id} className="flex items-center gap-3">
            <span className={`w-2 h-2 rounded-full shrink-0 ${task.dot}`} />
            <span className="flex-1 text-[13px] text-foreground truncate">{task.label}</span>
            <span className={`text-[11.5px] font-medium shrink-0 ${task.color}`}>{task.priority}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}
