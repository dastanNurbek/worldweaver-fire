import os

from mage_procgen.Drivers.BaseDriver import BaseDriver

from mage_procgen.Drivers.OSM.OsmLoader import OsmLoader
from mage_procgen.Drivers.OSM.OsmChLoader import OsmChLoader
from mage_procgen.Drivers.OSM.Preprocessor import Preprocessor


class OSMDriver(BaseDriver):

    supported_data_sources = ["OSM-CH", "OSM-SRTM"]

    def __init__(self, config, project_path):
        super().__init__(config, project_path)

        match config.data_source:
            case "OSM-CH":
                self.loader = OsmChLoader(config.base_folder, project_path)
                self.internal_crs = self.loader.internal_crs
            case "OSM-SRTM":
                self.loader = OsmLoader(config.base_folder, project_path)
                self.internal_crs = self.loader.internal_crs
            case _:
                raise ValueError(
                    "Invalid config: invalid data source type: ", config.data_source
                )
        self.__compute_geo_window__()
        self.processor = Preprocessor

    def process(self):

        geo_data = self.loader.load(self.geo_window)
        self.terrain_data = geo_data[2]
        print("Data loaded")
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

        rendering_data = self.processor.process(
            geo_data[0], geo_data[1], self.geo_window, self.config, self.internal_crs
        )

        return rendering_data

    def load_texture(self, mesh_box: tuple[float, float, float, float]) -> str:

        return self.loader.load_texture(mesh_box)
