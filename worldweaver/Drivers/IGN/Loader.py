import os
from abc import ABC, abstractmethod

import geopandas as g

from worldweaver.Drivers.IGN.Utils import GeoData

from worldweaver.Utils.Utils import GeoWindow


_IGN_DOMAINS = "data.geopf.fr,geo.api.gouv.fr"


class Loader(ABC):
    def __init__(self, base_folder: str, project_folder: str, use_sat_img: bool):
        self.base_folder = base_folder
        self.project_folder = project_folder
        self.use_sat_img = use_sat_img
        # The environment may carry HTTPS_PROXY pointing to proxy.ign.fr which
        # is only reachable inside the IGN network. Extend NO_PROXY so that all
        # requests to the public IGN endpoints bypass it.
        _existing = os.environ.get("NO_PROXY", os.environ.get("no_proxy", ""))
        if _IGN_DOMAINS not in _existing:
            os.environ["NO_PROXY"] = f"{_existing},{_IGN_DOMAINS}" if _existing else _IGN_DOMAINS

    @abstractmethod
    def load(self, geo_window: GeoWindow) -> GeoData:
        pass

    @abstractmethod
    def load_town_shape(self, town_id: str) -> g.GeoDataFrame:
        pass

    @abstractmethod
    def load_texture(self, mesh_box: tuple[float, float, float, float]) -> str:
        pass
