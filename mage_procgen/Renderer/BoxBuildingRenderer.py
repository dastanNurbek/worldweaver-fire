import math

from mage_procgen.Renderer.BaseRenderer import BaseRenderer
from bpy import data as D, context as C
import bmesh
from shapely.geometry import mapping
from tqdm import tqdm
from mage_procgen.Utils.Utils import BuildingList, Point, TerrainData
import os
import bpy

from mage_procgen.Utils.Geometry import (
    point_2d_almost_equal,
    point_2d_in_collection,
    point_2d_value_in_dict,
)
from ladybug_geometry.geometry2d.polygon import Polygon2D
from ladybug_geometry.geometry2d.pointvector import Point2D
from ladybug_geometry.geometry2d.line import LineSegment2D
from ladybug_geometry_polyskel.polyskel import skeleton_as_edge_list
from ladybug_geometry.triangulation import earcut

import random


class BoxBuildingRenderer(BaseRenderer):
    _mesh_name = "Houses"

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

        self._terrain_data = terrain_data

    def render(
        self,
        buildings: BuildingList,
        geo_center: tuple[float, float, float],
        parent_collection_name,
    ):
        # TODO: Cleanup
        self._mesh_names = []

        for building in tqdm(buildings):
            mesh = bmesh.new()
            # Kind of hack because Polygon.coords is not implemented

            polygon_geometry = mapping(building[1])["coordinates"]
            points_coords = [
                (x[0], x[1], self.interpolate_z(x[0], x[1]))
                for x in polygon_geometry[0]
            ]

            if len(polygon_geometry) > 1:
                # If there are holes
                for hole in polygon_geometry[1:]:
                    points_coords_hole = [
                        (x[0], x[1], self.interpolate_z(x[0], x[1])) for x in hole
                    ]

                    points_coords = self.insert_hole(points_coords, points_coords_hole)

            # Adapting the coordinates for rendering purposes
            centered_points_coords = self.adapt_coords(points_coords, geo_center)

            # Need to remove the last point so that it's not repeated and creates a segment of 0 length
            face_bot = mesh.faces.new(
                mesh.verts.new(x) for x in centered_points_coords[:-1]
            )

            # TODO: make those parametric
            building_height = random.uniform(2.5, 6)
            # If we have the info in the database, use it here
            if not math.isnan(building[0]):
                building_height = float(building[0])

            # 45° is a slope of 1, we want a max slope of 25°
            max_slope = 25 / 45

            # Sometimes one of the point of the skeleton will be very slightly different than the point of the polygon,
            # Which results in 2 entries in the dictionaries, and messes up the rest of the algorithm
            digit_precision = 8
            tolerance = math.pow(10, -digit_precision)

            quit_after_loop = False
            # Building straight skeleton roof
            # TODO: find out if rounding is necessary. Should not be, but a segfault was observed on the first run after
            #   it was disabled (only the first so far, others ran fine)
            polygon_points = [
                # Point2D(round(x[0], digit_precision), round(x[1], digit_precision))
                Point2D(x[0], x[1])
                for x in centered_points_coords[:-1]
            ]
            polygon = Polygon2D(polygon_points)
            straight_skel = skeleton_as_edge_list(polygon)
            # straight_skel_rounded = []
            # for line in straight_skel:
            #     new_line = LineSegment2D.from_end_points(
            #         Point2D(
            #             round(line.p1.x, digit_precision),
            #             round(line.p1.y, digit_precision),
            #         ),
            #         Point2D(
            #             round(line.p2.x, digit_precision),
            #             round(line.p2.y, digit_precision),
            #         ),
            #     )
            #     straight_skel_rounded.append(new_line)
            #
            # straight_skel = straight_skel_rounded
            roof_mesh = bmesh.new()
            roof_mesh_name = "Roof"
            roof_mesh_data = bpy.data.meshes.new(roof_mesh_name)

            base_height = centered_points_coords[0][2]
            # Dict whose key is the point in 2d and the value is the point in 3d
            points_3d = {}
            # Contains all the 2d lines in the roof
            roof_lines = []

            for pt in polygon.vertices:
                points_3d[pt] = (pt.x, pt.y, base_height + building_height)

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
                        base_height + building_height,
                    )
                if not point_2d_in_collection(line.p2, points_3d.keys(), tolerance):
                    points_3d[line.p2] = (
                        line.p2.x,
                        line.p2.y,
                        base_height + building_height,
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
                vert = roof_mesh.verts.new((p3d[0], p3d[1], p3d[2]))
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
                    # Which results in an error. We're keeping this simple try except with minimal trace to monitor
                    # TODO: Test more and decide what to do of this case
                    for triangle in triangles:
                        triangle_pts = [face_path[x] for x in triangle]
                        triangle_face = roof_mesh.faces.new(
                            [
                                point_2d_value_in_dict(x, verts_dict, tolerance)
                                for x in triangle_pts
                            ]
                        )
                except Exception as e:
                    print("Error trying to add face inside roof " + roof_mesh_data.name)
                    print(str(e))

            roof_mesh.to_mesh(roof_mesh_data)
            roof_mesh.free()
            roof_mesh_obj = bpy.data.objects.new(roof_mesh_data.name, roof_mesh_data)
            bpy.data.collections[parent_collection_name].objects.link(roof_mesh_obj)

            # Building the walls
            previous_point = None
            for point in centered_points_coords:
                if previous_point is None:
                    previous_point = point
                else:

                    wall_points = [
                        previous_point,
                        point,
                        (point[0], point[1], point[2] + building_height),
                        (
                            previous_point[0],
                            previous_point[1],
                            previous_point[2] + building_height,
                        ),
                    ]

                    wall_face = mesh.faces.new(mesh.verts.new(x) for x in wall_points)
                    previous_point = point

            mesh_name = self._mesh_name
            mesh_data = D.meshes.new(mesh_name)
            mesh.to_mesh(mesh_data)
            mesh.free()
            mesh_obj = D.objects.new(mesh_data.name, mesh_data)
            mesh_obj.pass_index = self.config.tagging_index
            D.collections[parent_collection_name].objects.link(mesh_obj)

            self._mesh_names.append(mesh_obj.name)

            # Fuse roof and walls
            bpy.ops.object.select_all(action="DESELECT")
            mesh_obj.select_set(True)
            C.view_layer.objects.active = mesh_obj
            roof_mesh_obj.select_set(True)
            bpy.ops.object.join()
            bpy.ops.object.select_all(action="DESELECT")

            m = mesh_obj.modifiers.new("", "NODES")
            m.node_group = D.node_groups[self.geometry_node_name]


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
            "Trying to find path between "
            + str(origin)
            + " and "
            + str(destinations)
            + " inside "
            + str(graph)
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
            trace_msg.append("Exploring node " + str(v))
            exploration_queue.remove(v)
            if point_2d_in_collection(v, destinations, tolerance):
                trace_msg.append("Found point in destination: " + str(v))
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
                    trace_msg.append("Adding line " + str(line))
                    possibles_edges.append(line)
            for line in possibles_edges:
                new_point = (
                    line.p2 if point_2d_almost_equal(line.p1, v, tolerance) else line.p1
                )
                trace_msg.append("Evaluating new point " + str(new_point))
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
        print("ERROR")
        print("Couldn't find a path")
        for msg in trace_msg:
            print(msg)
        print()
        print()
