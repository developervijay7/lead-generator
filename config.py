"""Configuration settings for Attrix Lead Generator."""

import os

def _env_bool(name, default):
    """Convert environment variable to boolean."""
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

def _env_int(name, default):
    """Convert environment variable to integer with fallback."""
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default

# ═══════════════════════════════════════════════
# BROWSER SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════

HEADLESS = _env_bool("HEADLESS", False)  # Set True for production/server
BROWSER_TIMEOUT = 30  # Seconds to wait for elements - increased for slow networks
DEBUG_SCREENSHOTS = _env_bool("DEBUG_SCREENSHOTS", True)  # Save screenshots for debugging

# ═══════════════════════════════════════════════
# SCRAPING SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════

MAX_RESULTS_PER_SEARCH = 1000  # Max leads to collect per search query
SCROLL_PAUSE_TIME = 3  # Seconds to pause between scrolls - helps avoid Google detection
SCROLL_MAX_STALL_RETRIES = 20  # How many "no new results" scrolls before giving up

# ═══════════════════════════════════════════════════════════════════════════════
# WEBSITE ANALYSIS SETTINGS
# ═══════════════════════════════════════════════

WEBSITE_CHECK_TIMEOUT = 10  # Seconds to wait when checking a website
MAX_CONCURRENT_CHECKS = 5  # Parallel website checks for speed

# ═══════════════════════════════════════════════
# LEAD SCORING WEIGHTS (0-100 scale)
# ═══════════════════════════════════════════════════════════════════════════════

SCORE_NO_WEBSITE = 95        # Business has no website at all - HIGH PRIORITY
SCORE_BAD_WEBSITE = 80       # Website exists but is very poor/broken
SCORE_OUTDATED_WEBSITE = 65  # Website looks outdated (old design)
SCORE_DECENT_WEBSITE = 30    # Website is okay but could improve
SCORE_GOOD_WEBSITE = 10      # Website is modern and good - LOW PRIORITY

# ═══════════════════════════════════════════════════════════════════════════════
# SEARCH TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_SEARCH_QUERIES = [
    "{business_type} in {location}, {country}",
]

# ═══════════════════════════════════════════════
# COUNTRY LIST - ALL 195 UN RECOGNIZED COUNTRIES + TERRITORIES
# ═══════════════════════════════════════════════════════════════════════════════

