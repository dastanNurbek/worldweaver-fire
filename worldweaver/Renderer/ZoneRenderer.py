from worldweaver.Renderer.HiddenPolygonRenderer import HiddenPolygonRenderer

from worldweaver.Utils.Config import CameraType
from worldweaver.Utils.Rendering import get_camera
from worldweaver.Utils.Utils import Point


class ZoneRenderer(HiddenPolygonRenderer):
    _mesh_name = "Zone"

    def _to_scene_coords(
        self, points_coords: list[Point], geo_center: Point
    ) -> list[Point]:

        # Centering the coordinates so that Blender's internal precision is less impactful,
        centered_points_coords = [
            (
                x[0] - geo_center[0],
                x[1] - geo_center[1],
                get_camera(CameraType.ORTHOGRAPHIC).location[2],
            )
            for x in points_coords
        ]

        return centered_points_coords


class WheatFieldRenderer(ZoneRenderer):
    _mesh_name = "WheatFieldsZone"


class CornFieldRenderer(ZoneRenderer):
    _mesh_name = "CornFieldsZone"


class GrassRenderer(ZoneRenderer):
    _mesh_name = "GrassZone"


class DevelopedRenderer(ZoneRenderer):
    _mesh_name = "DevelopedZone"


class TartanRenderer(ZoneRenderer):
    _mesh_name = "TartanZone"


class CompactedRenderer(ZoneRenderer):
    _mesh_name = "CompactedZone"


class AsphaltRenderer(ZoneRenderer):
    _mesh_name = "AsphaltZone"


class SandRenderer(ZoneRenderer):
    _mesh_name = "SandZone"
