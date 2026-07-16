"""Idempotent dev seed: full category taxonomy + a handful of demo accounts
and listings in the launch verticals (Photography, Videography, Editing,
Events) across a few cities, so the frontend has real data to render.

Run with: python -m app.seed.seed
"""
import datetime as dt

from slugify import slugify
from sqlalchemy.orm import Session

from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models.booking import Booking, BookingEvent
from app.models.business import BusinessProfile, BusinessStaff
from app.models.catalog import AvailabilitySlot, BusinessCategory, Category, Package, PortfolioItem, Service
from app.models.enums import BookingStatus, BusinessStaffRole, DiscountType, PaymentMethod, PaymentStatus, PaymentType, PayoutStatus, PortfolioType, UserRole
from app.models.engagement import Coupon
from app.models.payment import Payment, PayoutRecord
from app.models.user import User
from app.seed.categories_data import CATEGORY_ICONS, CATEGORY_TAXONOMY

DEMO_PASSWORD = "Password@123"


def seed_categories(db: Session) -> dict[str, Category]:
    slug_to_category: dict[str, Category] = {}
    for order, (main_name, subs) in enumerate(CATEGORY_TAXONOMY.items()):
        main_slug = slugify(main_name)
        main = db.query(Category).filter(Category.slug == main_slug).first()
        if not main:
            main = Category(name=main_name, slug=main_slug, icon=CATEGORY_ICONS.get(main_name), sort_order=order)
            db.add(main)
            db.flush()
        slug_to_category[main_slug] = main

        for sub_order, sub_name in enumerate(subs):
            sub_slug = f"{main_slug}-{slugify(sub_name)}"
            sub = db.query(Category).filter(Category.slug == sub_slug).first()
            if not sub:
                sub = Category(name=sub_name, slug=sub_slug, parent_id=main.id, sort_order=sub_order)
                db.add(sub)
                db.flush()
            slug_to_category[sub_slug] = sub
    db.commit()
    print(f"Seeded {len(slug_to_category)} categories across {len(CATEGORY_TAXONOMY)} main verticals.")
    return slug_to_category


def get_or_create_user(db: Session, email: str, full_name: str, role: UserRole, city: str | None = None) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user:
        return user
    user = User(email=email, full_name=full_name, role=role, city=city, password_hash=hash_password(DEMO_PASSWORD), is_verified=True)
    db.add(user)
    db.flush()
    return user


def get_or_create_business(db: Session, owner: User, company_name: str, city: str, category_slugs: list[str], categories: dict[str, Category], **extra) -> BusinessProfile:
    business = db.query(BusinessProfile).filter(BusinessProfile.owner_id == owner.id).first()
    if business:
        return business
    slug = slugify(company_name)
    business = BusinessProfile(
        owner_id=owner.id,
        company_name=company_name,
        slug=slug,
        city=city,
        state=extra.pop("state", "Telangana"),
        is_verified=True,
        is_approved=True,
        rating_avg=extra.pop("rating_avg", 4.7),
        rating_count=extra.pop("rating_count", 32),
        **extra,
    )
    db.add(business)
    db.flush()
    for slug_key in category_slugs:
        db.add(BusinessCategory(business_id=business.id, category_id=categories[slug_key].id))
    return business