COUNTRIES = [
    "Afghanistan",
    "Albania",
    "Algeria",
    "Andorra",
    "Angola",
    "Antigua and Barbuda",
    "Argentina",
    "Armenia",
    "Australia",
    "Austria",
    "Azerbaijan",
    "Bahamas",
    "Bahrain",
    "Bangladesh",
    "Barbados",
    "Belarus",
    "Belgium",
    "Belize",
    "Benin",
    "Bhutan",
    "Bolivia",
    "Bosnia and Herzegovina",
    "Botswana",
    "Brazil",
    "Brunei",
    "Bulgaria",
    "Burkina Faso",
    "Burundi",
    "Cabo Verde",
    "Cambodia",
    "Cameroon",
    "Canada",
    "Central African Republic",
    "Chad",
    "Chile",
    "China",
    "Colombia",
    "Comoros",
    "Costa Rica",
    "Croatia",
    "Cuba",
    "Cyprus",
    "Czechia",
    "Democratic Republic of the Congo",
    "Denmark",
    "Djibouti",
    "Dominica",
    "Dominican Republic",
    "Ecuador",
    "Egypt",
    "El Salvador",
    "Equatorial Guinea",
    "Eritrea",
    "Estonia",
    "Eswatini",
    "Ethiopia",
    "Fiji",
    "Finland",
    "France",
    "Gabon",
    "Gambia",
    "Georgia",
    "Germany",
    "Ghana",
    "Greece",
    "Grenada",
    "Guatemala",
    "Guinea",
    "Guinea-Bissau",
    "Guyana",
    "Haiti",
    "Honduras",
    "Hungary",
    "Iceland",
    "India",
    "Indonesia",
    "Iran",
    "Iraq",
    "Ireland",
    "Israel",
    "Italy",
    "Ivory Coast",
    "Jamaica",
    "Japan",
    "Jordan",
    "Kazakhstan",
    "Kenya",
    "Kiribati",
    "Kuwait",
    "Kyrgyzstan",
    "Laos",
    "Latvia",
    "Lebanon",
    "Lesotho",
    "Liberia",
    "Libya",
    "Liechtenstein",
    "Lithuania",
    "Luxembourg",
    "Madagascar",
    "Malawi",
    "Malaysia",
    "Maldives",
    "Mali",
    "Malta",
    "Marshall Islands",
    "Mauritania",
    "Mauritius",
    "Mexico",
    "Micronesia",
    "Moldova",
    "Monaco",
    "Mongolia",
    "Montenegro",
    "Morocco",
    "Mozambique",
    "Myanmar",
    "Namibia",
    "Nauru",
    "Nepal",
    "Netherlands",
    "New Zealand",
    "Nicaragua",
    "Niger",
    "Nigeria",
    "North Korea",
    "North Macedonia",
    "Norway",
    "Oman",
    "Pakistan",
    "Palau",
    "Palestine",
    "Panama",
    "Papua New Guinea",
    "Paraguay",
    "Peru",
    "Philippines",
    "Poland",
    "Portugal",
    "Qatar",
    "Republic of the Congo",
    "Romania",
    "Russia",
    "Rwanda",
    "Saint Kitts and Nevis",
    "Saint Lucia",
    "Saint Vincent and the Grenadines",
    "Samoa",
    "San Marino",
    "Sao Tome and Principe",
    "Saudi Arabia",
    "Senegal",
    "Serbia",
    "Seychelles",
    "Sierra Leone",
    "Singapore",
    "Slovakia",
    "Slovenia",
    "Solomon Islands",
    "Somalia",
    "South Africa",
    "South Korea",
    "South Sudan",
    "Spain",
    "Sri Lanka",
    "Sudan",
    "Suriname",
    "Sweden",
    "Switzerland",
    "Syria",
    "Taiwan",
    "Tajikistan",
    "Tanzania",
    "Thailand",
    "Timor-Leste",
    "Togo",
    "Tonga",
    "Trinidad and Tobago",
    "Tunisia",
    "Turkey",
    "Turkmenistan",
    "Tuvalu",
    "Uganda",
    "Ukraine",
    "United Arab Emirates",
    "United Kingdom",
    "United States",
    "Uruguay",
    "Uzbekistan",
    "Vanuatu",
    "Vatican City",
    "Venezuela",
    "Vietnam",
    "Yemen",
    "Zambia",
    "Zimbabwe",
]

# Alias for backward compatibility
COUNTRY_OPTIONS = COUNTRIES

# ═══════════════════════════════════════════════════════════════════════════════
# BUSINESS TYPES - MOST LIKELY TO NEED WEB DEVELOPMENT
# ═══════════════════════════════════════════════════════════════════════════════

BUSINESS_TYPES = [
    "restaurants",
    "cafes",
    "plumbers",
    "electricians",
    "dentists",
    "doctors",
    "lawyers",
    "real estate agents",
    "auto repair shops",
    "car dealerships",
    "beauty salons",
    "barber shops",
    "gyms",
    "fitness centers",
    "yoga studios",
    "contractors",
    "construction companies",
    "accountants",
    "tax consultants",
    "veterinarians",
    "pet grooming",
    "photographers",
    "wedding planners",
    "event venues",
    "florists",
    "bakeries",
    "catering services",
    "landscaping companies",
    "pest control",
    "cleaning services",
    "hotels",
    "guest houses",
    "travel agencies",
    "tour operators",
    "schools",
    "tutoring centers",
    "driving schools",
    "clinics",
    "pharmacies",
    "opticians",
    "jewelry stores",
    "clothing stores",
    "furniture stores",
]

# ═══════════════════════════════════════════════
# FLASK APP SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════

FLASK_HOST = os.environ.get("FLASK_HOST", "127.0.0.1")
FLASK_PORT = _env_int("FLASK_PORT", 5000)
FLASK_DEBUG = _env_bool("FLASK_DEBUG", True)

# ═══════════════════════════════════════════════
# LOGGING & DEBUGGING
# ═══════════════════════════════════════════════════════════════════════════════

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# VIP: Auto-create screenshots folder if debugging enabled
if DEBUG_SCREENSHOTS:
    SCREENSHOT_DIR = os.path.join(LOG_DIR, "screenshots")
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
