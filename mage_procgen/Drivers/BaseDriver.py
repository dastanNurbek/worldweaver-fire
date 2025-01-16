import os
import fiona

from mage_procgen.Utils.Config import Config
from mage_procgen.Utils.Utils import RenderingData
from mage_procgen.Utils.Utils import GeoWindow


class BaseDriver:

    max_allowed_area = 20

    def __init__(self, config: Config, project_path: str):
        self.config = config
        self.project_path = project_path
        self.internal_crs = None

        self.loader = None

        self.processor = None
        self.geo_window = None
        self.terrain_data = None

    def process(self) -> RenderingData:

        raise NotImplementedError("Method not implemented in this abstract class")

    def load_texture(self, mesh_box: tuple[float, float, float, float]) -> str:

        raise NotImplementedError("Method not implemented in this abstract class")

    def __compute_geo_window__(self):
        match self.config.window_type:
            case "TOWN":
                town = self.__compute_geo_window_town__()

                self.geo_window = GeoWindow(
                    town.geometry[0], self.internal_crs, self.internal_crs
                )
            case "FILE":
                file_window = fiona.open(self.config.window_shapefile)
                window_crs = int(file_window.crs.to_string().split(":")[1])
                file_bounds = file_window.bounds
                self.geo_window = GeoWindow.from_square(
                    file_bounds[0],
                    file_bounds[2],
                    file_bounds[1],
                    file_bounds[3],
                    window_crs,
                    self.internal_crs,
                )
            case "COORDS":
                self.geo_window: GeoWindow = GeoWindow.from_square(
                    self.config.geo_window.x_min,
                    self.config.geo_window.x_max,
                    self.config.geo_window.y_min,
                    self.config.geo_window.y_max,
                    self.config.geo_window.crs_from,
                    self.internal_crs,
                )
            case _:
                raise ValueError(
                    "Invalid config: invalid window type: ", self.config.window_type
                )

        window_x = (self.geo_window.bounds[2] - self.geo_window.bounds[0]) / 1000
        window_y = (self.geo_window.bounds[3] - self.geo_window.bounds[1]) / 1000
        area = window_x * window_y
        print("Project name:", os.path.basename(self.project_path))
        print(
            "Box size:",
            "{:.3f}".format(window_x),
            "*",
            "{:.3f}".format(window_y),
            "=",
            "{:.3f}".format(area),
            "km²",
        )
        if area > BaseDriver.max_allowed_area:
            raise ValueError(
                "Window too big. Max value allowed is "
                + str(BaseDriver.max_allowed_area)
                + "km²"
            )

    def __compute_geo_window_town__(self):

        raise NotImplementedError("Method not implemented in this abstract class")
