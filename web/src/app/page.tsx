import DashboardHeader from "@/components/dashboard/DashboardHeader";
import StatCardsRow from "@/components/dashboard/StatCardsRow";
import SalesOverviewCard from "@/components/dashboard/SalesOverviewCard";
import SalesByChannelCard from "@/components/dashboard/SalesByChannelCard";
import TasksCard from "@/components/dashboard/TasksCard";
import RecentOrdersCard from "@/components/dashboard/RecentOrdersCard";
import InventoryAlertsCard from "@/components/dashboard/InventoryAlertsCard";
import CustomerInsightsCard from "@/components/dashboard/CustomerInsightsCard";
import AIAssistantCard from "@/components/dashboard/AIAssistantCard";
import MarketingPerformanceCard from "@/components/dashboard/MarketingPerformanceCard";
import StoreHealthCard from "@/components/dashboard/StoreHealthCard";
import TopProductsCard from "@/components/dashboard/TopProductsCard";
import QuickActionsCard from "@/components/dashboard/QuickActionsCard";

export default function DashboardPage() {
  return (
    <div className="flex flex-col gap-6 max-w-[1600px] mx-auto">
      <DashboardHeader />
      <StatCardsRow />

      <div className="grid grid-cols-1 xl:grid-cols-[2fr_1fr_1fr] gap-4">
        <SalesOverviewCard />
        <SalesByChannelCard />
        <TasksCard />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[1.9fr_0.85fr_1fr_0.95fr] gap-4">
        <RecentOrdersCard />
        <InventoryAlertsCard />
        <CustomerInsightsCard />
        <AIAssistantCard />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <MarketingPerformanceCard />
        <StoreHealthCard />
        <TopProductsCard />
        <QuickActionsCard />
      </div>
    </div>
  );
}
