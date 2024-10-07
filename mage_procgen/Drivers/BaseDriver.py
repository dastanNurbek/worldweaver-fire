from mage_procgen.Utils.Config import Config
from mage_procgen.Utils.Utils import RenderingData


class BaseDriver:
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
