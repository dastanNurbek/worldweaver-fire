import geopandas as g

from dataclasses import dataclass

from mage_procgen.Utils.Utils import TerrainDataList


@dataclass
class GeoData:
    buildings: g.GeoDataFrame
    forests: g.GeoDataFrame
    roads: g.GeoDataFrame
    water: g.GeoDataFrame
    ocean: g.GeoDataFrame
    residentials: g.GeoDataFrame
    interest_zones: g.GeoDataFrame
    departements: g.GeoDataFrame
    plots: g.GeoDataFrame
    landuse: g.GeoDataFrame
    sport: g.GeoDataFrame
    terrain: TerrainDataList


class WFS_FR:
    wfs_url = "https://data.geopf.fr/wfs/ows"
    wfs_version = "2.0.0"
    road_key_name = "BDTOPO_V3:troncon_de_route"
    forests_key_name = "BDTOPO_V3:zone_de_vegetation"
    buildings_key_name = "BDTOPO_V3:batiment"
    water_key_name = "BDTOPO_V3:surface_hydrographique"
    activity_zone_key_name = "BDTOPO_V3:zone_d_activite_ou_d_interet"
    town_key_name = "BDTOPO_V3:commune"
    shore_key_name = "BDTOPO_V3:limite_terre_mer"
    residential_zone_key_name = "BDTOPO_V3:zone_d_habitation"
    departement_key_name = "BDTOPO_V3:arrondissement"
    sport_key_name = "BDTOPO_V3:terrain_de_sport"
    landuse_key_name = "BDCARTO_V5:occupation_du_sol"
    plot_key_name = "RPG.LATEST:parcelles_graphiques"

    bdortho_url = "https://data.geopf.fr/wms-r"
    bdortho_version = "1.3.0"
    bdortho_key_name = "ORTHOIMAGERY.ORTHOPHOTOS"

    wms_alti_url = "https://data.geopf.fr/annexes/ressources/wms-r/altimetrie.xml"
    wms_alti_version = "1.3.0"
    rge_key_name = "RGEALTI-MNT_PYR-ZIP_FXX_LAMB93_WMS"

    @staticmethod
    def get_town_request_url(town_name: str, town_dpt: str):
        return (
            "https://geo.api.gouv.fr/communes?nom="
            + town_name
            + "&codeDepartement="
            + town_dpt
            + "&format=geojson&geometry=contour"
        )


class IGN:

    # From https://geoservices.ign.fr/bd-cartor-descriptif-de-contenu
    bdcarto_landuses_values = [
        "Broussailles",
        "Bâti",
        "Carrière, décharge",
        "Eau libre",
        "Forêt",
        "Glacier, névé",
        "Mangrove",
        "Marais salant",
        "Marais, tourbière",
        "Prairie",
        "Rocher, éboulis",
        "Sable, gravier",
        "Vigne, verger",
        "Zone d'activités",
    ]

    bdcarto_sand_values = ["Sable, gravier"]

    # From BD TOPO documentation
    sport_values = [
        "Bassin de natation",
        "Grand terrain de sport",
        "Petit terrain multi - sports",
        "Piste de sport",
        "Terrain de tennis",
    ]

    # There are subcategories to most of those big ones, but as a first approximation of the surface material it's decent
    tartan_values = ["Terrain de tennis"]
    grass_values = ["Grand terrain de sport"]
    asphalt_values = ["Petit terrain multi - sports"]

    # From annex 1 of https://geoservices.ign.fr/sites/default/files/2023-11/DC_DL_RPG_2-1_0.pdf
    orchard_codes = ["20"]
    prairie_codes = ["18", "19"]
