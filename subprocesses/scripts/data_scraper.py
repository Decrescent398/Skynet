from skyfield.api import load
from skyfield.api import EarthSatellite
import os
import csv
import pathlib

def celestrak_data():
    base = 'https://celestrak.org/NORAD/elements/gp.php'

    try:
        os.mkdir('subprocesses/databases')
    except: 
        pass
    
    database = pathlib.Path('subprocesses/databases')

    space_stations = 'stations.csv'
    stations_url = base + '?GROUP=stations&FORMAT=csv'
    stationspath = pathlib.Path(space_stations)
    stations_filepath = database / stationspath

    active_sats = 'active_satellites.csv'
    active_sats_url = base + '?GROUP=active&FORMAT=csv'
    satspath = pathlib.Path(active_sats)
    sats_filepath = database / satspath

    def limiter(file, url):
        if load.days_old(file) >= 7.0:
            load.download(url, filename = str(file))
    
    limiter(stations_filepath, stations_url)
    limiter(sats_filepath, active_sats_url)

    skynet_objects = ['Space stations', 'Satellites']

    def csv_sort(filename):
        with load.open(filename, mode='r') as file:
            data = list(csv.DictReader(file))
        timescale = load.timescale()
        objects = [EarthSatellite.from_omm(timescale, fields) for fields in data]
        return objects

    skynet_objects[0] = csv_sort(str(stations_filepath))
    skynet_objects[1] = csv_sort(str(sats_filepath))

    return skynet_objects

celestrak_data()