from bpy import data as D

from mage_procgen.Renderer.BaseRenderer import BaseRenderer

from mage_procgen.Utils.Rendering import get_camera, CameraType
from mage_procgen.Utils.Utils import Point


class ForestRenderer(BaseRenderer):
    _mesh_name = "Forest"

    def __config_geometry_node(
        self, road_object, building_object, terrain_object, ray_length
    ):
        # Forests' geometry node requires references to other Blender objects present in the scene,
        # so this method needs to be called by the RenderManager whose responsibility is to be aware of the context of the whole scene
        node = D.objects[self._mesh_name].modifiers[self.geometry_node_name]
        node["Socket_4"] = road_object
        node["Socket_6"] = building_object
        node["Socket_8"] = terrain_object
        node["Socket_3"] = ray_length

    def _to_scene_coords(
        self, points_coords: list[Point], geo_center: Point
    ) -> list[Point]:

        # Centering the coordinates so that Blender's internal precision is less impactful,
        # But putting the Z location high up so that the trees can be projected onto the terrain by the geometrynode
        centered_points_coords = [
            (
                x[0] - geo_center[0],
                x[1] - geo_center[1],
                get_camera(CameraType.Camera_Ortho).location[2],
            )
            for x in points_coords
        ]

        return centered_points_coords
