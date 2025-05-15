import os

import bpy
import bmesh
from bpy import data as D

import geopandas as g

from shapely.geometry import mapping, MultiPolygon

from tqdm import tqdm

from mage_procgen.Utils.Geometry import interpolate_z
from mage_procgen.Utils.Utils import Point, TerrainData
from mage_procgen.Utils.DataFiles import assets_folder


class BaseRenderer:
    _mesh_name = ""

    def __init__(self, terrain_data: list[TerrainData], object_config):
        self.config = object_config
        _location = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__))
        )
        filepath = os.path.realpath(
            os.path.join(_location, "..", assets_folder, self.config.geometry_node_file)
        )
        try:
            with bpy.data.libraries.load(filepath) as (data_from, data_to):
                data_to.node_groups = [self.config.geometry_node_name]

            # A Geometry Nodes setup with name object_config.geometry_node_name may already exist.
            self.geometry_node_name = data_to.node_groups[0].name

        except Exception as _:
            raise Exception(
                f"Unable to load the Geometry Nodes setup with the name '"
                f"{self.config.geometry_node_name}"
                f"'"
                f" from the file "
                f"{filepath}"
                f". Please check that the name is correct."
            )

        self._terrain_data = terrain_data

    def render(
        self,
        objects_gdf: g.GeoDataFrame,
        geo_center: tuple[float, float, float],
        parent_collection_name,
    ):

        mesh_obj = self._draw_objects(objects_gdf, geo_center, parent_collection_name)

        mesh_obj.pass_index = self.config.tagging_index

        m = mesh_obj.modifiers.new("", "NODES")
        m.name = self.geometry_node_name
        m.node_group = D.node_groups[self.geometry_node_name]

    def _draw_objects(self, objects_gdf, geo_center, parent_collection_name):
        mesh = bmesh.new()

        for object_index in tqdm(objects_gdf.index):

            object_geom = objects_gdf.geometry[object_index]

            if object_geom.is_empty:
                continue

            if type(object_geom) == MultiPolygon:
                for polygon in object_geom.geoms:
                    self.__draw_face(mesh, polygon, geo_center)
            else:
                self.__draw_face(mesh, object_geom, geo_center)

        mesh_data = D.meshes.new(self._mesh_name)
        self._mesh_name = mesh_data.name
        mesh.to_mesh(mesh_data)
        mesh.free()
        mesh_obj = D.objects.new(self._mesh_name, mesh_data)
        D.collections[parent_collection_name].objects.link(mesh_obj)

        return mesh_obj

    def __draw_face(self, mesh, polygon, geo_center):
        # Kind of hack because Polygon.coords is not implemented
        # TODO : shapely.get_coordinates(polygon)
        polygon_geometry = mapping(polygon)["coordinates"]

        if len(polygon_geometry) > 0:
            points_coords = [
                (x[0], x[1], interpolate_z(self._terrain_data, x[0], x[1]))
                for x in polygon_geometry[0]
            ]

            # First getting the list of the edges that make the exterior of the face
            countour_ring = BaseRenderer._add_edge_ring(
                mesh, self._to_scene_coords(points_coords, geo_center)
            )

            if len(polygon_geometry) > 1:
                # If there are holes
                for hole in polygon_geometry[1:]:
                    points_coords_hole = [
                        (x[0], x[1], interpolate_z(self._terrain_data, x[0], x[1]))
                        for x in hole
                    ]

                    # Doing the same for all the holes
                    hole_ring = BaseRenderer._add_edge_ring(
                        mesh, self._to_scene_coords(points_coords_hole, geo_center)
                    )

                    countour_ring.extend(hole_ring)

            # Constructing the face this was will make blender triangulate it and allow us to do faces with holes
            bmesh.ops.triangle_fill(
                mesh, use_beauty=True, use_dissolve=False, edges=countour_ring
            )

    @staticmethod
    def _add_edge_ring(mesh, point_collection):

        edge_collection = []

        if len(point_collection) > 0:
            first_point = mesh.verts.new(point_collection[0])
            previous_point = first_point
            current_point = None
            for point in point_collection[1:-1]:
                current_point = mesh.verts.new(point)
                new_edge = mesh.edges.new([previous_point, current_point])
                edge_collection.append(new_edge)
                previous_point = current_point
            if current_point is not None:
                new_edge = mesh.edges.new([previous_point, first_point])
                edge_collection.append(new_edge)

        return edge_collection

    def _to_scene_coords(
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
