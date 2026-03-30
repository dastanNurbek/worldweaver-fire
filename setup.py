from distutils.core import setup

setup(
    name="worldweaver",
    version="1.1.0.0",
    description="Procedural Generator for satellite images",
    author="WorldWeaver Team",
    author_email="nicolas.audebert@ign.fr",
    url="",
    packages=[
        "worldweaver",
        "worldweaver.Drivers",
        "worldweaver.Drivers.IGN",
        "worldweaver.Drivers.OSM",
        "worldweaver.Loader",
        "worldweaver.Manager",
        "worldweaver.Parser",
        "worldweaver.Processor",
        "worldweaver.Renderer",
        "worldweaver.Utils",
    ],
)
