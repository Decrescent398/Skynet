from skyfield.api import wgs84
from skyfield.api import load
from datetime import datetime
from math import floor
from .data_scraper import celestrak_data
import geocoder

location = geocoder.ip('me')
city = str(location)[24:].split(', ')[0]
latitude, longitude = location.latlng[0], location.latlng[1]
print(f"Getting overhead satellites for {city}...\n")

def sats_now():
    loc = geocoder.ip('me')
    coordinates = loc.latlng
    retrieve_location = wgs84.latlon(coordinates[0], coordinates[1])
    date = str(datetime.now().date()).split('-')
    time = str(datetime.now().time()).split(':')
    timescale = load.timescale()

    time_start = timescale.utc(int(date[0]), int(date[1]), int(date[2]), int(time[0]), int(time[1]), floor(float(time[2])))
    time_end = timescale.utc(int(date[0]), int(date[1]), int(date[2]), int(time[0]), int(time[1])+10, floor(float(time[2])))

    object_count = 0
    for objects in celestrak_data():
        for satellite in objects:
            t, events = satellite.find_events(retrieve_location, time_start, time_end, altitude_degrees=30.0)
            event_names = 'rise above 30°', 'culminate', 'set below 30°'
            for ti, event in zip(t, events):
                name = event_names[event]
                simplified_name = name.split(' ')[0]
                if name.split(' ')[0] == 'culminate':
                    simplified_name = "reach it's apex"
                print(f"{str(satellite).partition(' catalog')[0]} will {simplified_name} at {ti.utc_strftime('%H:%M:%S')}")
                object_count+=1
    print(f"\nFound {object_count} satellites")

sats_now()