def seed_demo_marketplace(db: Session, categories: dict[str, Category]):
    admin = get_or_create_user(db, "admin@servicesos.io", "Platform Admin", UserRole.admin)
    customer = get_or_create_user(db, "customer@servicesos.io", "Ananya Rao", UserRole.customer, city="Hyderabad")

    demo_businesses = [
        {
            "email": "abc.photography@servicesos.io",
            "company_name": "ABC Photography",
            "city": "Hyderabad",
            "tagline": "Timeless wedding & portrait photography",
            "description": "8 years of capturing weddings, pre-wedding shoots and portraits across South India.",
            "experience_years": 8,
            "offers_instant_booking": True,
            "category_slugs": ["photography-wedding", "photography-pre-wedding", "photography-birthday", "photography-drone"],
            "packages": [
                ("Wedding Photography", "photography-wedding", [("Full Day Wedding", 35000, "8 hours, 2 photographers, 500+ edited photos")]),
                ("Pre-Wedding Shoot", "photography-pre-wedding", [("Classic Pre-Wedding", 18000, "3 hours, 1 location, 100 edited photos")]),
                ("Birthday Shoot", "photography-birthday", [("Birthday Package", 12000, "2 hours, candid + posed shots")]),
                ("Drone Coverage", "photography-drone", [("Aerial Add-on", 5000, "1 hour aerial coverage, 4K footage")]),
            ],
        },
        {
            "email": "framecraft.films@servicesos.io",
            "company_name": "FrameCraft Films",
            "city": "Bengaluru",
            "state": "Karnataka",
            "tagline": "Cinematic wedding & brand films",
            "description": "Full-service videography studio specialising in wedding films and corporate ads.",
            "experience_years": 6,
            "offers_instant_booking": False,
            "category_slugs": ["videography-wedding", "videography-reels", "videography-corporate"],
            "packages": [
                ("Wedding Film", "videography-wedding", [("Cinematic Wedding Film", 55000, "Full day, drone, same-day teaser reel")]),
                ("Reels Package", "videography-reels", [("5-Reel Bundle", 15000, "5 short-form vertical edits")]),
                ("Corporate Video", "videography-corporate", [("Brand Film", 40000, "2-day shoot, 3 min final film")]),
            ],
        },
        {
            "email": "pixelpost.studio@servicesos.io",
            "company_name": "PixelPost Studio",
            "city": "Mumbai",
            "state": "Maharashtra",
            "tagline": "Photo & video post-production specialists",
            "description": "Color grading, VFX and motion graphics for photographers and filmmakers.",
            "experience_years": 5,
            "offers_instant_booking": True,
            "category_slugs": ["editing-photo-editing", "editing-video-editing", "editing-color-grading"],
            "packages": [
                ("Photo Retouching", "editing-photo-editing", [("100-Photo Batch", 4000, "Color correction + retouch, 48hr turnaround")]),
                ("Video Editing", "editing-video-editing", [("Wedding Film Edit", 10000, "Up to 60 min raw footage edited to a 15 min film")]),
                ("Color Grading", "editing-color-grading", [("Cinematic Grade", 6000, "Per 10 minutes of footage")]),
            ],
        },
        {
            "email": "celebrate.events@servicesos.io",
            "company_name": "Celebrate Events Co.",
            "city": "Hyderabad",
            "tagline": "End-to-end wedding & birthday planning",
            "description": "Décor, catering coordination, DJ and full event management under one roof.",
            "experience_years": 10,
            "offers_instant_booking": False,
            "category_slugs": ["events-wedding-planner", "events-decoration", "events-dj"],
            "packages": [
                ("Wedding Planning", "events-wedding-planner", [("Full Wedding Management", 150000, "End-to-end planning for a 300-guest wedding")]),
                ("Decoration", "events-decoration", [("Stage & Venue Decor", 45000, "Floral + lighting decor package")]),
                ("DJ & Sound", "events-dj", [("DJ Night Package", 20000, "5 hours, sound + lighting")]),
            ],
        },
    ]

    for spec in demo_businesses:
        owner = get_or_create_user(db, spec["email"], spec["company_name"] + " Owner", UserRole.business, city=spec["city"])
        business = get_or_create_business(
            db,
            owner,
            spec["company_name"],
            spec["city"],
            spec["category_slugs"],
            categories,
            tagline=spec["tagline"],
            description=spec["description"],
            experience_years=spec["experience_years"],
            offers_instant_booking=spec["offers_instant_booking"],
            state=spec.get("state", "Telangana"),
        )
        if db.query(Service).filter(Service.business_id == business.id).first():
            continue  # already fully seeded

        for title, cat_slug, packages in spec["packages"]:
            service = Service(business_id=business.id, category_id=categories[cat_slug].id, title=title, is_instant_booking=spec["offers_instant_booking"])
            db.add(service)
            db.flush()
            for pkg_name, price, description in packages:
                db.add(Package(service_id=service.id, name=pkg_name, price=price, description=description))

        db.add(
            PortfolioItem(
                business_id=business.id,
                item_type=PortfolioType.image,
                url=f"https://picsum.photos/seed/{business.slug}-1/800/600",
                caption=f"{spec['company_name']} - featured work",
            )
        )
        today = dt.date.today()
        for i in range(1, 8):
            db.add(
                AvailabilitySlot(
                    business_id=business.id,
                    date=today + dt.timedelta(days=i),
                    start_time=dt.time(10, 0),
                    end_time=dt.time(18, 0),
                    capacity=1,
                )
            )

    if not db.query(Coupon).filter(Coupon.code == "WELCOME10").first():
        db.add(
            Coupon(
                code="WELCOME10",
                discount_type=DiscountType.percent,
                discount_value=10,
                min_order_value=5000,
                max_discount=3000,
                usage_limit=500,
            )
        )

    db.commit()
    print(f"Seeded demo accounts. Admin: admin@servicesos.io / {DEMO_PASSWORD}")
    print(f"Seeded demo customer: customer@servicesos.io / {DEMO_PASSWORD}")
    print(f"Seeded {len(demo_businesses)} demo businesses (password for all: {DEMO_PASSWORD}).")


