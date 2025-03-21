from mage_procgen.Renderer.BaseRenderer import BaseRenderer
from bpy import data as D
import bmesh
from shapely.geometry import mapping, MultiLineString
from tqdm import tqdm
from mage_procgen.Utils.Utils import TerrainData
from mage_procgen.Utils.Geometry import interpolate_z


class HiddenPolygonRenderer(BaseRenderer):
    _mesh_name = "HiddenObject"

    def __init__(self, terrain_data: list[TerrainData]):

        self._terrain_data = terrain_data

    def render(
        self,
        objects: list,
        geo_center: tuple[float, float, float],
        parent_collection_name,
    ):

        mesh = bmesh.new()

        for object in tqdm(objects):

            # Kind of hack because Polygon.coords is not implemented
            polygon_geometry = mapping(object)["coordinates"]

            if len(polygon_geometry) == 0:
                continue

            points_coords = [
                (x[0], x[1], interpolate_z(self._terrain_data, x[0], x[1]))
                for x in polygon_geometry[0]
            ]

            if len(polygon_geometry) > 1:
                # If there are holes
                for hole in polygon_geometry[1:]:
                    points_coords_hole = [
                        (x[0], x[1], interpolate_z(self._terrain_data, x[0], x[1]))
                        for x in hole
                    ]

                    points_coords = self.insert_hole(points_coords, points_coords_hole)

            # Adapting the coordinates for rendering purposes
            centered_points_coords = self.adapt_coords(points_coords, geo_center)

            # Need to remove the last point so that it's not repeated and creates a segment of 0 length
            face = mesh.faces.new(
                mesh.verts.new(x) for x in centered_points_coords[:-1]
            )

        mesh_data = D.meshes.new(self._mesh_name)
        self._mesh_name = mesh_data.name
        mesh.to_mesh(mesh_data)
        mesh.free()
        mesh_obj = D.objects.new(self._mesh_name, mesh_data)
        D.collections[parent_collection_name].objects.link(mesh_obj)

        mesh_obj.hide_render = True
        mesh_obj.hide_viewport = True

    def get_mesh_obj(self):
        return D.objects[self._mesh_name]
