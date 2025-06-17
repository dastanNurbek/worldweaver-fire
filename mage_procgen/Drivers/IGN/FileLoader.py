import os

import geopandas as g
import pandas as p

from mage_procgen.Drivers.IGN.Loader import Loader
from mage_procgen.Drivers.IGN.Utils import GeoData
from mage_procgen.Drivers.IGN.DataFrames import (
    BuildingDataFrame,
    RoadDataFrame,
    ZoneInterestDataFrame,
    WaterDataFrame,
    SportDataFrame,
    LandUseDataFrame,
    PlotDataFrame,
)

from mage_procgen.Parser.ShapeFileParser import ShapeFileParser, RoadShapeFileParser
from mage_procgen.Parser.ASCParser import ASCParser
from mage_procgen.Parser.JP2Parser import JP2Parser

from mage_procgen.Utils.Logging import logger
from mage_procgen.Utils.RenderingDataFrames import (
    RenderingBuildingDataFrame,
)
from mage_procgen.Utils.Utils import (
    GeoWindow,
    CRS_fr,
    CRS_degrees,
    TerrainData,
    safe_overlay,
    OverlayType,
)
import mage_procgen.Utils.DataFiles as df


class FileLoader(Loader):
    def load(self, geo_window: GeoWindow) -> GeoData:

        bbox = geo_window.bounds
        if geo_window.crs != CRS_fr:
            logger.warn(f"IGN FileLoader: Provided window was not in CRS {CRS_fr}")
        logger.info("Loading shp files")

        arrondissements = ShapeFileParser.load(
            os.path.join(self.base_folder, df.regions_file),
            bbox,
            CRS_fr,
        )

        departements_names = set(arrondissements["CODE_DEPT"].values)

        building_data = None
        forest_data = None
        road_data = None
        water_data = None
        residential_data = None
        interest_zone_data = None
        oceans_data = None
        sport_data = None
        landuse_data = None
        plot_data = None
        departements_data = None
        terrain_data = []

        load_oceans = False

        # TODO: this "= geo_window" is weird, look into it
        # Specifically for terrain, we have to make sure it loads a complete rectangle
        terrain_window = geo_window = GeoWindow.from_square(
            x_min=bbox[0],
            x_max=bbox[2],
            y_min=bbox[1],
            y_max=bbox[3],
            from_crs=CRS_fr,
            to_crs=CRS_fr,
        )

        for current_departement in departements_names:

            logger.info(
                "Loading data for departement " + current_departement,
            )

            current_terrain_data = self.load_departement_terrain(
                current_departement, terrain_window
            )

            terrain_data.extend(current_terrain_data)

            current_building_data = ShapeFileParser.load(
                os.path.join(
                    self.base_folder,
                    df.departements,
                    current_departement,
                    df.bdtopo_folder,
                    df.delivery,
                    df.building_folder,
                    df.building_file,
                ),
                bbox,
                CRS_fr,
            )
            if building_data is not None:
                building_data = p.concat([building_data, current_building_data])
            else:
                building_data = current_building_data

            current_forest_data = ShapeFileParser.load(
                os.path.join(
                    self.base_folder,
                    df.departements,
                    current_departement,
                    df.bdtopo_folder,
                    df.delivery,
                    df.forest_folder,
                    df.forest_file,
                ),
                bbox,
                CRS_fr,
            )
            if forest_data is not None:
                forest_data = p.concat([forest_data, current_forest_data])
            else:
                forest_data = current_forest_data

            current_road_data = RoadShapeFileParser.load(
                os.path.join(
                    self.base_folder,
                    df.departements,
                    current_departement,
                    df.bdtopo_folder,
                    df.delivery,
                    df.road_folder,
                    df.road_file,
                ),
                bbox,
                CRS_fr,
            )
            if road_data is not None:
                road_data = p.concat([road_data, current_road_data])
            else:
                road_data = current_road_data

            current_water_data = ShapeFileParser.load(
                os.path.join(
                    self.base_folder,
                    df.departements,
                    current_departement,
                    df.bdtopo_folder,
                    df.delivery,
                    df.water_folder,
                    df.water_file,
                ),
                bbox,
                CRS_fr,
                force_2d=True,
            )
            if water_data is not None:
                water_data = p.concat([water_data, current_water_data])
            else:
                water_data = current_water_data

            current_residential_data = ShapeFileParser.load(
                os.path.join(
                    self.base_folder,
                    df.departements,
                    current_departement,
                    df.bdtopo_folder,
                    df.delivery,
                    df.residential_folder,
                    df.residential_file,
                ),
                bbox,
                CRS_fr,
                force_2d=True,
            )
            if residential_data is not None:
                residential_data = p.concat(
                    [residential_data, current_residential_data]
                )
            else:
                residential_data = current_residential_data

            current_interest_zone_data = ShapeFileParser.load(
                os.path.join(
                    self.base_folder,
                    df.departements,
                    current_departement,
                    df.bdtopo_folder,
                    df.delivery,
                    df.interest_zone_folder,
                    df.interest_zone_file,
                ),
                bbox,
                CRS_fr,
                force_2d=True,
            )
            if interest_zone_data is not None:
                interest_zone_data = p.concat(
                    [interest_zone_data, current_interest_zone_data]
                )
            else:
                interest_zone_data = current_interest_zone_data

            current_sport_data = ShapeFileParser.load(
                os.path.join(
                    self.base_folder,
                    df.departements,
                    current_departement,
                    df.bdtopo_folder,
                    df.delivery,
                    df.building_folder,
                    df.sport_file,
                ),
                bbox,
                CRS_fr,
                force_2d=True,
            )
            if sport_data is not None:
                sport_data = p.concat([sport_data, current_sport_data])
            else:
                sport_data = current_sport_data

            current_plot_data = ShapeFileParser.load(
                os.path.join(
                    self.base_folder,
                    df.departements,
                    current_departement,
                    df.rpg_folder,
                    df.delivery,
                    df.plot_file,
                ),
                bbox,
                CRS_fr,
                force_2d=True,
            )
            if plot_data is not None:
                plot_data = p.concat([plot_data, current_plot_data])
            else:
                plot_data = current_plot_data

            current_landuse_data = ShapeFileParser.load(
                os.path.join(
                    self.base_folder,
                    df.departements,
                    current_departement,
                    df.bdcarto_folder,
                    df.delivery,
                    df.landuse_folder,
                    df.landuse_file,
                ),
                bbox,
                CRS_fr,
                force_2d=True,
            )
            if landuse_data is not None:
                landuse_data = p.concat([landuse_data, current_landuse_data])
            else:
                landuse_data = current_landuse_data

            current_departement_data = ShapeFileParser.load(
                os.path.join(
                    self.base_folder,
                    df.departements,
                    current_departement,
                    df.bdtopo_folder,
                    df.delivery,
                    df.dpt_folder,
                    df.dpt_file,
                ),
                bbox,
                CRS_fr,
                force_2d=True,
            )
            if departements_data is not None:
                departements_data = p.concat(
                    [departements_data, current_departement_data]
                )
            else:
                departements_data = current_departement_data

            if os.path.isfile(
                os.path.join(
                    self.base_folder,
                    df.departements,
                    current_departement,
                    df.bdtopo_folder,
                    df.delivery,
                    df.water_folder,
                    df.shore_file,
                )
            ):
                load_oceans = True

        if load_oceans:
            # Ocean file is in degrees so we have to convert the box back to this csr
            ocean_box = geo_window.dataframe.to_crs(CRS_degrees).geometry[0].bounds
            oceans_data = ShapeFileParser.load(
                os.path.join(self.base_folder, df.ocean_file),
                ocean_box,
                CRS_fr,
                force_2d=True,
            )
        else:
            oceans_data = g.GeoDataFrame(
                columns=["id", "geometry"], geometry="geometry"
            )

        # Treat the data to homogenise column names between different data sources
        building_data_dict = {
            BuildingDataFrame.ID: building_data[BuildingDataFrame.File.ID],
            BuildingDataFrame.nature: building_data[BuildingDataFrame.File.nature],
            BuildingDataFrame.usage_1: building_data[BuildingDataFrame.File.usage_1],
            BuildingDataFrame.usage_2: building_data[BuildingDataFrame.File.usage_2],
            BuildingDataFrame.number_housings: building_data[
                BuildingDataFrame.File.number_housings
            ],
            RenderingBuildingDataFrame.number_floors: building_data[
                BuildingDataFrame.File.number_floors
            ],
            RenderingBuildingDataFrame.height: building_data[
                BuildingDataFrame.File.height
            ],
            BuildingDataFrame.geometry: building_data[BuildingDataFrame.File.geometry],
        }
        building_data = g.GeoDataFrame(building_data_dict)

        road_data_dict = {
            RoadDataFrame.ID: road_data[RoadDataFrame.File.ID],
            RoadDataFrame.nature: road_data[RoadDataFrame.File.nature],
            RoadDataFrame.importance: road_data[RoadDataFrame.File.importance],
            RoadDataFrame.number_lanes: road_data[RoadDataFrame.File.number_lanes],
            RoadDataFrame.direction: road_data[RoadDataFrame.File.direction],
            RoadDataFrame.position_rel_to_ground: road_data[
                RoadDataFrame.File.position_rel_to_ground
            ],
            RoadDataFrame.width: road_data[RoadDataFrame.File.width],
            RoadDataFrame.urban: road_data[RoadDataFrame.File.urban],
            RoadDataFrame.geometry: road_data[RoadDataFrame.File.geometry],
        }
        road_data = g.GeoDataFrame(road_data_dict)

        interest_zone_data_dict = {
            ZoneInterestDataFrame.ID: interest_zone_data[ZoneInterestDataFrame.File.ID],
            ZoneInterestDataFrame.detail_nature: interest_zone_data[
                ZoneInterestDataFrame.File.detail_nature
            ],
            ZoneInterestDataFrame.geometry: interest_zone_data[
                ZoneInterestDataFrame.File.geometry
            ],
        }
        interest_zone_data = g.GeoDataFrame(interest_zone_data_dict)

        water_data_dict = {
            WaterDataFrame.ID: water_data[WaterDataFrame.File.ID],
            WaterDataFrame.nature: water_data[WaterDataFrame.File.nature],
            WaterDataFrame.geometry: water_data[WaterDataFrame.File.geometry],
        }
        water_data = g.GeoDataFrame(water_data_dict)

        sport_data_dict = {
            SportDataFrame.ID: sport_data[SportDataFrame.File.ID],
            SportDataFrame.nature: sport_data[SportDataFrame.File.nature],
            SportDataFrame.detail_nature: sport_data[SportDataFrame.File.detail_nature],
            SportDataFrame.geometry: sport_data[SportDataFrame.File.geometry],
        }
        sport_data = g.GeoDataFrame(sport_data_dict)

        landuse_data_dict = {
            LandUseDataFrame.ID: landuse_data[LandUseDataFrame.File.ID],
            LandUseDataFrame.nature: landuse_data[LandUseDataFrame.File.nature],
            LandUseDataFrame.geometry: landuse_data[LandUseDataFrame.File.geometry],
        }
        landuse_data = g.GeoDataFrame(landuse_data_dict)

        plot_data_dict = {
            PlotDataFrame.ID: plot_data[PlotDataFrame.File.ID],
            PlotDataFrame.culture: plot_data[PlotDataFrame.File.culture],
            PlotDataFrame.group: plot_data[PlotDataFrame.File.group],
            PlotDataFrame.geometry: plot_data[PlotDataFrame.File.geometry],
        }
        plot_data = g.GeoDataFrame(plot_data_dict)

        geo_data = GeoData(
            buildings=building_data,
            forests=forest_data,
            roads=road_data,
            water=water_data,
            ocean=oceans_data,
            residentials=residential_data,
            interest_zones=interest_zone_data,
            departements=departements_data,
            terrain=terrain_data,
            sport=sport_data,
            landuse=landuse_data,
            plots=plot_data,
        )

        return geo_data

    def load_town_shape(self, town_id: str) -> g.GeoDataFrame:

        town_name = town_id.split(" ")[:-1]
        departement_nbr = town_id.split(" ")[-1]

        towns = ShapeFileParser.load_no_window(
            os.path.join(
                self.base_folder,
                df.departements,
                departement_nbr,
                df.bdtopo_folder,
                df.delivery,
                df.dpt_folder,
                df.town_file,
            ),
            CRS_fr,
        )

        # Need to reset the index of the dataframe to ease the access of the data, and there is only one line anyway
        town = towns.query("NOM == @town_name").reset_index()

        if town.empty:
            raise ValueError(
                f"Query of town with identifier {town_id} returned nothing. Format should be '<name_of_town> <departement_number>'"
            )

        return town

    def load_departement_terrain(self, current_departement, terrain_window):

        bbox = terrain_window.bounds
        file_folder = os.path.join(
            self.base_folder,
            df.departements,
            current_departement,
            df.terrain_DB,
            df.delivery,
        )
        slab_file = os.path.join(
            self.base_folder,
            df.departements,
            current_departement,
            df.terrain_DB,
            df.additional,
            df.slab_file,
        )
        slabs = ShapeFileParser.load(slab_file, bbox, CRS_fr)

        slab_parts = safe_overlay(
            slabs, terrain_window.dataframe, OverlayType.INTERSECTION
        )

        loaded_files = []

        for index, row in slab_parts.iterrows():
            file_name = f"{os.path.basename(row['NOM_DALLE'])}.asc"

            file_full_path = os.path.join(file_folder, file_name)

            # Sometimes the name of the file in the dalles.shp file does not correspond to the actual name of the file
            if not os.path.isfile(file_full_path):
                # The corner of the file seems always be present in format _DDDD_DDDD_
                # We can use that to find the file we want
                file_coords = df.file_coords_regex.findall(file_name)[0]

                file_name = next(x for x in os.listdir(file_folder) if file_coords in x)
                file_full_path = os.path.join(file_folder, file_name)

            asc_data = ASCParser.load(file_full_path)

            current_box = (
                asc_data.x_min,
                asc_data.y_min,
                asc_data.x_max,
                asc_data.y_max,
            )

            terrain_base_map = ""
            if self.use_sat_img:
                try:
                    terrain_base_map = self.load_texture(current_box)
                except Exception as e:
                    logger.error(
                        "Couldn't load texture image of terrain slab",
                        exc_info=e,
                    )

            loaded_files.append(
                TerrainData(
                    x_min=asc_data.x_min,
                    y_min=asc_data.y_min,
                    x_max=asc_data.x_max,
                    y_max=asc_data.y_max,
                    resolution=asc_data.resolution,
                    nbcol=asc_data.nbcol,
                    nbrow=asc_data.nbrow,
                    no_data=asc_data.no_data,
                    base_map_file=terrain_base_map,
                    data=asc_data.data,
                )
            )

        # Coherence check: find out if we are missing a slab
        global_x_min = min([x.x_min for x in loaded_files])
        global_x_max = max([x.x_max for x in loaded_files])
        global_y_min = min([x.y_min for x in loaded_files])
        global_y_max = max([x.y_max for x in loaded_files])

        resolution = loaded_files[0].resolution
        nbcols = loaded_files[0].nbcol
        nbrows = loaded_files[0].nbrow
        no_data = loaded_files[0].no_data

        terrain_data = p.DataFrame([[0 for x in range(nbcols)] for y in range(nbrows)])

        current_x = global_x_min
        current_y = global_y_min
        current_terrain = None

        while current_x < global_x_max and current_y < global_y_max:

            for terrain in loaded_files:
                if current_x == terrain.x_min and current_y == terrain.y_min:
                    current_terrain = terrain
                    break

            # If the terrain that is supposed to be there is not, add it
            if current_terrain is None:
                current_box = (
                    current_x,
                    current_y,
                    current_x + resolution * nbcols,
                    current_y + resolution * nbrows,
                )

                # Sometimes (ex: in sea but near-ish coastline) there is no elevation data but there is an ortho img
                # In this case, we should fetch it.
                terrain_base_map = ""
                if self.use_sat_img:
                    try:
                        terrain_base_map = self.load_texture(current_box)
                    except Exception as e:
                        logger.error(
                            "Couldn't load texture image of terrain slab",
                            exc_info=e,
                        )

                loaded_files.append(
                    TerrainData(
                        x_min=current_x,
                        y_min=current_y,
                        x_max=current_x + resolution * nbcols,
                        y_max=current_y + resolution * nbrows,
                        resolution=resolution,
                        nbcol=nbcols,
                        nbrow=nbrows,
                        no_data=no_data,
                        base_map_file=terrain_base_map,
                        data=terrain_data,
                    )
                )

            # If we're at the end of a line
            if current_x >= global_x_max:
                current_y = current_y + resolution * nbrows
                current_x = global_x_min
            else:
                current_x = current_x + resolution * nbcols

        return loaded_files

    def load_texture(self, mesh_box: tuple[float, float, float, float]) -> str:

        arrondissements = ShapeFileParser.load(
            os.path.join(self.base_folder, df.regions_file),
            mesh_box,
            CRS_fr,
        )

        departements = list(set(arrondissements["CODE_DEPT"].values))

        if len(departements) > 1:
            raise ValueError("A single slab cannot be over multiple regions")

        current_departement = departements[0]

        current_texture_folder = os.path.join(self.project_folder, df.texture_folder)

        if not os.path.isdir(current_texture_folder):
            os.makedirs(current_texture_folder, exist_ok=True)

        texture_file_name = (
            f"Texture_"
            f"{int(mesh_box[0])}_"
            f"{int(mesh_box[1])}_"
            f"{int(mesh_box[2])}_"
            f"{int(mesh_box[3])}_.tif"
        )

        texture_full_path = os.path.join(current_texture_folder, texture_file_name)

        current_texture_image_folder = os.path.join(
            self.base_folder,
            df.departements,
            current_departement,
            df.texture_image_DB,
            df.delivery,
        )
        current_texture_image_slab_file = os.path.join(
            self.base_folder,
            df.departements,
            current_departement,
            df.texture_image_DB,
            df.additional,
            df.slab_file,
        )

        current_terrain_window = GeoWindow.from_square(
            x_min=mesh_box[0],
            x_max=mesh_box[2],
            y_min=mesh_box[1],
            y_max=mesh_box[3],
            from_crs=CRS_fr,
            to_crs=CRS_fr,
        )

        if not os.path.isfile(texture_full_path):
            JP2Parser.create_texture_img(
                file_folder=current_texture_image_folder,
                geo_window=current_terrain_window,
                slab_file=current_texture_image_slab_file,
                texture_file_path=texture_full_path,
            )

        return texture_full_path