def seed_demo_activity(db: Session):
    """Gives ABC Photography a staff teammate and one full order lifecycle
    (booking -> payment -> partial refund -> payout) so Orders, Customers,
    Staff, and Payouts all have real data on first login."""
    business = db.query(BusinessProfile).filter(BusinessProfile.slug == "abc-photography").first()
    customer = db.query(User).filter(User.email == "customer@servicesos.io").first()
    if not business or not customer:
        return

    manager = get_or_create_user(db, "staff.manager@servicesos.io", "Priya Menon", UserRole.business, city="Hyderabad")
    if not db.query(BusinessStaff).filter(BusinessStaff.business_id == business.id, BusinessStaff.user_id == manager.id).first():
        db.add(BusinessStaff(business_id=business.id, user_id=manager.id, role=BusinessStaffRole.manager))

    if db.query(Booking).filter(Booking.business_id == business.id, Booking.customer_id == customer.id).first():
        db.commit()
        return  # activity already seeded

    service = db.query(Service).filter(Service.business_id == business.id, Service.title == "Wedding Photography").first()
    package = db.query(Package).filter(Package.service_id == service.id).first()

    booking = Booking(
        customer_id=customer.id,
        business_id=business.id,
        service_id=service.id,
        package_id=package.id,
        status=BookingStatus.completed,
        scheduled_date=dt.date.today() - dt.timedelta(days=5),
        amount_total=float(package.price),
        amount_advance=round(float(package.price) * 0.3, 2),
        amount_paid=float(package.price),
        amount_refunded=2000,
        commission_rate=float(business.commission_rate),
        commission_amount=round(float(package.price) * float(business.commission_rate), 2),
        tags="vip,referral",
        completed_at=dt.datetime.utcnow() - dt.timedelta(days=3),
    )
    db.add(booking)
    db.flush()

    db.add(Payment(booking_id=booking.id, amount=booking.amount_paid, payment_type=PaymentType.full, method=PaymentMethod.upi, status=PaymentStatus.success, gateway_ref="mock_txn_seed001"))
    db.add(Payment(booking_id=booking.id, amount=2000, payment_type=PaymentType.refund, method=PaymentMethod.wallet, status=PaymentStatus.refunded, gateway_ref="mock_refund_seed001"))
    customer.wallet_balance = float(customer.wallet_balance) + 2000

    for event_type, message in [
        ("status_change", "Booking requested by Ananya Rao."),
        ("status_change", "Status changed from requested to accepted by ABC Photography Owner."),
        ("status_change", "Status changed from accepted to scheduled by ABC Photography Owner."),
        ("status_change", "Status changed from scheduled to in_progress by ABC Photography Owner."),
        ("status_change", "Status changed from in_progress to completed by ABC Photography Owner."),
        ("tag", "Tags updated: vip,referral"),
        ("note", "Customer requested extra album copies — noted for delivery."),
        ("refund", "Refunded ₹2,000.00 — one edited album was delivered late."),
    ]:
        db.add(BookingEvent(booking_id=booking.id, actor_id=business.owner_id, event_type=event_type, message=message))

    net_available = float(booking.amount_paid) - float(booking.amount_refunded) - float(booking.commission_amount)
    payout_amount = round(net_available * 0.6, 2)
    db.add(PayoutRecord(business_id=business.id, amount=payout_amount, status=PayoutStatus.paid, reference="payout_seed001"))

    db.commit()
    print("Seeded one full order lifecycle (booking, payment, refund, payout) and a manager teammate for ABC Photography.")


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        categories = seed_categories(db)
        seed_demo_marketplace(db, categories)
        seed_demo_activity(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
