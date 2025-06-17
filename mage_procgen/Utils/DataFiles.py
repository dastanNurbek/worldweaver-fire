import os
import re
import shutil
import subprocess

import funkybob

from mage_procgen.Utils.Logging import logger

rendering = "Rendering"

temp_folder = "TMP"

depth_map_file = "depth_map"

depth_map_file_full_name = "depth_map0001.exr"
semantic_map_file_full_name = "semantic_map0001.png"

temp_rendering_file = "rendering_tmp"

departements = "Departements/"

shapefiles_folder = "Shapefiles"

regions_file = "ARRONDISSEMENT/ARRONDISSEMENT.shp"
regions_archive = "ARRONDISSEMENT.7z"

ocean_file = "OCEAN/water_polygons.shp"
ocean_archive = "OCEAN.7z"

terrain_DB = "RGEALTI"
terrain_data_folder = "MNT"

bdtopo_folder = "BDTOPO"
forest_folder = "OCCUPATION_DU_SOL"
forest_file = "ZONE_DE_VEGETATION.shp"
road_folder = "TRANSPORT"
road_file = "TRONCON_DE_ROUTE.shp"
water_folder = "HYDROGRAPHIE"
water_file = "SURFACE_HYDROGRAPHIQUE.shp"
dpt_folder = "ADMINISTRATIF"
dpt_file = "ARRONDISSEMENT.shp"
town_file = "COMMUNE.shp"
building_folder = "BATI"
building_file = "BATIMENT.shp"
sport_file = "TERRAIN_DE_SPORT.shp"
residential_folder = "LIEUX_NOMMES"
residential_file = "ZONE_D_HABITATION.shp"
interest_zone_folder = "SERVICES_ET_ACTIVITES"
interest_zone_file = "ZONE_D_ACTIVITE_OU_D_INTERET.shp"

bdcarto_folder = "BDCARTO"
landuse_folder = "ZONE_D_OCCUPATION_DU_SOL"
landuse_file = "OCCUPATION_DU_SOL.shp"

rpg_folder = "RPG"
plot_file = "PARCELLES_GRAPHIQUES.shp"

shore_file = "LIMITE_TERRE_MER.shp"

texture_folder = "Textures"
texture_image_DB = "BDORTHO"
delivery = "DONNEES"
delivery_db = "1_DONNEES"
texture_data_folder = "OHR_RVB"

additional = "SUPPLEMENTS"
slab_file = "dalles.shp"

config_folder = "Config"
base_config_file = "base_config.json"
default_config_file = "config.json"

hash_file_extenstion = ".md5"

assets_folder = "Assets"

projects_folder = "Projects"
input_data_folder = "Inputs"

log_folder = "Logs"
log_file_name = "worldweaver.log"
render_log_file = "render.log"


file_coords_regex = re.compile("_[0-9]{4}_[0-9]{4}_")


def setup_bdtopo(base_folder: str, departement: str, archive_file: str):
    """
    Extracts BDTOPO archive, and changes the folders to simplify it from:

        * BDTOPO
            * BDTOPO_3-3_TOUSTHEMES_SHP_LAMB93_D006_2023-06-15
                * BDTOPO
                    * 1_DONNEES_LIVRAISON_2021-04-00084
                         * BDT_3-3_SHP_LAMB93_D006-ED2023-06-15
                             * OCCUPATION_DU_SOL
                                 * ZONE_DE_VEGETATION.shp
                             * TRANSPORT
                                 * TRONCON_DE_ROUTE.shp
                             * HYDROGRAPHIE
                                 * SURFACE_HYDROGRAPHIQUE.shp

    to:

        * BDTOPO:
             * DONNEES
                 * OCCUPATION_DU_SOL
                     * ZONE_DE_VEGETATION.shp
                 * TRANSPORT
                     * TRONCON_DE_ROUTE.shp
                 * HYDROGRAPHIE
                     * SURFACE_HYDROGRAPHIQUE.shp

    Parameters:
        base_folder: base folder of the application (same one as the one written in the config file)
        departement: number of the departement as a 2 character string (ex: "06", "77" ...)
        archive_file: archive of the database (or the first file of the split archive)
    """

    current_base_folder = os.path.join(
        base_folder, departements, str(departement), bdtopo_folder
    )

    archive_name = os.path.basename(archive_file).split(".")[0]

    out_file_option = f"-o{current_base_folder}"

    command_line = f"{get_installed_7z()} x {archive_file} {out_file_option}"

    subprocess.run([command_line], shell=True)

    # BDTOPO_3-3_TOUSTHEMES_SHP_LAMB93_D006_2023-06-15
    path1 = os.path.join(current_base_folder, archive_name)

    # BDTOPO
    dir1 = os.listdir(path1)[0]
    path2 = os.path.join(path1, dir1)

    # 1_DONNEES_LIVRAISON_2021-04-00084
    # os.listdir return order is not sorted. better match by substring
    dir2 = next(x for x in os.listdir(path2) if delivery_db in x)
    path3 = os.path.join(path2, dir2)

    # BDT_3-3_SHP_LAMB93_D006-ED2023-06-15
    # Other file in the directory has the same name but it's the hashfile
    dir3 = next(x for x in os.listdir(path3) if hash_file_extenstion not in x)
    path4 = os.path.join(path3, dir3)

    os.makedirs(
        os.path.join(base_folder, departements, str(departement), bdtopo_folder),
        exist_ok=True,
    )
    os.rename(
        path4,
        os.path.join(
            base_folder, departements, str(departement), bdtopo_folder, delivery
        ),
    )
    shutil.rmtree(path1, ignore_errors=True)


