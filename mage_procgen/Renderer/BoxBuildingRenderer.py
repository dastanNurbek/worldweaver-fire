from dataclasses import dataclass

import bmesh
from bpy import data as D

import geopandas as g
import pandas as p
import random
from shapely.geometry import mapping, MultiPolygon, Polygon

from tqdm import tqdm

from ladybug_geometry.geometry2d.polygon import Polygon2D
from ladybug_geometry.geometry2d.pointvector import Point2D
from ladybug_geometry_polyskel.polyskel import skeleton_as_edge_list
from ladybug_geometry.triangulation import earcut

from mage_procgen.Renderer.BaseRenderer import BaseRenderer

from mage_procgen.Utils.Geometry import (
    point_2d_almost_equal,
    point_2d_in_collection,
    point_2d_value_in_dict,
    interpolate_z,
)
from mage_procgen.Utils.Logging import logger
from mage_procgen.Utils.Utils import Point, TerrainData
from mage_procgen.Utils.Rendering import additionals_collection_name
from mage_procgen.Utils.RenderingDataFrames import RenderingBuildingDataFrame


class BoxBuildingRenderer(BaseRenderer):
    _mesh_name = "Houses"

    _top_material_name = "Top_Layer_Material"
    _roof_colors = [
        (0.454, 0.260, 0.092, 1),
        (0.454, 0.337, 0.347, 1),
        (0.056, 0.043, 0.044, 1),
        (0.616, 0.182, 0.023, 1),
        (0, 0, 0, 0),
        (0, 0, 0, 0),
    ]

    _wall_colors = [
        (1, 0.510, 0.157, 1),
        (1, 1, 1, 1),
        (1, 0.242, 0.028, 1),
        (0.429, 0.067, 0.030, 1),
        (0.429, 0.067, 0.030, 1),
    ]

    class GeometryCollection:
        def __init__(self):
            # Contains all the edges of the bottom face
            self.bottom_edges_collection = []
            # Contains all the edges of the top face
            self.top_edges_collection = []
            # Contains all the edges of the mockup face
            self.mockup_edges_collection = []
            # Contains the points of the top face that will be used to contruct the base of the roof
            self.top_points_dict = {}

    @dataclass
    class PointGroup:
        bottom_point: bmesh.types.BMVert
        top_point: bmesh.types.BMVert
        mockup_point: bmesh.types.BMVert

    def __init__(self, terrain_data: list[TerrainData], object_config):

        super().__init__(terrain_data, object_config)

        # PBGen does not realize instances of the objects it adds, so they have their own pass index.
        # In order to set it, we have to get the objects that are used by the geometry nodes.
        # We get all collections that are used in the imported geometrynode, and deduce the objects.
        added_collections = []
        for node in D.node_groups[self.geometry_node_name].nodes:
            for input in node.inputs:
                if input.type == "COLLECTION":
                    added_collections.append(input.default_value)

        for collection in set(added_collections):
            for obj in collection.objects:
                obj.pass_index = object_config.tagging_index

    def render(
        self,
        buildings_gdf: g.GeoDataFrame,
        geo_center: tuple[float, float, float],
        parent_collection_name: str,
    ):

        # TODO: Cleanup
        self._mesh_names = []

        for building_index in tqdm(buildings_gdf.index):

            if buildings_gdf.geometry[building_index].is_empty:
                continue

            # TODO: make those parametric
            building_height = random.uniform(2.5, 6)
            # Height of each floor in meters
            floor_height = 3
            if not p.isnull(
                buildings_gdf[RenderingBuildingDataFrame.height][building_index]
            ):
                building_height = float(
                    buildings_gdf[RenderingBuildingDataFrame.height][building_index]
                )
            if not p.isnull(
                buildings_gdf[RenderingBuildingDataFrame.number_floors][building_index]
            ):
                building_height = float(
                    buildings_gdf[RenderingBuildingDataFrame.number_floors][
                        building_index
                    ]
                    * floor_height
                )

            if type(buildings_gdf.geometry[building_index]) == MultiPolygon:
                for polygon in buildings_gdf.geometry[building_index].geoms:
                    self.__draw_building(
                        polygon, geo_center, building_height, parent_collection_name
                    )
            else:
                self.__draw_building(
                    buildings_gdf.geometry[building_index],
                    geo_center,
                    building_height,
                    parent_collection_name,
                )

    def __draw_building(
        self,
        polygon: Polygon,
        geo_center: tuple[float, float, float],
        building_height: float,
        parent_collection_name: str,
    ):
        mesh = bmesh.new()

        # Mockup object used to fix PBGen's issue with complex roofs.
        # Currently PBGen often introduces "holes" in the roof with are seen in the resulting tagging image
        # Simply trying to add another polygon below the roof doesn't work since pbgen deletes it.
        # Instead, we create another mesh and pass it the correct tagging index.
        mesh_top_mockup = bmesh.new()
        # Kind of hack because Polygon.coords is not implemented
        polygon_geometry = mapping(polygon)["coordinates"]

        points_coords_bot = [
            (x[0], x[1], interpolate_z(self._terrain_data, x[0], x[1]))
            for x in polygon_geometry[0]
        ]

        # Buildings have to be perfectly flat.
        # To achieve this we place all the points at the lowest z of the contour points
        z_min = min([x[2] for x in points_coords_bot])
        points_coords_bot = [(x[0], x[1], z_min) for x in points_coords_bot]

        # Coordinates for future computation of straight skeleton
        points_scene_coords_contour_2d = [
            Point2D(x[0] - geo_center[0], x[1] - geo_center[1])
            for x in points_coords_bot
        ]
        points_scene_coords_holes_2d = []

        geometry_parts = BoxBuildingRenderer.__build_geometry_part(
            mesh,
            mesh_top_mockup,
            self._to_scene_coords(points_coords_bot, geo_center),
            building_height,
        )

        if len(polygon_geometry) > 1:
            # If there are holes
            for hole in polygon_geometry[1:]:
                points_coords_hole_bot = [(x[0], x[1], z_min) for x in hole]
                points_coords_hole_2d = [
                    Point2D(x[0] - geo_center[0], x[1] - geo_center[1])
                    for x in points_coords_hole_bot
                ]
                points_scene_coords_holes_2d.append(points_coords_hole_2d)

                geometry_parts_hole = BoxBuildingRenderer.__build_geometry_part(
                    mesh,
                    mesh_top_mockup,
                    self._to_scene_coords(points_coords_hole_bot, geo_center),
                    building_height,
                )

                geometry_parts.bottom_edges_collection.extend(
                    geometry_parts_hole.bottom_edges_collection
                )
                geometry_parts.top_edges_collection.extend(
                    geometry_parts_hole.top_edges_collection
                )
                geometry_parts.mockup_edges_collection.extend(
                    geometry_parts_hole.mockup_edges_collection
                )
                geometry_parts.top_points_dict = {
                    **geometry_parts.top_points_dict,
                    **geometry_parts_hole.top_points_dict,
                }

        bmesh.ops.triangle_fill(
            mesh,
            use_beauty=True,
            use_dissolve=False,
            edges=geometry_parts.bottom_edges_collection,
        )
        bmesh.ops.triangle_fill(
            mesh,
            use_beauty=True,
            use_dissolve=False,
            edges=geometry_parts.top_edges_collection,
        )
        bmesh.ops.triangle_fill(
            mesh_top_mockup,
            use_beauty=True,
            use_dissolve=False,
            edges=geometry_parts.mockup_edges_collection,
        )

        # TODO: add to config
        # 45° is a slope of 1, we want a max slope of 25°
        max_slope = 25 / 45

        # Sometimes one of the point of the skeleton will be very slightly different than the point of the polygon,
        # Which results in 2 entries in the dictionaries, and messes up the rest of the algorithm
        tolerance = 1e-8

        # Building straight skeleton roof
        polygon = Polygon2D.from_shape_with_holes(
            points_scene_coords_contour_2d, points_scene_coords_holes_2d
        )
        straight_skel = skeleton_as_edge_list(polygon)

        # Dict whose key is the point in 2d and the value is the point in 3d
        points_3d = {}
        # Contains all the 2d lines in the roof
        roof_lines = []

        for pt in polygon.vertices:
            points_3d[pt] = (pt.x, pt.y, z_min + building_height)

        for line in polygon.segments:
            roof_lines.append(line)

        roof_lines.extend(straight_skel)

        # Dict containing the 2d points not on the edge of the roof polygon, and the distance and path towards the polygon.
        interior_pts = {}

        for line in straight_skel:

            if not point_2d_in_collection(line.p1, points_3d.keys(), tolerance):
                points_3d[line.p1] = (
                    line.p1.x,
                    line.p1.y,
                    z_min + building_height,
                )
            if not point_2d_in_collection(line.p2, points_3d.keys(), tolerance):
                points_3d[line.p2] = (
                    line.p2.x,
                    line.p2.y,
                    z_min + building_height,
                )
            if not point_2d_in_collection(
                line.p1, polygon.vertices, tolerance
            ) and not point_2d_in_collection(line.p1, interior_pts, tolerance):
                interior_pts[line.p1] = self.__compute_shortest_path_tree(
                    line.p1, polygon.vertices, roof_lines, tolerance
                )
            if not point_2d_in_collection(
                line.p2, polygon.vertices, tolerance
            ) and not point_2d_in_collection(line.p2, interior_pts, tolerance):
                interior_pts[line.p2] = self.__compute_shortest_path_tree(
                    line.p2, polygon.vertices, roof_lines, tolerance
                )

        # Ordering the interior points by shortest path length to polygon shell.
        # This is to ensure that no segment goes beyond the slope limit
        orderer_pts = list(interior_pts.keys())
        orderer_pts.sort(key=lambda x: interior_pts[x][0])
        for pt in orderer_pts:
            # Last point is the origin, point before that is the other point of the line in the shortest path
            line_other_point = interior_pts[pt][1][-2]
            point_parent_3d = point_2d_value_in_dict(
                line_other_point, points_3d, tolerance
            )
            line_length = pt.distance_to_point(line_other_point)
            # Once we have the segment on which the point is, we can deduce its z coordinate
            d_z = line_length * max_slope
            points_3d[pt] = (pt.x, pt.y, point_parent_3d[2] + d_z)

        verts_dict = {}
        for p2d, p3d in points_3d.items():
            if p2d not in geometry_parts.top_points_dict:
                vert = mesh.verts.new((p3d[0], p3d[1], p3d[2]))
            else:
                vert = geometry_parts.top_points_dict[p2d]
            verts_dict[p2d] = vert

        for line in polygon.segments:
            graph = []
            for graph_line in roof_lines:
                if graph_line != line:
                    graph.append(graph_line)

            face_path = []
            face_path = self.__compute_shortest_path_tree(
                line.p1, [line.p2], graph, tolerance
            )[1]

            # PBGen does not work for faces that are not perfectly flat, meaning we have to triangulate our faces.
            path_flat_array = []
            for point in face_path:
                path_flat_array.extend([point.x, point.y])

            triangles_flat = earcut(path_flat_array)
            triangles = []
            end = len(triangles_flat)
            step = 3
            for tri_ind in range(0, end, step):
                triangles.append(triangles_flat[tri_ind : tri_ind + step])
            try:
                # Sometimes due to bad geometry we will try to create the same face more than once,
                # Which results in an error. We filter and swallow this exact error
                # because it happens only a few time in a scene and is completely benign.
                for triangle in triangles:
                    triangle_pts = [face_path[x] for x in triangle]
                    triangle_face = mesh.faces.new(
                        [
                            point_2d_value_in_dict(x, verts_dict, tolerance)
                            for x in triangle_pts
                        ]
                    )
            except ValueError as e:
                if not str(e) == "faces.new(verts): face already exists":
                    raise e

        mesh_name = self._mesh_name
        mesh_data = D.meshes.new(mesh_name)
        mesh.to_mesh(mesh_data)
        mesh.free()
        mesh_obj = D.objects.new(mesh_data.name, mesh_data)
        mesh_obj.pass_index = self.config.tagging_index
        D.collections[parent_collection_name].objects.link(mesh_obj)

        self._mesh_names.append(mesh_obj.name)

        m = mesh_obj.modifiers.new("", "NODES")
        m.node_group = D.node_groups[self.geometry_node_name]

        # Changing colors of house
        wall_color_index = random.randint(0, len(self._wall_colors) - 1)
        m["Input_11"][0] = self._wall_colors[wall_color_index][0]
        m["Input_11"][1] = self._wall_colors[wall_color_index][1]
        m["Input_11"][2] = self._wall_colors[wall_color_index][2]
        m["Input_11"][3] = self._wall_colors[wall_color_index][3]

        roof_color_index = random.randint(0, len(self._roof_colors) - 1)
        m["Input_13"][0] = self._roof_colors[roof_color_index][0]
        m["Input_13"][1] = self._roof_colors[roof_color_index][1]
        m["Input_13"][2] = self._roof_colors[roof_color_index][2]
        m["Input_13"][3] = self._roof_colors[roof_color_index][3]

        mesh_data_top = D.meshes.new(mesh_name + "_Top")
        mesh_top_mockup.to_mesh(mesh_data_top)
        mesh_top_mockup.free()
        mesh_obj_top = D.objects.new(mesh_data_top.name, mesh_data_top)
        mesh_obj_top.pass_index = self.config.tagging_index
        D.collections[additionals_collection_name].objects.link(mesh_obj_top)

        # Dark grey material so that the top layer is not very visible
        if self._top_material_name not in D.materials:
            top_material = D.materials.new(self._top_material_name)
            top_material.diffuse_color[0] = 0.05
            top_material.diffuse_color[1] = 0.05
            top_material.diffuse_color[2] = 0.05

        mesh_obj_top.data.materials.append(D.materials[self._top_material_name])

        self._mesh_names.append(mesh_obj_top.name)

    @staticmethod
    def __build_geometry_part(
        building_mesh, mockup_mesh, point_collection, building_height
    ) -> GeometryCollection:

        geometry_collection = BoxBuildingRenderer.GeometryCollection()

        if len(point_collection) > 0:
            # Point in bottom face has the same coordinates as the points in point_collection.
            # Points in top face and mockup are shifted along +z by building_height
            first_points = BoxBuildingRenderer.PointGroup(
                bottom_point=building_mesh.verts.new(point_collection[0]),
                top_point=building_mesh.verts.new(
                    (
                        point_collection[0][0],
                        point_collection[0][1],
                        point_collection[0][2] + building_height,
                    )
                ),
                mockup_point=mockup_mesh.verts.new(
                    (
                        point_collection[0][0],
                        point_collection[0][1],
                        point_collection[0][2] + building_height,
                    )
                ),
            )
            geometry_collection.top_points_dict[
                Point2D(point_collection[0][0], point_collection[0][1])
            ] = first_points.top_point
            previous_points = first_points
            current_points = None
            for point in point_collection[1:-1]:
                current_points = BoxBuildingRenderer.PointGroup(
                    bottom_point=building_mesh.verts.new(point),
                    top_point=building_mesh.verts.new(
                        (point[0], point[1], point[2] + building_height)
                    ),
                    mockup_point=mockup_mesh.verts.new(
                        (point[0], point[1], point[2] + building_height)
                    ),
                )
                geometry_collection.top_points_dict[
                    Point2D(point[0], point[1])
                ] = current_points.top_point
                new_edges = (
                    building_mesh.edges.new(
                        [previous_points.bottom_point, current_points.bottom_point]
                    ),
                    building_mesh.edges.new(
                        [previous_points.top_point, current_points.top_point]
                    ),
                    mockup_mesh.edges.new(
                        [previous_points.mockup_point, current_points.mockup_point]
                    ),
                )

                geometry_collection.bottom_edges_collection.append(new_edges[0])
                geometry_collection.top_edges_collection.append(new_edges[1])
                geometry_collection.mockup_edges_collection.append(new_edges[2])

                # Building walls
                wall_points = [
                    previous_points.bottom_point,
                    current_points.bottom_point,
                    current_points.top_point,
                    previous_points.top_point,
                ]
                wall_face = building_mesh.faces.new(wall_points)

                previous_points = current_points
            if current_points is not None:
                new_edges = (
                    building_mesh.edges.new(
                        [previous_points.bottom_point, first_points.bottom_point]
                    ),
                    building_mesh.edges.new(
                        [previous_points.top_point, first_points.top_point]
                    ),
                    mockup_mesh.edges.new(
                        [previous_points.mockup_point, first_points.mockup_point]
                    ),
                )
                geometry_collection.bottom_edges_collection.append(new_edges[0])
                geometry_collection.top_edges_collection.append(new_edges[1])
                geometry_collection.mockup_edges_collection.append(new_edges[2])

                # Building last wall
                wall_points = [
                    previous_points.bottom_point,
                    first_points.bottom_point,
                    first_points.top_point,
                    previous_points.top_point,
                ]
                wall_face = building_mesh.faces.new(wall_points)

        return geometry_collection

    def clear_object(self):

        for object_name in self._mesh_names:
            D.objects.remove(D.objects[object_name], do_unlink=True)
            D.meshes.remove(D.meshes[object_name], do_unlink=True)

    def __compute_shortest_path_tree(self, origin, destinations, graph, tolerance):
        """
        Shortest path in a 2D graph where the weight of an edge is its length.
        Based on https://www.youtube.com/watch?v=w8oM3cSEQsk
        :param origin: Origin 2D point
        :param destinations: List of 2D points that are valid destinations
        :param graph: List of 2D segments that constitute the graph
        :param tolerance: Geometric tolerance for point equality
        :return: The length of the path to the destination, and a list of the points visited.
        """
        trace_msg = []
        trace_msg.append(
            f"Trying to find path between "
            f"{origin}"
            f" and "
            f"{destinations}"
            f" inside "
            f"{graph}"
        )
        exploration_queue = []
        nodes_status = {}
        exploration_queue.append(origin)
        nodes_status[origin] = (True, 0, None)
        while len(exploration_queue) > 0:
            v = exploration_queue[0]
            # Find the node to explore with the lowest cost
            for pt in exploration_queue:
                if nodes_status[pt][1] < nodes_status[v][1]:
                    v = pt
            trace_msg.append(f"Exploring node {v}")
            exploration_queue.remove(v)
            if point_2d_in_collection(v, destinations, tolerance):
                trace_msg.append(f"Found point in destination: {v}")
                path = []
                current_point = v
                while current_point != origin:
                    path.append(current_point)
                    current_point = nodes_status[current_point][2]
                path.append(current_point)
                # Return the length of the total path to destination, and the path
                return nodes_status[v][1], path
            possibles_edges = []
            for line in graph:
                if point_2d_almost_equal(
                    line.p1, v, tolerance
                ) or point_2d_almost_equal(line.p2, v, tolerance):
                    trace_msg.append(f"Adding line {line}")
                    possibles_edges.append(line)
            for line in possibles_edges:
                new_point = (
                    line.p2 if point_2d_almost_equal(line.p1, v, tolerance) else line.p1
                )
                trace_msg.append(f"Evaluating new point {new_point}")
                if new_point in nodes_status:
                    # If new_point already has been seen
                    if nodes_status[v][1] + line.length < nodes_status[new_point][1]:
                        # If we found a shorter path
                        trace_msg.append("Shortening new point path")
                        nodes_status[new_point] = (
                            True,
                            nodes_status[v][1] + line.length,
                            v,
                        )
                else:
                    trace_msg.append("Adding new point to queue")
                    nodes_status[new_point] = (
                        True,
                        nodes_status[v][1] + line.length,
                        v,
                    )
                    exploration_queue.append(new_point)
        logger.error(
            "BoxBuildingGenerator.__compute_shortest_path_tree: Couldn't find a path. Execution details:"
        )
        for msg in trace_msg:
            logger.error(msg)
