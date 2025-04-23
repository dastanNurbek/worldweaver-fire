from bpy import data as D

from mage_procgen.Utils.Utils import TerrainData
from mage_procgen.Renderer.FlatPolygonRenderer import FlatPolygonRenderer


class HiddenPolygonRenderer(FlatPolygonRenderer):
    _mesh_name = "HiddenObject"

    def __init__(self, terrain_data: list[TerrainData]):

        self._terrain_data = terrain_data

    def render(
        self,
        objects: list,
        geo_center: tuple[float, float, float],
        parent_collection_name,
    ):

        mesh_obj = self.draw_objects(objects, geo_center, parent_collection_name)

        mesh_obj.hide_render = True
        mesh_obj.hide_viewport = True

    def get_mesh_obj(self):
        return D.objects[self._mesh_name]
