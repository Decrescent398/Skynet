import csv
import time
import pathlib
import sqlalchemy
import reflex as rx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from skyfield.api import wgs84
from skyfield.api import load
from skyfield.api import EarthSatellite
from rxconfig import config
from sgp4.api import Satrec, WGS72

# =============================
# Database model for satellites and stations. Uses NORAD ID as primary key.
# =============================
class db(rx.Model, table=True): #Using NORAD ID as primary key - merging with default id
    
    OBJECT_NAME: str
    OBJECT_ID: str
    EPOCH: str
    MEAN_MOTION: str
    ECCENTRICITY: str
    INCLINATION: str
    RA_OF_ASC_NODE: str
    ARG_OF_PERICENTER: str
    MEAN_ANOMALY: str
    EPHEMERIS_TYPE: str
    CLASSIFICATION_TYPE: str
    ELEMENT_SET_NO: str
    REV_AT_EPOCH: str
    BSTAR: str
    MEAN_MOTION_DOT: str
    MEAN_MOTION_DDOT: str

    # Skyfield timescale object for all orbital calculations (universal time reference)
timescale = load.timescale()

# =============================
# State: The reactive heart of the app. Holds all live data, toggles, and event handlers.
# =============================
class State(rx.State):
    """The app state."""
    details: str = ''
    isclicked: bool = False
    db_data: list[db]
    sats: pd.DataFrame
    station: pd.DataFrame
    colnames: list = []
    custom_data: list = []
    custom: list = []
    form_error: bool = False
    satellites: list = []
    stations: list = []
    show_satellites: bool = True
    show_stations: bool = True
    relayout: bool = True
    # DataFrame for plotting satellite positions on the globe
    df: pd.DataFrame
    # Main Plotly figure for the interactive globe
    fig: go.Figure = px.scatter_geo(
        pd.DataFrame(columns=["lat", "lon"]),
        lat="lat",
        lon="lon",
        projection="orthographic",
        template="ggplot2",
        width=1300,
        height=1000
    )
    
    # Handles user submission of custom satellite data and adds it to the system
    @rx.event
    def handle_submit(self, form_data: dict):
        self.custom_data = self.custom_data + [form_data]
        
        satnum = 100000 + len(self.custom_data) #To not conflict with existing norad_ids
        
        with rx.session() as session:
            session.execute(
                sqlalchemy.text(
                    f"INSERT INTO db ({", ".join(self.colnames)}) ",
                    f"Values({satnum}, {form_data["name"]}, 'customsat-{satnum}', {form_data["epoch"]}, {form_data["no_kozai"]} {form_data["ecco"]}, {form_data["inclo"]}, {form_data["nodeo"]}, {form_data["argpo"]}, {form_data["mo"]}, '0', 'U', '999', '0', {form_data["bstar"]}, {form_data["ndot"]}, {form_data["nddot"]})"
                )
            )
            session.commit()

        satrec = Satrec()
        satrec.sgp4init(
            WGS72,
            'i',
            satnum,
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
    
    # Toggle the visibility of space stations on the map
    @rx.event
    def toggle_stations(self):
        self.show_stations = not self.show_stations
        
    # Toggle the visibility of satellites on the map
    @rx.event
    def toggle_satellites(self):
        self.show_satellites = not self.show_satellites
        
    # Toggle the relayout state for the map (for UI responsiveness)
    @rx.event
    def toggle_relayout(self):
        self.relayout = not self.relayout
        self.create_map()
        
    # Fetch and return all data for a given satellite/station by ID
    @rx.event
    def show_data(self, id):
        
        with rx.session() as session:
            return[
                list(row)
                for row in session.execute(
                    sqlalchemy.text(
                        "SELECT * FROM db "
                        f"WHERE OBJECT_NAME = '{self.df.iloc[id]["name"]}'"
                    )
                )
            ]
            
    @rx.event
    def set_details(self, vals):
        if not vals or len(vals) == 0 or len(vals) == 0:
            self.details = "No data available for this satellite."
        else:
            print(self.colnames)
            self.details = '\n'.join(f'{col}: {val}' for col, val in zip(self.colnames, vals))
        self.create_map()
            
    # Handle click events on the map (for future interactivity)
    @rx.event
    def handle_click(self, clickData):
        
        if clickData is None:
            return
        
        self.isclicked = True
        point_index = clickData[0]["pointIndex"]
        vals = self.show_data(point_index)
        self.set_details(vals)
    
    # Generates the Plotly globe visualization with all visible satellites, stations, and custom objects
    # Updates the figure in real time as the state changes
    @rx.event
    def create_map(self):
        
        self.isclicked = False
        
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
                            color_discrete_map={
                                "Satellite" : "#686ffe",
                                "Station": "#e2344d",
                                "Custom": "#4ab2ac"
                            },
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
                         "Lon: %{lon:.2f}°<extra></extra><br>" +
                         "Click on this satellite to view more info!"
                        )
            self.fig.update_layout(
                uirevision="constant",
                showlegend=False
                )
        
    # Downloads new data from Celestrak if the local file is older than 15 days
    # Updates the database with the latest satellite and station data
    @rx.event
    # Download new data if the local file is older than 7 days
    def download_limiter(self, url, file):
        if load.days_old(file) >= 15.0:
            load.download(url, filename = str(file))
            
            self.colnames = list(col if col != "NORAD_CAT_ID" else "id" for col in self.sats.columns)
        
            for index, row in self.sats.iterrows():
                
                vals = [int(item) if idx == 11 else str(item) for idx, item in enumerate(row)]
                
                with rx.session() as session:
                    session.execute(
                        sqlalchemy.text(
                            f"INSERT INTO db ({", ".join(self.colnames)}) "
                            f"VALUES ({", ".join(f":{col}" for col in self.colnames)})"
                        ), dict(zip(self.colnames, vals))
                    )
                    session.commit()
            
            for index, row in self.station.iterrows():
                
                vals = [int(item) if idx == 11 else str(item) for idx, item in enumerate(row)]
                
                with rx.session() as session:
                    session.execute(
                        sqlalchemy.text(
                            f"INSERT INTO db ({", ".join(self.colnames)}) "
                            f"VALUES ({", ".join(f":{col}" for col in self.colnames)})"
                        ), dict(zip(self.colnames, vals))
                    )
                    session.commit()
    
    # Downloads the latest satellite and station data from Celestrak
    # Loads the data into Pandas DataFrames and Skyfield objects for visualization
    # Removes any previously stored custom satellites from the database
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
        
        self.sats = pd.read_csv(sats_filepath)
        self.station = pd.read_csv(stations_filepath)
        
        self.colnames = list(col if col != "NORAD_CAT_ID" else "id" for col in self.sats.columns)
        
        sats_data = []
        stations_data = []
        
        for index, row in self.sats.iterrows():
            sats_data.append(row.to_dict())
            
        for index, row in self.station.iterrows():
            stations_data.append(row.to_dict())
        
        self.satellites = [(fields["OBJECT_NAME"], EarthSatellite.from_omm(timescale, fields)) for fields in sats_data]
        self.stations = [(fields["OBJECT_NAME"], EarthSatellite.from_omm(timescale, fields)) for fields in stations_data]
        
        #Remove previously stored custom sats
        
        with rx.session() as session:
            session.execute(
                sqlalchemy.text(
                    "DELETE FROM db "
                    "WHERE id > 100000"
                )
            )
            session.commit()
        
# =============================
# Main page: builds the entire interactive dashboard, including toggles, forms, and the globe.
# =============================
def index() -> rx.Component:
    # Welcome Page (Index)
    return rx.box(    
                rx.center(
                    rx.cond(
                        State.isclicked,
                        rx.dialog.root(
                            rx.dialog.content(
                                
                                rx.text(
                                    State.details,
                                    white_space="pre-line"
                                    )

                            ),
                            open=State.isclicked
                        ),
                        None
                    ),
                ),
                rx.vstack(
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
                                                    "Close",
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
                            on_click=State.handle_click,
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
        )

    # Bootstrap the Reflex app and register the main page
app = rx.App()
app.add_page(index)