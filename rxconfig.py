import reflex as rx

config = rx.Config(
    app_name="Skynet",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ]
)