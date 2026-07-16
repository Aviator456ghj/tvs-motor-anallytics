// Minimal stroke-based icon set (18x18, 1.6 stroke) — hand-rolled to avoid
// an icon-library dependency, styled to sit quietly next to sidebar labels.
import { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement>;

const base = {
  width: 18,
  height: 18,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.7,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

export const HomeIcon = (p: IconProps) => (
  <svg {...base} {...p}>
    <path d="M3 11.5 12 4l9 7.5" />
    <path d="M5.5 10v9a1 1 0 0 0 1 1H9a1 1 0 0 0 1-1v-4a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v4a1 1 0 0 0 1 1h2.5a1 1 0 0 0 1-1v-9" />
  </svg>
);

export const OrdersIcon = (p: IconProps) => (
  <svg {...base} {...p}>
    <rect x="4" y="6" width="16" height="14" rx="2" />
    <path d="M8 6V5a4 4 0 0 1 8 0v1" />
    <path d="M8 11h8M8 15h5" />
  </svg>
);

export const ProductsIcon = (p: IconProps) => (
  <svg {...base} {...p}>
    <path d="M3.5 7.5 12 3l8.5 4.5L12 12 3.5 7.5Z" />
    <path d="M3.5 7.5V16L12 20.5 20.5 16V7.5" />
    <path d="M12 12v8.5" />
  </svg>
);

export const CustomersIcon = (p: IconProps) => (
  <svg {...base} {...p}>
    <circle cx="9" cy="8" r="3.2" />
    <path d="M3.5 19c0-3.3 2.5-5.5 5.5-5.5s5.5 2.2 5.5 5.5" />
    <circle cx="17" cy="8.5" r="2.4" />
    <path d="M15.8 13.3c2.6.2 4.7 2.3 4.7 5.2" />
  </svg>
);

export const DiscountIcon = (p: IconProps) => (
  <svg {...base} {...p}>
    <path d="M4 12.5 12.5 4a2 2 0 0 1 2.8 0l4.7 4.7a2 2 0 0 1 0 2.8L11.5 20 4 12.5Z" />
    <circle cx="9.5" cy="9.5" r="1.4" fill="currentColor" stroke="none" />
    <path d="M9 15.5 15.5 9" />
  </svg>
);

export const FinanceIcon = (p: IconProps) => (
  <svg {...base} {...p}>
    <rect x="3" y="6" width="18" height="13" rx="2" />
    <path d="M3 10h18" />
    <path d="M7 14.5h4" />
  </svg>
);

export const AnalyticsIcon = (p: IconProps) => (
  <svg {...base} {...p}>
    <path d="M4 20V10M11 20V4M18 20v-7" />
    <path d="M3 20h18" />
  </svg>
);

export const StoreIcon = (p: IconProps) => (
  <svg {...base} {...p}>
    <path d="M4 9.5 5 4h14l1 5.5" />
    <path d="M3.5 9.5a2.3 2.3 0 0 0 4.4 1.1 2.3 2.3 0 0 0 4.2 0 2.3 2.3 0 0 0 4.2 0 2.3 2.3 0 0 0 4.4-1.1" />
    <path d="M5 11v8.5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V11" />
    <path d="M10 20.5V15a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v5.5" />
  </svg>
);

export const SettingsIcon = (p: IconProps) => (
  <svg {...base} {...p}>
    <circle cx="12" cy="12" r="3" />
    <path d="M19.4 13.5a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 1 1-2.9 2.9l-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1a2 2 0 1 1-2.9-2.9l.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.6-1h-.2a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.6-1.1 1.7 1.7 0 0 0-.3-1.9l-.1-.1a2 2 0 1 1 2.9-2.9l.1.1a1.7 1.7 0 0 0 1.9.3H10a1.7 1.7 0 0 0 1-1.6v-.2a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1a2 2 0 1 1 2.9 2.9l-.1.1a1.7 1.7 0 0 0-.3 1.9V10a1.7 1.7 0 0 0 1.6 1h.2a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.6 1Z" />
  </svg>
);

export const BellIcon = (p: IconProps) => (
  <svg {...base} {...p}>
    <path d="M6 10a6 6 0 1 1 12 0c0 4 1.5 5.5 1.5 5.5H4.5S6 14 6 10Z" />
    <path d="M10 19a2 2 0 0 0 4 0" />
  </svg>
);

export const SearchIcon = (p: IconProps) => (
  <svg {...base} {...p}>
    <circle cx="11" cy="11" r="6.5" />
    <path d="m20 20-3.5-3.5" />
  </svg>
);

export const PlusIcon = (p: IconProps) => (
  <svg {...base} {...p}>
    <path d="M12 5v14M5 12h14" />
  </svg>
);

export const ChevronDownIcon = (p: IconProps) => (
  <svg {...base} {...p}>
    <path d="m6 9 6 6 6-6" />
  </svg>
);

export const ReportsIcon = (p: IconProps) => (
  <svg {...base} {...p}>
    <rect x="4" y="3.5" width="16" height="17" rx="2" />
    <path d="M8 8h8M8 12h8M8 16h5" />
  </svg>
);

export const StaffIcon = (p: IconProps) => (
  <svg {...base} {...p}>
    <circle cx="12" cy="8" r="3.3" />
    <path d="M5 20c0-3.9 3.1-7 7-7s7 3.1 7 7" />
  </svg>
);
