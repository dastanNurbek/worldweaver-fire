import os

import geopandas as g

from worldweaver.Drivers.IGN.StreamLoader import StreamLoader
from worldweaver.Drivers.IGN.Utils import GeoData, SubDenseData
from worldweaver.Drivers.IGN.DataFrames import (
    BuildingDataFrame,
)

from worldweaver.Parser.ShapeFileParser import ShapeFileParser

import worldweaver.Utils.DataFiles as df
from worldweaver.Utils.Logging import logger
from worldweaver.Utils.Utils import (
    GeoWindow,
    CRS_fr,
    ensure_columns_existence,
)
from worldweaver.Utils.RenderingDataFrames import (
    RenderingBuildingDataFrame,
)


class SubdenseLoader(StreamLoader):
    def load(self, geo_window: GeoWindow) -> GeoData:
        geodata = super().load(geo_window)

        bbox = geo_window.bounds
        logger.info("Loading subdense data")
        folder = os.path.join(self.base_folder, df.subdense_folder)
        # TODO: derive file names from indexing file once it's created
        old_building_data = ShapeFileParser.load(
            os.path.join(folder, "FR-STR-FUA-Building-2011.gpkg"),
            bbox,
            CRS_fr,
        )

        new_building_data = ShapeFileParser.load(
            os.path.join(folder, "FR-STR-FUA-Evolution-2021.gpkg"),
            bbox,
            CRS_fr,
        )

        changes_data = ShapeFileParser.load(
            os.path.join(folder, "FR-STR-FUA-Evolution-2011-21.gpkg"),
            bbox,
            CRS_fr,
        )

        # Treat the data to homogenise column names between different data sources
        # HACK: adding columns to 2011 data because some are missing.
        ensure_columns_existence(
            old_building_data,
            [
                BuildingDataFrame.File.ID,
                BuildingDataFrame.File.nature,
                BuildingDataFrame.File.usage_1,
                BuildingDataFrame.File.usage_2,
                BuildingDataFrame.File.number_housings,
                BuildingDataFrame.File.height,
                BuildingDataFrame.File.number_floors,
                BuildingDataFrame.File.geometry,
            ],
        )
        old_building_data_dict = {
            BuildingDataFrame.ID: old_building_data[BuildingDataFrame.File.ID],
            BuildingDataFrame.nature: old_building_data[BuildingDataFrame.File.nature],
            BuildingDataFrame.usage_1: old_building_data[
                BuildingDataFrame.File.usage_1
            ],
            BuildingDataFrame.usage_2: old_building_data[
                BuildingDataFrame.File.usage_2
            ],
            BuildingDataFrame.number_housings: old_building_data[
                BuildingDataFrame.File.number_housings
            ],
            RenderingBuildingDataFrame.number_floors: old_building_data[
                BuildingDataFrame.File.number_floors
            ],
            RenderingBuildingDataFrame.height: old_building_data[
                BuildingDataFrame.File.height
            ],
            BuildingDataFrame.geometry: old_building_data[
                BuildingDataFrame.File.geometry
            ],
        }
        old_building_data = g.GeoDataFrame(old_building_data_dict)

        new_building_data_dict = {
            BuildingDataFrame.ID: new_building_data[BuildingDataFrame.File.ID],
            BuildingDataFrame.nature: new_building_data[BuildingDataFrame.File.nature],
            BuildingDataFrame.usage_1: new_building_data[
                BuildingDataFrame.File.usage_1
            ],
            BuildingDataFrame.usage_2: new_building_data[
                BuildingDataFrame.File.usage_2
            ],
            BuildingDataFrame.number_housings: new_building_data[
                BuildingDataFrame.File.number_housings
            ],
            RenderingBuildingDataFrame.number_floors: new_building_data[
                BuildingDataFrame.File.number_floors
            ],
            RenderingBuildingDataFrame.height: new_building_data[
                BuildingDataFrame.File.height
            ],
            BuildingDataFrame.geometry: new_building_data[
                BuildingDataFrame.File.geometry
            ],
        }
        new_building_data = g.GeoDataFrame(new_building_data_dict)

        new_geodata = GeoData(
            buildings=geodata.buildings,
            forests=geodata.forests,
            roads=geodata.roads,
            water=geodata.water,
            water_line=geodata.water_line,
            ocean=geodata.ocean,
            residentials=geodata.residentials,
            interest_zones=geodata.interest_zones,
            departements=geodata.departements,
            terrain=geodata.terrain,
            sport=geodata.sport,
            landuse=geodata.landuse,
            plots=geodata.plots,
            is_subdense=True,
            subdense_data=SubDenseData(
                old_buildings=old_building_data,
                new_buildings=new_building_data,
                buildings_changes=changes_data,
            ),
        )

        return new_geodata
