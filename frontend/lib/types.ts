export type UserRole = "customer" | "business" | "admin";

export interface User {
  id: string;
  email: string;
  phone: string | null;
  full_name: string;
  role: UserRole;
  avatar_url: string | null;
  city: string | null;
  is_verified: boolean;
  wallet_balance: number;
}

export interface Category {
  id: string;
  parent_id: string | null;
  name: string;
  slug: string;
  icon: string | null;
  description: string | null;
  sort_order: number;
  is_active: boolean;
}

export interface CategoryTree extends Category {
  children: CategoryTree[];
}

export interface Package {
  id: string;
  service_id: string;
  name: string;
  price: number;
  duration_minutes: number | null;
  description: string | null;
  deliverables: string | null;
  is_active: boolean;
}

export interface Service {
  id: string;
  business_id: string;
  category_id: string;
  title: string;
  description: string | null;
  is_home_service: boolean;
  is_instant_booking: boolean;
  is_active: boolean;
  packages: Package[];
}

export interface PortfolioItem {
  id: string;
  business_id: string;
  item_type: "image" | "video";
  url: string;
  thumbnail_url: string | null;
  caption: string | null;
}

export interface Business {
  id: string;
  owner_id: string;
  company_name: string;
  slug: string;
  tagline: string | null;
  description: string | null;
  logo_url: string | null;
  cover_image_url: string | null;
  city: string | null;
  state: string | null;
  experience_years: number;
  offers_home_service: boolean;
  offers_instant_booking: boolean;
  is_verified: boolean;
  kyc_status: string;
  is_approved: boolean;
  rating_avg: number;
  rating_count: number;
  subscription_plan: string;
}

export interface BusinessDetail extends Business {
  services: Service[];
  portfolio_items: PortfolioItem[];
}

export type BookingStatus = "requested" | "accepted" | "rejected" | "scheduled" | "in_progress" | "completed" | "cancelled";

export interface Booking {
  id: string;
  customer_id: string;
  business_id: string;
  service_id: string;
  package_id: string;
  status: BookingStatus;
  scheduled_date: string | null;
  scheduled_time: string | null;
  service_address: string | null;
  notes: string | null;
  amount_total: number;
  amount_advance: number;
  amount_paid: number;
  commission_amount: number;
  discount_amount: number;
  created_at: string;
}

export interface Review {
  id: string;
  booking_id: string;
  customer_id: string;
  business_id: string;
  rating: number;
  comment: string | null;
  provider_response: string | null;
  is_flagged: boolean;
  created_at: string;
}

export interface Notification {
  id: string;
  type: string;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
}

export interface Coupon {
  id: string;
  code: string;
  discount_type: "flat" | "percent";
  discount_value: number;
  usage_limit: number | null;
  usage_count: number;
  is_active: boolean;
}
