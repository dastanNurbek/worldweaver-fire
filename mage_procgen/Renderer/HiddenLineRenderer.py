import bmesh
from bpy import data as D

import geopandas as g

from shapely.geometry import mapping, MultiLineString

from tqdm import tqdm

from mage_procgen.Utils.Utils import TerrainData, GeoWindow, Point
from mage_procgen.Utils.Geometry import interpolate_z


class HiddenLineRenderer:
    _mesh_name = "HiddenLine"

    def __init__(self, terrain_data: list[TerrainData]):

        self._terrain_data = terrain_data

    def render(
        self,
        lines: g.GeoDataFrame,
        geo_window: GeoWindow,
        parent_collection_name,
    ):

        mesh = bmesh.new()

        for line_index in tqdm(lines.index):

            line_geom = lines.geometry[line_index]

            # Windowing is done here since lines and polygons cannot be mixed for dataframe overlay operations
            windowed_line = []

            if type(line_geom) == MultiLineString:
                for geom in line_geom.geoms:
                    for point in geom.coords:
                        if (
                            geo_window.bounds[0] < point[0] < geo_window.bounds[2]
                            and geo_window.bounds[1] < point[1] < geo_window.bounds[3]
                        ):
                            windowed_line.append(point)
            else:
                for point in line_geom.coords:
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

            # Adapting the coordinates for rendering purposes
            centered_points_coords = self.adapt_coords(points_coords, geo_window.center)

            for pt_index in range(1, len(centered_points_coords)):
                edge = mesh.edges.new(
                    [
                        mesh.verts.new(centered_points_coords[pt_index - 1]),
                        mesh.verts.new(centered_points_coords[pt_index]),
                    ]
                )

        mesh_data = D.meshes.new(self._mesh_name)
        self._mesh_name = mesh_data.name
        mesh.to_mesh(mesh_data)
        mesh.free()
        mesh_obj = D.objects.new(self._mesh_name, mesh_data)
        D.collections[parent_collection_name].objects.link(mesh_obj)

        mesh_obj.hide_render = True
        mesh_obj.hide_viewport = True

    def adapt_coords(
        self, points_coords: list[Point], geo_center: Point
    ) -> list[Point]:

        # Centering the coordinates so that Blender's internal precision is less impactful
        centered_points_coords = [
            (x[0] - geo_center[0], x[1] - geo_center[1], x[2] - geo_center[2])
            for x in points_coords
        ]

        return centered_points_coords

    def get_mesh_obj(self):
        return D.objects[self._mesh_name]
