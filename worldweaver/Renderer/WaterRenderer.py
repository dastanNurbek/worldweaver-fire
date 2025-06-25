from math import floor, ceil

import bmesh
from bpy import data as D

import geopandas as g
import numpy as np

import scipy as sp
import scipy.sparse.linalg as ssl
from scipy.interpolate import griddata
from skimage import measure

import rasterio
from rasterio.features import rasterize

from tqdm import tqdm

from worldweaver.Utils.Geometry import interpolate_z
from worldweaver.Utils.Logging import logger
from worldweaver.Utils.Utils import GeoWindow, safe_overlay, OverlayType

from worldweaver.Renderer.BaseRenderer import BaseRenderer
from worldweaver.Renderer.FlatPolygonRenderer import FlatPolygonRenderer


class StillWaterRenderer(FlatPolygonRenderer):
    _mesh_name = "Still_Water"

    def get_mesh_obj(self):
        return D.objects[self._mesh_name]


class OceanRenderer(FlatPolygonRenderer):
    _mesh_name = "Ocean_Water"

    def get_mesh_obj(self):
        return D.objects[self._mesh_name]


class FlowingWaterRendererUtils:
    @staticmethod
    def to_vect(data):
        return np.reshape(data, data.shape[0] * data.shape[1])

    # sparse column gradient matrix
    @staticmethod
    def Gcs(nl, nc):
        data = []
        row_ind = []
        col_ind = []
        i_l = 0
        for l in range(nl):
            for c in range(nc - 1):
                data.append(-1)
                row_ind.append(i_l)
                col_ind.append(c + nc * l)
                data.append(1)
                row_ind.append(i_l)
                col_ind.append(c + 1 + nc * l)
                i_l += 1
        return sp.sparse.csr_matrix((data, (row_ind, col_ind)))

    # sparse line gradient matrix
    @staticmethod
    def Gls(nl, nc):
        data = []
        row_ind = []
        col_ind = []
        i_l = 0
        for l in range(nl - 1):
            for c in range(nc):
                data.append(-1)
                row_ind.append(i_l)
                col_ind.append(c + nc * l)
                data.append(1)
                row_ind.append(i_l)
                col_ind.append(c + nc * (l + 1))
                i_l += 1
        return sp.sparse.csr_matrix((data, (row_ind, col_ind)))

    @staticmethod
    def sparse_eye(n):
        return sp.sparse.csr_matrix((np.ones(n), (range(n), range(n))))

    @staticmethod
    def sparse_diag(v):
        n = v.shape[0]
        return sp.sparse.csr_matrix((v, (range(n), range(n))))

    @staticmethod
    def weighted_square(M, l_ground, l_water, water_weight):
        weight_diag = FlowingWaterRendererUtils.sparse_diag(
            l_ground * np.ones(water_weight.shape[0]) + l_water * water_weight
        )
        wM = np.dot(weight_diag, M)
        return np.dot(M.transpose(), wM)


