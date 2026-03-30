import bmesh
from bpy import data as D

import geopandas as g

from tqdm import tqdm

from shapely.geometry import mapping, MultiPolygon, GeometryCollection, Polygon

from worldweaver.Utils.Geometry import interpolate_z

from worldweaver.Renderer.BaseRenderer import BaseRenderer
from worldweaver.Renderer.FlatPolygonRenderer import FlatPolygonRenderer

from worldweaver.flatten.process import process_all


class StillWaterRenderer(FlatPolygonRenderer):
    _mesh_name = "Still_Water"

    def get_mesh_obj(self):
        return D.objects[self._mesh_name]


class OceanRenderer(FlatPolygonRenderer):
    _mesh_name = "Ocean_Water"

    def get_mesh_obj(self):
        return D.objects[self._mesh_name]


class FlowingWaterRenderer(BaseRenderer):
    _mesh_name = "Flowing_Water"

    def get_elevation(self, coords: [list[float]]) -> float:
        return interpolate_z(self._terrain_data, coords[0], coords[1])

    def render(
        self,
        water_data: g.GeoDataFrame,
        water_line_data: g.GeoDataFrame,
        ocean_data: g.GeoDataFrame,
        geo_center: tuple[float, float, float],
        parent_collection_name: str,
    ):
        # Rendering water using code from https://github.com/umrlastig/flatten/
        # flatten module was strapped to worldweaver due to time constraints,
        # a better integration should be possible for future releases.
        max_segment_length = 20.0
        alpha = 1.0
        beta = 1.0
        gamma = 1.0
        delta = 0.0
        epsilon = 10.0

        mesh = bmesh.new()

        if not water_data.empty:

            points, final_triangles_gdf = process_all(
                water_data,
                water_line_data,
                max_segment_length,
                alpha,
                beta,
                gamma,
                delta,
                epsilon,
                self.get_elevation,
                None,
            )

            # Storing the points inside a dict to avoid point duplication
            points_dict = {}

            for polygon in tqdm(final_triangles_gdf.geometry.to_list()):

                if polygon.is_empty:
                    continue

                polygon_geometry = mapping(polygon)["coordinates"]
                if len(polygon_geometry) > 0:
                    points_coords = [
                        (x[0], x[1], x[2]) for x in polygon_geometry[0][:-1]
                    ]

                    centered_points_coords = self._to_scene_coords(
                        points_coords, geo_center
                    )

                    new_face_mesh_verts = []
                    for pt in centered_points_coords:

                        if pt not in points_dict.keys():
                            points_dict[pt] = mesh.verts.new(pt)

                        new_face_mesh_verts.append(points_dict[pt])

                    face = mesh.faces.new(new_face_mesh_verts)

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

    def get_mesh_obj(self):
        return D.objects[self._mesh_name]

    @staticmethod
    def raster_to_real_coords(
        raster_coords, lower_left, upper_right, raster_resolution
    ):
        return (
            lower_left[0] + raster_coords[1] * raster_resolution,
            upper_right[1] - raster_coords[0] * raster_resolution,
        )
