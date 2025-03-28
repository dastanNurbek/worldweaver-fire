from abc import ABC, abstractmethod

import geopandas as g

from mage_procgen.Drivers.IGN.Utils import GeoData

from mage_procgen.Utils.Utils import GeoWindow


class Loader(ABC):
    def __init__(self, base_folder: str, project_folder: str, use_sat_img: bool):
        self.base_folder = base_folder
        self.project_folder = project_folder
        self.use_sat_img = use_sat_img

    @abstractmethod
    def load(self, geo_window: GeoWindow) -> GeoData:
        pass

    @abstractmethod
    def load_town_shape(self, departement_nbr: int, town_name: str) -> g.GeoDataFrame:
        pass

    @abstractmethod
    def load_texture(self, mesh_box: tuple[float, float, float, float]) -> str:
        pass
