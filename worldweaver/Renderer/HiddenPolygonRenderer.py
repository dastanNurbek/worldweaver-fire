from bpy import data as D

import geopandas as g

from worldweaver.Utils.Utils import TerrainData
from worldweaver.Renderer.FlatPolygonRenderer import FlatPolygonRenderer


class HiddenPolygonRenderer(FlatPolygonRenderer):
    _mesh_name = "HiddenObject"

    def __init__(self, terrain_data: list[TerrainData]):

        self._terrain_data = terrain_data

    def render(
        self,
        objects_gdf: g.GeoDataFrame,
        geo_center: tuple[float, float, float],
        parent_collection_name: str,
    ):

        mesh_obj = self._draw_objects(objects_gdf, geo_center, parent_collection_name)

        mesh_obj.hide_render = True
        mesh_obj.hide_viewport = True

    def get_mesh_obj(self):
        return D.objects[self._mesh_name]
