import os
import shutil

from datetime import datetime
from time import time

import numpy as np
from PIL import Image
from scipy.ndimage import zoom

from worldweaver.Drivers.BaseDriver import BaseDriver
from worldweaver.Drivers.IGN.IGNDriver import IGNDriver
from worldweaver.Drivers.OSM.OSMDriver import OSMDriver
from worldweaver.Loader.ConfigLoader import ConfigLoader
from worldweaver.Processor.FloodProcessor import FloodProcessor
from worldweaver.Processor.FireProcessor import FireProcessor
from worldweaver.Manager.RenderManager import RenderManager

from worldweaver.Utils.Config import Config
from worldweaver.Utils.Logging import (
    setup_logger,
    logger,
)
from worldweaver.Utils.Rendering import (
    export_rendered_img,
    setup_img_persp,
    setup_img_ortho_res,
    setup_compositing_render,
    set_compositing_render_image_name,
    check_is_sun_activated,
    CameraType,
)
from worldweaver.Utils.DataFiles import (
    check_shapefiles_presence,
    setup_project_folder,
    setup_rendering_folder,
    log_folder,
    log_file_name,
)
from worldweaver.Utils.Export import export_scene_to_tileset


def _render_pass(config, render_manager, export_folder, project_path, driver, fire_data, suffix):
    if not config.rendering.output.export_img:
        now_str = datetime.now().strftime("%Y_%m_%d:%H:%M:%S:%f")
        set_compositing_render_image_name(now_str + suffix + "_tagging")

        if config.rendering.output.camera_type == CameraType.PERSPECTIVE:
            setup_img_persp(
                config.rendering.output.tile_size,
                config.rendering.output.ground_sampling_distance,
                (0, 0),
            )
        else:
            setup_img_ortho_res(
                config.rendering.output.tile_size,
                config.rendering.output.ground_sampling_distance,
                (0, 0),
            )

        render_manager.draw_decor(False)
        logger.info("Drawing scene done")
        logger.info("Rendering sample image")
        export_rendered_img(config.base_folder, export_folder, now_str + suffix)

        if config.rendering.output.export_scene:
            export_scene_to_tileset(project_path)
    else:
        render_times = []

        img_size = (
            config.rendering.output.tile_size
            * config.rendering.output.ground_sampling_distance
        )

        camera_step = img_size * 0.9

        scene_box = driver.geo_window.bounds
        camera_x_min = scene_box[0] - driver.geo_window.center[0] + img_size / 2
        camera_x_max = scene_box[2] - driver.geo_window.center[0] - img_size / 2
        camera_y_min = scene_box[1] - driver.geo_window.center[1] + img_size / 2
        camera_y_max = scene_box[3] - driver.geo_window.center[1] - img_size / 2

        for camera_x in np.arange(camera_x_min, camera_x_max, camera_step):
            for camera_y in np.arange(camera_y_min, camera_y_max, camera_step):
                try:
                    now = datetime.now()
                    now_str = now.strftime("%Y_%m_%d:%H:%M:%S:%f")

                    if config.rendering.output.camera_type == CameraType.PERSPECTIVE:
                        setup_img_persp(
                            config.rendering.output.tile_size,
                            config.rendering.output.ground_sampling_distance,
                            (camera_x, camera_y),
                        )
                        zone_window = render_manager.draw_decor(True, True)
                    else:
                        setup_img_ortho_res(
                            config.rendering.output.tile_size,
                            config.rendering.output.ground_sampling_distance,
                            (camera_x, camera_y),
                        )
                        zone_window = render_manager.draw_decor(True)

                    set_compositing_render_image_name(now_str + suffix + "_tagging")
                    export_rendered_img(config.base_folder, export_folder, now_str + suffix)

                    if fire_data is not None:
                        is_burnt, lower_left, upper_right, fire_cell_size = fire_data
                        gsd = config.rendering.output.ground_sampling_distance
                        tile_x_min = driver.geo_window.center[0] + camera_x - img_size / 2
                        tile_x_max = driver.geo_window.center[0] + camera_x + img_size / 2
                        tile_y_min = driver.geo_window.center[1] + camera_y - img_size / 2
                        tile_y_max = driver.geo_window.center[1] + camera_y + img_size / 2
                        col_min = max(0, int((tile_x_min - lower_left[0]) / fire_cell_size))
                        col_max = min(is_burnt.shape[1], int((tile_x_max - lower_left[0]) / fire_cell_size))
                        row_min = max(0, int((upper_right[1] - tile_y_max) / fire_cell_size))
                        row_max = min(is_burnt.shape[0], int((upper_right[1] - tile_y_min) / fire_cell_size))
                        tile_burnt = is_burnt[row_min:row_max, col_min:col_max]
                        tile_burnt_hires = zoom(tile_burnt.astype(float), fire_cell_size / gsd, order=0) > 0.5
                        Image.fromarray((tile_burnt_hires * 255).astype(np.uint8), mode='L').save(
                            os.path.join(export_folder, now_str + suffix + "_burnt.png")
                        )

                    render_manager.clean_zone()
                    render_times.append(datetime.now() - now)

                except Exception as error:
                    logger.exception("Could not generate an image", exc_info=error)

        logger.info(
            f"Generated {len(render_times)} image pairs. "
            f"Min render time: {min(render_times).total_seconds():.3f}. "
            f"Max: {max(render_times).total_seconds():.3f}. "
            f"Average: {np.average(render_times).total_seconds():.3f}"
        )


