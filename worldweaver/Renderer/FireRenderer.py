import bmesh
from bpy import data as D

from tqdm import tqdm

from worldweaver.Utils.Geometry import interpolate_z, center_point
from worldweaver.Utils.Logging import logger
from worldweaver.Utils.Utils import TerrainData


class FireRenderer:

    _mesh_name = "BurntArea"

    def __init__(self, terrain_data: list[TerrainData], tagging_index: int):
        self._terrain_data = terrain_data
        self._tagging_index = tagging_index

    def render(self, fire_data, geo_center, parent_collection_name):
        is_burnt, lower_left, upper_right, cell_size = fire_data

        mesh = bmesh.new()
        mesh_points = {}

        logger.info("Rendering burnt area")

        for row in tqdm(range(len(is_burnt))):
            for col in range(len(is_burnt[row])):
                if not is_burnt[row][col]:
                    continue

                x0 = lower_left[0] + col * cell_size
                x1 = lower_left[0] + (col + 1) * cell_size
                y0 = upper_right[1] - (row + 1) * cell_size
                y1 = upper_right[1] - row * cell_size

                face_verts = []
                for rx, ry in [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]:
                    key = (rx, ry)
                    if key not in mesh_points:
                        z = interpolate_z(self._terrain_data, rx, ry)
                        mesh_points[key] = mesh.verts.new(
                            center_point((rx, ry, z), geo_center)
                        )
                    face_verts.append(mesh_points[key])

                mesh.faces.new(face_verts)

        mesh_data = D.meshes.new(self._mesh_name)
        self._mesh_name = mesh_data.name
        mesh.to_mesh(mesh_data)
        mesh.free()

        mesh_obj = D.objects.new(self._mesh_name, mesh_data)
        mesh_obj.pass_index = self._tagging_index
        mesh_obj.hide_render = True
        mesh_obj.hide_viewport = True
        D.collections[parent_collection_name].objects.link(mesh_obj)

    def get_mesh_obj(self):
        return D.objects[self._mesh_name]
