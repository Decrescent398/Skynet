from skyfield.api import load
from skyfield.api import wgs84
import csv
import os
import geocoder

def celestrak_data():
    base = 'https://celestrak.org/NORAD/elements/gp.php'

    space_stations = 'stations.csv'
    stations_url = base + '?GROUP=stations&FORMAT=csv'
    load.download(stations_url, filename = space_stations)

    active_sats = 'active_satellites.csv'
    active_sats_url = base + '?GROUP=active&FORMAT=csv'
    load.download(active_sats_url, filename = active_sats)

    skynet_objects = ['Space stations', 'Satellites']
    stations = []
    active_satellites = []

    def csv_sort(filename, sorter_list):
        ignore_table = 0
        with load.open(filename, 'r') as file:
            for object in csv.reader(file, delimiter = ','):
                if ignore_table != 0:
                    sorter_list.append(object[0])
                ignore_table +=1

    csv_sort(active_sats, active_satellites)
    csv_sort(space_stations, stations)

    skynet_objects[0] = stations
    skynet_objects[1] = active_satellites

    os.remove('active_satellites.csv')
    os.remove('stations.csv')

    return skynet_objects

location = geocoder.ip('me')
city = str(location)[24:].split(', ')[0]
latitude, longitude = location.latlng[0], location.latlng[1]
print(f"Getting overhead satellites for {city}")