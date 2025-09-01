"""Welcome to Reflex! This file outlines the steps to create a basic app."""

import csv
import time
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
    satellites: list = []
    stations: list = []
    show_satellites: bool = True
    show_stations: bool = True
    relayout: bool = True
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
    def toggle_stations(self):
        self.show_stations = not self.show_stations
        self.create_map()
        
    @rx.event
    def toggle_satellites(self):
        self.show_satellites = not self.show_satellites
        self.create_map()
        
    @rx.event
    def toggle_relayout(self):
        self.relayout = not self.relayout
        self.create_map()
    
    @rx.event
    def create_map(self):
        
        if self.relayout == True:
            
            t = timescale.now()
            coords = []
            typ = ""
            
            if self.show_satellites == True:
                for sat in self.satellites:
                    typ = "Satellite"
                    name, obj = sat
                    lat, lon = wgs84.latlon_of(obj.at(t))
                    coords.append((lat.degrees, lon.degrees, typ, name))
            
            if self.show_stations == True:
                for sat in self.stations:
                    typ = "Station"
                    name, obj = sat
                    lat, lon = wgs84.latlon_of(obj.at(t))
                    coords.append((lat.degrees, lon.degrees, typ, name))
                
            self.df = pd.DataFrame(coords, columns=["lat", "lon", "type", "name"])
            self.fig = px.scatter_geo(self.df,
                            lat="lat",
                            lon="lon",
                            color="type",
                            color_discrete_map={"Satellite": "#636EFA",
                                                "Station": "#38E54D"},
                            hover_name="name",
                            projection="orthographic", 
                            template="plotly_dark",
                            width=1300,
                            height=900
                            )
            self.fig.update_geos(
                            showlakes=False,
                            landcolor='#B2A5FF',
                            oceancolor='#424874',
                            )
            self.fig.update_layout(
                uirevision="constant",
                showlegend=False
            )
        
    @rx.event
    # Download new data if the local file is older than 7 days
    def download_limiter(self, url, file):
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
        
        self.download_limiter(stations_url, stations_filepath)
        self.download_limiter(active_sats_url, sats_filepath)
        
        with load.open(sats_filepath.as_posix(), mode='r') as file:
            
            sats_data = list(csv.DictReader(file))
            
        with load.open(stations_filepath.as_posix(), mode='r') as file:
            
            stations_data = list(csv.DictReader(file))
        
        self.satellites = [(fields["OBJECT_NAME"], EarthSatellite.from_omm(timescale, fields)) for fields in sats_data]
        self.stations = [(fields["OBJECT_NAME"], EarthSatellite.from_omm(timescale, fields)) for fields in stations_data]
        

timescale = load.timescale()


def index() -> rx.Component:
    # Welcome Page (Index)
    return rx.container(
        rx.vstack(
                rx.hstack(
                    rx.hstack(
                        rx.text("Toggle Satellites: ",
                                size="3",
                                weight="medium",
                                trim="both",
                                color_scheme="purple",
                                ),
                        rx.switch(on_change=State.toggle_satellites,
                                  checked=State.show_satellites,
                                  size="3",
                                  color_scheme="iris",
                                  high_contrast=True,
                                  radius="full",
                                  variant="surface"
                                  )
                    ),
                    rx.hstack(
                        rx.text("Toggle Space Stations: ",
                                size="3",
                                weight="medium",
                                trim="both",
                                color_scheme="purple"
                                ),
                        rx.switch(on_change=State.toggle_stations,
                                  checked=State.show_stations,
                                  size="3",
                                  color_scheme="iris",
                                  high_contrast=True,
                                  radius="full",
                                  variant="surface"
                                  )
                    )
                ),
            rx.box(
                rx.plotly(data=State.fig,
                        on_after_plot=State.create_map,
                        on_relayout=State.create_map,
                        on_relayouting=State.toggle_relayout,
                        use_resize_handler=True,
                        config={"displayModeBar":False,
                                "doubleClick": False}),
                width="100%",
                height="60vh"
            ),
            rx.box(
                rx.color_mode.button(position="bottom-right"),
            ),
            on_mount=State.download_celestrak_data,
            align_items = "center",
            justify = "center",
            display = "flex",
        ),
    )

app = rx.App()
app.add_page(index)