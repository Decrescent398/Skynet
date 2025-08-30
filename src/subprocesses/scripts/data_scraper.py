from skyfield.api import load
from skyfield.api import EarthSatellite
import os
import csv
import pathlib

# This script downloads and processes satellite and space station data from Celestrak,
# storing it in CSV files and loading it into Skyfield EarthSatellite objects.

def celestrak_data():
    # Base URL for Celestrak NORAD elements in CSV format
    base = 'https://celestrak.org/NORAD/elements/gp.php'

    # Ensure the databases directory exists
    try:
        os.mkdir('subprocesses/databases')
    except: 
        pass  # Ignore error if directory already exists

    database = pathlib.Path('src/subprocesses/databases')

    # File paths and URLs for space stations and active satellites
    space_stations = 'stations.csv'
    stations_url = base + '?GROUP=stations&FORMAT=csv'
    stationspath = pathlib.Path(space_stations)
    stations_filepath = database / stationspath

    active_sats = 'active_satellites.csv'
    active_sats_url = base + '?GROUP=active&FORMAT=csv'
    satspath = pathlib.Path(active_sats)
    sats_filepath = database / satspath

    # Download new data if the local file is older than 7 days
    def limiter(file, url):
        if load.days_old(file) >= 7.0:
            load.download(url, filename = str(file))

    limiter(stations_filepath, stations_url)
    limiter(sats_filepath, active_sats_url)

    # List to store Skyfield EarthSatellite objects for stations and satellites
    skynet_objects = ['Space stations', 'Satellites']

    # Read CSV and convert each row to an EarthSatellite object
    def csv_sort(filename):
        with load.open(filename, mode='r') as file:
            data = list(csv.DictReader(file))
        timescale = load.timescale()
        objects = [EarthSatellite.from_omm(timescale, fields) for fields in data]
        return objects

    skynet_objects[0] = csv_sort(str(stations_filepath))
    skynet_objects[1] = csv_sort(str(sats_filepath))

    # Return the list of EarthSatellite objects for further use
    return skynet_objects

# Run the data download and processing when the script is executed
celestrak_data()