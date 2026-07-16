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
  amount_refunded: number;
  commission_amount: number;
  discount_amount: number;
  tags: string | null;
  created_via: string;
  created_at: string;
}

export interface BookingListItem extends Booking {
  customer_name: string;
  business_name: string;
  service_title: string;
  package_name: string;
}

export interface BookingEvent {
  id: string;
  booking_id: string;
  actor_id: string | null;
  event_type: "status_change" | "note" | "payment" | "refund" | "tag";
  message: string;
  created_at: string;
}

export type BusinessStaffRole = "staff" | "manager" | "owner";

export interface StaffMember {
  id: string;
  user_id: string;
  full_name: string;
  email: string;
  role: BusinessStaffRole;
  created_at: string;
}

export interface CustomerSummary {
  customer_id: string;
  full_name: string;
  email: string;
  city: string | null;
  order_count: number;
  total_spent: number;
  last_order_at: string;
}

export interface CustomerDetail extends CustomerSummary {
  bookings: BookingListItem[];
}

export type PayoutStatus = "scheduled" | "paid" | "failed";

export interface Payout {
  id: string;
  business_id: string;
  amount: number;
  status: PayoutStatus;
  reference: string;
  created_at: string;
}

export interface PayoutBalance {
  available_balance: number;
  lifetime_gross: number;
  lifetime_commission: number;
  lifetime_refunded: number;
  lifetime_paid_out: number;
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
  business_id: string | null;
  discount_type: "flat" | "percent";
  discount_value: number;
  min_order_value: number;
  usage_limit: number | null;
  usage_count: number;
  is_active: boolean;
}
