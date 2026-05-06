import os
import shutil
from dataclasses import dataclass

import json

import worldweaver.Utils.Config as Config
import worldweaver.Utils.DataFiles as df


@dataclass
class ConfigStatus:
    config: Config.Config
    log_messages: list[str]
    config_file_path: str


class ConfigTag:
    root = "root"
    base_folder = "base_folder"
    input_data = "input_data"
    type = "type"
    simulation_area = "simulation_area"
    window_type = "window_type"
    geo_window = "geo_window"
    x_min = "x_min"
    y_min = "y_min"
    x_max = "x_max"
    y_max = "y_max"
    crs_from = "crs_from"
    town = "town"
    identifier = "identifier"
    shapefile = "shapefile"
    path = "path"
    terrain = "terrain"
    terrain_resolution = "terrain_resolution"
    use_orthoimage_as_basemap = "use_orthoimage_as_basemap"
    flood = "flood"
    activate = "activate"
    flood_height = "flood_height"
    flood_cell_size = "flood_cell_size"
    fire = "fire"
    ignition_points = "ignition_points"
    fire_cell_size = "fire_cell_size"
    fire_threshold = "fire_threshold"
    fire_seed = "seed"
    rendering = "rendering"
    export_images = "export_images"
    export_scene = "export_scene"
    device_type = "device_type"
    camera_type = "camera_type"
    ground_sampling_distance = "ground_sampling_distance"
    tile_size = "tile_size"
    objects = "objects"
    building_render = "building_render"
    geometry_node_file = "geometry_node_file"
    geometry_node_name = "geometry_node_name"
    tagging_index = "tagging_index"
    default_levels_min = "default_levels_min"
    default_levels_max = "default_levels_max"
    house_render = "house_render"
    default_height_min = "default_height_min"
    default_height_max = "default_height_max"
    roof_slope_degrees = "roof_slope_degrees"
    church_render = "church_render"
    factory_render = "factory_render"
    mall_render = "mall_render"
    flood_render = "flood_render"
    placeholder_forest_render = "placeholder_forest_render"
    pretty_forest_render = "pretty_forest_render"
    road_render = "road_render"
    car_collection_info_node_name = "car_collection_info_node_name"
    car_tagging_index = "car_tagging_index"
    bridge_render = "bridge_render"
    bridge_group_name = "bridge_group_name"
    water_render = "water_render"
    terrain_render = "terrain_render"
    adaptation_node_name = "adaptation_node_name"
    tagging_node_name = "tagging_node_name"
    decorating_node_name = "decorating_node_name"
    base_material_name = "base_material_name"
    tagged_material_name = "tagged_material_name"
    decor_tagging_index = "decor_tagging_index"