class FlowingWaterRenderer(BaseRenderer):
    _mesh_name = "Flowing_Water"

    def render(
        self,
        water_data: g.GeoDataFrame,
        ocean_data: g.GeoDataFrame,
        geo_center: tuple[float, float, float],
        parent_collection_name: str,
    ):
        # Rendering of flowing water if done with a crude implementation of https://github.com/brunovallet/LaplaceDTM/blob/master/LaplaceDTM.py
        # It mostly does the job except at the interface between water and terrain where gaps can be created.
        # A better way of rendering flowing water would be very beneficial but at this point we have not found a more satisfactory way of doing it.

        mesh = bmesh.new()

        water_render_resolution = 1

        # Variables to pilot the Laplace smoothing
        l_water = 1.0e-9  # amount of smoothing in the water
        l_ground = 0  # amount of smoothing on the ground
        buffer = 10
        max_iter = 10
        max_error = 1e-1

        surface_count = 1
        for surface in water_data.geometry:

            logger.info(f"Processing surface {surface_count}")
            # Transforming the polygon into a raster
            surface_box = surface.bounds
            surface_ll = (surface_box[0], surface_box[1])
            surface_ur = (surface_box[2], surface_box[3])
            rounded_surface_ll = (ceil(surface_ll[0]), ceil(surface_ll[1]), 0)
            rounded_surface_ur = (floor(surface_ur[0]), floor(surface_ur[1]), 0)

            current_window = GeoWindow.from_square(
                rounded_surface_ll[0],
                rounded_surface_ur[0],
                rounded_surface_ll[1],
                rounded_surface_ur[1],
                water_data.crs,
                water_data.crs,
            )
            rounded_surface_bounds = current_window.bounds
            current_oceans = safe_overlay(
                ocean_data, current_window.dataframe, OverlayType.INTERSECTION
            )
            current_ocean_geometry = current_oceans.geometry.union_all()

            # Need to rasterize the geometries in order to render them
            surface_size_x = rounded_surface_ur[0] - rounded_surface_ll[0]
            surface_size_y = rounded_surface_ur[1] - rounded_surface_ll[1]
            surface_pts_nbr_x = surface_size_x * water_render_resolution + 1
            surface_pts_nbr_y = surface_size_y * water_render_resolution + 1
            transform = rasterio.transform.from_bounds(
                *rounded_surface_bounds, surface_pts_nbr_x, surface_pts_nbr_y
            )

            water_mask = rasterize(
                [surface],
                out_shape=(surface_pts_nbr_y, surface_pts_nbr_x),
                transform=transform,
                fill=0,
                all_touched=True,
                dtype=rasterio.uint8,
            )
            if not current_ocean_geometry.is_empty:
                # Rasterize does not work on empty geometries
                ocean_mask = rasterize(
                    [current_ocean_geometry],
                    out_shape=(surface_pts_nbr_y, surface_pts_nbr_x),
                    transform=transform,
                    fill=0,
                    all_touched=True,
                    dtype=rasterio.uint8,
                )
            else:
                ocean_mask = np.zeros_like(water_mask)

            logger.info("Getting contour height")

            DSM = np.empty_like(water_mask, dtype=float)

            # Need to use a value below 1 because nothing will be returned if we use 1.
            water_contours = measure.find_contours(water_mask, 0.999)
            # find_contours returns a list of arrays so we concatenate into a single one
            water_contours = np.concatenate(water_contours)

            # Getting all the countour points as control points for the linear interpolation that will serve as the initialisation of the surface
            water_countour_x_y = np.array(
                [
                    FlowingWaterRenderer.raster_to_real_coords(
                        pt_countour,
                        rounded_surface_ll,
                        rounded_surface_ur,
                        water_render_resolution,
                    )
                    for pt_countour in water_contours
                ]
            )
            # Have to treat points in ocean differently and put them at z=0
            water_countour_z = np.array(
                [
                    interpolate_z(
                        self._terrain_data,
                        *FlowingWaterRenderer.raster_to_real_coords(
                            pt_countour,
                            rounded_surface_ll,
                            rounded_surface_ur,
                            water_render_resolution,
                        ),
                    )
                    if not ocean_mask[int(pt_countour[0])][int(pt_countour[1])]
                    else 0
                    for pt_countour in water_contours
                ]
            )

            interior_x_y = []
            water_interior_indexes = np.zeros_like(water_mask, dtype=int)
            # TODO: is there a better way for this ?
            # We have to loop on the image to get the x and y coords of all the interior points
            for row in tqdm(range(water_mask.shape[0])):
                for col in range(water_mask.shape[1]):
                    if water_mask[row][col] > 0:
                        current_point_coords = (
                            FlowingWaterRenderer.raster_to_real_coords(
                                (row, col),
                                rounded_surface_ll,
                                rounded_surface_ur,
                                water_render_resolution,
                            )
                        )
                        water_interior_indexes[row][col] = len(interior_x_y)
                        interior_x_y.append(current_point_coords)

            interior_x_y = np.array(interior_x_y)
            interior_z_pred = griddata(
                water_countour_x_y, water_countour_z, interior_x_y, method="linear"
            )

            logger.info("Initializing surface")
            # Next step is to smooth out the water surface with an algorithm based on https://github.com/brunovallet/LaplaceDTM/blob/master/LaplaceDTM.py
            # TODO: better init by array slicing and stitching (but maybe there needs to be requirements on resolutions)
            for row in tqdm(range(DSM.shape[0])):
                for col in range(DSM.shape[1]):
                    # Apparently there are some "nan" returned by griddata, unsure why at the moment
                    if water_mask[row][col] > 0 and not np.isnan(
                        interior_z_pred[water_interior_indexes[row][col]]
                    ):
                        # If the point is strictly inside the water, its z is interpolated from the edge points
                        DSM[row][col] = interior_z_pred[
                            water_interior_indexes[row][col]
                        ]
                    else:
                        # If not, it's just the DSM
                        current_point_coords = (
                            FlowingWaterRenderer.raster_to_real_coords(
                                (row, col),
                                rounded_surface_ll,
                                rounded_surface_ur,
                                water_render_resolution,
                            )
                        )
                        DSM[row][col] = interpolate_z(
                            self._terrain_data,
                            current_point_coords[0],
                            current_point_coords[1],
                        )

            DSM_vect = FlowingWaterRendererUtils.to_vect(DSM)
            water_mask_c = water_mask[:, 0:-1]
            water_mask_c_vect = FlowingWaterRendererUtils.to_vect(water_mask_c)
            water_mask_l = water_mask[0:-1, :]
            water_mask_l_vect = FlowingWaterRendererUtils.to_vect(water_mask_l)

            grad_c = FlowingWaterRendererUtils.Gcs(DSM.shape[0], DSM.shape[1])
            grad_l = FlowingWaterRendererUtils.Gls(DSM.shape[0], DSM.shape[1])

            ground_mask = 1 - water_mask

            ground_mask_vect = FlowingWaterRendererUtils.to_vect(ground_mask)

            G = FlowingWaterRendererUtils.weighted_square(
                grad_c, l_ground, l_water, water_mask_c_vect
            ) + FlowingWaterRendererUtils.weighted_square(
                grad_l, l_ground, l_water, water_mask_l_vect
            )

            prev_u = DSM_vect

            for i_iter in range(max_iter):
                logger.info(f"Laplace smoothing loop {i_iter + 1} begins")
                # DSM attachment only on ground
                ground_mask_diag = FlowingWaterRendererUtils.sparse_diag(
                    ground_mask_vect
                )

                # final system
                A = ground_mask_diag + G
                f = ground_mask_diag.dot(DSM_vect)
                u = ssl.spsolve(A, f)  # solves Au=f in the least squares sense

                # This update of ground mask seems unfit for us but still not quite sure
                if i_iter == 0:
                    ground_mask_vect = DSM_vect < u
                else:
                    ground_mask_vect = DSM_vect < (u + buffer)

                error = np.sqrt(np.linalg.norm(u - prev_u) / u.shape[0])
                logger.info(f"Error at this step: {error}")

                prev_u = u

                if error < max_error:
                    DTM = np.reshape(u, DSM.shape)
                    break
                elif i_iter == max_iter - 1:
                    logger.error(
                        "Could not converge in time. Using pre-smoothed surface model."
                    )
                    DTM = DSM

            # Neighbors relative coordinates
            cell_coords = [
                (-1, -1),
                (-1, 0),
                (0, 0),
                (0, -1),
            ]

            meshes_points = {}

            # Drawing the surface by looping again on the image and plotting all faces for which at least 3 points are inside the water mask
            logger.info("Drawing")
            for y in tqdm(range(1, len(water_mask))):

                for x in range(1, len(water_mask[y])):

                    face_coords = []

                    for coord_mod in cell_coords:

                        current_x = x + coord_mod[0]
                        current_y = y + coord_mod[1]

                        current_point_x = (
                            rounded_surface_ll[0] + current_x * water_render_resolution
                        )
                        current_point_y = (
                            rounded_surface_ur[1] - current_y * water_render_resolution
                        )

                        current_point_is_in_surface = (
                            water_mask[current_y][current_x] > 0
                        )

                        if current_point_is_in_surface:
                            current_point_z = DTM[current_y][current_x]

                            current_point_coords = (
                                current_point_x,
                                current_point_y,
                                current_point_z,
                            )

                            current_point_scene_coords = (
                                current_point_coords[0] - geo_center[0],
                                current_point_coords[1] - geo_center[1],
                                current_point_coords[2] - geo_center[2],
                            )

                            if current_point_scene_coords not in meshes_points:
                                meshes_points[
                                    current_point_scene_coords
                                ] = mesh.verts.new(current_point_scene_coords)
                            face_coords.append(
                                meshes_points[current_point_scene_coords]
                            )

                    if len(face_coords) >= 3:
                        face = mesh.faces.new(face_coords)

            surface_count += 1

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
