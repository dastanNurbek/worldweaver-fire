from mage_procgen.Drivers.BaseDriver import BaseDriver

from mage_procgen.Drivers.IGN.StreamLoader import StreamLoader
from mage_procgen.Drivers.IGN.FileLoader import FileLoader
from mage_procgen.Drivers.IGN.IGNPreprocessor import IGNPreprocessor

from mage_procgen.Utils.Utils import CRS_fr
from mage_procgen.Utils.Logging import logger


class IGNDriver(BaseDriver):

    supported_data_sources = ["STREAM", "FILE"]

    def __init__(self, config, project_path):

        super().__init__(config, project_path)
        self.internal_crs = CRS_fr

        match config.data_source:
            case "STREAM":
                self.loader = StreamLoader(
                    config.base_folder, project_path, self.config.use_sat_img
                )
            case "FILE":
                self.loader = FileLoader(
                    config.base_folder, project_path, self.config.use_sat_img
                )
            case _:
                raise ValueError(
                    "Invalid config: invalid data source type: ", config.data_source
                )

        self.__compute_geo_window__()
        self.processor = IGNPreprocessor

    def process(self):

        geo_data = self.loader.load(self.geo_window)
        self.terrain_data = geo_data.terrain

        logger.info("Data loaded")

        rendering_data = self.processor.process(
            geo_data, self.geo_window, self.config, CRS_fr
        )

        return rendering_data

    def load_texture(self, mesh_box: tuple[float, float, float, float]) -> str:

        return self.loader.load_texture(mesh_box)

    def __compute_geo_window_town__(self):

        return self.loader.load_town_shape(self.config.town_dpt, self.config.town_name)
