class BuildingDataFrame:

    ID = "ID"
    religious = "religious"
    commercial = "commercial"
    house = "house"
    industrial = "industrial"
    geometry = "geometry"


class RoadDataFrame:

    non_car_natures = ["Chemin", "Escalier", "Sentier"]
    directions = ["Double sens", "Sens direct", "Sens inverse"]

    ID = "ID"
    nature = "Nature"
    importance = "Importance"
    number_lanes = "Nb_lanes"
    position_rel_to_ground = "Position_rel_to_ground"
    direction = "Direction"
    urban = "Urban"
    geometry = "geometry"


class ZoneInterestDataFrame:

    industrial_commercial_tags = [
        "Zone artisanale",
        "Zone commerciale",
        "Zone d'activités",
    ]

    ID = "ID"
    detail_nature = "Detail_nature"
    geometry = "geometry"

    class File:
        ID = "ID"
        detail_nature = "NAT_DETAIL"
        geometry = "geometry"

    class WFS:
        ID = "cleabs"
        detail_nature = "nature_detaillee"
        geometry = "geometry"

        @staticmethod
        def get_columns():
            return [
                ZoneInterestDataFrame.WFS.ID,
                ZoneInterestDataFrame.WFS.detail_nature,
                ZoneInterestDataFrame.WFS.geometry,
            ]


class WaterDataFrame:

    flowing_water_tags = ["Ecoulement naturel", "Ecoulement canalisé", "Canal"]

    ID = "ID"
    nature = "Nature"
    geometry = "geometry"

    class File:
        ID = "ID"
        nature = "NATURE"
        geometry = "geometry"

    class WFS:
        ID = "cleabs"
        nature = "nature"
        geometry = "geometry"

        @staticmethod
        def get_columns():
            return [
                WaterDataFrame.WFS.ID,
                WaterDataFrame.WFS.nature,
                WaterDataFrame.WFS.geometry,
            ]


class DefaultDataFrame:
    ID = "ID"
    geometry = "geometry"

    @staticmethod
    def get_columns():
        return [
            DefaultDataFrame.ID,
            DefaultDataFrame.geometry,
        ]
