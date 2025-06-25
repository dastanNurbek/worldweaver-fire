from worldweaver.Utils.Utils import Point

from worldweaver.Renderer.BaseRenderer import BaseRenderer


class FlatPolygonRenderer(BaseRenderer):
    def _to_scene_coords(
        self, points_coords: list[Point], geo_center: Point
    ) -> list[Point]:

        # Centering the coordinates so that Blender's internal precision is less impactful
        # Oceans are also drawn at a constant z
        z_min = min([x[2] for x in points_coords])

        centered_points_coords = [
            (x[0] - geo_center[0], x[1] - geo_center[1], z_min - geo_center[2])
            for x in points_coords
        ]

        return centered_points_coords