def setup_bdcarto(base_folder: str, departement: str, archive_file: str):
    """
    Extracts BDCARTO archive, and changes the folders to simplify it from:

        * BDCARTO
            * BDCARTO_5-0_TOUSTHEMES_SHP_LAMB93_D006_2024-09-15
                * BDCARTO
                    * 1_DONNEES_LIVRAISON_2024-12-00075
                         * BDC_5-0_SHP_LAMB93_D006-ED2024-09-15
                             * ZONE_D_OCCUPATION_DU_SOL
                                 * OCCUPATION_DU_SOL.shp

    to:

        * BDCARTO:
             * DONNEES
                 * ZONE_D_OCCUPATION_DU_SOL
                     * OCCUPATION_DU_SOL.shp

    Parameters:
        base_folder: base folder of the application (same one as the one written in the config file)
        departement: number of the departement as a 2 character string (ex: "06", "77" ...)
        archive_file: archive of the database (or the first file of the split archive)
    """

    current_base_folder = os.path.join(
        base_folder, departements, str(departement), bdcarto_folder
    )

    archive_name = os.path.basename(archive_file).split(".")[0]

    out_file_option = f"-o{current_base_folder}"

    command_line = f"{get_installed_7z()} x {archive_file} {out_file_option}"

    subprocess.run([command_line], shell=True)

    # BDCARTO_5-0_TOUSTHEMES_SHP_LAMB93_D006_2024-09-15
    path1 = os.path.join(current_base_folder, archive_name)

    # BDCARTO
    dir1 = os.listdir(path1)[0]
    path2 = os.path.join(path1, dir1)

    # 1_DONNEES_LIVRAISON_2024-12-00075
    # os.listdir return order is not sorted. better match by substring
    dir2 = next(x for x in os.listdir(path2) if delivery_db in x)
    path3 = os.path.join(path2, dir2)

    # BDC_5-0_SHP_LAMB93_D006-ED2024-09-15
    # Other file in the directory has the same name but it's the hashfile
    dir3 = next(x for x in os.listdir(path3) if hash_file_extenstion not in x)
    path4 = os.path.join(path3, dir3)

    os.makedirs(
        os.path.join(base_folder, departements, str(departement), bdcarto_folder),
        exist_ok=True,
    )
    os.rename(
        path4,
        os.path.join(
            base_folder, departements, str(departement), bdcarto_folder, delivery
        ),
    )
    shutil.rmtree(path1, ignore_errors=True)


def setup_rpg(base_folder: str, departement: str, archive_file: str):
    """
    Extracts RPG archive, and changes the folders to simplify it from:

        * RPG
            * RPG_2-2__SHP_LAMB93_R93_2023-01-01
                * RPG
                    * 1_DONNEES_LIVRAISON_2023
                         * RPG_2-2__SHP_LAMB93_R93_2023-01-01
                             * PARCELLES_GRAPHIQUES.shp

    to:

        * RPG:
             * DONNEES
                 * PARCELLES_GRAPHIQUES.shp

    Parameters:
        base_folder: base folder of the application (same one as the one written in the config file)
        departement: number of the departement as a 2 character string (ex: "06", "77" ...)
        archive_file: archive of the database (or the first file of the split archive)
    """

    current_base_folder = os.path.join(
        base_folder, departements, str(departement), rpg_folder
    )

    archive_name = os.path.basename(archive_file).split(".")[0]

    out_file_option = f"-o{current_base_folder}"

    command_line = f"{get_installed_7z()} x {archive_file} {out_file_option}"

    subprocess.run([command_line], shell=True)

    # RPG_2-2__SHP_LAMB93_R93_2023-01-01
    path1 = os.path.join(current_base_folder, archive_name)

    # RPG
    dir1 = os.listdir(path1)[0]
    path2 = os.path.join(path1, dir1)

    # 1_DONNEES_LIVRAISON_2023
    # os.listdir return order is not sorted. better match by substring
    dir2 = next(x for x in os.listdir(path2) if delivery_db in x)
    path3 = os.path.join(path2, dir2)

    # RPG_2-2__SHP_LAMB93_R93_2023-01-01
    # Other file in the directory has the same name but it's the hashfile
    dir3 = next(x for x in os.listdir(path3) if hash_file_extenstion not in x)
    path4 = os.path.join(path3, dir3)

    os.makedirs(
        os.path.join(base_folder, departements, str(departement), rpg_folder),
        exist_ok=True,
    )
    os.rename(
        path4,
        os.path.join(base_folder, departements, str(departement), rpg_folder, delivery),
    )
    shutil.rmtree(path1, ignore_errors=True)


