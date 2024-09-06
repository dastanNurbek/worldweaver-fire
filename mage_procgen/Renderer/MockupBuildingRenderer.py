from mage_procgen.Renderer.BaseRenderer import BaseRenderer
from bpy import data as D
import bmesh
from shapely.geometry import mapping
from tqdm import tqdm
from mage_procgen.Utils.Utils import BuildingList, Point, TerrainData
from mage_procgen.Utils.Geometry import interpolate_z


class MockupBuildingRenderer(BaseRenderer):
    _mesh_name = "Mockup_Buildings"

    def __init__(self, terrain_data: list[TerrainData]):

        self._terrain_data = terrain_data

    def render(
        self,
        buildings: BuildingList,
        geo_center: tuple[float, float, float],
        parent_collection_name,
    ):

        mesh = bmesh.new()

        for building in tqdm(buildings):

            # Kind of hack because Polygon.coords is not implemented
            polygon_geometry = mapping(building)["coordinates"]
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

        mesh_name = self._mesh_name
        mesh_data = D.meshes.new(mesh_name)
        mesh.to_mesh(mesh_data)
        mesh.free()
        mesh_obj = D.objects.new(mesh_data.name, mesh_data)
        D.collections[parent_collection_name].objects.link(mesh_obj)

        mesh_obj.hide_render = True
        mesh_obj.hide_viewport = True

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

    def get_mesh_obj(self):
        return D.objects[self._mesh_name]
