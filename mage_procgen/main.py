# Need to import dependencies of packages, and this folder is not in blender's pythonpath
import shutil

import os
from numpy import arange

from datetime import datetime
from time import time, sleep

from mage_procgen.Utils.DataFiles import (
    config_folder,
    base_config_file,
    default_config_file,
    check_shapefiles_presence,
    setup_project_folder,
    setup_export_folder,
    log_folder,
    log_file_name,
)
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm, tqdm_logging_redirect
from contextlib import redirect_stdout

from mage_procgen.Loader.ConfigLoader import ConfigLoader
from mage_procgen.Processor.FloodProcessor import FloodProcessor
from mage_procgen.Manager.RenderManager import RenderManager
from mage_procgen.Utils.Rendering import (
    export_rendered_img,
    setup_img_persp,
    setup_img_ortho_res,
    setup_compositing_render,
    set_compositing_render_image_name,
    check_is_sun_activated,
)
from mage_procgen.Utils.Logging import (
    setup_logger,
    logger,
)  # get_logger, log_info, log_error
from mage_procgen.Drivers.IGN.IGNDriver import IGNDriver
from mage_procgen.Drivers.OSM.OSMDriver import OSMDriver


def main(filepath):

    start_time = time()
    # Buffering log messages until logger is created
    log_messages = []

    # Loading config
    if len(filepath) > 0:
        log_messages.append("Using config file path given by user")
        config_filepath = filepath
    else:
        log_messages.append("Falling back to default conf")
        _location = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__))
        )
        config_filepath = os.path.realpath(
            os.path.join(_location, config_folder, default_config_file)
        )

        if not os.path.isfile(config_filepath):
            log_messages.append("No config file found, copying base config")
            shutil.copyfile(
                os.path.join(_location, config_folder, base_config_file),
                config_filepath,
            )

    config = ConfigLoader.load(config_filepath)
    if ".." in config.base_folder:
        _location = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__))
        )
        config.base_folder = os.path.realpath(
            os.path.join(_location, config.base_folder)
        )

    setup_logger(os.path.join(config.base_folder, log_folder), log_file_name, False)
    logger.info("Worldweaver starting")
    for log_message in log_messages:
        logger.info(log_message)

    # with redirect_stdout(logger):
    #     print("Test of redirection")
    # TODO: remove this example.
    # Tests of redirection in case we want to print during a tqdm loop
    # Besoin de redirect sinon les logs de tqdm sont pas effacés
    # with logging_redirect_tqdm([logger]):
    #     for i in tqdm(range(9)):
    #
    #         logger.info("processing item number "+ str(i))
    #         sleep(0.1)

    # with tqdm_logging_redirect([_get_logger()]):
    #     for i in tqdm(range(9)):
    #
    #         log_info("processing item number "+ str(i))
    #         sleep(0.1)

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
    render_manager.draw_flood_interactors()

    if config.flood:

        render_manager.change_non_sources_visibility(False)

        # First render: writing a height map
        logger.info("Computing height map")
        FloodProcessor.generate_height_map(
            config.base_folder,
            driver.geo_window,
            config.flood_cell_size,
        )

        render_manager.change_terrain_visibility(False)

        # Second render: getting a semantic map without terrain
        # We have to hide terrain because it's very irregular in rivers, and thus terrain often clips through river surface,
        # Making flood init worse
        logger.info("Computing sources")
        FloodProcessor.generate_semantic_map(
            config.base_folder,
            driver.geo_window,
            config.flood_cell_size,
        )

        render_manager.change_terrain_visibility(True)

        flood_threshold = 1000
        flood_data = FloodProcessor.flood(
            config.base_folder,
            driver.geo_window,
            config.flood_height,
            flood_threshold,
            config.flood_cell_size,
        )

        render_manager.draw_flood(flood_data)

        render_manager.change_non_sources_visibility(True)

    if not config.export_img:

        export_folder = setup_export_folder(project_path)

        config_filename = os.path.basename(config_filepath)
        shutil.copyfile(
            config_filepath,
            os.path.join(project_path, config_filename),
        )

        setup_compositing_render(export_folder, config)
        now = datetime.now()
        now_str = now.strftime("%Y_%m_%d:%H:%M:%S:%f")
        set_compositing_render_image_name(now_str + "_tagging")

        if not config.use_camera_ortho:
            setup_img_persp(
                config.out_img_resolution,
                config.out_img_pixel_size,
                (0, 0, 0),
            )

        else:
            setup_img_ortho_res(
                config.out_img_resolution,
                config.out_img_pixel_size,
                (0, 0, 0),
            )

        render_manager.beautify_zone(False)
        export_rendered_img(export_folder, now_str)

    if config.export_img:

        export_folder = setup_export_folder(project_path)

        config_filename = os.path.basename(config_filepath)
        shutil.copyfile(
            config_filepath,
            os.path.join(project_path, config_filename),
        )

        setup_compositing_render(export_folder, config)

        img_size = config.out_img_resolution * config.out_img_pixel_size

        camera_step = img_size * 0.9

        scene_box = driver.geo_window.bounds
        camera_x_min = scene_box[0] - driver.geo_window.center[0] + img_size / 2
        camera_x_max = scene_box[2] - driver.geo_window.center[0] - img_size / 2
        camera_y_min = scene_box[1] - driver.geo_window.center[1] + img_size / 2
        camera_y_max = scene_box[3] - driver.geo_window.center[1] - img_size / 2

        for camera_x in arange(camera_x_min, camera_x_max, camera_step):
            for camera_y in arange(camera_y_min, camera_y_max, camera_step):
                try:
                    now = datetime.now()
                    now_str = now.strftime("%Y_%m_%d:%H:%M:%S:%f")

                    if not config.use_camera_ortho:
                        setup_img_persp(
                            config.out_img_resolution,
                            config.out_img_pixel_size,
                            (camera_x, camera_y, 0),
                        )
                        # Beautify
                        zone_window = render_manager.beautify_zone(True, True)
                    else:
                        setup_img_ortho_res(
                            config.out_img_resolution,
                            config.out_img_pixel_size,
                            (camera_x, camera_y, 0),
                        )
                        zone_window = render_manager.beautify_zone(True)

                    set_compositing_render_image_name(now_str + "_tagging")

                    export_rendered_img(export_folder, now_str)

                    # Clean
                    render_manager.clean_zone()

                except Exception as error:
                    logger.exception("Could not generate an image", exc_info=error)

    stop_time = time()
    logger.info("Done in " + str(stop_time - start_time))


def select_driver(config, project_path):
    if config.data_source in OSMDriver.supported_data_sources:
        return OSMDriver(config, project_path)
    elif config.data_source in IGNDriver.supported_data_sources:
        return IGNDriver(config, project_path)
    else:
        raise ValueError("Unsupported data source in config file:", config.data_source)


if __name__ == "__main__":
    main("")