class ConfigLoader:
    @staticmethod
    def report_error(filepath, tag, parent):
        raise ValueError(
            f"Invalid config file: {filepath}, missing tag: {tag} in node {parent}"
        )

    @staticmethod
    def get_mandatory_field(parent_dict, tag, parent_tag, filepath):
        return ConfigLoader.get_field(parent_dict, tag, parent_tag, filepath, False)

    @staticmethod
    def get_field(parent_dict, tag, parent_tag, filepath, is_optional):

        if tag in parent_dict.keys():
            return parent_dict[tag]
        else:
            if is_optional:
                return None
            else:
                ConfigLoader.report_error(filepath, tag, parent_tag)

    @staticmethod
    def load_default() -> ConfigStatus:

        log_messages = []

        _location = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__))
        )
        config_folder = os.path.realpath(
            os.path.join(_location, "..", df.config_folder)
        )

        default_config_filepath = os.path.realpath(
            os.path.join(config_folder, df.default_config_file)
        )

        if not os.path.isfile(default_config_filepath):
            log_messages.append("No config file found, copying base config")
            shutil.copyfile(
                os.path.join(config_folder, df.base_config_file),
                default_config_filepath,
            )
        default_config = ConfigLoader.__load_file(default_config_filepath, False, None)

        return ConfigStatus(default_config, log_messages, default_config_filepath)

    @staticmethod
    def load(filepath) -> ConfigStatus:

        log_messages = []

        default_config_status = ConfigLoader.load_default()
        log_messages.extend(default_config_status.log_messages)

        if len(filepath) > 0:
            log_messages.append("Using config file path given by user")
            config_filepath = filepath

            config = ConfigLoader.__load_file(
                config_filepath, True, default_config_status.config
            )

            return ConfigStatus(config, log_messages, config_filepath)
        else:
            log_messages.append("Falling back to default conf")
            return default_config_status

    @staticmethod
    def __load_file(filepath: str, use_defaults: bool, default_config: Config.Config):

        with open(filepath, "r") as f:
            json_dump = f.read()

        json_dict = json.loads(json_dump)

        # Base
        base_folder = ConfigLoader.get_mandatory_field(
            parent_dict=json_dict,
            tag=ConfigTag.base_folder,
            parent_tag=ConfigTag.root,
            filepath=filepath,
        )

        # Input Data
        input_data = ConfigLoader.get_mandatory_field(
            parent_dict=json_dict,
            tag=ConfigTag.input_data,
            parent_tag=ConfigTag.root,
            filepath=filepath,
        )

        input_data_type = ConfigLoader.get_mandatory_field(
            parent_dict=input_data,
            tag=ConfigTag.type,
            parent_tag=ConfigTag.input_data,
            filepath=filepath,
        )

        # Simulation Area
        simulation_area = ConfigLoader.get_mandatory_field(
            parent_dict=json_dict,
            tag=ConfigTag.simulation_area,
            parent_tag=ConfigTag.root,
            filepath=filepath,
        )

        window_type = ConfigLoader.get_mandatory_field(
            parent_dict=simulation_area,
            tag=ConfigTag.window_type,
            parent_tag=ConfigTag.simulation_area,
            filepath=filepath,
        )

        sim_area_geo_window = ConfigLoader.get_field(
            parent_dict=simulation_area,
            tag=ConfigTag.geo_window,
            parent_tag=ConfigTag.simulation_area,
            filepath=filepath,
            is_optional=use_defaults,
        )
        if sim_area_geo_window is not None:
            # Geo Window is defined in the file
            x_min = ConfigLoader.get_mandatory_field(
                parent_dict=sim_area_geo_window,
                tag=ConfigTag.x_min,
                parent_tag=ConfigTag.geo_window,
                filepath=filepath,
            )

            y_min = ConfigLoader.get_mandatory_field(
                parent_dict=sim_area_geo_window,
                tag=ConfigTag.y_min,
                parent_tag=ConfigTag.geo_window,
                filepath=filepath,
            )

            x_max = ConfigLoader.get_mandatory_field(
                parent_dict=sim_area_geo_window,
                tag=ConfigTag.x_max,
                parent_tag=ConfigTag.geo_window,
                filepath=filepath,
            )

            y_max = ConfigLoader.get_mandatory_field(
                parent_dict=sim_area_geo_window,
                tag=ConfigTag.y_max,
                parent_tag=ConfigTag.geo_window,
                filepath=filepath,
            )

            crs_from = ConfigLoader.get_field(
                parent_dict=sim_area_geo_window,
                tag=ConfigTag.crs_from,
                parent_tag=ConfigTag.geo_window,
                filepath=filepath,
                is_optional=use_defaults,
            )
            if crs_from is None and use_defaults:
                crs_from = default_config.geo_window.geo_window.crs_from

            geo_window_config = Config.CoordsGeoWindowConfig(
                x_min, y_min, x_max, y_max, crs_from
            )
        elif window_type == Config.WindowTypes.COORDS:
            # Geo Window is not defined in the file but should be
            ConfigLoader.report_error(
                filepath, ConfigTag.geo_window, ConfigTag.simulation_area
            )
        else:
            # Geo Window is not defined, but will not be used anyway
            geo_window_config = None

        sim_area_town = ConfigLoader.get_field(
            parent_dict=simulation_area,
            tag=ConfigTag.town,
            parent_tag=ConfigTag.simulation_area,
            filepath=filepath,
            is_optional=use_defaults,
        )
        if sim_area_town is not None:
            town_identifier = ConfigLoader.get_mandatory_field(
                parent_dict=sim_area_town,
                tag=ConfigTag.identifier,
                parent_tag=ConfigTag.town,
                filepath=filepath,
            )
        elif window_type == Config.WindowTypes.TOWN:
            ConfigLoader.report_error(
                filepath, ConfigTag.town, ConfigTag.simulation_area
            )
        else:
            town_identifier = None

        sim_area_shapefile = ConfigLoader.get_field(
            parent_dict=simulation_area,
            tag=ConfigTag.shapefile,
            parent_tag=ConfigTag.simulation_area,
            filepath=filepath,
            is_optional=use_defaults,
        )
        if sim_area_shapefile is not None:
            town_file_path = ConfigLoader.get_mandatory_field(
                parent_dict=sim_area_shapefile,
                tag=ConfigTag.path,
                parent_tag=ConfigTag.shapefile,
                filepath=filepath,
            )
        elif window_type == Config.WindowTypes.FILE:
            ConfigLoader.report_error(
                filepath, ConfigTag.shapefile, ConfigTag.simulation_area
            )
        else:
            town_file_path = None

        window_config = Config.GeoWindowConfig(
            window_type=window_type,
            geo_window=geo_window_config,
            town_id=town_identifier,
            window_shapefile=town_file_path,
        )

        # Terrain
        terrain = ConfigLoader.get_mandatory_field(
            parent_dict=json_dict,
            tag=ConfigTag.terrain,
            parent_tag=ConfigTag.root,
            filepath=filepath,
        )

        terrain_resolution = ConfigLoader.get_mandatory_field(
            parent_dict=terrain,
            tag=ConfigTag.terrain_resolution,
            parent_tag=ConfigTag.terrain,
            filepath=filepath,
        )

        use_orthoimage_as_basemap = ConfigLoader.get_mandatory_field(
            parent_dict=terrain,
            tag=ConfigTag.use_orthoimage_as_basemap,
            parent_tag=ConfigTag.terrain,
            filepath=filepath,
        )

        terrain_config = Config.TerrainConfig(
            terrain_resolution=terrain_resolution, use_sat_img=use_orthoimage_as_basemap
        )
        # Flood
        flood = ConfigLoader.get_field(
            parent_dict=json_dict,
            tag=ConfigTag.flood,
            parent_tag=ConfigTag.root,
            filepath=filepath,
            is_optional=use_defaults,
        )
        if flood is not None:
            activate = ConfigLoader.get_mandatory_field(
                parent_dict=flood,
                tag=ConfigTag.activate,
                parent_tag=ConfigTag.flood,
                filepath=filepath,
            )

            flood_height = ConfigLoader.get_mandatory_field(
                parent_dict=flood,
                tag=ConfigTag.flood_height,
                parent_tag=ConfigTag.flood,
                filepath=filepath,
            )

            flood_cell_size = ConfigLoader.get_mandatory_field(
                parent_dict=flood,
                tag=ConfigTag.flood_cell_size,
                parent_tag=ConfigTag.flood,
                filepath=filepath,
            )

            flood_config = Config.FloodConfig(
                activate=activate,
                flood_height=flood_height,
                flood_cell_size=flood_cell_size,
            )
        else:
            flood_config = default_config.flood

        # Fire
        fire = ConfigLoader.get_field(
            parent_dict=json_dict,
            tag=ConfigTag.fire,
            parent_tag=ConfigTag.root,
            filepath=filepath,
            is_optional=use_defaults,
        )
        if fire is not None:
            fire_activate = ConfigLoader.get_mandatory_field(
                parent_dict=fire,
                tag=ConfigTag.activate,
                parent_tag=ConfigTag.fire,
                filepath=filepath,
            )
            fire_ignition_points = ConfigLoader.get_mandatory_field(
                parent_dict=fire,
                tag=ConfigTag.ignition_points,
                parent_tag=ConfigTag.fire,
                filepath=filepath,
            )
            fire_cell_size = ConfigLoader.get_mandatory_field(
                parent_dict=fire,
                tag=ConfigTag.fire_cell_size,
                parent_tag=ConfigTag.fire,
                filepath=filepath,
            )
            fire_threshold = ConfigLoader.get_mandatory_field(
                parent_dict=fire,
                tag=ConfigTag.fire_threshold,
                parent_tag=ConfigTag.fire,
                filepath=filepath,
            )
            fire_tagging_index = ConfigLoader.get_mandatory_field(
                parent_dict=fire,
                tag=ConfigTag.tagging_index,
                parent_tag=ConfigTag.fire,
                filepath=filepath,
            )
            fire_seed = ConfigLoader.get_field(
                parent_dict=fire,
                tag=ConfigTag.fire_seed,
                parent_tag=ConfigTag.fire,
                filepath=filepath,
                is_optional=True,
            )
            fire_config = Config.FireConfig(
                activate=fire_activate,
                ignition_points=fire_ignition_points,
                fire_cell_size=fire_cell_size,
                fire_threshold=fire_threshold,
                tagging_index=fire_tagging_index,
                seed=fire_seed,
            )
        else:
            fire_config = default_config.fire

        # Rendering
        rendering = ConfigLoader.get_mandatory_field(
            parent_dict=json_dict,
            tag=ConfigTag.rendering,
            parent_tag=ConfigTag.root,
            filepath=filepath,
        )

        export_images = ConfigLoader.get_mandatory_field(
            parent_dict=rendering,
            tag=ConfigTag.export_images,
            parent_tag=ConfigTag.rendering,
            filepath=filepath,
        )

        export_scene = ConfigLoader.get_field(
            parent_dict=rendering,
            tag=ConfigTag.export_scene,
            parent_tag=ConfigTag.rendering,
            filepath=filepath,
            is_optional=use_defaults,
        )

        device_type = ConfigLoader.get_mandatory_field(
            parent_dict=rendering,
            tag=ConfigTag.device_type,
            parent_tag=ConfigTag.rendering,
            filepath=filepath,
        )

        camera_type = ConfigLoader.get_mandatory_field(
            parent_dict=rendering,
            tag=ConfigTag.camera_type,
            parent_tag=ConfigTag.rendering,
            filepath=filepath,
        )

        ground_sampling_distance = ConfigLoader.get_mandatory_field(
            parent_dict=rendering,
            tag=ConfigTag.ground_sampling_distance,
            parent_tag=ConfigTag.rendering,
            filepath=filepath,
        )

        tile_size = ConfigLoader.get_mandatory_field(
            parent_dict=rendering,
            tag=ConfigTag.tile_size,
            parent_tag=ConfigTag.rendering,
            filepath=filepath,
        )

        output_config = Config.OutputConfig(
            export_img=export_images,
            export_scene=export_scene,
            device_type=device_type,
            camera_type=camera_type,
            tile_size=tile_size,
            ground_sampling_distance=ground_sampling_distance,
        )

        objects = ConfigLoader.get_mandatory_field(
            parent_dict=rendering,
            tag=ConfigTag.objects,
            parent_tag=ConfigTag.rendering,
            filepath=filepath,
        )

        # Buildings
        building_render = ConfigLoader.get_field(
            parent_dict=objects,
            tag=ConfigTag.building_render,
            parent_tag=ConfigTag.objects,
            filepath=filepath,
            is_optional=use_defaults,
        )
        if building_render is not None:
            building_geometry_node_file = ConfigLoader.get_mandatory_field(
                parent_dict=building_render,
                tag=ConfigTag.geometry_node_file,
                parent_tag=ConfigTag.building_render,
                filepath=filepath,
            )
            building_geometry_node_name = ConfigLoader.get_mandatory_field(
                parent_dict=building_render,
                tag=ConfigTag.geometry_node_name,
                parent_tag=ConfigTag.building_render,
                filepath=filepath,
            )
            building_tagging_index = ConfigLoader.get_mandatory_field(
                parent_dict=building_render,
                tag=ConfigTag.tagging_index,
                parent_tag=ConfigTag.building_render,
                filepath=filepath,
            )
            building_default_levels_min = ConfigLoader.get_mandatory_field(
                parent_dict=building_render,
                tag=ConfigTag.default_levels_min,
                parent_tag=ConfigTag.building_render,
                filepath=filepath,
            )
            building_default_levels_max = ConfigLoader.get_mandatory_field(
                parent_dict=building_render,
                tag=ConfigTag.default_levels_max,
                parent_tag=ConfigTag.building_render,
                filepath=filepath,
            )

            building_render_config = Config.BuildingRendererConfig(
                geometry_node_file=building_geometry_node_file,
                geometry_node_name=building_geometry_node_name,
                tagging_index=building_tagging_index,
                default_levels_min=building_default_levels_min,
                default_levels_max=building_default_levels_max,
            )
        else:
            building_render_config = default_config.rendering.building_render_config

        # Houses
        house_render = ConfigLoader.get_field(
            parent_dict=objects,
            tag=ConfigTag.house_render,
            parent_tag=ConfigTag.objects,
            filepath=filepath,
            is_optional=use_defaults,
        )
        if house_render is not None:
            house_geometry_node_file = ConfigLoader.get_mandatory_field(
                parent_dict=house_render,
                tag=ConfigTag.geometry_node_file,
                parent_tag=ConfigTag.house_render,
                filepath=filepath,
            )
            house_geometry_node_name = ConfigLoader.get_mandatory_field(
                parent_dict=house_render,
                tag=ConfigTag.geometry_node_name,
                parent_tag=ConfigTag.house_render,
                filepath=filepath,
            )
            house_tagging_index = ConfigLoader.get_mandatory_field(
                parent_dict=house_render,
                tag=ConfigTag.tagging_index,
                parent_tag=ConfigTag.house_render,
                filepath=filepath,
            )
            house_default_height_min = ConfigLoader.get_mandatory_field(
                parent_dict=house_render,
                tag=ConfigTag.default_height_min,
                parent_tag=ConfigTag.house_render,
                filepath=filepath,
            )
            house_default_height_max = ConfigLoader.get_mandatory_field(
                parent_dict=house_render,
                tag=ConfigTag.default_height_max,
                parent_tag=ConfigTag.house_render,
                filepath=filepath,
            )
            house_roof_slope = ConfigLoader.get_mandatory_field(
                parent_dict=house_render,
                tag=ConfigTag.roof_slope_degrees,
                parent_tag=ConfigTag.house_render,
                filepath=filepath,
            )

            house_render_config = Config.HouseRendererConfig(
                geometry_node_file=house_geometry_node_file,
                geometry_node_name=house_geometry_node_name,
                tagging_index=house_tagging_index,
                default_height_min=house_default_height_min,
                default_height_max=house_default_height_max,
                roof_slope=house_roof_slope,
            )
        else:
            house_render_config = default_config.rendering.house_render_config

        # Churches
        church_render = ConfigLoader.get_field(
            parent_dict=objects,
            tag=ConfigTag.church_render,
            parent_tag=ConfigTag.objects,
            filepath=filepath,
            is_optional=use_defaults,
        )
        if church_render is not None:
            church_geometry_node_file = ConfigLoader.get_mandatory_field(
                parent_dict=church_render,
                tag=ConfigTag.geometry_node_file,
                parent_tag=ConfigTag.church_render,
                filepath=filepath,
            )
            church_geometry_node_name = ConfigLoader.get_mandatory_field(
                parent_dict=church_render,
                tag=ConfigTag.geometry_node_name,
                parent_tag=ConfigTag.church_render,
                filepath=filepath,
            )
            church_tagging_index = ConfigLoader.get_mandatory_field(
                parent_dict=church_render,
                tag=ConfigTag.tagging_index,
                parent_tag=ConfigTag.church_render,
                filepath=filepath,
            )
            church_default_levels_min = ConfigLoader.get_mandatory_field(
                parent_dict=church_render,
                tag=ConfigTag.default_levels_min,
                parent_tag=ConfigTag.church_render,
                filepath=filepath,
            )
            church_default_levels_max = ConfigLoader.get_mandatory_field(
                parent_dict=church_render,
                tag=ConfigTag.default_levels_max,
                parent_tag=ConfigTag.church_render,
                filepath=filepath,
            )

            church_render_config = Config.BuildingRendererConfig(
                geometry_node_file=church_geometry_node_file,
                geometry_node_name=church_geometry_node_name,
                tagging_index=church_tagging_index,
                default_levels_min=church_default_levels_min,
                default_levels_max=church_default_levels_max,
            )
        else:
            church_render_config = default_config.rendering.church_render_config

        # Factories
        factory_render = ConfigLoader.get_field(
            parent_dict=objects,
            tag=ConfigTag.factory_render,
            parent_tag=ConfigTag.objects,
            filepath=filepath,
            is_optional=use_defaults,
        )
        if factory_render is not None:
            factory_geometry_node_file = ConfigLoader.get_mandatory_field(
                parent_dict=factory_render,
                tag=ConfigTag.geometry_node_file,
                parent_tag=ConfigTag.factory_render,
                filepath=filepath,
            )
            factory_geometry_node_name = ConfigLoader.get_mandatory_field(
                parent_dict=factory_render,
                tag=ConfigTag.geometry_node_name,
                parent_tag=ConfigTag.factory_render,
                filepath=filepath,
            )
            factory_tagging_index = ConfigLoader.get_mandatory_field(
                parent_dict=factory_render,
                tag=ConfigTag.tagging_index,
                parent_tag=ConfigTag.factory_render,
                filepath=filepath,
            )
            factory_default_levels_min = ConfigLoader.get_mandatory_field(
                parent_dict=factory_render,
                tag=ConfigTag.default_levels_min,
                parent_tag=ConfigTag.factory_render,
                filepath=filepath,
            )
            factory_default_levels_max = ConfigLoader.get_mandatory_field(
                parent_dict=factory_render,
                tag=ConfigTag.default_levels_max,
                parent_tag=ConfigTag.factory_render,
                filepath=filepath,
            )

            factory_render_config = Config.BuildingRendererConfig(
                geometry_node_file=factory_geometry_node_file,
                geometry_node_name=factory_geometry_node_name,
                tagging_index=factory_tagging_index,
                default_levels_min=factory_default_levels_min,
                default_levels_max=factory_default_levels_max,
            )
        else:
            factory_render_config = default_config.rendering.factory_render_config

        # Malls
        mall_render = ConfigLoader.get_field(
            parent_dict=objects,
            tag=ConfigTag.mall_render,
            parent_tag=ConfigTag.objects,
            filepath=filepath,
            is_optional=use_defaults,
        )
        if mall_render is not None:
            mall_geometry_node_file = ConfigLoader.get_mandatory_field(
                parent_dict=mall_render,
                tag=ConfigTag.geometry_node_file,
                parent_tag=ConfigTag.mall_render,
                filepath=filepath,
            )
            mall_geometry_node_name = ConfigLoader.get_mandatory_field(
                parent_dict=mall_render,
                tag=ConfigTag.geometry_node_name,
                parent_tag=ConfigTag.mall_render,
                filepath=filepath,
            )
            mall_tagging_index = ConfigLoader.get_mandatory_field(
                parent_dict=mall_render,
                tag=ConfigTag.tagging_index,
                parent_tag=ConfigTag.mall_render,
                filepath=filepath,
            )
            mall_default_levels_min = ConfigLoader.get_mandatory_field(
                parent_dict=mall_render,
                tag=ConfigTag.default_levels_min,
                parent_tag=ConfigTag.mall_render,
                filepath=filepath,
            )
            mall_default_levels_max = ConfigLoader.get_mandatory_field(
                parent_dict=mall_render,
                tag=ConfigTag.default_levels_max,
                parent_tag=ConfigTag.mall_render,
                filepath=filepath,
            )

            mall_render_config = Config.BuildingRendererConfig(
                geometry_node_file=mall_geometry_node_file,
                geometry_node_name=mall_geometry_node_name,
                tagging_index=mall_tagging_index,
                default_levels_min=mall_default_levels_min,
                default_levels_max=mall_default_levels_max,
            )
        else:
            mall_render_config = default_config.rendering.mall_render_config

        # Flood
        flood_render = ConfigLoader.get_field(
            parent_dict=objects,
            tag=ConfigTag.flood_render,
            parent_tag=ConfigTag.objects,
            filepath=filepath,
            is_optional=use_defaults,
        )
        if flood_render is not None:
            flood_geometry_node_file = ConfigLoader.get_mandatory_field(
                parent_dict=flood_render,
                tag=ConfigTag.geometry_node_file,
                parent_tag=ConfigTag.flood_render,
                filepath=filepath,
            )
            flood_geometry_node_name = ConfigLoader.get_mandatory_field(
                parent_dict=flood_render,
                tag=ConfigTag.geometry_node_name,
                parent_tag=ConfigTag.flood_render,
                filepath=filepath,
            )
            flood_tagging_index = ConfigLoader.get_mandatory_field(
                parent_dict=flood_render,
                tag=ConfigTag.tagging_index,
                parent_tag=ConfigTag.flood_render,
                filepath=filepath,
            )

            flood_render_config = Config.RenderObjectConfig(
                geometry_node_file=flood_geometry_node_file,
                geometry_node_name=flood_geometry_node_name,
                tagging_index=flood_tagging_index,
            )
        else:
            flood_render_config = default_config.rendering.flood_render_config

        # Forest
        placeholder_forest_render = ConfigLoader.get_field(
            parent_dict=objects,
            tag=ConfigTag.placeholder_forest_render,
            parent_tag=ConfigTag.objects,
            filepath=filepath,
            is_optional=use_defaults,
        )
        if placeholder_forest_render is not None:
            placeholder_forest_geometry_node_file = ConfigLoader.get_mandatory_field(
                parent_dict=placeholder_forest_render,
                tag=ConfigTag.geometry_node_file,
                parent_tag=ConfigTag.placeholder_forest_render,
                filepath=filepath,
            )
            placeholder_forest_geometry_node_name = ConfigLoader.get_mandatory_field(
                parent_dict=placeholder_forest_render,
                tag=ConfigTag.geometry_node_name,
                parent_tag=ConfigTag.placeholder_forest_render,
                filepath=filepath,
            )
            placeholder_forest_tagging_index = ConfigLoader.get_mandatory_field(
                parent_dict=placeholder_forest_render,
                tag=ConfigTag.tagging_index,
                parent_tag=ConfigTag.placeholder_forest_render,
                filepath=filepath,
            )

            placeholder_forest_render_config = Config.RenderObjectConfig(
                geometry_node_file=placeholder_forest_geometry_node_file,
                geometry_node_name=placeholder_forest_geometry_node_name,
                tagging_index=placeholder_forest_tagging_index,
            )
        else:
            placeholder_forest_render_config = (
                default_config.rendering.placeholder_forest_render_config
            )

        pretty_forest_render = ConfigLoader.get_field(
            parent_dict=objects,
            tag=ConfigTag.pretty_forest_render,
            parent_tag=ConfigTag.objects,
            filepath=filepath,
            is_optional=use_defaults,
        )
        if pretty_forest_render is not None:
            pretty_forest_geometry_node_file = ConfigLoader.get_mandatory_field(
                parent_dict=pretty_forest_render,
                tag=ConfigTag.geometry_node_file,
                parent_tag=ConfigTag.pretty_forest_render,
                filepath=filepath,
            )
            pretty_forest_geometry_node_name = ConfigLoader.get_mandatory_field(
                parent_dict=pretty_forest_render,
                tag=ConfigTag.geometry_node_name,
                parent_tag=ConfigTag.pretty_forest_render,
                filepath=filepath,
            )
            pretty_forest_tagging_index = ConfigLoader.get_mandatory_field(
                parent_dict=pretty_forest_render,
                tag=ConfigTag.tagging_index,
                parent_tag=ConfigTag.pretty_forest_render,
                filepath=filepath,
            )

            pretty_forest_render_config = Config.RenderObjectConfig(
                geometry_node_file=pretty_forest_geometry_node_file,
                geometry_node_name=pretty_forest_geometry_node_name,
                tagging_index=pretty_forest_tagging_index,
            )
        else:
            pretty_forest_render_config = (
                default_config.rendering.pretty_forest_render_config
            )

        # Road
        road_render = ConfigLoader.get_field(
            parent_dict=objects,
            tag=ConfigTag.road_render,
            parent_tag=ConfigTag.objects,
            filepath=filepath,
            is_optional=use_defaults,
        )
        if road_render is not None:
            road_geometry_node_file = ConfigLoader.get_mandatory_field(
                parent_dict=road_render,
                tag=ConfigTag.geometry_node_file,
                parent_tag=ConfigTag.road_render,
                filepath=filepath,
            )
            road_geometry_node_name = ConfigLoader.get_mandatory_field(
                parent_dict=road_render,
                tag=ConfigTag.geometry_node_name,
                parent_tag=ConfigTag.road_render,
                filepath=filepath,
            )
            car_collection_info_node_name = ConfigLoader.get_mandatory_field(
                parent_dict=road_render,
                tag=ConfigTag.car_collection_info_node_name,
                parent_tag=ConfigTag.road_render,
                filepath=filepath,
            )
            road_tagging_index = ConfigLoader.get_mandatory_field(
                parent_dict=road_render,
                tag=ConfigTag.tagging_index,
                parent_tag=ConfigTag.road_render,
                filepath=filepath,
            )
            car_tagging_index = ConfigLoader.get_mandatory_field(
                parent_dict=road_render,
                tag=ConfigTag.car_tagging_index,
                parent_tag=ConfigTag.road_render,
                filepath=filepath,
            )

            road_render_config = Config.RoadRendererConfig(
                geometry_node_file=road_geometry_node_file,
                geometry_node_name=road_geometry_node_name,
                car_collection_info_node_name=car_collection_info_node_name,
                road_tagging_index=road_tagging_index,
                car_tagging_index=car_tagging_index,
            )
        else:
            road_render_config = default_config.rendering.road_render_config

        # Bridge
        bridge_render = ConfigLoader.get_field(
            parent_dict=objects,
            tag=ConfigTag.bridge_render,
            parent_tag=ConfigTag.objects,
            filepath=filepath,
            is_optional=use_defaults,
        )
        if bridge_render is not None:
            bridge_geometry_node_file = ConfigLoader.get_mandatory_field(
                parent_dict=bridge_render,
                tag=ConfigTag.geometry_node_file,
                parent_tag=ConfigTag.bridge_render,
                filepath=filepath,
            )
            bridge_geometry_node_name = ConfigLoader.get_mandatory_field(
                parent_dict=bridge_render,
                tag=ConfigTag.geometry_node_name,
                parent_tag=ConfigTag.bridge_render,
                filepath=filepath,
            )
            bridge_group_name = ConfigLoader.get_mandatory_field(
                parent_dict=bridge_render,
                tag=ConfigTag.bridge_group_name,
                parent_tag=ConfigTag.bridge_render,
                filepath=filepath,
            )
            bridge_tagging_index = ConfigLoader.get_mandatory_field(
                parent_dict=bridge_render,
                tag=ConfigTag.tagging_index,
                parent_tag=ConfigTag.bridge_render,
                filepath=filepath,
            )

            bridge_render_config = Config.BridgeRendererConfig(
                geometry_node_file=bridge_geometry_node_file,
                geometry_node_name=bridge_geometry_node_name,
                tagging_index=bridge_tagging_index,
                bridge_group_name=bridge_group_name,
            )
        else:
            bridge_render_config = default_config.rendering.bridge_render_config

        # Water
        water_render = ConfigLoader.get_field(
            parent_dict=objects,
            tag=ConfigTag.water_render,
            parent_tag=ConfigTag.objects,
            filepath=filepath,
            is_optional=use_defaults,
        )
        if water_render is not None:
            water_geometry_node_file = ConfigLoader.get_mandatory_field(
                parent_dict=water_render,
                tag=ConfigTag.geometry_node_file,
                parent_tag=ConfigTag.water_render,
                filepath=filepath,
            )
            water_geometry_node_name = ConfigLoader.get_mandatory_field(
                parent_dict=water_render,
                tag=ConfigTag.geometry_node_name,
                parent_tag=ConfigTag.water_render,
                filepath=filepath,
            )
            water_tagging_index = ConfigLoader.get_mandatory_field(
                parent_dict=water_render,
                tag=ConfigTag.tagging_index,
                parent_tag=ConfigTag.water_render,
                filepath=filepath,
            )

            water_render_config = Config.RenderObjectConfig(
                geometry_node_file=water_geometry_node_file,
                geometry_node_name=water_geometry_node_name,
                tagging_index=water_tagging_index,
            )
        else:
            water_render_config = default_config.rendering.water_render_config

        # Terrain
        terrain_render = ConfigLoader.get_field(
            parent_dict=objects,
            tag=ConfigTag.terrain_render,
            parent_tag=ConfigTag.objects,
            filepath=filepath,
            is_optional=use_defaults,
        )
        if terrain_render is not None:
            terrain_geometry_node_file = ConfigLoader.get_mandatory_field(
                parent_dict=terrain_render,
                tag=ConfigTag.geometry_node_file,
                parent_tag=ConfigTag.terrain_render,
                filepath=filepath,
            )
            terrain_adaptation_node_name = ConfigLoader.get_mandatory_field(
                parent_dict=terrain_render,
                tag=ConfigTag.adaptation_node_name,
                parent_tag=ConfigTag.terrain_render,
                filepath=filepath,
            )
            terrain_tagging_node_name = ConfigLoader.get_mandatory_field(
                parent_dict=terrain_render,
                tag=ConfigTag.tagging_node_name,
                parent_tag=ConfigTag.terrain_render,
                filepath=filepath,
            )
            terrain_decorating_node_name = ConfigLoader.get_mandatory_field(
                parent_dict=terrain_render,
                tag=ConfigTag.decorating_node_name,
                parent_tag=ConfigTag.terrain_render,
                filepath=filepath,
            )
            terrain_base_material_name = ConfigLoader.get_mandatory_field(
                parent_dict=terrain_render,
                tag=ConfigTag.base_material_name,
                parent_tag=ConfigTag.terrain_render,
                filepath=filepath,
            )
            terrain_tagged_material_name = ConfigLoader.get_mandatory_field(
                parent_dict=terrain_render,
                tag=ConfigTag.tagged_material_name,
                parent_tag=ConfigTag.terrain_render,
                filepath=filepath,
            )
            terrain_tagging_index = ConfigLoader.get_mandatory_field(
                parent_dict=terrain_render,
                tag=ConfigTag.tagging_index,
                parent_tag=ConfigTag.terrain_render,
                filepath=filepath,
            )
            decor_tagging_index = ConfigLoader.get_mandatory_field(
                parent_dict=terrain_render,
                tag=ConfigTag.decor_tagging_index,
                parent_tag=ConfigTag.terrain_render,
                filepath=filepath,
            )

            terrain_render_config = Config.TerrainRendererConfig(
                geometry_node_file=terrain_geometry_node_file,
                adaptation_node_name=terrain_adaptation_node_name,
                tagging_node_name=terrain_tagging_node_name,
                decorating_node_name=terrain_decorating_node_name,
                base_material_name=terrain_base_material_name,
                tagged_material_name=terrain_tagged_material_name,
                tagging_index=terrain_tagging_index,
                decor_tagging_index=decor_tagging_index,
            )
        else:
            terrain_render_config = default_config.rendering.terrain_render_config

        render_config = Config.RenderingConfig(
            output=output_config,
            building_render_config=building_render_config,
            house_render_config=house_render_config,
            church_render_config=church_render_config,
            factory_render_config=factory_render_config,
            mall_render_config=mall_render_config,
            flood_render_config=flood_render_config,
            placeholder_forest_render_config=placeholder_forest_render_config,
            pretty_forest_render_config=pretty_forest_render_config,
            road_render_config=road_render_config,
            bridge_render_config=bridge_render_config,
            water_render_config=water_render_config,
            terrain_render_config=terrain_render_config,
        )

        config = Config.Config(
            base_folder=base_folder,
            data_source=input_data_type,
            geo_window=window_config,
            terrain=terrain_config,
            flood=flood_config,
            fire=fire_config,
            rendering=render_config,
        )

        return config
