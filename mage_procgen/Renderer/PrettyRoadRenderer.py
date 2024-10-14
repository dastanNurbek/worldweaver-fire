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

from shapely.geometry import MultiLineString
from mage_procgen.Utils.Rendering import terrain_collection_name
from mage_procgen.Utils.RenderingDataFrames import RenderingRoadDataFrame
from mage_procgen.Utils.Geometry import interpolate_z
from ladybug_geometry.geometry2d.pointvector import Point2D


# TODO: find common paths with BaseRenderer
class PrettyRoadRenderer:
    _AssetsFolder = "Assets"
    _mesh_name = "Roads"
    _bridge_mesh_name = "Bridges"
    _car_mesh_name = "Cars"

    _Asset_File = "Roads_pretty_3.blend"
    _GN_Name = "Next_Streets_V3_custom_cars"
    _car_collection_info_node_name = "Cars Collection Info"

    _Bridge_Asset_File = "Bridges.blend"
    _Bridge_GN_Name = "Bridges"
    _Bridge_Group_Name = "Group.001"

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

        filepath_bridge = os.path.realpath(
            os.path.join(_location, "..", self._AssetsFolder, self._Bridge_Asset_File)
        )
        try:
            with bpy.data.libraries.load(filepath_bridge) as (data_from, data_to):
                data_to.node_groups = [self._Bridge_GN_Name]

            # A Geometry Nodes setup with name object_config.geometry_node_name may already exist.
            self.bridge_geometry_node_name = data_to.node_groups[0].name
        except Exception as _:
            raise Exception(
                'Unable to load the Geometry Nodes setup with the name "'
                + self._Bridge_GN_Name
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

        # Setting pass index of bridge pillar
        bridge_pillar = (
            D.node_groups[self.bridge_geometry_node_name]
            .nodes[self._Bridge_Group_Name]
            .inputs[2]
            .default_value
        )

        bridge_pillar.pass_index = car_object_config.tagging_index

    def render(
        self,
        roads: g.GeoDataFrame,
        geo_window: GeoWindow,
        parent_collection_name: str,
    ):
        mesh = bmesh.new()

        bridge_mesh = bmesh.new()

        geo_center = geo_window.center

        # Storing the points inside a dict to avoid point duplication, which messes up crossroads
        # TODO: check that this method works and does not need "fuzzy matching"
        points_dict = {}

        edges_config = {}
        edge_index = 0

        for road_index in tqdm(roads.index):

            road_geom = roads.geometry[road_index]

            # Windowing is done here since lines and polygons cannot be mixed for dataframe overlay operations
            windowed_line = []

            if type(road_geom) == MultiLineString:
                for geom in road_geom.geoms:
                    for point in geom.coords:
                        if (
                            geo_window.bounds[0] < point[0] < geo_window.bounds[2]
                            and geo_window.bounds[1] < point[1] < geo_window.bounds[3]
                        ):
                            windowed_line.append(point)
            else:
                for point in road_geom.coords:
                    if (
                        geo_window.bounds[0] < point[0] < geo_window.bounds[2]
                        and geo_window.bounds[1] < point[1] < geo_window.bounds[3]
                    ):
                        windowed_line.append(point)

            if len(windowed_line) == 0:
                continue

            points_coords = [
                (x[0], x[1], interpolate_z(self._terrain_data, x[0], x[1]))
                for x in windowed_line
            ]

            is_bridge = False
            is_tunnel = False

            road_pos_to_ground = roads[RenderingRoadDataFrame.position_rel_to_ground][
                road_index
            ]
            is_int = road_pos_to_ground.isdigit()
            if is_int:
                road_pos_to_ground_value = int(
                    roads[RenderingRoadDataFrame.position_rel_to_ground][road_index]
                )
                is_bridge = road_pos_to_ground_value >= 1
                is_tunnel = road_pos_to_ground_value <= -1

            # Adapting the coordinates for rendering purposes
            centered_points_coords = self.adapt_coords(
                points_coords, geo_center, is_bridge, is_tunnel
            )

            previous_point_2d = Point2D(
                centered_points_coords[0][0], centered_points_coords[0][1]
            )
            if previous_point_2d not in points_dict:
                previous_point = mesh.verts.new(centered_points_coords[0])
                points_dict[previous_point_2d] = previous_point
            else:
                previous_point = points_dict[previous_point_2d]
                if is_bridge or is_tunnel:
                    previous_point.co[2] = centered_points_coords[0][2]

            if is_bridge:
                previous_point_bridge = bridge_mesh.verts.new(centered_points_coords[0])

            for i in range(1, len(points_coords)):

                new_point_2d = Point2D(
                    centered_points_coords[i][0], centered_points_coords[i][1]
                )
                if new_point_2d not in points_dict:
                    new_point = mesh.verts.new(centered_points_coords[i])
                    points_dict[new_point_2d] = new_point
                else:
                    new_point = points_dict[new_point_2d]
                    if is_bridge or is_tunnel:
                        new_point.co[2] = centered_points_coords[i][2]

                if new_point == previous_point:
                    continue

                try:
                    # Sometimes due to bad geometry we will try to create the same edge more than once,
                    # Which results in an error. We filter and swallow this exact error
                    # because it happens only a few time in a scene and is completely benign.
                    edge = mesh.edges.new([previous_point, new_point])
                except ValueError as e:
                    if not str(e) == "edges.new(): this edge exists":
                        raise e

                if is_bridge:
                    new_point_bridge = bridge_mesh.verts.new(centered_points_coords[i])
                    edge_bridge = bridge_mesh.edges.new(
                        [previous_point_bridge, new_point_bridge]
                    )

                edges_config[edge_index] = (
                    roads[RenderingRoadDataFrame.has_sidewalks][road_index],
                    roads[RenderingRoadDataFrame.has_guardrails][road_index],
                    roads[RenderingRoadDataFrame.number_lanes][road_index],
                )

                previous_point = new_point
                if is_bridge:
                    previous_point_bridge = new_point_bridge
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

        bridge_mesh_name = self._bridge_mesh_name
        bridge_mesh_data = D.meshes.new(bridge_mesh_name)
        bridge_mesh.to_mesh(bridge_mesh_data)
        bridge_mesh.free()
        bridge_mesh_obj = D.objects.new(bridge_mesh_data.name, bridge_mesh_data)
        bridge_mesh_obj.pass_index = self.config.tagging_index
        D.collections[parent_collection_name].objects.link(bridge_mesh_obj)

        mb = bridge_mesh_obj.modifiers.new("", "NODES")
        mb.node_group = D.node_groups[self.bridge_geometry_node_name]

        # Pluging terrain to make bridge supports
        D.node_groups[self.bridge_geometry_node_name].nodes["Group.001"].inputs[
            1
        ].default_value = D.collections[terrain_collection_name].objects[0]

    def adapt_coords(
        self, points_coords: list[Point], geo_center: Point, is_bridge, is_tunnel
    ) -> list[Point]:

        # Centering the coordinates so that Blender's internal precision is less impactful
        # Also, for bridges and tunnels we put them at a constant z
        z_max = max([x[2] for x in points_coords])
        z_min = min([x[2] for x in points_coords])

        if is_bridge:
            centered_points_coords = [
                (x[0] - geo_center[0], x[1] - geo_center[1], z_max - geo_center[2])
                for x in points_coords
            ]
        elif is_tunnel:
            centered_points_coords = [
                (x[0] - geo_center[0], x[1] - geo_center[1], z_min - geo_center[2])
                for x in points_coords
            ]
        else:
            centered_points_coords = [
                (x[0] - geo_center[0], x[1] - geo_center[1], x[2] - geo_center[2])
                for x in points_coords
            ]

        return centered_points_coords

    def clear_object(self):

        D.objects.remove(D.objects[self._mesh_name], do_unlink=True)
        D.meshes.remove(D.meshes[self._mesh_name], do_unlink=True)

        D.objects.remove(D.objects[self._bridge_mesh_name], do_unlink=True)
        D.meshes.remove(D.meshes[self._bridge_mesh_name], do_unlink=True)

    def get_meshes_objs(self):
        return [D.objects[self._mesh_name], D.objects[self._bridge_mesh_name]]

    def get_mesh_obj(self):
        return D.objects[self._mesh_name]
