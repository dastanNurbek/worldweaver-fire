import math

import geopandas as g
from bpy import data as D
import bmesh
from shapely.geometry import mapping
from shapely.geometry import Point as sPoint
from shapely import intersection, LineString, union
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures, SplineTransformer
from sklearn.model_selection import GridSearchCV

import scipy as sp
import scipy.misc as sm
import scipy.sparse.linalg as ssl
import matplotlib.pyplot as plt
import matplotlib.colors as pltc
from mpl_toolkits.axes_grid1 import make_axes_locatable
from rasterio.features import rasterize
import rasterio


import imageio

from skimage import measure
from sklearn.linear_model import RANSACRegressor
from scipy.interpolate import griddata
from math import floor, ceil
from mage_procgen.Utils.Geometry import interpolate_z
from mage_procgen.Utils.Utils import Point
from tqdm import tqdm


from mage_procgen.Renderer.BaseRenderer import BaseRenderer


class StillWaterRenderer(BaseRenderer):
    _mesh_name = "Still_Water"

    def get_mesh_obj(self):
        return D.objects[self._mesh_name]

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


class OceanRenderer(BaseRenderer):
    _mesh_name = "Ocean_Water"

    def get_mesh_obj(self):
        return D.objects[self._mesh_name]

    def adapt_coords(
        self, points_coords: list[Point], geo_center: Point
    ) -> list[Point]:

        # Centering the coordinates so that Blender's internal precision is less impactful
        # Oceans are also drawn at a constant z
        z_min = min([x[2] for x in points_coords])

        centered_points_coords = [
            (x[0] - geo_center[0], x[1] - geo_center[1], z_min - geo_center[2])
            for x in points_coords
        ]

        return centered_points_coords


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

    # Laplace smoothing of surface. Very much still WIP
    def render(
        self,
        water_polygons: g.GeoDataFrame,
        geo_center: tuple[float, float, float],
        parent_collection_name: str,
    ):
        mesh = bmesh.new()

        water_render_resolution = 1
        l_water = 1.0e3  # amount of smoothing in the water
        l_water = 0.1
        l_ground = 100  # amount of smoothing on the ground
        l_ground = 0
        buffer = 10
        max_iter = 10
        max_error = 1e-1
        show_result = 1

        surfaces = [water_polygons.geometry[i] for i in water_polygons.index]
        loop_needed = True
        loop_count = 0

        while loop_needed:
            fused_surfaces = []
            loop_needed = False
            for surface in surfaces:
                has_fused = False
                for f_surface_ind in range(len(fused_surfaces)):
                    if not intersection(
                        surface, fused_surfaces[f_surface_ind]
                    ).is_empty:
                        fused_surfaces[f_surface_ind] = union(
                            surface, fused_surfaces[f_surface_ind]
                        )
                        has_fused = True
                        loop_needed = True
                        break
                if not has_fused:
                    fused_surfaces.append(surface)
            surfaces = fused_surfaces
            loop_count += 1
            if loop_count > 50:
                raise ValueError("Water polygon fusion exceeded max loop count of 50")

        print("Fusion done in", loop_count, "loops")
        surface_count = 1
        for surface in surfaces:

            print("Rendering surface", str(surface_count))
            surface_box = surface.bounds
            surface_ll = (surface_box[0], surface_box[1])
            surface_ur = (surface_box[2], surface_box[3])
            rounded_surface_ll = (ceil(surface_ll[0]), ceil(surface_ll[1]), 0)
            rounded_surface_ur = (floor(surface_ur[0]), floor(surface_ur[1]), 0)

            rounded_surface_bounds = (
                rounded_surface_ll[0],
                rounded_surface_ll[1],
                rounded_surface_ur[0],
                rounded_surface_ur[1],
            )

            surface_size_x = rounded_surface_ur[0] - rounded_surface_ll[0]
            surface_size_y = rounded_surface_ur[1] - rounded_surface_ll[1]
            surface_pts_nbr_x = surface_size_x * water_render_resolution
            surface_pts_nbr_y = surface_size_y * water_render_resolution
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

            imageio.imwrite(
                "~/Work/scraps/Water/Laplace/water_mask_original.png",
                255 * water_mask,
            )

            print("Init")

            DSM = np.empty_like(water_mask, dtype=float)

            water_contours = measure.find_contours(water_mask, 0.9)
            # find_contours returns a list of arrays so we concatenate into a single one
            water_contours = np.concatenate(water_contours)

            # Test of making the edge pixels behave like ground to try to limit water going above the ground
            water_interior_mask = np.copy(water_mask)
            for contour_point in tqdm(water_contours):
                point_col = int(contour_point[1])
                point_row = int(contour_point[0])
                water_interior_mask[point_row][point_col] = 0

            imageio.imwrite(
                "~/Work/scraps/Water/Laplace/water_interior_mask_original.png",
                255 * water_interior_mask,
            )

            water_countour_x_y = np.array(
                [
                    (
                        rounded_surface_ll[0]
                        + pt_countour[1] * water_render_resolution,
                        rounded_surface_ur[1]
                        - pt_countour[0] * water_render_resolution,
                    )
                    for pt_countour in water_contours
                ]
            )
            water_countour_z = np.array(
                [
                    interpolate_z(self._terrain_data, pt_countour[0], pt_countour[1])
                    for pt_countour in water_countour_x_y
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
                            rounded_surface_ll[0] + col * water_render_resolution,
                            rounded_surface_ur[1] - row * water_render_resolution,
                        )
                        water_interior_indexes[row][col] = len(interior_x_y)
                        interior_x_y.append(current_point_coords)

            interior_x_y = np.array(interior_x_y)
            interior_z_pred = griddata(
                water_countour_x_y, water_countour_z, interior_x_y, method="linear"
            )

            print("Getting DSM")
            # TODO: better init by array slicing and stitching (but maybe there needs to be requirements on resolutions)
            for row in tqdm(range(DSM.shape[0])):
                for col in range(DSM.shape[1]):
                    # Apparently there are some "nan" returned by griddata, unsure why at the moment
                    if water_mask[row][col] > 0 and not math.isnan(
                        interior_z_pred[water_interior_indexes[row][col]]
                    ):
                        # If the point is strictly inside the water, its z is interpolated from the edge points
                        DSM[row][col] = interior_z_pred[
                            water_interior_indexes[row][col]
                        ]
                    else:
                        # If not, it's just the DSM
                        current_point_coords = (
                            rounded_surface_ll[0] + col * water_render_resolution,
                            rounded_surface_ur[1] - row * water_render_resolution,
                        )
                        DSM[row][col] = interpolate_z(
                            self._terrain_data,
                            current_point_coords[0],
                            current_point_coords[1],
                        )

            DSM_vect = FlowingWaterRendererUtils.to_vect(DSM)
            water_interior_mask_c = water_interior_mask[:, 0:-1]
            water_interior_mask_c_vect = FlowingWaterRendererUtils.to_vect(
                water_interior_mask_c
            )
            water_interior_mask_l = water_interior_mask[0:-1, :]
            water_interior_mask_l_vect = FlowingWaterRendererUtils.to_vect(
                water_interior_mask_l
            )

            print("DSM stats:", DSM.min(), DSM.max())
            print(DSM)

            imageio.imwrite(
                "~/Work/scraps/Water/Laplace/DSM.png",
                np.uint8((DSM - DSM.min()) * 255 / (DSM.max() - DSM.min())),
            )
            imageio.imwrite(
                "~/Work/scraps/Water/Laplace/water_interior_mask.png",
                255 * water_interior_mask,
            )

            grad_c = FlowingWaterRendererUtils.Gcs(DSM.shape[0], DSM.shape[1])
            grad_l = FlowingWaterRendererUtils.Gls(DSM.shape[0], DSM.shape[1])

            ground_mask = 1 - water_interior_mask
            imageio.imwrite(
                "~/Work/scraps/Water/Laplace/ground_mask_original.png",
                255 * ground_mask,
            )
            ground_mask_vect = FlowingWaterRendererUtils.to_vect(ground_mask)

            G = FlowingWaterRendererUtils.weighted_square(
                grad_c, l_ground, l_water, water_interior_mask_c_vect
            ) + FlowingWaterRendererUtils.weighted_square(
                grad_l, l_ground, l_water, water_interior_mask_l_vect
            )

            prev_u = DSM_vect

            for i_iter in range(max_iter):
                print("Loop", i_iter + 1, "begins")
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
                local_error = np.reshape(prev_u - u, DSM.shape)
                print(error)

                prev_u = u

                # export result
                current_grad_c = np.reshape(
                    grad_c.dot(u), (DSM.shape[0], DSM.shape[1] - 1)
                )  # * water_mask_c
                current_grad_l = np.reshape(
                    grad_l.dot(u), (DSM.shape[0] - 1, DSM.shape[1])
                )  # * water_mask_l
                current_grad_c_e = np.uint8(
                    (current_grad_c - current_grad_c.min())
                    * 255
                    / (current_grad_c.max() - current_grad_c.min())
                )
                current_grad_l_e = np.uint8(
                    (current_grad_l - current_grad_l.min())
                    * 255
                    / (current_grad_l.max() - current_grad_l.min())
                )
                local_error_e = np.uint8(
                    (local_error - local_error.min())
                    * 255
                    / (local_error.max() - local_error.min())
                )
                DTM_e = np.uint8(
                    (np.reshape(u, DSM.shape) - DSM.min())
                    * 255
                    / (DSM.max() - DSM.min())
                )
                ground_mask_e = np.uint8(np.reshape(255 * ground_mask_vect, DSM.shape))

                if show_result:
                    # ax = plt.subplot()
                    # im = ax.imshow(np.concatenate((DSM,DTM,ground_mask), 1), norm=pltc.Normalize(vmin=0, vmax=255))
                    # # create an axes on the right side of ax. The width of cax will be 5%
                    # # of ax and the padding between cax and ax will be fixed at 0.05 inch.
                    # divider = make_axes_locatable(ax)
                    # cax = divider.append_axes("right", size="5%", pad=0.05)
                    # plt.colorbar(im, cax=cax)
                    # plt.show()
                    imageio.imwrite(
                        "~/Work/scraps/Water/Laplace/DTM_step_" + str(i_iter) + ".png",
                        DTM_e,
                    )
                    imageio.imwrite(
                        "~/Work/scraps/Water/Laplace/ground_mask_step_"
                        + str(i_iter)
                        + ".png",
                        ground_mask_e,
                    )
                    imageio.imwrite(
                        "~/Work/scraps/Water/Laplace/local_error_step_"
                        + str(i_iter)
                        + ".png",
                        local_error_e,
                    )
                    imageio.imwrite(
                        "~/Work/scraps/Water/Laplace/grad_c_step_"
                        + str(i_iter)
                        + ".png",
                        current_grad_c_e,
                    )
                    imageio.imwrite(
                        "~/Work/scraps/Water/Laplace/grad_l_step_"
                        + str(i_iter)
                        + ".png",
                        current_grad_l_e,
                    )
                    print(
                        "grad_c min:",
                        current_grad_c.min(),
                        "max:",
                        current_grad_c.max(),
                    )
                    print(
                        "grad_l min:",
                        current_grad_l.min(),
                        "max:",
                        current_grad_l.max(),
                    )
                    print(
                        "local_error min:",
                        local_error.min(),
                        "max:",
                        local_error.max(),
                    )

                if error < max_error:
                    DTM_filename = "~/Work/scraps/Water/Laplace/DTM_final.png"
                    print("Saving %s" % DTM_filename)
                    imageio.imwrite("~/Work/scraps/Water/Laplace/DTM_final.png", DTM_e)
                    DTM = np.reshape(u, DSM.shape)
                    break

            # Neighbors relative coordinates
            cell_coords = [
                (-1, -1),
                (-1, 0),
                (0, 0),
                (0, -1),
            ]

            meshes_points = {}

            # Reparcourt du tableau, si le point est dans le masque d'eau on fait une face en utilisant z=DTM
            print("Drawing")
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

                            adapted_current_point_coords = (
                                current_point_coords[0] - geo_center[0],
                                current_point_coords[1] - geo_center[1],
                                current_point_coords[2] - geo_center[2],
                            )

                            if adapted_current_point_coords not in meshes_points:
                                meshes_points[
                                    adapted_current_point_coords
                                ] = mesh.verts.new(adapted_current_point_coords)
                            face_coords.append(
                                meshes_points[adapted_current_point_coords]
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

    # POLYNOMIAL RANSAC
    # def render(
    #         self,
    #         water_polygons: g.GeoDataFrame,
    #         geo_center: tuple[float, float, float],
    #         parent_collection_name: str,
    # ):
    #     mesh = bmesh.new()
    #
    #     # Strategy for water is to create "water bodies" from continuously contiguous water polygons,
    #     # and then fit the z coordinates on a polynomial regression of the ground truth.
    #     # This approach smoothes out outliers and allows for a better water surface.
    #
    #     surfaces = [water_polygons.geometry[i] for i in water_polygons.index]
    #     loop_needed = True
    #     loop_count = 0
    #
    #     while loop_needed:
    #         fused_surfaces = []
    #         loop_needed = False
    #         for surface in surfaces:
    #             has_fused = False
    #             for f_surface_ind in range(len(fused_surfaces)):
    #                 if not intersection(
    #                         surface, fused_surfaces[f_surface_ind]
    #                 ).is_empty:
    #                     fused_surfaces[f_surface_ind] = union(
    #                         surface, fused_surfaces[f_surface_ind]
    #                     )
    #                     has_fused = True
    #                     loop_needed = True
    #                     break
    #             if not has_fused:
    #                 fused_surfaces.append(surface)
    #         surfaces = fused_surfaces
    #         loop_count += 1
    #         if loop_count > 50:
    #             raise ValueError("Water polygon fusion exceeded max loop count of 50")
    #
    #     print("Fusion done in", loop_count, "loops")
    #     for surface in surfaces:
    #         polygon_geometry = mapping(surface)["coordinates"]
    #
    #         points_coords = [
    #             (x[0], x[1], interpolate_z(self._terrain_data, x[0], x[1]))
    #             for x in polygon_geometry[0]
    #         ]
    #
    #         if len(polygon_geometry) > 1:
    #             # If there are holes
    #             for hole in polygon_geometry[1:]:
    #                 points_coords_hole = [
    #                     (x[0], x[1], interpolate_z(self._terrain_data, x[0], x[1]))
    #                     for x in hole
    #                 ]
    #
    #                 points_coords = self.insert_hole(points_coords, points_coords_hole)
    #
    #         points_coords = np.array(points_coords)
    #         x_y_coords = points_coords[:, :2]
    #         z_ground_truth = points_coords[:, 2]
    #
    #         z_pred = self.predict_poly_ransac(x_y_coords, z_ground_truth)
    #
    #         # z_def = np.array([min(z_pred[i],z_ground_truth[i]) for i in range(len(z_pred))])
    #
    #         points_coords[:, 2] = z_pred
    #
    #         # Une fois qu'on a le nouveau Z apres c'est juste de la geometrie de blender comme on fait d'habitude
    #         adjusted_points_coords = list(map(tuple, points_coords))
    #
    #         centered_points_coords = self.adapt_coords(
    #             adjusted_points_coords, geo_center
    #         )
    #         face = mesh.faces.new(mesh.verts.new(x) for x in centered_points_coords)
    #
    #     mesh_data = D.meshes.new(self._mesh_name)
    #     self._mesh_name = mesh_data.name
    #     mesh.to_mesh(mesh_data)
    #     mesh.free()
    #     mesh_obj = D.objects.new(self._mesh_name, mesh_data)
    #     mesh_obj.pass_index = self.config.tagging_index
    #     D.collections[parent_collection_name].objects.link(mesh_obj)
    #
    #     m = mesh_obj.modifiers.new("", "NODES")
    #     m.name = self.geometry_node_name
    #     m.node_group = D.node_groups[self.geometry_node_name]

    # SURFACE AS CUBIC INTERP OF POINTS
    # def render(
    #     self,
    #      : g.GeoDataFrame,
    #     geo_center: tuple[float, float, float],
    #     parent_collection_name: str,
    # ):
    #     mesh = bmesh.new()
    #
    #     # Strategy for water is to create "water bodies" from continuously contiguous water polygons,
    #     # and then fit the z coordinates on a polynomial regression of the ground truth.
    #     # This approach smoothes out outliers and allows for a better water surface.
    #
    #     water_render_resolution = 1
    #
    #     surfaces = [water_polygons.geometry[i] for i in water_polygons.index]
    #     loop_needed = True
    #     loop_count = 0
    #
    #     while loop_needed:
    #         fused_surfaces = []
    #         loop_needed = False
    #         for surface in surfaces:
    #             has_fused = False
    #             for f_surface_ind in range(len(fused_surfaces)):
    #                 if not intersection(
    #                     surface, fused_surfaces[f_surface_ind]
    #                 ).is_empty:
    #                     fused_surfaces[f_surface_ind] = union(
    #                         surface, fused_surfaces[f_surface_ind]
    #                     )
    #                     has_fused = True
    #                     loop_needed = True
    #                     break
    #             if not has_fused:
    #                 fused_surfaces.append(surface)
    #         surfaces = fused_surfaces
    #         loop_count += 1
    #         if loop_count > 50:
    #             raise ValueError("Water polygon fusion exceeded max loop count of 50")
    #
    #     print("Fusion done in", loop_count, "loops")
    #     surface_count = 1
    #     for surface in surfaces:
    #
    #         print("Rendering surface", str(surface_count))
    #
    #         polygon_geometry = mapping(surface)["coordinates"]
    #
    #         points_coords = [
    #             (x[0], x[1], interpolate_z(self._terrain_data, x[0], x[1]))
    #             for x in polygon_geometry[0]
    #         ]
    #
    #         if len(polygon_geometry) > 1:
    #             # If there are holes
    #             for hole in polygon_geometry[1:]:
    #                 points_coords_hole = [
    #                     (x[0], x[1], interpolate_z(self._terrain_data, x[0], x[1]))
    #                     for x in hole
    #                 ]
    #
    #                 points_coords = self.insert_hole(points_coords, points_coords_hole)
    #
    #         points_coords = np.array(points_coords)
    #         x_y_coords = points_coords[:, :2]
    #         z_ground_truth = points_coords[:, 2]
    #
    #         surface_box = surface.bounds
    #         surface_ll = (surface_box[0], surface_box[1])
    #         surface_ur = (surface_box[2], surface_box[3])
    #         rounded_surface_ll = (ceil(surface_ll[0]), ceil(surface_ll[1]), 0)
    #         rounded_surface_ur = (floor(surface_ur[0]), floor(surface_ur[1]), 0)
    #
    #         surface_size_x = rounded_surface_ur[0] - rounded_surface_ll[0]
    #         surface_size_y = rounded_surface_ur[1] - rounded_surface_ll[1]
    #
    #         surface_grid = np.full((surface_size_x, surface_size_y), -1)
    #         x_y_tests = []
    #
    #         print("Init")
    #
    #         # TODO: if we keep this, use rasterize instead of whatever the hell this is
    #         for row in tqdm(range(surface_size_x)):
    #             for col in range(surface_size_y):
    #
    #                 current_point_coords = (rounded_surface_ll[0] + row * water_render_resolution,
    #                                         rounded_surface_ll[1] + col * water_render_resolution)
    #                 current_point = sPoint(current_point_coords)
    #                 is_water = surface.contains(current_point)
    #                 if is_water:
    #                     surface_grid[row][col] = len(x_y_tests)
    #                     x_y_tests.append(current_point_coords)
    #                 else:
    #                     surface_grid[row][col] = -1
    #
    #
    #         #
    #         z_pred = griddata(x_y_coords, z_ground_truth, x_y_tests, method='cubic')
    #
    #         # Reparcourt du tableau, si y'a une valeur de z alors on fait une face (comme pour la flood)
    #         cell_coords = [
    #             (-1, -1),
    #             (-1, 0),
    #             (0, 0),
    #             (0, -1),
    #         ]
    #
    #         meshes_points = {}
    #
    #         print("Drawing")
    #         for x in tqdm(range(1, len(surface_grid))):
    #
    #             for y in range(1, len(surface_grid[x])):
    #
    #                 face_coords = []
    #
    #                 for coord_mod in cell_coords:
    #
    #                     current_x = x + coord_mod[0]
    #                     current_y = y + coord_mod[1]
    #
    #                     current_point_y = rounded_surface_ll[1] + current_y * water_render_resolution
    #                     current_point_x = rounded_surface_ll[0] + current_x * water_render_resolution
    #
    #                     current_point_is_in_surface = surface_grid[current_x][current_y] >= 0
    #
    #                     if current_point_is_in_surface:
    #                         current_point_z_index = surface_grid[current_x][current_y]
    #                         current_point_z = z_pred[current_point_z_index]
    #
    #
    #                         current_point_coords = (
    #                             current_point_x,
    #                             current_point_y,
    #                             current_point_z,
    #                         )
    #
    #                         adapted_current_point_coords = (
    #                             current_point_coords[0] - geo_center[0],
    #                             current_point_coords[1] - geo_center[1],
    #                             current_point_coords[2] - geo_center[2],
    #                         )
    #
    #                         if adapted_current_point_coords not in meshes_points:
    #                             meshes_points[
    #                                 adapted_current_point_coords
    #                             ] = mesh.verts.new(adapted_current_point_coords)
    #                         face_coords.append(
    #                             meshes_points[adapted_current_point_coords]
    #                         )
    #
    #                 if len(face_coords) >= 3:
    #                     face = mesh.faces.new(face_coords)
    #
    #         surface_count += 1
    #
    #     mesh_data = D.meshes.new(self._mesh_name)
    #     self._mesh_name = mesh_data.name
    #     mesh.to_mesh(mesh_data)
    #     mesh.free()
    #     mesh_obj = D.objects.new(self._mesh_name, mesh_data)
    #     mesh_obj.pass_index = self.config.tagging_index
    #     D.collections[parent_collection_name].objects.link(mesh_obj)
    #
    #     m = mesh_obj.modifiers.new("", "NODES")
    #     m.name = self.geometry_node_name
    #     m.node_group = D.node_groups[self.geometry_node_name]

    def predict_poly_ransac(self, x_y_coords, z_ground_truth):

        pipeline = Pipeline(
            steps=(
                ("polynomial", PolynomialFeatures()),
                ("regression", RANSACRegressor(random_state=42)),
            )
        )

        grid = {
            "polynomial__degree": [0, 1, 2, 3, 4, 5]
        }  # allow polynomials from degree 1 to 5
        # cv = 5 means that we perform 5-fold cross validation
        # refit = True means that we automatically fit a RANSAC with the best hyperparameter on the full dataset
        # use root mean squared error as the metric (instead of R2 coeff by default)
        grid_search = GridSearchCV(
            estimator=pipeline,
            param_grid=grid,
            cv=5,
            refit=True,
            scoring="neg_root_mean_squared_error",
        )

        # Perform grid search with cross validation, this will find the best RANSAC model
        grid_search.fit(x_y_coords, z_ground_truth)

        # Predict the new altitude
        z_pred = grid_search.predict(x_y_coords)

        print(
            "Found best fit for water at order",
            str(grid_search.best_estimator_[0].degree),
        )

        return z_pred

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
