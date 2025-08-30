"""Welcome to Reflex! This file outlines the steps to create a basic app."""

import csv
import reflex as rx
import pandas as pd
import plotly.express as px
from skyfield.api import wgs84
from skyfield.api import load
from skyfield.api import EarthSatellite
from rxconfig import config

class State(rx.State):
    """The app state."""

def csv_sort(filename='databases/active_satellites.csv'):
    timescale = load.timescale()
    time = timescale.now()
    with load.open(filename, mode='r') as file:
        data = list(csv.DictReader(file))
    objects = [EarthSatellite.from_omm(timescale, fields) for fields in data]
    coords = []
    for sat in objects:
        lat, lon = wgs84.latlon_of(sat.at(time))
        coords.append((lat.degrees, lon.degrees))
    return pd.DataFrame(coords, columns=["lat", "lon"])

df = csv_sort()
fig = px.scatter_geo(df,
                  lat="lat",
                  lon="lon",
                  projection="orthographic", 
                  template="ggplot2",
                  width=1300,
                  height=1000
                  )

def index() -> rx.Component:
    # Welcome Page (Index)
    return rx.container(
        rx.color_mode.button(position="bottom-left"),
        rx.box(
            rx.plotly(data=fig),
            align = "center",
            justify = "center",
            display = "flex"
        ),
    )


app = rx.App()
app.add_page(index)