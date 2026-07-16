"""Full category taxonomy from the product spec: 16 main categories with
their subcategories. Each main category plugs into the same booking/payment/
review engine — new verticals are added here without touching core code."""

CATEGORY_TAXONOMY: dict[str, list[str]] = {
    "Photography": [
        "Wedding", "Pre Wedding", "Birthday", "Baby Shoot", "Product", "Corporate",
        "Fashion", "Lifestyle", "Food", "Real Estate", "Drone", "Wildlife", "Travel",
    ],
    "Videography": [
        "Wedding", "Reels", "Commercial", "Advertisement", "Documentary", "Events",
        "Corporate", "Music Video", "Short Film",
    ],
    "Editing": [
        "Photo Editing", "Video Editing", "VFX", "Motion Graphics", "Color Grading",
        "Thumbnail Design",
    ],
    "Film Industry": [
        "Director", "Assistant Director", "Script Writer", "Cinematographer", "Actor",
        "Actress", "Voice Artist", "Dubbing", "Music Director", "Editor",
    ],
    "Events": [
        "Wedding Planner", "Birthday Planner", "Decoration", "Catering", "DJ",
        "Lighting", "Stage", "Anchor", "Makeup",
    ],
    "Food": ["Catering", "Home Chef", "Bakery", "Restaurant Booking", "Meal Plans"],
    "Home Services": [
        "Electrician", "Plumber", "Carpenter", "AC Repair", "Cleaning", "Painting",
        "Interior Design",
    ],
    "Education": ["Tutors", "Music Teachers", "Coding Trainers", "Spoken English", "Dance", "Yoga"],
    "Health": ["Doctor", "Physiotherapist", "Nutritionist", "Fitness Trainer"],
    "Digital Services": [
        "Graphic Design", "Web Development", "App Development", "SEO",
        "Digital Marketing", "AI Automation",
    ],
    "Legal": ["Lawyers", "CA", "Tax Consultant", "GST"],
    "Travel": ["Driver", "Guide", "Rental Cars", "Hotels"],
    "Real Estate": ["Agents", "Property Photography", "Interior Designer"],
    "Beauty": ["Salon", "Makeup Artist", "Mehendi", "Spa"],
    "Automobile": ["Mechanic", "Bike Service", "Car Wash"],
    "Freelancers": ["Content Writer", "Translator", "Voice Artist", "Virtual Assistant"],
}

CATEGORY_ICONS: dict[str, str] = {
    "Photography": "camera",
    "Videography": "video",
    "Editing": "film",
    "Film Industry": "clapperboard",
    "Events": "party-popper",
    "Food": "utensils",
    "Home Services": "wrench",
    "Education": "graduation-cap",
    "Health": "heart-pulse",
    "Digital Services": "code",
    "Legal": "scale",
    "Travel": "plane",
    "Real Estate": "home",
    "Beauty": "sparkles",
    "Automobile": "car",
    "Freelancers": "briefcase",
}
