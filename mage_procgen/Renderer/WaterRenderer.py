from bpy import data as D

from mage_procgen.Utils.Utils import Point

from mage_procgen.Renderer.BaseRenderer import BaseRenderer


class StillWaterRenderer(BaseRenderer):
    _mesh_name = "Still_Water"

    def get_mesh_obj(self):
        return D.objects[self._mesh_name]

    def adapt_coords(
        self, points_coords: list[Point], geo_center: Point
    ) -> list[Point]:

        # Centering the coordinates so that Blender's internal precision is less impactful
        # Also, building rendering requires the base polygon to have constant z, so we fix every point's z to be the lowest in the set.
        z_min = min([x[2] for x in points_coords])

        centered_points_coords = [
            (x[0] - geo_center[0], x[1] - geo_center[1], z_min - geo_center[2])
            for x in points_coords
        ]

        return centered_points_coords


class FlowingWaterRenderer(BaseRenderer):
    _mesh_name = "Flowing_Water"

    def get_mesh_obj(self):
        return D.objects[self._mesh_name]


class OceanRenderer(BaseRenderer):
    _mesh_name = "Ocean_Water"

    def get_mesh_obj(self):
        return D.objects[self._mesh_name]

    def adapt_coords(
        self, points_coords: list[Point], geo_center: Point
    ) -> list[Point]:

        # Centering the coordinates so that Blender's internal precision is less impactful
        # Also, building rendering requires the base polygon to have constant z, so we fix every point's z to be the lowest in the set.
        z_min = min([x[2] for x in points_coords])

        centered_points_coords = [
            (x[0] - geo_center[0], x[1] - geo_center[1], z_min - geo_center[2])
            for x in points_coords
        ]

        return centered_points_coords
