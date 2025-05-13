from mage_procgen.Renderer.HiddenLineRenderer import HiddenLineRenderer

from mage_procgen.Utils.Utils import Point
from mage_procgen.Utils.Rendering import get_camera, CameraType


class LineZoneRenderer(HiddenLineRenderer):
    _mesh_name = "LineZone"

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


class PathRenderer(LineZoneRenderer):
    _mesh_name = "PathLineZone"
