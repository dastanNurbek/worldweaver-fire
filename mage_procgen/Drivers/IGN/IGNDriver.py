import os
import fiona

from mage_procgen.Drivers.BaseDriver import BaseDriver

from mage_procgen.Drivers.IGN.StreamLoader import StreamLoader
from mage_procgen.Drivers.IGN.FileLoader import FileLoader
from mage_procgen.Drivers.IGN.Preprocessor import Preprocessor

from mage_procgen.Utils.Utils import GeoWindow, CRS_fr


class IGNDriver(BaseDriver):

    supported_data_sources = ["STREAM", "FILE"]

    def __init__(self, config, project_path):

        super().__init__(config, project_path)

        self.internal_crs = CRS_fr

        match config.data_source:
            case "STREAM":
                self.loader = StreamLoader(config.base_folder, project_path)
            case "FILE":
                self.loader = FileLoader(config.base_folder, project_path)
            case _:
                raise ValueError(
                    "Invalid config: invalid data source type: ", config.data_source
                )

        self.__compute_geo_window__()
        self.processor = Preprocessor

    def process(self):

        geo_data = self.loader.load(self.geo_window)
        self.terrain_data = geo_data.terrain

        print("Files loaded")
        window_x = (self.geo_window.bounds[2] - self.geo_window.bounds[0]) / 1000
        window_y = (self.geo_window.bounds[3] - self.geo_window.bounds[1]) / 1000
        print("Project name:", os.path.basename(self.project_path))
        print(
            "Box size:",
            "{:.3f}".format(window_x),
            "*",
            "{:.3f}".format(window_y),
            "=",
            "{:.3f}".format(window_x * window_y),
            "km²",
        )
        print(str(len(geo_data.buildings)), "buildings")

        rendering_data = self.processor.process(
            geo_data, self.geo_window, self.config, CRS_fr
        )

        return rendering_data

    def load_texture(self, mesh_box: tuple[float, float, float, float]) -> str:

        return self.loader.load_texture(mesh_box)
