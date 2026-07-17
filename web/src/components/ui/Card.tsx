import { type ReactNode } from "react";
import clsx from "clsx";

export function Card({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={clsx(
        "bg-card-bg border border-card-border rounded-xl",
        className
      )}
    >
      {children}
    </div>
  );
}

export function CardHeader({
  title,
  action,
}: {
  title: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex items-center justify-between px-5 pt-4 pb-1">
      <h3 className="text-[14.5px] font-semibold text-foreground">{title}</h3>
      {action}
    </div>
  );
}

export function ViewAllLink() {
  return (
    <a href="#" className="text-[12.5px] font-medium text-brand-start hover:underline">
      View all
    </a>
  );
}
