import os
import bpy
import geopandas as g
from bpy import data as D, ops as O, context as C
import bmesh
import math

from tqdm import tqdm
from mage_procgen.Utils.Utils import (
    PolygonList,
    Point,
    TerrainData,
    LineStringList,
    GeoWindow,
)
from ladybug_geometry.geometry2d.pointvector import Point2D

# TODO: find common paths with BaseRenderer
class PrettyRoadRenderer:
    _AssetsFolder = "Assets"
    _mesh_name = "Roads"
    _car_mesh_name = "Cars"

    _Asset_File = "Roads_pretty_3.blend"
    _GN_Name = "Next_Streets_V3_custom_cars"
    _car_collection_info_node_name = "Cars Collection Info"

    _Largeur = "LARGEUR"
    _NB_Voies = "NB_VOIES"
    _Sens = "SENS"
    _Pos_Sol = "POS_SOL"
    _has_sidewalks = "has_sidewalks"
    _has_guardrails = "has_guardrails"
    _Directions = ["Double sens", "Sens direct", "Sens inverse"]

    _default_road_thickness = 3
    _default_road_lanes = 1

    def __init__(
        self, terrain_data: list[TerrainData], object_config, car_object_config
    ):
        self.config = object_config
        self.car_config = car_object_config
        _location = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__))
        )
        filepath = os.path.realpath(
            os.path.join(_location, "..", self._AssetsFolder, self._Asset_File)
        )
        try:
            with bpy.data.libraries.load(filepath) as (data_from, data_to):
                data_to.node_groups = [self._GN_Name]

            # A Geometry Nodes setup with name object_config.geometry_node_name may already exist.
            self.geometry_node_name = data_to.node_groups[0].name

        except Exception as _:
            raise Exception(
                'Unable to load the Geometry Nodes setup with the name "'
                + self._GN_Name
                + '"'
                + "from the file "
                + filepath
                + " . Please check that the name is correct."
            )

        self._terrain_data = terrain_data

        # Setting pass index of cars
        cars_collection = (
            D.node_groups[self.geometry_node_name]
            .nodes[self._car_collection_info_node_name]
            .inputs[0]
            .default_value
        )
        for obj in cars_collection.objects:
            obj.pass_index = car_object_config.tagging_index

    def render(
        self,
        roads: g.GeoDataFrame,
        geo_window: GeoWindow,
        parent_collection_name: str,
    ):
        mesh = bmesh.new()

        geo_center = geo_window.center

        # Storing the points inside a dict to avoid point duplication, which messes up crossroads
        # TODO: check that this method works and does not need "fuzzy matching"
        points_dict = {}

        edges_config = {}
        edge_index = 0
        for road_index in tqdm(roads.index):

            road_geom = roads.geometry[road_index]

            # Windowing
            windowed_line = []
            for point in road_geom.coords:

                if (
                    geo_window.bounds[0] < point[0] < geo_window.bounds[2]
                    and geo_window.bounds[1] < point[1] < geo_window.bounds[3]
                ):
                    windowed_line.append(point)

            if len(windowed_line) == 0:
                continue

            points_coords = [
                (x[0], x[1], self.interpolate_z(x[0], x[1])) for x in windowed_line
            ]

            # Adapting the coordinates for rendering purposes
            centered_points_coords = self.adapt_coords(points_coords, geo_center)

            previous_point_2d = Point2D(
                centered_points_coords[0][0], centered_points_coords[0][1]
            )
            if previous_point_2d not in points_dict:
                previous_point = mesh.verts.new(centered_points_coords[0])
                points_dict[previous_point_2d] = previous_point
            else:
                previous_point = points_dict[previous_point_2d]
            for i in range(1, len(points_coords)):

                new_point_2d = Point2D(
                    centered_points_coords[i][0], centered_points_coords[i][1]
                )
                if new_point_2d not in points_dict:
                    new_point = mesh.verts.new(centered_points_coords[i])
                    points_dict[new_point_2d] = new_point
                else:
                    new_point = points_dict[new_point_2d]

                edge = mesh.edges.new([previous_point, new_point])

                edges_config[edge_index] = (
                    roads[self._has_sidewalks][road_index],
                    roads[self._has_guardrails][road_index],
                    roads[self._NB_Voies][road_index],
                )

                previous_point = new_point
                edge_index += 1

        mesh_name = self._mesh_name
        mesh_data = D.meshes.new(mesh_name)
        mesh.to_mesh(mesh_data)
        mesh.free()
        mesh_obj = D.objects.new(mesh_data.name, mesh_data)
        mesh_obj.pass_index = self.config.tagging_index
        D.collections[parent_collection_name].objects.link(mesh_obj)

        m = mesh_obj.modifiers.new("", "NODES")
        m.node_group = D.node_groups[self.geometry_node_name]

        # Setting up named attributes used to pilot the geometryNode.
        # Everything has to be done in edit mode otherwise attribute names get mixed up
        # TODO: improve these settings to have finer control of the geometrynodes
        mesh_obj.select_set(True)
        C.view_layer.objects.active = mesh_obj
        O.object.mode_set(mode="EDIT")
        mesh_data = D.objects[mesh_name].data
        attribute_lane_nbr = mesh_data.attributes.new(
            name="street type", type="INT", domain="EDGE"
        )
        attribute_sidewalk_type = mesh_data.attributes.new(
            name="switch side walk", type="INT", domain="EDGE"
        )
        attribute_intersection_type = mesh_data.attributes.new(
            name="intersection type", type="INT", domain="POINT"
        )
        bm = bmesh.from_edit_mesh(mesh_data)
        layer_lane_nbr = bm.edges.layers.int.get(attribute_lane_nbr.name)
        layer_sidewalk_type = bm.edges.layers.int.get(attribute_sidewalk_type.name)
        layer_intersection_type = bm.verts.layers.int.get(
            attribute_intersection_type.name
        )
        for ed in bm.edges:

            edge_config = edges_config[ed.index]

            lane_nbr = (
                self._default_road_lanes
                if math.isnan(edge_config[2])
                else int(edge_config[2])
            )

            # Not a very good name but it's there to separate 1*1 roads vs 2*2
            # TODO: currently, nextstreet cannt handle single way roads.
            #  If we find out a way to make it work, change this by taking road direction into account
            total_lane_nbr = max(lane_nbr // 2, self._default_road_lanes)

            # TODO: correlate lane_nbr and road_width to "street type"
            ed[layer_lane_nbr] = total_lane_nbr

            sidewalk_type = 2
            if edge_config[0]:
                sidewalk_type = 0
            elif edge_config[1]:
                sidewalk_type = 1

            ed[layer_sidewalk_type] = sidewalk_type

            # For intersections, no sidewalk has priority over guardrails, who has priority over sidewalks
            for vert in ed.verts:
                vert[layer_intersection_type] = max(
                    vert[layer_intersection_type], sidewalk_type
                )

        bmesh.update_edit_mesh(mesh_data)

        O.object.mode_set(mode="OBJECT")
        O.object.select_all(action="DESELECT")

        # Disabling lights
        # bpy.data.node_groups["Next_Streets_V3"].nodes["Switch.004"].inputs[0].default_value = False

    def interpolate_z(self, x, y):
        """
        Finds the z coordinate corresponding to the (x,y) point in the input using bilinear interpolation
        :param x: the x coordinate of the point
        :param y: the y coordinate of the point
        :return: the corresponding z coordinate of the point
        """

        current_terrain = None

        for terrain in self._terrain_data:
            is_point_in_terrain = True
            is_point_in_terrain &= x >= terrain.x_min
            is_point_in_terrain &= x < terrain.x_max
            is_point_in_terrain &= y >= terrain.y_min
            is_point_in_terrain &= y < terrain.y_max

            if is_point_in_terrain:
                current_terrain = terrain
                break

        if current_terrain is None:
            # Should never happen
            return 0
            # raise ValueError(
            #    "Point is outside of terrain: x=" + str(x) + ", y=" + str(y)
            # )

        point_offset_x = x - current_terrain.x_min
        point_offset_y = y - current_terrain.y_min

        # Index of the point in the grid to the lower left of the current point
        ll_index_x = int(point_offset_x / current_terrain.resolution)
        ll_index_y = 999 - int(point_offset_y / current_terrain.resolution)

        in_cell_offset_x = point_offset_x % current_terrain.resolution
        in_cell_offset_y = point_offset_y % current_terrain.resolution

        if ll_index_x == 999:
            # If x index is at max, we cannt use the point to its right for interpolation
            if ll_index_y == 999:
                # If y index is at max, we cannt use the point above for interpolation
                z_ll = current_terrain.data.values[ll_index_y][ll_index_x]

                return z_ll
            else:
                z_ll = current_terrain.data.values[ll_index_y][ll_index_x]
                z_ul = current_terrain.data.values[ll_index_y + 1][ll_index_x]

                return (
                    in_cell_offset_y * z_ul + (1 - in_cell_offset_y) * z_ll
                ) / current_terrain.resolution
        elif ll_index_y == 999:
            # If y index is at max, we cannt use the point above for interpolation
            z_ll = current_terrain.data.values[ll_index_y][ll_index_x]
            z_lr = current_terrain.data.values[ll_index_y][ll_index_x + 1]

            return (
                in_cell_offset_x * z_lr + (1 - in_cell_offset_x) * z_ll
            ) / current_terrain.resolution
        else:
            z_ll = current_terrain.data.values[ll_index_y][ll_index_x]
            z_ul = current_terrain.data.values[ll_index_y + 1][ll_index_x]
            z_ur = current_terrain.data.values[ll_index_y + 1][ll_index_x + 1]
            z_lr = current_terrain.data.values[ll_index_y][ll_index_x + 1]

            z_l = (
                in_cell_offset_x * z_lr + (1 - in_cell_offset_x) * z_ll
            ) / current_terrain.resolution
            z_u = (
                in_cell_offset_x * z_ur + (1 - in_cell_offset_x) * z_ul
            ) / current_terrain.resolution

            return (
                in_cell_offset_y * z_u + (1 - in_cell_offset_y) * z_l
            ) / current_terrain.resolution

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

    def get_mesh_obj(self):
        return D.objects[self._mesh_name]
