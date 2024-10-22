import os

import pandas as p
import geopandas as g

from mage_procgen.Parser.ShapeFileParser import ShapeFileParser, RoadShapeFileParser
from mage_procgen.Parser.ASCParser import ASCParser, ASCData
from mage_procgen.Parser.JP2Parser import JP2Parser

from mage_procgen.Drivers.IGN.Loader import Loader
from mage_procgen.Utils.Utils import GeoWindow, CRS_fr, CRS_degrees
from mage_procgen.Drivers.IGN.Utils import GeoData
import mage_procgen.Utils.DataFiles as df
from mage_procgen.Drivers.IGN.DataFrames import (
    BuildingDataFrame,
    RoadDataFrame,
    ZoneInterestDataFrame,
    WaterDataFrame,
)
from mage_procgen.Utils.RenderingDataFrames import (
    RenderingRoadDataFrame,
    RenderingBuildingDataFrame,
)
from mage_procgen.Utils.Utils import TerrainData


class FileLoader(Loader):
    def load(self, geo_window: GeoWindow) -> GeoData:

        bbox = geo_window.bounds

        print("Loading shp files")

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
        departements_data = None
        terrain_data = []

        load_oceans = False

        # TODO: this "= geo_window" is weird, look into it
        # Specifically for terrain, we have to make sure it loads a complete rectangle
        terrain_window = geo_window = GeoWindow.from_square(
            bbox[0], bbox[2], bbox[1], bbox[3], CRS_fr, CRS_fr
        )

        for current_departement in departements_names:

            print("Loading data for departement " + current_departement)

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

        # Treat the data to remove the particularities of files
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
            RenderingRoadDataFrame.width: road_data[RoadDataFrame.File.width],
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
        )

        return geo_data

    def load_town_shape(self, departement_nbr: int, town_name: str):

        towns = ShapeFileParser.load_no_window(
            os.path.join(
                self.base_folder,
                df.departements,
                str(departement_nbr),
                df.bdtopo_folder,
                df.delivery,
                df.dpt_folder,
                df.town_file,
            ),
            CRS_fr,
        )

        # Need to reset the index of the dataframe to ease the access of the data, and there is only one line anyway
        town = towns.query("NOM == @town_name").reset_index()

        return town

    def load_departement_terrain(self, current_departement, terrain_window):

        bbox = terrain_window.bounds
        file_folder = os.path.join(
            self.base_folder,
            df.departements,
            current_departement,
            df.terrain_DB,
            df.delivery,
            df.terrain_data_folder,
        )
        slab_file = os.path.join(
            self.base_folder,
            df.departements,
            current_departement,
            df.terrain_DB,
            df.additional,
            df.terrain_data_folder,
            df.slab_file,
        )
        slabs = ShapeFileParser.load(slab_file, bbox, CRS_fr)
        slab_parts = slabs.overlay(
            terrain_window.dataframe, how="intersection", keep_geom_type=True
        )

        loaded_files = []

        for index, row in slab_parts.iterrows():
            file_name = os.path.basename(row["NOM_DALLE"]) + ".asc"

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
                    print("Couldn't load texture image of terrain slab: " + str(e))

            loaded_files.append(
                TerrainData(
                    asc_data.x_min,
                    asc_data.y_min,
                    asc_data.x_max,
                    asc_data.y_max,
                    asc_data.resolution,
                    asc_data.nbcol,
                    asc_data.nbrow,
                    asc_data.no_data,
                    terrain_base_map,
                    asc_data.data,
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
                        print("Couldn't load texture image of terrain slab: " + str(e))

                loaded_files.append(
                    TerrainData(
                        current_x,
                        current_y,
                        current_x + resolution * nbcols,
                        current_y + resolution * nbrows,
                        resolution,
                        nbcols,
                        nbrows,
                        no_data,
                        terrain_base_map,
                        terrain_data,
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
            "Texture_"
            + str(int(mesh_box[0]))
            + "_"
            + str(int(mesh_box[1]))
            + "_"
            + str(int(mesh_box[2]))
            + "_"
            + str(int(mesh_box[3]))
            + "_"
            + ".tif"
        )

        texture_full_path = os.path.join(current_texture_folder, texture_file_name)

        current_texture_image_folder = os.path.join(
            self.base_folder,
            df.departements,
            current_departement,
            df.texture_image_DB,
            df.delivery,
            df.texture_data_folder,
        )
        current_texture_image_slab_file = os.path.join(
            self.base_folder,
            df.departements,
            current_departement,
            df.texture_image_DB,
            df.additional,
            df.texture_data_folder,
            df.slab_file,
        )

        current_terrain_window = GeoWindow.from_square(
            mesh_box[0],
            mesh_box[2],
            mesh_box[1],
            mesh_box[3],
            CRS_fr,
            CRS_fr,
        )

        if not os.path.isfile(texture_full_path):
            JP2Parser.create_texture_img(
                current_texture_image_folder,
                current_terrain_window,
                current_texture_image_slab_file,
                texture_full_path,
            )

        return texture_full_path
