"""India-only jurisdiction constants for Legal Case Demystifier.

The application is exclusively for the Indian legal context: the country is
always "India" and the state/UT is chosen from the official lists below.
"""

JURISDICTION_COUNTRY = "India"

INDIAN_STATES = [
    "Andhra Pradesh",
    "Arunachal Pradesh",
    "Assam",
    "Bihar",
    "Chhattisgarh",
    "Goa",
    "Gujarat",
    "Haryana",
    "Himachal Pradesh",
    "Jharkhand",
    "Karnataka",
    "Kerala",
    "Madhya Pradesh",
    "Maharashtra",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Odisha",
    "Punjab",
    "Rajasthan",
    "Sikkim",
    "Tamil Nadu",
    "Telangana",
    "Tripura",
    "Uttar Pradesh",
    "Uttarakhand",
    "West Bengal",
]

INDIAN_UNION_TERRITORIES = [
    "Andaman and Nicobar Islands",
    "Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi",
    "Jammu and Kashmir",
    "Ladakh",
    "Lakshadweep",
    "Puducherry",
]

INDIAN_STATES_UTS = INDIAN_STATES + INDIAN_UNION_TERRITORIES


def is_indian_state_ut(value) -> bool:
    return (value or "").strip() in INDIAN_STATES_UTS


def jurisdiction_string(state: str = "") -> str:
    """Derived jurisdiction label: 'India' or 'India, <state/UT>'."""
    state = (state or "").strip()
    if state:
        return f"{JURISDICTION_COUNTRY}, {state}"
    return JURISDICTION_COUNTRY


# Sensible Indian states for legacy demo cases that were seeded before the
# India-only lock (keyed by case type). Keeps fictional demos coherent.
DEMO_STATE_BY_CASE_TYPE = {
    "Tenant/Landlord": "Delhi",
    "Employment": "Karnataka",
    "Consumer": "Delhi",
    "Contract": "Maharashtra",
    "Property": "Kerala",
}