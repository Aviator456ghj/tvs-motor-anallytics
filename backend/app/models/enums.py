import enum


class UserRole(str, enum.Enum):
    customer = "customer"
    business = "business"
    admin = "admin"


class KycStatus(str, enum.Enum):
    pending = "pending"
    submitted = "submitted"
    approved = "approved"
    rejected = "rejected"


class BookingStatus(str, enum.Enum):
    requested = "requested"
    accepted = "accepted"
    rejected = "rejected"
    scheduled = "scheduled"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class PaymentType(str, enum.Enum):
    advance = "advance"
    remaining = "remaining"
    full = "full"
    refund = "refund"


class PaymentMethod(str, enum.Enum):
    upi = "upi"
    card = "card"
    netbanking = "netbanking"
    wallet = "wallet"
    emi = "emi"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    success = "success"
    failed = "failed"
    refunded = "refunded"


class PortfolioType(str, enum.Enum):
    image = "image"
    video = "video"


class DocumentStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class NotificationType(str, enum.Enum):
    booking_created = "booking_created"
    booking_accepted = "booking_accepted"
    booking_rejected = "booking_rejected"
    reminder = "reminder"
    payment_received = "payment_received"
    cancellation = "cancellation"
    refund = "refund"
    review_request = "review_request"
    kyc_update = "kyc_update"
    system = "system"


class SubscriptionPlan(str, enum.Enum):
    free = "free"
    starter = "starter"
    pro = "pro"
    enterprise = "enterprise"


class DiscountType(str, enum.Enum):
    flat = "flat"
    percent = "percent"


class BusinessStaffRole(str, enum.Enum):
    staff = "staff"
    manager = "manager"
    owner = "owner"


class PayoutStatus(str, enum.Enum):
    scheduled = "scheduled"
    paid = "paid"
    failed = "failed"
