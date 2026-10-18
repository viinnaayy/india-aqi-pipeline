"""Settings: which cities we track and how far back we load data."""

# (city, state, region, latitude, longitude)
CITIES = [
    ("Delhi", "Delhi", "North", 28.6139, 77.2090),
    ("Mumbai", "Maharashtra", "West", 19.0760, 72.8777),
    ("Kolkata", "West Bengal", "East", 22.5726, 88.3639),
    ("Chennai", "Tamil Nadu", "South", 13.0827, 80.2707),
    ("Bengaluru", "Karnataka", "South", 12.9716, 77.5946),
    ("Hyderabad", "Telangana", "South", 17.3850, 78.4867),
    ("Ahmedabad", "Gujarat", "West", 23.0225, 72.5714),
    ("Pune", "Maharashtra", "West", 18.5204, 73.8567),
    ("Jaipur", "Rajasthan", "North", 26.9124, 75.7873),
    ("Lucknow", "Uttar Pradesh", "North", 26.8467, 80.9462),
    ("Kanpur", "Uttar Pradesh", "North", 26.4499, 80.3319),
    ("Patna", "Bihar", "East", 25.5941, 85.1376),
    ("Bhopal", "Madhya Pradesh", "Central", 23.2599, 77.4126),
    ("Chandigarh", "Chandigarh", "North", 30.7333, 76.7794),
    ("Ludhiana", "Punjab", "North", 30.9010, 75.8573),
    ("Nagpur", "Maharashtra", "Central", 21.1458, 79.0882),
    ("Visakhapatnam", "Andhra Pradesh", "South", 17.6868, 83.2185),
    ("Guwahati", "Assam", "Northeast", 26.1445, 91.7362),
    ("Kochi", "Kerala", "South", 9.9312, 76.2673),
    ("Bhubaneswar", "Odisha", "East", 20.2961, 85.8245),
]

# Open-Meteo air quality data for India is only available from mid-2022,
# so we start safely in 2023.
START_DATE = "2023-01-01"
