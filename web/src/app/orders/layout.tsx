import { type ReactNode } from "react";
import OrdersWorkspaceNav from "@/components/orders/OrdersWorkspaceNav";

export default function OrdersLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-col gap-5 max-w-[1600px] mx-auto">
      <OrdersWorkspaceNav />
      {children}
    </div>
  );
}
