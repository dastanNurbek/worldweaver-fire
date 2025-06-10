import os
import shutil

from datetime import datetime
from time import time

import numpy as np

from mage_procgen.Drivers.IGN.IGNDriver import IGNDriver
from mage_procgen.Drivers.OSM.OSMDriver import OSMDriver
from mage_procgen.Loader.ConfigLoader import ConfigLoader
from mage_procgen.Processor.FloodProcessor import FloodProcessor
from mage_procgen.Manager.RenderManager import RenderManager

from mage_procgen.Utils.Logging import (
    setup_logger,
    logger,
)
from mage_procgen.Utils.Rendering import (
    export_rendered_img,
    setup_img_persp,
    setup_img_ortho_res,
    setup_compositing_render,
    set_compositing_render_image_name,
    check_is_sun_activated,
    CameraType,
)
from mage_procgen.Utils.DataFiles import (
    check_shapefiles_presence,
    setup_project_folder,
    setup_export_folder,
    log_folder,
    log_file_name,
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

    export_folder = setup_export_folder(project_path)

    config_filename = os.path.basename(config_status.config_file_path)
    shutil.copyfile(
        config_status.config_file_path,
        os.path.join(project_path, config_filename),
    )

    setup_compositing_render(export_folder, config)

    if not config.rendering.output.export_img:

        now = datetime.now()
        now_str = now.strftime("%Y_%m_%d:%H:%M:%S:%f")
        set_compositing_render_image_name(now_str + "_tagging")

        if config.rendering.output.camera_type == CameraType.PERSPECTIVE:
            setup_img_persp(
                config.rendering.output.tile_size,
                config.rendering.output.ground_sampling_distance,
                (0, 0, 0),
            )

        else:
            setup_img_ortho_res(
                config.rendering.output.tile_size,
                config.rendering.output.ground_sampling_distance,
                (0, 0, 0),
            )

        render_manager.draw_decor(False)
        export_rendered_img(export_folder, now_str)
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
                            (camera_x, camera_y, 0),
                        )
                        # Beautify
                        zone_window = render_manager.draw_decor(True, True)
                    else:
                        setup_img_ortho_res(
                            config.rendering.output.tile_size,
                            config.rendering.output.ground_sampling_distance,
                            (camera_x, camera_y, 0),
                        )
                        zone_window = render_manager.draw_decor(True)

                    set_compositing_render_image_name(now_str + "_tagging")
                    export_rendered_img(export_folder, now_str)

                    # Clean
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

    stop_time = time()

    logger.info(f"Done in {(stop_time - start_time):.3f} seconds")


def select_driver(config, project_path):
    if config.data_source in OSMDriver.get_supported_sources():
        return OSMDriver(config, project_path)
    elif config.data_source in IGNDriver.get_supported_sources():
        return IGNDriver(config, project_path)
    else:
        raise ValueError("Unsupported data source in config file:", config.data_source)


if __name__ == "__main__":
    main("")
