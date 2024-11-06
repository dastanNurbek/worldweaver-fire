import os
import bpy
from bpy import data as D
import bmesh
from shapely.geometry import mapping
from tqdm import tqdm
import math
from collections import deque
from mage_procgen.Utils.Utils import PolygonList, Point, TerrainData
from mage_procgen.Utils.Geometry import interpolate_z


class BaseRenderer:
    _AssetsFolder = "Assets"
    _mesh_name = ""

    def __init__(self, terrain_data: list[TerrainData], object_config):
        self.config = object_config
        _location = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__))
        )
        filepath = os.path.realpath(
            os.path.join(
                _location, "..", self._AssetsFolder, self.config.geometry_node_file
            )
        )
        try:
            with bpy.data.libraries.load(filepath) as (data_from, data_to):
                data_to.node_groups = [self.config.geometry_node_name]

            # A Geometry Nodes setup with name object_config.geometry_node_name may already exist.
            self.geometry_node_name = data_to.node_groups[0].name

        except Exception as _:
            raise Exception(
                'Unable to load the Geometry Nodes setup with the name "'
                + self.config.geometry_node_name
                + '"'
                + "from the file "
                + filepath
                + " . Please check that the name is correct."
            )

        self._terrain_data = terrain_data

    def render(
        self,
        polygons: PolygonList,
        geo_center: tuple[float, float, float],
        parent_collection_name,
    ):
        mesh = bmesh.new()

        for polygon in tqdm(polygons):
            # Kind of hack because Polygon.coords is not implemented
            polygon_geometry = mapping(polygon)["coordinates"]
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
        mesh_obj.pass_index = self.config.tagging_index
        D.collections[parent_collection_name].objects.link(mesh_obj)

        m = mesh_obj.modifiers.new("", "NODES")
        m.name = self.geometry_node_name
        m.node_group = D.node_groups[self.geometry_node_name]

    def insert_hole(
        self, points_coords: list[Point], points_coords_hole: list[Point]
    ) -> list[Point]:
        min_dist = math.inf
        closest_pt_poly = None
        closest_pt_hole = None

        # Last point is always repeated to close the polygon/hole
        unique_points_coords = points_coords[:-1]
        unique_points_coords_hole = points_coords_hole[:-1]

        # Finding the closest distance between the poly and the hole, and associated points
        for pt_poly in unique_points_coords:
            for pt_hole in unique_points_coords_hole:
                distance = math.dist(pt_poly, pt_hole)
                if distance < min_dist:
                    min_dist = distance
                    closest_pt_poly = pt_poly
                    closest_pt_hole = pt_hole

        # Making the closest point of the hole the first in the list
        rotation_index = -unique_points_coords_hole.index(closest_pt_hole)
        deq = deque(unique_points_coords_hole)
        deq.rotate(rotation_index)
        rotated_hole = list(deq)

        # Splitting the orignal polygon at the correct index
        insertion_index = unique_points_coords.index(closest_pt_poly) + 1
        poly_first_part = unique_points_coords[:insertion_index]
        poly_second_part = unique_points_coords[insertion_index:]

        # Fusing the polygon with the hole
        toreturn = []
        toreturn.extend(poly_first_part)
        toreturn.extend(rotated_hole)
        toreturn.append(closest_pt_hole)
        toreturn.append(closest_pt_poly)
        toreturn.extend(poly_second_part)
        toreturn.append(poly_first_part[0])

        return toreturn

    def adapt_coords(
        self, points_coords: list[Point], geo_center: Point
    ) -> list[Point]:

        # Centering the coordinates so that Blender's internal precision is less impactful
        centered_points_coords = [
            (x[0] - geo_center[0], x[1] - geo_center[1], x[2] - geo_center[2])
            for x in points_coords
        ]

        return centered_points_coords

    def clear_object(self):

        D.objects.remove(D.objects[self._mesh_name], do_unlink=True)
        D.meshes.remove(D.meshes[self._mesh_name], do_unlink=True)
