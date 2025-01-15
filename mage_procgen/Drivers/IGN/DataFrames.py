class BuildingDataFrame:

    ID = "ID"
    nature = "Nature"
    usage_1 = "Usage_1"
    usage_2 = "Usage_2"
    number_housings = "Nb_Housing"
    geometry = "geometry"

    churches_tags = ["Religieux"]
    malls_tags = ["Commercial et services"]
    factories_tags = ["Industriel"]

    class File:
        ID = "ID"
        nature = "NATURE"
        usage_1 = "USAGE1"
        usage_2 = "USAGE2"
        number_housings = "NB_LOGTS"
        height = "HAUTEUR"
        number_floors = "NB_ETAGES"

        geometry = "geometry"

    class WFS:
        ID = "cleabs"
        nature = "nature"
        usage_1 = "usage_1"
        usage_2 = "usage_2"
        number_housings = "nombre_de_logements"
        height = "hauteur"
        number_floors = "nombre_d_etages"
        geometry = "geometry"

        @staticmethod
        def get_columns():
            return [
                BuildingDataFrame.WFS.ID,
                BuildingDataFrame.WFS.nature,
                BuildingDataFrame.WFS.usage_1,
                BuildingDataFrame.WFS.usage_2,
                BuildingDataFrame.WFS.number_housings,
                BuildingDataFrame.WFS.height,
                BuildingDataFrame.WFS.number_floors,
                BuildingDataFrame.WFS.geometry,
            ]


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

    class File:
        ID = "ID"
        nature = "NATURE"
        importance = "IMPORTANCE"
        number_lanes = "NB_VOIES"
        direction = "SENS"
        position_rel_to_ground = "POS_SOL"
        width = "LARGEUR"
        urban = "URBAIN"
        geometry = "geometry"

    class WFS:
        ID = "cleabs"
        nature = "nature"
        importance = "importance"
        number_lanes = "nombre_de_voies"
        direction = "sens_de_circulation"
        position_rel_to_ground = "position_par_rapport_au_sol"
        width = "largeur_de_chaussee"
        urban = "urbain"
        geometry = "geometry"

        @staticmethod
        def get_columns():
            return [
                RoadDataFrame.WFS.ID,
                RoadDataFrame.WFS.nature,
                RoadDataFrame.WFS.importance,
                RoadDataFrame.WFS.number_lanes,
                RoadDataFrame.WFS.direction,
                RoadDataFrame.WFS.position_rel_to_ground,
                RoadDataFrame.WFS.width,
                RoadDataFrame.WFS.urban,
                RoadDataFrame.WFS.geometry,
            ]


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


class SportDataFrame:

    tags = [""]

    ID = "ID"
    nature = "Nature"
    detail_nature = "Detail_nature"
    geometry = "geometry"

    class File:
        ID = "ID"
        nature = "NATURE"
        detail_nature = "NAT_DETAIL"
        geometry = "geometry"

    class WFS:
        ID = "cleabs"
        nature = "nature"
        detail_nature = "nature_detaillee"
        geometry = "geometry"

        @staticmethod
        def get_columns():
            return [
                SportDataFrame.WFS.ID,
                SportDataFrame.WFS.nature,
                SportDataFrame.WFS.detail_nature,
                SportDataFrame.WFS.geometry,
            ]


class LandUseDataFrame:

    tags = [""]

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
                LandUseDataFrame.WFS.ID,
                LandUseDataFrame.WFS.nature,
                LandUseDataFrame.WFS.geometry,
            ]


class PlotDataFrame:

    tags = [""]

    ID = "ID"
    culture = "Culture"
    group = "Group"
    geometry = "geometry"

    class File:
        ID = "ID_PARCEL"
        culture = "CODE_CULTU"
        group = "CODE_GROUP"
        geometry = "geometry"

    class WFS:
        ID = "id_parcel"
        culture = "code_cultu"
        group = "code_group"
        geometry = "geometry"

        @staticmethod
        def get_columns():
            return [
                PlotDataFrame.WFS.ID,
                PlotDataFrame.WFS.culture,
                PlotDataFrame.WFS.group,
                PlotDataFrame.WFS.geometry,
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
