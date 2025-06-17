import math

import bmesh
from bpy import data as D

import geopandas as g
import pandas as p
import random
from shapely.geometry import mapping, MultiPolygon, Polygon

from tqdm import tqdm

from mage_procgen.Renderer.BaseRenderer import BaseRenderer

from mage_procgen.Utils.Config import BuildingRendererConfig
from mage_procgen.Utils.Geometry import interpolate_z
from mage_procgen.Utils.Utils import TerrainData
from mage_procgen.Utils.RenderingDataFrames import RenderingBuildingDataFrame


class BuildingRenderer(BaseRenderer):
    _mesh_name = "Buildings"

    def __init__(
        self, terrain_data: list[TerrainData], object_config: BuildingRendererConfig
    ):

        super().__init__(terrain_data, object_config)

        # Buildify does not realize instances of the objects it adds, so they have their own pass index.
        # In order to set it, we have to get the objects that are used by the geometry nodes.
        # This way is quite dirty and specific to Buildify, but it works.
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

        self._mesh_names = []

        for building_index in tqdm(buildings_gdf.index):

            if buildings_gdf.geometry[building_index].is_empty:
                continue

            building_floor_numbers = random.randint(
                self.config.default_levels_min, self.config.default_levels_max
            )
            # Height of each floor in meters
            floor_height = 3

            if not p.isnull(
                buildings_gdf[RenderingBuildingDataFrame.number_floors][building_index]
            ):
                building_floor_numbers = int(
                    buildings_gdf[RenderingBuildingDataFrame.number_floors][
                        building_index
                    ]
                )
            elif not p.isnull(
                buildings_gdf[RenderingBuildingDataFrame.height][building_index]
            ):
                # Better to round up than down in this case
                building_floor_numbers = math.ceil(
                    buildings_gdf[RenderingBuildingDataFrame.height][building_index]
                    / floor_height
                )

            if type(buildings_gdf.geometry[building_index]) == MultiPolygon:
                for polygon in buildings_gdf.geometry[building_index].geoms:
                    self.__draw_building(
                        polygon,
                        geo_center,
                        building_floor_numbers,
                        parent_collection_name,
                    )
            else:
                self.__draw_building(
                    buildings_gdf.geometry[building_index],
                    geo_center,
                    building_floor_numbers,
                    parent_collection_name,
                )

    def __draw_building(
        self,
        polygon: Polygon,
        geo_center: tuple[float, float, float],
        building_floor_numbers: int,
        parent_collection_name: str,
    ):

        mesh = bmesh.new()

        # Kind of hack because Polygon.coords is not implemented
        polygon_geometry = mapping(polygon)["coordinates"]

        points_coords = [
            (x[0], x[1], interpolate_z(self._terrain_data, x[0], x[1]))
            for x in polygon_geometry[0]
        ]
        # Buildings have to be perfectly flat in order for Buildify to work.
        # To achieve that we place all the points at the lowest z of the contour points
        z_min = min([x[2] for x in points_coords])
        points_coords = [(x[0], x[1], z_min) for x in points_coords]
        countour_ring = BaseRenderer._add_edge_ring(
            mesh, self._to_scene_coords(points_coords, geo_center)
        )

        if len(polygon_geometry) > 1:
            # If there are holes
            for hole in polygon_geometry[1:]:
                points_coords_hole = [(x[0], x[1], z_min) for x in hole]

                hole_ring = BaseRenderer._add_edge_ring(
                    mesh, self._to_scene_coords(points_coords_hole, geo_center)
                )

                countour_ring.extend(hole_ring)

        bmesh.ops.triangle_fill(
            mesh, use_beauty=True, use_dissolve=False, edges=countour_ring
        )

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

        # Adding 1 to the DB value because the (flat) roof is considered as a floor
        mesh_obj.modifiers[0]["Input_6"] = int(building_floor_numbers) + 1
        mesh_obj.modifiers[0]["Input_7"] = int(building_floor_numbers) + 1

    def clear_object(self):

        for object_name in self._mesh_names:
            D.objects.remove(D.objects[object_name], do_unlink=True)
            D.meshes.remove(D.meshes[object_name], do_unlink=True)


class ChurchRenderer(BuildingRenderer):
    _mesh_name = "Churches"


class MallRenderer(BuildingRenderer):
    _mesh_name = "Malls"


class FactoryRenderer(BuildingRenderer):
    _mesh_name = "Factories"