def main(filepath):

    start_time = time()

    config_status = ConfigLoader.load(filepath)
    config = config_status.config

    if ".." in config.base_folder:
        _location = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__))
        )
        config.base_folder = os.path.realpath(
            os.path.join(_location, config.base_folder)
        )

    setup_logger(
        os.path.join(config.base_folder, log_folder), log_file_name, add_debug=False
    )
    logger.info("Worldweaver starting")
    for log_message in config_status.log_messages:
        logger.info(log_message)

    # Pre-run checks
    check_is_sun_activated()

    check_shapefiles_presence(config.base_folder)

    project_path = setup_project_folder(config.base_folder)

    driver = select_driver(config, project_path)

    rendering_data = driver.process()

    render_manager = RenderManager(
        driver.terrain_data,
        rendering_data,
        driver.geo_window,
        driver.internal_crs,
        config,
    )
    render_manager.draw_terrain()

    if config.flood.activate:

        render_manager.change_non_sources_visibility(False)

        # First render: writing a height map
        logger.info("Computing height map")
        FloodProcessor.generate_height_map(
            config.base_folder,
            driver.geo_window,
            config.flood.flood_cell_size,
        )

        render_manager.change_terrain_visibility(False)

        # Second render: getting a semantic map without terrain
        # We have to hide terrain because it's very irregular in rivers, and thus terrain often clips through river surface,
        # Making flood init worse
        logger.info("Computing sources")
        FloodProcessor.generate_semantic_map(
            config.base_folder,
            driver.geo_window,
            config.flood.flood_cell_size,
        )

        render_manager.change_terrain_visibility(True)

        flood_threshold = 1000
        flood_data = FloodProcessor.flood(
            config.base_folder,
            driver.geo_window,
            config.flood.flood_height,
            flood_threshold,
            config.flood.flood_cell_size,
        )

        render_manager.draw_flood(flood_data)

        render_manager.change_non_sources_visibility(True)

    fire_data = None

    if config.fire.activate:
        if config.fire.ignition_points:
            import geopandas as g
            from shapely.geometry import Point
            ignition_gdf = g.GeoDataFrame(
                geometry=[Point(lon, lat) for lon, lat in config.fire.ignition_points],
                crs=4326,
            ).to_crs(driver.internal_crs)
            ignition_points_crs = [(geom.x, geom.y) for geom in ignition_gdf.geometry]
        else:
            ignition_points_crs = []

        fire_data = FireProcessor.burn(
            driver.geo_window,
            rendering_data.forests,
            rendering_data.zones.wheatfields,
            rendering_data.zones.cornfields,
            rendering_data.zones.grass,
            rendering_data.zones.paths,
            rendering_data.roads,
            ignition_points_crs,
            config.fire.fire_cell_size,
            config.fire.fire_threshold,
            config.fire.seed,
        )

    export_folder = setup_rendering_folder(project_path)

    config_filename = os.path.basename(config_status.config_file_path)
    shutil.copyfile(
        config_status.config_file_path,
        os.path.join(project_path, config_filename),
    )

    setup_compositing_render(export_folder, config)

    do_pre_fire_render = fire_data is not None and config.fire.save_pre_fire_render

    if not config.rendering.output.export_img and do_pre_fire_render:
        # Single-shot mode with pre-fire: draw decor once, render twice around draw_fire
        now_str = datetime.now().strftime("%Y_%m_%d:%H:%M:%S:%f")

        if config.rendering.output.camera_type == CameraType.PERSPECTIVE:
            setup_img_persp(
                config.rendering.output.tile_size,
                config.rendering.output.ground_sampling_distance,
                (0, 0),
            )
        else:
            setup_img_ortho_res(
                config.rendering.output.tile_size,
                config.rendering.output.ground_sampling_distance,
                (0, 0),
            )

        render_manager.draw_decor(False)
        logger.info("Drawing scene done")

        set_compositing_render_image_name(now_str + "_pre_fire_tagging")
        logger.info("Rendering pre-fire sample image")
        export_rendered_img(config.base_folder, export_folder, now_str + "_pre_fire")

        render_manager.draw_fire(fire_data)
        render_manager.update_forests_for_fire()

        now_str = datetime.now().strftime("%Y_%m_%d:%H:%M:%S:%f")
        set_compositing_render_image_name(now_str + "_tagging")
        logger.info("Rendering post-fire sample image")
        export_rendered_img(config.base_folder, export_folder, now_str)

        if config.rendering.output.export_scene:
            export_scene_to_tileset(project_path)
    else:
        if do_pre_fire_render:
            logger.info("Rendering pre-fire scene")
            _render_pass(config, render_manager, export_folder, project_path, driver, fire_data=None, suffix="_pre_fire")

        if fire_data is not None:
            render_manager.draw_fire(fire_data)

        _render_pass(config, render_manager, export_folder, project_path, driver, fire_data=fire_data, suffix="")

    stop_time = time()

    logger.info(f"Done in {(stop_time - start_time):.3f} seconds")


def select_driver(config: Config, project_path: str) -> BaseDriver:
    """
    Select the driver used for the project based on the data_source of the config.
    :param config: The configuration of the project.
    :param project_path: The path to the project.
    :return: The selected driver.
    """
    if config.data_source in OSMDriver.get_supported_sources():
        return OSMDriver(config, project_path)
    elif config.data_source in IGNDriver.get_supported_sources():
        return IGNDriver(config, project_path)
    else:
        raise ValueError("Unsupported data source in config file:", config.data_source)


if __name__ == "__main__":
    main("")
