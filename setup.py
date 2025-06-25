from distutils.core import setup

setup(
    name="worldweaver",
    version="1.0.0.0",
    description="Procedural Generator for satellite images",
    author="Armand Verstraete",
    author_email="armand.verstraete@lecnam.net",
    url="",
    packages=[
        "worldweaver",
        "worldweaver.Drivers",
        "worldweaver.Loader",
        "worldweaver.Manager",
        "worldweaver.Parser",
        "worldweaver.Processor",
        "worldweaver.Renderer",
        "worldweaver.Utils",
    ],
)
