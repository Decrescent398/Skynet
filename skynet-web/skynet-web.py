"""Welcome to Reflex! This file outlines the steps to create a basic app."""

import csv
import pathlib
import reflex as rx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from skyfield.api import wgs84
from skyfield.api import load
from skyfield.api import EarthSatellite
from rxconfig import config

class State(rx.State):
    """The app state."""
    df: pd.DataFrame
    objects: list = []
    fig: go.Figure = px.scatter_geo(
        pd.DataFrame(columns=["lat", "lon"]),
        lat="lat",
        lon="lon",
        projection="orthographic",
        template="ggplot2",
        width=1300,
        height=1000
    )
    
    @rx.event
    def create_map(self):
        
        time = timescale.now()
        
        coords = []
        
        for idx, classification in enumerate(self.objects):
            typ = "Stations" if idx == 1 else "Satellite"
            for sat in classification:
            
                lat, lon = wgs84.latlon_of(sat.at(time))
                coords.append((lat.degrees, lon.degrees, typ))
            
        self.df = pd.DataFrame(coords, columns=["lat", "lon", "type"])
        self.fig = px.scatter_geo(self.df,
                        lat="lat",
                        lon="lon",
                        color="type",
                        projection="orthographic", 
                        template="plotly_dark",
                        width=1300,
                        height=1000
                        )
        self.fig.update_geos(
                        showlakes=False,
                        landcolor='#DCD6F7',
                        oceancolor='#424874'
                        )
        self.fig.update_layout(
            uirevision="constant",
            showlegend=False
        )
        
    @rx.event
    # Download new data if the local file is older than 7 days
    def download_limiter(self, file, url):
        if load.days_old(file) >= 7.0:
            load.download(url, filename = str(file))
    
    @rx.event
    def download_celestrak_data(self):
        # Base URL for Celestrak NORAD elements in CSV format
        base = 'https://celestrak.org/NORAD/elements/gp.php'

        database = pathlib.Path('databases/')

        # File paths and URLs for space stations and active satellites
        space_stations = 'stations.csv'
        stations_url = base + '?GROUP=stations&FORMAT=csv'
        stations_filepath = database / "stations.csv"

        active_sats = 'active_satellites.csv'
        active_sats_url = base + '?GROUP=active&FORMAT=csv'
        sats_filepath = database / "active_satellites.csv"
        
        self.download_limiter(stations_filepath, stations_url)
        self.download_limiter(sats_filepath, active_sats_url)
        
        with load.open(sats_filepath.as_posix(), mode='r') as file:
            
            sats_data = list(csv.DictReader(file))
            
        with load.open(stations_filepath.as_posix(), mode='r') as file:
            
            stations_data = list(csv.DictReader(file))
            
        self.objects.append([EarthSatellite.from_omm(timescale, fields) for fields in sats_data])
        self.objects.append([EarthSatellite.from_omm(timescale, fields) for fields in stations_data])
        

timescale = load.timescale()


def index() -> rx.Component:
    # Welcome Page (Index)
    return rx.container(
        rx.color_mode.button(position="bottom-left"),
        rx.hstack(
            rx.box(
                rx.plotly(data=State.fig,
                        on_after_plot=State.create_map,
                        use_resize_handler=True,
                        config={"displayModeBar":False}),
                on_mount=State.download_celestrak_data,
                align = "center",
                justify = "center",
                display = "flex",
            )
        ),
    )

app = rx.App()
app.add_page(index)