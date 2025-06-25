from enum import StrEnum

from worldweaver.Drivers.BaseDriver import BaseDriver
from worldweaver.Drivers.OSM.OsmLoader import OsmLoader
from worldweaver.Drivers.OSM.OsmChLoader import OsmChLoader
from worldweaver.Drivers.OSM.OSMPreprocessor import OSMPreprocessor

from worldweaver.Utils.Config import Config
from worldweaver.Utils.Logging import logger


class OSMDataSources(StrEnum):
    OSM_CH = "OSM-CH"
    OSM_SRTM = "OSM-SRTM"


class OSMDriver(BaseDriver):
    def __init__(self, config: Config, project_path: str):
        super().__init__(config, project_path)
        match config.data_source:
            case OSMDataSources.OSM_CH:
                self.loader = OsmChLoader(config.base_folder, project_path)
                self.internal_crs = self.loader.internal_crs
            case OSMDataSources.OSM_SRTM:
                self.loader = OsmLoader(config.base_folder, project_path)
                self.internal_crs = self.loader.internal_crs
            case _:
                raise ValueError(
                    "Invalid config: invalid data source type: ", config.data_source
                )
        self.__compute_geo_window__()
        self.processor = OSMPreprocessor

    def process(self):

        geo_data = self.loader.load(self.geo_window)
        self.terrain_data = geo_data[2]
        logger.info("Data loaded")

        rendering_data = self.processor.process(
            geo_data[0], geo_data[1], self.geo_window
        )

        return rendering_data

    @staticmethod
    def get_supported_sources() -> list[str]:
        return [source.value for source in OSMDataSources]

    def load_texture(self, mesh_box: tuple[float, float, float, float]) -> str:

        return self.loader.load_texture(mesh_box)

    def __compute_geo_window_town__(self):

        return self.loader.load_town_shape(self.config.geo_window.town_id)
