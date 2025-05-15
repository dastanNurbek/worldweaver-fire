import os
from abc import ABC, abstractmethod
from enum import StrEnum

import geopandas as g

import fiona

from mage_procgen.Utils.Config import Config
from mage_procgen.Utils.Logging import logger
from mage_procgen.Utils.RenderingDataFrames import RenderingData
from mage_procgen.Utils.Utils import GeoWindow


class WindowTypes(StrEnum):
    TOWN = "TOWN"
    FILE = "FILE"
    COORDS = "COORDS"


class BaseDriver(ABC):

    # Maximum surface, in km², that is allowed to be rendered in the software
    # TODO: move this in config ? It SHOULD depend on the computing power of the machine it's being ran on
    # So its role is mainly to avoid users starting something that is way too big and will drain resources
    max_allowed_area = 20

    def __init__(self, config: Config, project_path: str):
        self.config = config
        self.project_path = project_path
        self.internal_crs = None

        self.loader = None

        self.processor = None
        self.geo_window = None
        self.terrain_data = None

    @abstractmethod
    def process(self) -> RenderingData:
        pass

    @staticmethod
    @abstractmethod
    def get_supported_sources() -> list[str]:
        pass

    @abstractmethod
    def load_texture(self, mesh_box: tuple[float, float, float, float]) -> str:
        pass

    def __compute_geo_window__(self):
        match self.config.window_type:
            case WindowTypes.TOWN:
                town = self.__compute_geo_window_town__()

                town_bounds = town.geometry[0].bounds
                self.geo_window = GeoWindow.from_square(
                    x_min=town_bounds[0],
                    x_max=town_bounds[2],
                    y_min=town_bounds[1],
                    y_max=town_bounds[3],
                    from_crs=self.internal_crs,
                    to_crs=self.internal_crs,
                )
            case WindowTypes.FILE:
                file_window = fiona.open(self.config.window_shapefile)
                window_crs = int(file_window.crs.to_string().split(":")[1])
                file_bounds = file_window.bounds
                self.geo_window = GeoWindow.from_square(
                    x_min=file_bounds[0],
                    x_max=file_bounds[2],
                    y_min=file_bounds[1],
                    y_max=file_bounds[3],
                    from_crs=window_crs,
                    to_crs=self.internal_crs,
                )
            case WindowTypes.COORDS:
                self.geo_window: GeoWindow = GeoWindow.from_square(
                    x_min=self.config.geo_window.x_min,
                    x_max=self.config.geo_window.x_max,
                    y_min=self.config.geo_window.y_min,
                    y_max=self.config.geo_window.y_max,
                    from_crs=self.config.geo_window.crs_from,
                    to_crs=self.internal_crs,
                )
            case _:
                raise ValueError(
                    "Invalid config: invalid window type: ", self.config.window_type
                )

        window_x = (self.geo_window.bounds[2] - self.geo_window.bounds[0]) / 1000
        window_y = (self.geo_window.bounds[3] - self.geo_window.bounds[1]) / 1000
        area = window_x * window_y
        logger.info("Project name: " + os.path.basename(self.project_path))
        logger.info(
            f"Box size: "
            f"{window_x:.3f}"
            f" * "
            f"{window_y:.3f}"
            f" = "
            f"{area:.3f}"
            f" km²"
        )
        if area > BaseDriver.max_allowed_area:
            raise ValueError(
                f"Window too big. Max value allowed is "
                f"{BaseDriver.max_allowed_area}"
                f" km²"
            )

    @abstractmethod
    def __compute_geo_window_town__(self) -> g.GeoDataFrame:
        pass
