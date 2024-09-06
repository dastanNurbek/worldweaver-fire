from mage_procgen.Utils.Utils import GeoWindow, GeoData


class Loader:
    def __init__(self, base_folder: str, project_folder: str):
        self.base_folder = base_folder
        self.project_folder = project_folder

    def load(self, geo_window: GeoWindow) -> GeoData:

        raise NotImplementedError("Method not implemented in this abstract class")

    def load_town_shape(self, departement_nbr: int, town_name: str):

        raise NotImplementedError("Method not implemented in this abstract class")

    def load_texture(self, mesh_box: tuple[float, float, float, float]) -> str:

        raise NotImplementedError("Method not implemented in this abstract class")
