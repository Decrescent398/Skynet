import requests
from skyfield.api import load, Topos
from datetime import datetime, timezone

# Define observer's location
lat, lon = 37.7749, -122.4194  # Example: San Francisco
observer = Topos(latitude_degrees=lat, longitude_degrees=lon)

# Fetch latest TLE data from CelesTrak (NORAD)
tle_url = "https://celestrak.org/NORAD/elements/stations.txt"
tle_data = requests.get(tle_url).text.strip().split("\n")

# Load TLE into Skyfield
ts = load.timescale()
satellites = []
for i in range(0, len(tle_data), 3):
    name, line1, line2 = tle_data[i:i+3]
    satellite = load.tle(name, line1, line2)
    satellites.append((name.strip(), satellite))

# Check which satellites are overhead
now = ts.now()
print("\n🌍 Overhead Satellites:")
for name, sat in satellites:
    difference = sat - observer
    topocentric = difference.at(now)
    alt, az, _ = topocentric.altaz()
    
    if alt.degrees > 10:  # Only show satellites above 10° elevation
        print(f"🛰 {name}: Altitude {alt.degrees:.2f}°, Azimuth {az.degrees:.2f}°")