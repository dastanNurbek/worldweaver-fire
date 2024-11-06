from bpy import data as D

from mage_procgen.Renderer.HiddenObjectRenderer import HiddenObjectRenderer
from mage_procgen.Utils.Rendering import ortho_camera_name
from mage_procgen.Utils.Utils import Point


class ZoneRenderer(HiddenObjectRenderer):
    _mesh_name = "Zone"

    # def config_geometry_node(
    #     self, road_object, building_object, terrain_object, ray_length
    # ):
    #     pass

    def adapt_coords(
        self, points_coords: list[Point], geo_center: Point
    ) -> list[Point]:

        # Centering the coordinates so that Blender's internal precision is less impactful,
        # But putting the Z location high up so that the trees can be projected onto the terrain by the geometrynode
        centered_points_coords = [
            (
                x[0] - geo_center[0],
                x[1] - geo_center[1],
                D.objects[ortho_camera_name].location[2],
            )
            for x in points_coords
        ]

        return centered_points_coords


class FieldsRenderer(ZoneRenderer):
    _mesh_name = "Fields"


class GrassRenderer(ZoneRenderer):
    _mesh_name = "Grass"


class DevelopedRenderer(ZoneRenderer):
    _mesh_name = "Developed"
