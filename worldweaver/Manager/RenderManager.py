import math

from bpy import data as D

import pandas as p

from worldweaver.Drivers.IGN.IGNDriver import IGNDataSources
from worldweaver.Renderer import (
    BuildingRenderer,
    BoxBuildingRenderer,
    BuildingFootprintRenderer,
    ForestRenderer,
    FireRenderer,
    PrettyRoadRenderer,
    WaterRenderer,
    TerrainRenderer,
    FloodRenderer,
    ZoneRenderer,
    LineZoneRenderer,
)

from worldweaver.Utils.Config import Config, CameraType
from worldweaver.Utils.Logging import logger
from worldweaver.Utils.Utils import TerrainData
from worldweaver.Utils.Utils import GeoWindow, safe_overlay, OverlayType
from worldweaver.Utils.Rendering import (
    configure_scene,
    rendering_collection_name,
    terrain_collection_name,
    buildings_collection_name,
    additionals_collection_name,
    get_camera,
)
from worldweaver.Utils.RenderingDataFrames import RenderingData


class RenderManager:
    def __init__(
        self,
        terrain_data: list[TerrainData],
        rendering_data: RenderingData,
        geowindow: GeoWindow,
        crs: int,
        config: Config,
    ):
        self.terrain_data = terrain_data
        self.rendering_data = rendering_data
        self.window = geowindow
        self.crs = crs
        self.config = config
        self.current_zone = None
        self.is_subdense_run = self.config.data_source == IGNDataSources.SUBDENSE
        configure_scene(
            self.window.center_deg,
            self.config.rendering.output.device_type,
            self.is_subdense_run,
            self.config.rendering.output.time_of_day,
            self.config.rendering.output.sky_strength,
        )
        self.terrain_renderer = TerrainRenderer.TerrainRenderer(
            terrain_data,
            self.config.terrain,
            self.config.rendering.terrain_render_config,
        )
        self.building_renderer = BuildingRenderer.BuildingRenderer(
            self.terrain_data, self.config.rendering.building_render_config
        )
        self.houses_renderer = BoxBuildingRenderer.BoxBuildingRenderer(
            self.terrain_data, self.config.rendering.house_render_config
        )
        self.malls_renderer = BuildingRenderer.MallRenderer(
            self.terrain_data, self.config.rendering.mall_render_config
        )
        self.churches_renderer = BuildingRenderer.ChurchRenderer(
            self.terrain_data, self.config.rendering.church_render_config
        )
        self.factories_renderer = BuildingRenderer.FactoryRenderer(
            self.terrain_data, self.config.rendering.factory_render_config
        )
        self.flowing_water_renderer = WaterRenderer.FlowingWaterRenderer(
            self.terrain_data, self.config.rendering.water_render_config
        )
        self.ocean_renderer = WaterRenderer.OceanRenderer(
            self.terrain_data, self.config.rendering.water_render_config
        )
        self.flood_renderer = FloodRenderer.FloodRenderer(
            self.config.rendering.flood_render_config
        )
        chosen_forest_config = (
            self.config.rendering.pretty_forest_render_config
            if self.config.rendering.output.export_img
            else self.config.rendering.placeholder_forest_render_config
        )
        self.forests_renderer = ForestRenderer.ForestRenderer(
            self.terrain_data, chosen_forest_config
        )
        self.road_renderer = PrettyRoadRenderer.PrettyRoadRenderer(
            self.terrain_data,
            self.config.rendering.road_render_config,
            self.config.rendering.bridge_render_config,
        )
        self.still_water_renderer = WaterRenderer.StillWaterRenderer(
            self.terrain_data, self.config.rendering.water_render_config
        )
        self.building_footprint_renderer = (
            BuildingFootprintRenderer.BuildingFootprintRenderer(self.terrain_data)
        )
        self.wheatfields_renderer = ZoneRenderer.WheatFieldRenderer(self.terrain_data)
        self.cornfields_renderer = ZoneRenderer.CornFieldRenderer(self.terrain_data)
        self.grass_renderer = ZoneRenderer.GrassRenderer(self.terrain_data)
        self.developed_renderer = ZoneRenderer.DevelopedRenderer(self.terrain_data)
        self.tartan_renderer = ZoneRenderer.TartanRenderer(self.terrain_data)
        self.compacted_renderer = ZoneRenderer.CompactedRenderer(self.terrain_data)
        self.asphalt_renderer = ZoneRenderer.AsphaltRenderer(self.terrain_data)
        self.sand_renderer = ZoneRenderer.SandRenderer(self.terrain_data)
        self.path_renderer = LineZoneRenderer.PathRenderer(self.terrain_data)
        self.forest_zone_renderer = ZoneRenderer.ForestZoneRenderer(self.terrain_data)
        self.fire_renderer = FireRenderer.FireRenderer(
            self.terrain_data, self.config.fire.tagging_index
        )

    def draw_terrain(self):
        # Rendering objects that are ground level or interact with terrain
        logger.info("Rendering terrain and its dependencies")
        self.terrain_renderer.render(
            self.window,
            terrain_collection_name,
        )
        logger.info("Terrain rendered")

        # Drawing water
        logger.info("Rendering flowing water")
        self.flowing_water_renderer.render(
            self.rendering_data.flowing_water,
            self.rendering_data.flowing_water_line,
            self.rendering_data.ocean,
            self.window.center,
            rendering_collection_name,
        )

        self.ocean_renderer.render(
            self.rendering_data.ocean, self.window.center, rendering_collection_name
        )

        self.still_water_renderer.render(
            self.rendering_data.still_water,
            self.window.center,
            rendering_collection_name,
        )

        logger.info("Rendering roads")
        # Drawing roads and buildind footprints to modify terrain
        self.road_renderer.render(
            self.rendering_data.roads,
            self.window,
            rendering_collection_name,
        )

        logger.info("Rendering zones")
        buildings_zone = safe_overlay(
            self.rendering_data.buildings.default_buildings,
            self.window.dataframe,
            OverlayType.INTERSECTION,
        )

        houses_zone = safe_overlay(
            self.rendering_data.buildings.houses,
            self.window.dataframe,
            OverlayType.INTERSECTION,
        )

        churches_zone = safe_overlay(
            self.rendering_data.buildings.churches,
            self.window.dataframe,
            OverlayType.INTERSECTION,
        )

        factories_zone = safe_overlay(
            self.rendering_data.buildings.factories,
            self.window.dataframe,
            OverlayType.INTERSECTION,
        )

        malls_zone = safe_overlay(
            self.rendering_data.buildings.malls,
            self.window.dataframe,
            OverlayType.INTERSECTION,
        )

        # Filtering for empty dataframes to avoid a FutureWarning of p.concat that we don't really care about
        buildings_df_list = [
            buildings_zone,
            houses_zone,
            churches_zone,
            factories_zone,
            malls_zone,
        ]

        # Concatenating empty dataframes results in an error
        all_dfs_empty = all([building_df.empty for building_df in buildings_df_list])
        if not all_dfs_empty:
            buildings = p.concat(
                [
                    building_df
                    for building_df in buildings_df_list
                    if not building_df.empty
                ],
                ignore_index=True,
            )
        else:
            buildings = buildings_df_list[0]

        self.building_footprint_renderer.render(
            buildings, self.window.center, additionals_collection_name
        )

        # Drawing zones to texture terrain
        self.wheatfields_renderer.render(
            self.rendering_data.zones.wheatfields,
            self.window.center,
            additionals_collection_name,
        )

        self.cornfields_renderer.render(
            self.rendering_data.zones.cornfields,
            self.window.center,
            additionals_collection_name,
        )

        self.grass_renderer.render(
            self.rendering_data.zones.grass,
            self.window.center,
            additionals_collection_name,
        )

        self.developed_renderer.render(
            self.rendering_data.zones.developed,
            self.window.center,
            additionals_collection_name,
        )

        self.tartan_renderer.render(
            self.rendering_data.zones.tartan,
            self.window.center,
            additionals_collection_name,
        )

        self.compacted_renderer.render(
            self.rendering_data.zones.compacted,
            self.window.center,
            additionals_collection_name,
        )

        self.asphalt_renderer.render(
            self.rendering_data.zones.asphalt,
            self.window.center,
            additionals_collection_name,
        )

        self.sand_renderer.render(
            self.rendering_data.zones.sand,
            self.window.center,
            additionals_collection_name,
        )

        self.path_renderer.render(
            self.rendering_data.zones.paths,
            self.window,
            additionals_collection_name,
        )

        # Once everything is rendered, it can be plugged into the terrain's geometrynodes
        self.terrain_renderer._TerrainRenderer__config_geometry_node(
            road_object=self.road_renderer.get_mesh_obj(),
            water_object=self.flowing_water_renderer.get_mesh_obj(),
            still_water_object=self.still_water_renderer.get_mesh_obj(),
            ocean_object=self.ocean_renderer.get_mesh_obj(),
            building_object=self.building_footprint_renderer.get_mesh_obj(),
        )

        if not self.config.terrain.use_sat_img:
            self.terrain_renderer._TerrainRenderer__config_tagging_node(
                wheatfields_object=self.wheatfields_renderer.get_mesh_obj(),
                cornields_object=self.cornfields_renderer.get_mesh_obj(),
                grass_object=self.grass_renderer.get_mesh_obj(),
                developed_object=self.developed_renderer.get_mesh_obj(),
                tartan_object=self.tartan_renderer.get_mesh_obj(),
                compacted_object=self.compacted_renderer.get_mesh_obj(),
                asphalt_object=self.asphalt_renderer.get_mesh_obj(),
                sand_object=self.sand_renderer.get_mesh_obj(),
                roads_object=self.road_renderer.get_mesh_obj(),
                path_object=self.path_renderer.get_mesh_obj(),
            )

        logger.info("Objects that interact with flood rendered")

    def draw_flood(self, flood_data):
        self.flood_renderer.render(flood_data, rendering_collection_name)

    def draw_fire(self, fire_data):
        self.fire_renderer.render(fire_data, self.window.center, rendering_collection_name)
        self.terrain_renderer.set_burnt_zone(self.fire_renderer.get_mesh_obj())

    def update_forests_for_fire(self):
        self.forests_renderer._ForestRenderer__config_geometry_node(
            self.road_renderer.get_mesh_obj(),
            self.building_footprint_renderer.get_mesh_obj(),
            self.terrain_renderer.get_mesh_obj(),
            get_camera(CameraType.ORTHOGRAPHIC).location[2] * 2,
            self.fire_renderer.get_mesh_obj(),
        )

    @staticmethod
    def _clip_gdf(gdf, bounds):
        if gdf is None or gdf.empty:
            return gdf
        return gdf.clip(bounds)

    def draw_decor(self, restrict_to_camera, use_camera_presp=False):

        zone_window = self.window

        if restrict_to_camera:

            # To draw more than the actual view
            vector_multiplier = 1.2

            # Calculating an area that is roughly vector_multiplier times bigger than the field of view of the camera
            # So that we only draw objects that are inside this area
            if use_camera_presp:
                camera = get_camera(CameraType.PERSPECTIVE)
                origin = camera.location

                # camera Z should be by far the highest so this rule of thumb should hold
                max_distance = 2 * origin[2]

                vector_coord = math.tan(camera.data.angle / 2)

                vector_ul = (
                    -vector_multiplier * vector_coord,
                    -vector_multiplier * vector_coord,
                    -1,
                )
                vector_ur = (
                    vector_multiplier * vector_coord,
                    -vector_multiplier * vector_coord,
                    -1,
                )
                vector_ll = (
                    -vector_multiplier * vector_coord,
                    vector_multiplier * vector_coord,
                    -1,
                )
                vector_lr = (
                    vector_multiplier * vector_coord,
                    vector_multiplier * vector_coord,
                    -1,
                )

                zone_delimiters = (
                    self.__corner_coord(vector_ul, max_distance, origin),
                    self.__corner_coord(vector_ur, max_distance, origin),
                    self.__corner_coord(vector_ll, max_distance, origin),
                    self.__corner_coord(vector_lr, max_distance, origin),
                )

                try:
                    zone_x_min = (
                        min([c[0][0] for c in zone_delimiters]) + self.window.center[0]
                    )
                    zone_x_max = (
                        max([c[0][0] for c in zone_delimiters]) + self.window.center[0]
                    )
                    zone_y_min = (
                        min([c[0][1] for c in zone_delimiters]) + self.window.center[1]
                    )
                    zone_y_max = (
                        max([c[0][1] for c in zone_delimiters]) + self.window.center[1]
                    )

                    zone_window = GeoWindow.from_square(
                        x_min=zone_x_min,
                        x_max=zone_x_max,
                        y_min=zone_y_min,
                        y_max=zone_y_max,
                        from_crs=self.crs,
                        to_crs=self.crs,
                    )

                except:
                    raise ValueError(
                        "Zone to beautify is outside of the boundaries of the scene"
                    )
            else:
                camera = get_camera(CameraType.ORTHOGRAPHIC)
                origin = camera.location
                window_size = camera.data.ortho_scale

                zone_x_min = (
                    origin[0]
                    - (window_size / 2) * vector_multiplier
                    + self.window.center[0]
                )
                zone_x_max = (
                    origin[0]
                    + (window_size / 2) * vector_multiplier
                    + self.window.center[0]
                )
                zone_y_min = (
                    origin[1]
                    - (window_size / 2) * vector_multiplier
                    + self.window.center[1]
                )
                zone_y_max = (
                    origin[1]
                    + (window_size / 2) * vector_multiplier
                    + self.window.center[1]
                )

                zone_window = GeoWindow.from_square(
                    x_min=zone_x_min,
                    x_max=zone_x_max,
                    y_min=zone_y_min,
                    y_max=zone_y_max,
                    from_crs=self.crs,
                    to_crs=self.crs,
                )

        if not restrict_to_camera:
            logger.info("Rendering buildings")
        tile_bounds = zone_window.bounds
        buildings_zone = self._clip_gdf(
            self.rendering_data.buildings.default_buildings, tile_bounds
        )
        self.building_renderer.render(
            buildings_zone, self.window.center, buildings_collection_name
        )

        houses_zone = self._clip_gdf(
            self.rendering_data.buildings.houses, tile_bounds
        )
        self.houses_renderer.render(
            houses_zone, self.window.center, buildings_collection_name
        )

        churches_zone = self._clip_gdf(
            self.rendering_data.buildings.churches, tile_bounds
        )
        self.churches_renderer.render(
            churches_zone, self.window.center, buildings_collection_name
        )

        factories_zone = self._clip_gdf(
            self.rendering_data.buildings.factories, tile_bounds
        )
        self.factories_renderer.render(
            factories_zone, self.window.center, buildings_collection_name
        )

        malls_zone = self._clip_gdf(
            self.rendering_data.buildings.malls, tile_bounds
        )
        self.malls_renderer.render(
            malls_zone, self.window.center, buildings_collection_name
        )

        if not restrict_to_camera:
            logger.info("Rendering forests")
        forests_zone = self._clip_gdf(
            self.rendering_data.forests, tile_bounds
        )
        self.forests_renderer.render(
            forests_zone, self.window.center, rendering_collection_name
        )
        self.forest_zone_renderer.render(
            forests_zone, self.window.center, additionals_collection_name
        )
        self.forests_renderer._ForestRenderer__config_geometry_node(
            self.road_renderer.get_mesh_obj(),
            self.building_footprint_renderer.get_mesh_obj(),
            self.terrain_renderer.get_mesh_obj(),
            get_camera(CameraType.ORTHOGRAPHIC).location[2] * 2,
            self.fire_renderer.get_mesh_obj() if self.fire_renderer else None,
        )

        self.terrain_renderer.set_forest_zone(self.forest_zone_renderer.get_mesh_obj())

        return zone_window

    def clean_zone(self):

        self.building_renderer.clear_object()

        self.houses_renderer.clear_object()

        self.churches_renderer.clear_object()

        self.malls_renderer.clear_object()

        self.factories_renderer.clear_object()

        self.forests_renderer.clear_object()

    def change_terrain_visibility(self, is_terrain_visible):

        terrain_collection = D.collections[terrain_collection_name].objects
        for terrain in terrain_collection:
            terrain.hide_viewport = not is_terrain_visible
            terrain.hide_render = not is_terrain_visible

    def change_non_sources_visibility(self, is_visible):
        """
        Hides objects that need to be displayed before flood because they interact with terrain, but need to be hidden
        during source computation
        """

        # Decor of terrain needs to be hidden during source computation
        self.terrain_renderer.change_decor_visibility(is_visible)

        for road_object in self.road_renderer.get_meshes_objs():
            road_object.hide_viewport = not is_visible
            road_object.hide_render = not is_visible

        still_water_obj = self.still_water_renderer.get_mesh_obj()
        still_water_obj.hide_viewport = not is_visible
        still_water_obj.hide_render = not is_visible

    def __corner_coord(self, ray_direction, max_distance, origin):

        terrain_collection = D.collections[terrain_collection_name].objects

        coord = None

        terrain_hit = None

        for terrain in terrain_collection:
            ray_result = terrain.ray_cast(origin, ray_direction, distance=max_distance)

            if ray_result[0]:
                coord = ray_result[1]
                terrain_hit = terrain.name

        return coord, terrain_hit
