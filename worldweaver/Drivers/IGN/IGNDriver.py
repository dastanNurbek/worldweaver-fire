from enum import StrEnum

import geopandas as g

from worldweaver.Drivers.BaseDriver import BaseDriver

from worldweaver.Drivers.IGN.StreamLoader import StreamLoader
from worldweaver.Drivers.IGN.FileLoader import FileLoader
from worldweaver.Drivers.IGN.IGNPreprocessor import IGNPreprocessor
from worldweaver.Drivers.IGN.SubdenseLoader import SubdenseLoader

from worldweaver.Utils.Config import Config
from worldweaver.Utils.Logging import logger
from worldweaver.Utils.Utils import CRS_fr


class IGNDataSources(StrEnum):
    STREAM = "STREAM"
    FILE = "FILE"
    SUBDENSE = "SUBDENSE"


class IGNDriver(BaseDriver):
    def __init__(self, config: Config, project_path):

        super().__init__(config, project_path)
        self.internal_crs = CRS_fr

        match config.data_source:
            case IGNDataSources.STREAM:
                self.loader = StreamLoader(
                    config.base_folder, project_path, self.config.terrain.use_sat_img
                )
            case IGNDataSources.SUBDENSE:
                self.loader = SubdenseLoader(
                    config.base_folder, project_path, self.config.terrain.use_sat_img
                )
            case IGNDataSources.FILE:
                self.loader = FileLoader(
                    config.base_folder, project_path, self.config.terrain.use_sat_img
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
            geo_data=geo_data, geowindow=self.geo_window
        )

        return rendering_data

    @staticmethod
    def get_supported_sources() -> list[str]:
        return [source.value for source in IGNDataSources]

    def load_texture(self, mesh_box: tuple[float, float, float, float]) -> str:

        return self.loader.load_texture(mesh_box)

    def __compute_geo_window_town__(self) -> g.GeoDataFrame:

        return self.loader.load_town_shape(self.config.geo_window.town_id)