def setup_bdortho(base_folder: str, departement: str, archive_file: str):
    """
    Extracts BDORTHO archive, and changes the folders to simplify it from:

         * BDORTHO
             * ORTHOHR_1-0_RVB-0M20_JP2-E080_LAMB93_D006_2020-01-01
                 * ORTHOHR
                     * 1_DONNEES_LIVRAISON_2021-04-00084
                          * OHR_RVB_0M20_JP2-E080_LAMB93_D06-2020
                              * *.jp2
                      * 2_METADONNEES_LIVRAISON_2021-04-00084
                      * 3_SUPPLEMENTS_LIVRAISON_2021-04-00084
                          * OHR_RVB_0M20_JP2-E080_LAMB93_D06-2020/
                              * dalles.shp

    to:

         * BDORTHO
             * DONNEES
                 * *.jp2
             * SUPPLEMENTS
                 * dalles.shp

    Parameters:
        base_folder: base folder of the application (same one as the one written in the config file)
        departement: number of the departement as a 2 character string (ex: "06", "77" ...)
        archive_file: archive of the database (or the first file of the split archive)
    """

    current_base_folder = os.path.join(
        base_folder, departements, str(departement), texture_image_DB
    )

    archive_name = os.path.basename(archive_file).split(".")[0]

    out_file_option = f"-o{current_base_folder}"

    command_line = f"{get_installed_7z()} x {archive_file} {out_file_option}"

    subprocess.run([command_line], shell=True)

    # ORTHOHR_1-0_RVB-0M20_JP2-E080_LAMB93_D006_2020-01-01
    path1 = os.path.join(current_base_folder, archive_name)

    # ORTHOHR
    dir1 = os.listdir(path1)[0]
    path2 = os.path.join(path1, dir1)

    # 1_DONNEES_LIVRAISON_2021-04-00084
    # os.listdir return order is not sorted. better match by substring
    dir2 = next(x for x in os.listdir(path2) if delivery_db in x)
    path3 = os.path.join(path2, dir2)

    # OHR_RVB_0M20_JP2-E080_LAMB93_D06-2020
    # Other file in the directory has the same name but it's the hashfile
    dir3 = next(x for x in os.listdir(path3) if hash_file_extenstion not in x)
    path4 = os.path.join(path3, dir3)

    os.makedirs(
        os.path.join(
            base_folder, departements, str(departement), texture_image_DB, delivery
        ),
        exist_ok=True,
    )
    os.rename(
        path4,
        os.path.join(
            base_folder,
            departements,
            str(departement),
            texture_image_DB,
            delivery,
        ),
    )

    # 3_SUPPLEMENTS_LIVRAISON_2021-04-00084
    dir4 = next(x for x in os.listdir(path2) if additional in x)
    path5 = os.path.join(path2, dir4)

    # OHR_RVB_0M20_JP2-E080_LAMB93_D06-2020
    dir5 = next(x for x in os.listdir(path5) if hash_file_extenstion not in x)
    path6 = os.path.join(path5, dir5)

    os.makedirs(
        os.path.join(base_folder, departements, str(departement), texture_image_DB),
        exist_ok=True,
    )
    os.rename(
        path6,
        os.path.join(
            base_folder,
            departements,
            str(departement),
            texture_image_DB,
            additional,
        ),
    )
    shutil.rmtree(path1, ignore_errors=True)


