import geopandas as g
from bpy import data as D
import bmesh
from shapely.geometry import mapping
from shapely import intersection, LineString, union
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures, SplineTransformer
from sklearn.model_selection import GridSearchCV

from sklearn.linear_model import RANSACRegressor

from mage_procgen.Utils.Geometry import interpolate_z
from mage_procgen.Utils.Utils import Point

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


class FlowingWaterRenderer(BaseRenderer):
    _mesh_name = "Flowing_Water"

    def render(
        self,
        water_polygons: g.GeoDataFrame,
        geo_center: tuple[float, float, float],
        parent_collection_name: str,
    ):
        mesh = bmesh.new()

        # Strategy for water is to create "water bodies" from continuously contiguous water polygons,
        # and then fit the z coordinates on a polynomial regression of the ground truth.
        # This approach smoothes out outliers and allows for a better water surface.

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

        for surface in surfaces:
            polygon_geometry = mapping(surface)["coordinates"]

            points_coords = [
                (x[0], x[1], interpolate_z(self._terrain_data, x[0], x[1]))
                for x in polygon_geometry[0]
            ]

            if len(polygon_geometry) > 1:
                # If there are holes
                for hole in polygon_geometry[1:]:
                    points_coords_hole = [
                        (x[0], x[1], interpolate_z(self._terrain_data, x[0], x[1]))
                        for x in hole
                    ]

                    points_coords = self.insert_hole(points_coords, points_coords_hole)

            points_coords = np.array(points_coords)
            x_y_coords = points_coords[:, :2]
            z_ground_truth = points_coords[:, 2]

            # Create the polynomial RANSAC regression pipeline
            pipeline = Pipeline(
                steps=(
                    ("polynomial", PolynomialFeatures()),
                    ("regression", RANSACRegressor()),
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

            points_coords[:, 2] = z_pred

            # Une fois qu'on a le nouveau Z apres c'est juste de la geometrie de blender comme on fait d'habitude
            adjusted_points_coords = list(map(tuple, points_coords))

            centered_points_coords = self.adapt_coords(
                adjusted_points_coords, geo_center
            )
            face = mesh.faces.new(mesh.verts.new(x) for x in centered_points_coords)

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
