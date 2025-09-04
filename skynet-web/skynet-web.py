#TODO: 
#Dynamic Pan, Search, SQL Migration, Sidebar, Icons (Probably), Switch Buffer & Lock, and comments aaagh

import csv
import time
import pathlib
import reflex as rx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from termcolor import colored
from sgp4.api import Satrec, WGS72
from skyfield.api import wgs84
from skyfield.api import load
from skyfield.api import EarthSatellite
from rxconfig import config

timescale = load.timescale()

class State(rx.State):
    """The app state."""
    custom_data: list = []
    custom: list = []
    form_error: bool = False
    satellites: list = []
    stations: list = []
    show_satellites: bool = True
    show_stations: bool = True
    relayout: bool = True
    df: pd.DataFrame
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
    def handle_submit(self, form_data: dict):
        print(colored("Submitted", "green"))
        self.custom_data = self.custom_data + [form_data]

        satrec = Satrec()
        satrec.sgp4init(
            WGS72,
            'i',
            70000 + len(self.custom_data),
            float(form_data["epoch"]),
            float(form_data["bstar"]),
            float(form_data["ndot"]),
            float(form_data["nddot"]),
            float(form_data["ecco"]),
            float(form_data["argpo"]),
            float(form_data["inclo"]),
            float(form_data["mo"]),
            float(form_data["no_kozai"]),
            float(form_data["nodeo"]),
        )
        earth_sat = EarthSatellite.from_satrec(satrec, timescale)
        self.custom = self.custom + [(form_data["name"], earth_sat)]
        self.create_map()
    
    @rx.event
    def toggle_stations(self):
        self.show_stations = not self.show_stations
        
    @rx.event
    def toggle_satellites(self):
        self.show_satellites = not self.show_satellites
        
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
            
            if self.custom:
                for sat in self.custom:
                    typ = "Custom"
                    name, obj = sat
                    lat, lon = wgs84.latlon_of(obj.at(t))
                    coords.append((lat.degrees, lon.degrees, typ, name))
                
            self.df = pd.DataFrame(coords, columns=["lat", "lon", "type", "name"])
            self.fig = px.scatter_geo(self.df,
                            lat="lat",
                            lon="lon",
                            color="type",
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
            self.fig.update_traces(
                        marker=dict(size=8),
                        hovertemplate="<b>%{hovertext}</b><br>" +
                         "Lat: %{lat:.2f}°<br>" +
                         "Lon: %{lon:.2f}°<extra></extra>"
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

def index() -> rx.Component:
    # Welcome Page (Index)
    return rx.vstack(
                rx.spacer(),
                rx.spacer(),
                rx.spacer(spacing="2"),
                rx.hstack(
                    rx.hstack(
                        rx.hstack(
                            rx.text("Toggle Satellites: ",
                                    size="4",
                                    weight="medium",
                                    align="center",
                                    color_scheme="purple",
                                    ),
                            rx.switch(on_change=State.toggle_satellites,
                                    checked=State.show_satellites,
                                    size="3",
                                    color_scheme="iris",
                                    high_contrast=True,
                                    radius="full",
                                    variant="surface"
                                    ),
                        ),
                        rx.hstack(
                            rx.text("Toggle Space Stations: ",
                                    size="4",
                                    weight="medium",
                                    align="center",
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
                        ),
                    align_items = "center",
                    padding="0 0 0 300px"
                    ),
                    rx.dialog.root(
                        rx.dialog.trigger(
                            rx.button(
                                rx.icon("plus", size=20),
                                rx.text("Add Satellite", 
                                        size="4"),
                                color_scheme="violet"
                            ),
                        ),
                        rx.dialog.content(
                            rx.dialog.title("Add your own Satellite!", 
                                            align="center"),
                            rx.dialog.description("Build a custom satellite from orbital elements", 
                                                  align="center"),
                            rx.form(
                                rx.flex(
                                    rx.input(placeholder="Name of your satellite",
                                            name="name",
                                            required=True,
                                            ),
                                    rx.flex(
                                        rx.hover_card.root(
                                            rx.hover_card.trigger(
                                                rx.input(placeholder="epoch",
                                                         name="epoch"),
                                            ),
                                            rx.hover_card.content(
                                                rx.text("Days since 1949 December 31 00:00 UTC",
                                                        align="center"),
                                                rx.text("Eg: 18441.785",
                                                        size="1",
                                                        color_scheme="gray",
                                                        align="center"),
                                                side="left",
                                                align="center",
                                                size="1"
                                            )
                                        ),
                                        rx.spacer(),
                                        rx.hover_card.root(
                                            rx.hover_card.trigger(
                                                rx.input(placeholder="bstar",
                                                         name="bstar"),
                                            ),
                                            rx.hover_card.content(
                                                rx.text("Drag coefficient",
                                                        align="center"),
                                                rx.text("Eg: 0.000028098",
                                                        size="1",
                                                        color_scheme="gray",
                                                        align="center"),
                                                side="right",
                                                align="center",
                                                size="1"
                                            )
                                        ),
                                        direction="row",
                                    ),
                                    rx.flex(
                                        rx.hover_card.root(
                                            rx.hover_card.trigger(
                                                rx.input(placeholder="ndot",
                                                         name="ndot"),
                                            ),
                                            rx.hover_card.content(
                                                rx.text("Ballistic coefficient",
                                                        align="center"),
                                                rx.text("Eg: 0.0000000000006969196665",
                                                        size="1",
                                                        color_scheme="gray",
                                                        align="center"),
                                                side="left",
                                                align="center",
                                                size="1"
                                            )
                                        ),
                                        rx.spacer(),
                                        rx.hover_card.root(
                                            rx.hover_card.trigger(
                                                rx.input(placeholder="nddot",
                                                         name="nddot"),
                                            ),
                                            rx.hover_card.content(
                                                rx.text("Second derivative of mean motion",
                                                        align="center"),
                                                rx.text("Eg: 0.0",
                                                        size="1",
                                                        color_scheme="gray",
                                                        align="center"),
                                                side="right",
                                                align="center",
                                                size="1"
                                            )
                                        ),
                                        direction="row",
                                    ),
                                    rx.flex(
                                        rx.hover_card.root(
                                            rx.hover_card.trigger(
                                                rx.input(placeholder="ecco",
                                                         name="ecco"),
                                            ),
                                            rx.hover_card.content(
                                                rx.text("Eccentricity",
                                                        align="center"),
                                                rx.text("Eg: 0.1859667",
                                                        size="1",
                                                        color_scheme="gray",
                                                        align="center"),
                                                side="left",
                                                align="center",
                                                size="1"
                                            )
                                        ),
                                        rx.spacer(),
                                        rx.hover_card.root(
                                            rx.hover_card.trigger(
                                                rx.input(placeholder="argpo",
                                                         name="argpo"),
                                            ),
                                            rx.hover_card.content(
                                                rx.text("Argument of perigee",
                                                        align="center"),
                                                rx.text("Eg: 5.7904160274885",
                                                        size="1",
                                                        color_scheme="gray",
                                                        align="center"),
                                                side="right",
                                                align="center",
                                                size="1"
                                            )
                                        ),
                                        direction="row",
                                    ),
                                    rx.flex(
                                        rx.hover_card.root(
                                            rx.hover_card.trigger(
                                                rx.input(placeholder="inclo",
                                                         name="inclo"),
                                            ),
                                            rx.hover_card.content(
                                                rx.text("Inclination",
                                                        align="center"),
                                                rx.text("Eg: 0.5980929187319",
                                                        size="1",
                                                        color_scheme="gray",
                                                        align="center"),
                                                side="left",
                                                align="center",
                                                size="1"
                                            )
                                        ),
                                        rx.spacer(),
                                        rx.hover_card.root(
                                            rx.hover_card.trigger(
                                                rx.input(placeholder="mo",
                                                         name="mo"),
                                            ),
                                            rx.hover_card.content(
                                                rx.text("Mean anomaly",
                                                        align="center"),
                                                rx.text("Eg: 0.3373093125574",
                                                        size="1",
                                                        color_scheme="gray",
                                                        align="center"),
                                                side="right",
                                                align="center",
                                                size="1"
                                            )
                                        ),
                                        direction="row",
                                    ),
                                    rx.flex(
                                        rx.hover_card.root(
                                            rx.hover_card.trigger(
                                                rx.input(placeholder="no_kozai",
                                                         name="no_kozai"),
                                            ),
                                            rx.hover_card.content(
                                                rx.text("Mean motion",
                                                        align="center"),
                                                rx.text("Eg: 0.0472294454407",
                                                        size="1",
                                                        color_scheme="gray",
                                                        align="center"),
                                                side="left",
                                                align="center",
                                                size="1",
                                            )
                                        ),
                                        rx.spacer(),
                                        rx.hover_card.root(
                                            rx.hover_card.trigger(
                                                rx.input(placeholder="nodeo",
                                                         name="nodeo"),
                                            ),
                                            rx.hover_card.content(
                                                rx.text("Right ascension of ascending node",
                                                        align="center"),
                                                rx.text("Eg: 6.0863854713832", 
                                                        size="1",
                                                        color_scheme="gray",
                                                        align="center"),
                                                side="right",
                                                align="center",
                                                size="1"
                                            )
                                        ),
                                        direction="row",
                                    ),
                                    rx.flex(
                                        rx.dialog.close(
                                            rx.button(
                                                "Cancel",
                                                variant="soft",
                                                color_scheme="gray"
                                            )
                                        ),
                                        rx.button(
                                                "Submit",
                                                color_scheme="violet",
                                                type="submit"
                                            ),
                                        spacing="3",
                                        justify="end"
                                    ),
                                    direction="column",
                                    spacing="4",
                                ),
                                on_submit=State.handle_submit,
                                reset_on_submit=True
                            ),
                            max_width="450px"
                        ),
                    ),
                    rx.box(
                        rx.image("/www2.gif")
                    ),
                    align_items="start",
                    align="start",
                    justify="start",
                    spacing="4"
                ),
            rx.flex(
                rx.box(),
                rx.plotly(data=State.fig,
                        on_after_plot=State.create_map,
                        on_relayout=State.create_map,
                        on_relayouting=State.toggle_relayout,
                        use_resize_handler=True,
                        config={"displayModeBar":False,
                                "doubleClick": False}),
                width="100%",
                height="90vh",
                direction="row",
                spacing="3",
            ),
            rx.box(
                rx.color_mode.button(position="bottom-left"),
            ),
            on_mount=State.download_celestrak_data,
            justify = "center",
            display = "flex",
        )

app = rx.App()
app.add_page(index)