def setup_rgealti(base_folder: str, departement: str, archive_file: str):
    """
    Extracts RGEALTI archive, and changes the folders to simplify it from:

         * RGEALTI
             * RGEALTI_2-0_1M_ASC_LAMB93-IGN69_D077_2021-03-03
                 * RGEALTI
                     * 1_DONNEES_LIVRAISON_2021-04-00084
                         * RGEALTI_MNT_1M_ASC_LAMB93_IGN69_D077_20210303
                             * *.asc
                     * 2_METADONNEES_LIVRAISON_2021-04-00084
                     * 3_SUPPLEMENTS_LIVRAISON_2021-04-00084
                         * RGEALTI_MNT_1M_ASC_LAMB93_IGN69_D077_20210303
                             * dalles.shp

    to:

         * RGEALTI
             * DONNEES
                * *.asc
             * SUPPLEMENTS
                * dalles.shp

    Parameters:
        base_folder: base folder of the application (same one as the one written in the config file)
        departement: number of the departement as a 2 character string (ex: "06", "77" ...)
        archive_file: archive of the database (or the first file of the split archive)
    """

    current_base_folder = os.path.join(
        base_folder, departements, str(departement), terrain_DB
    )

    archive_name = os.path.basename(archive_file).split(".")[0]

    out_file_option = f"-o{current_base_folder}"

    command_line = f"{get_installed_7z()} x {archive_file} {out_file_option}"

    subprocess.run([command_line], shell=True)

    # RGEALTI_2-0_1M_ASC_LAMB93-IGN69_D077_2021-03-03
    path1 = os.path.join(current_base_folder, archive_name)

    # RGEALTI
    dir1 = os.listdir(path1)[0]
    path2 = os.path.join(path1, dir1)

    # 1_DONNEES_LIVRAISON_2021-04-00084
    # os.listdir return order is not sorted. better match by substring
    dir2 = next(x for x in os.listdir(path2) if delivery_db in x)
    path3 = os.path.join(path2, dir2)

    # RGEALTI_MNT_1M_ASC_LAMB93_IGN69_D077_20210303
    # Folder contains 3 subfolders, and the corresponding hashfiles.
    dirs3 = [x for x in os.listdir(path3) if hash_file_extenstion not in x]
    dir3 = next(x for x in dirs3 if terrain_data_folder in x)
    path4 = os.path.join(path3, dir3)

    os.makedirs(
        os.path.join(base_folder, departements, str(departement), terrain_DB),
        exist_ok=True,
    )
    os.rename(
        path4,
        os.path.join(
            base_folder,
            departements,
            str(departement),
            terrain_DB,
            delivery,
        ),
    )

    # 3_SUPPLEMENTS_LIVRAISON_2021-04-00084
    dir4 = next(x for x in os.listdir(path2) if additional in x)
    path5 = os.path.join(path2, dir4)

    # RGEALTI_MNT_1M_ASC_LAMB93_IGN69_D077_20210303
    dir5 = next(x for x in os.listdir(path5) if hash_file_extenstion not in x)
    path6 = os.path.join(path5, dir5)

    os.makedirs(
        os.path.join(
            base_folder, departements, str(departement), terrain_DB, additional
        ),
        exist_ok=True,
    )
    os.rename(
        path6,
        os.path.join(
            base_folder,
            departements,
            str(departement),
            terrain_DB,
            additional,
        ),
    )
    shutil.rmtree(path1, ignore_errors=True)


def check_shapefiles_presence(base_folder: str):

    if not os.path.isfile(os.path.join(base_folder, ocean_file)):
        logger.warn("Ocean file not found. Extracting it from archive")

        _location = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__))
        )
        archive_path = os.path.realpath(
            os.path.join(_location, "..", shapefiles_folder, ocean_archive)
        )

        out_file_option = f"-o{base_folder}"

        command_line = f"{get_installed_7z()} x {archive_path} {out_file_option}"

        subprocess.run([command_line], shell=True)

    if not os.path.isfile(os.path.join(base_folder, regions_file)):
        logger.warn("Region file not found. Extracting it from archive")

        _location = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__))
        )
        archive_path = os.path.realpath(
            os.path.join(_location, "..", shapefiles_folder, regions_archive)
        )

        out_file_option = f"-o{base_folder}"

        command_line = f"{get_installed_7z()} x {archive_path} {out_file_option}"

        subprocess.run([command_line], shell=True)


def get_installed_7z():

    first_command = subprocess.run(["7zz"], stdout=subprocess.PIPE)
    if first_command.returncode == 0:
        return "7zz"

    second_command = subprocess.run(["7z"], stdout=subprocess.PIPE)
    if second_command.returncode == 0:
        return "7z"

    raise Exception(
        "Neither 7zip nor py7zip-full are installed. Please install of one those."
    )


def setup_project_folder(base_folder: str):

    project_name = funkybob.UniqueRandomNameGenerator(members=4)[0]

    base_path = os.path.join(base_folder, projects_folder, project_name)
    os.makedirs(base_path, exist_ok=True)
    return base_path


def setup_export_folder(project_folder: str):

    export_folder = os.path.join(project_folder, rendering)

    if not os.path.isdir(export_folder):
        os.makedirs(export_folder, exist_ok=True)

    return export_folder
