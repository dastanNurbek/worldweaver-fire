class BuildingDataFrame:

    ID = "ID"
    nature = "Nature"
    usage_1 = "Usage_1"
    usage_2 = "Usage_2"
    number_housings = "Nb_Housing"
    height = "height"
    number_floors = "Nb_floors"
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
        geometry = "geometry"


class RoadDataFrame:

    non_car_natures = ["Chemin", "Escalier", "Sentier"]
    directions = ["Double sens", "Sens direct", "Sens inverse"]

    ID = "ID"
    nature = "Nature"
    importance = "Importance"
    number_lanes = "Nb_lanes"
    direction = "Direction"
    position_rel_to_ground = "Position_rel_to_ground"
    width = "Width"
    urban = "Urban"
    geometry = "geometry"

    # Added columns
    has_sidewalks = "has_sidewalks"
    has_guardrails = "has_guardrails"

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
