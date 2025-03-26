class OSM:
    @staticmethod
    def get_town_request_ch(town_name: str):
        return (
            'area["ISO3166-1"=CH];nwr["name"="'
            + town_name
            + '"][boundary=administrative][type=boundary][admin_level="8"](area);out;(way(r); >;);out skel;'
        )

    @staticmethod
    def get_town_request(town_name: str):
        return (
            'nwr[name="'
            + town_name
            + '"][boundary=administrative][type=boundary][admin_level="8"];out;(way(r); >;);out skel;'
        )

    @staticmethod
    def get_additional_request_inners(bbox: tuple[float, float, float, float]):
        # Order of coords for query is south, west, north, east
        return (
            "nwr("
            + "{:.5f}".format(bbox[1])
            + ","
            + "{:.5f}".format(bbox[0])
            + ","
            + "{:.5f}".format(bbox[3])
            + ","
            + "{:.5f}".format(bbox[2])
            + ")->.a;"
            + 'way(r.a:"inner")-> .b;'
            + 'way.b["landuse"]->.c;'
            + "(.c;.c>;);"
            + "out;"
        )

    @staticmethod
    def get_additional_request_landuses(bbox: tuple[float, float, float, float]):
        # Order of coords for query is south, west, north, east
        return (
            "nwr("
            + "{:.5f}".format(bbox[1])
            + ","
            + "{:.5f}".format(bbox[0])
            + ","
            + "{:.5f}".format(bbox[3])
            + ","
            + "{:.5f}".format(bbox[2])
            + ")->.a;"
            + ".a is_in ->.d;"
            + ".d < ->.e;"
            + 'nwr.e["landuse"]->.f;'
            + "(.f;.f>;);"
            + "out;"
        )

    # General
    tags = "tags"
    amenity = "amenity"

    # Geometry types
    point = "Point"
    geometry = "geometry"
    multi_polygon = "MultiPolygon"
    polygon = "Polygon"
    multi_line_string = "MultiLineString"
    line_string = "LineString"

    building_tag = "building"

    highway_tag = "highway"

    path_tags = [
        "footway",
        "bridleway",
        "steps",
        "corridor",
        "path",
        "via_ferrata",
    ]

    # Land
    landuse = "landuse"
    natural = "natural"

    water = "water"

    usage_forests_tags = "forest"
    usage_residential_tags = "residential"
    usage_commercial_tags = "residential"
    usage_industrial_tags = "industrial"

    # Roads
    lanes = "lanes"
    max_speed = "maxspeed"
    mph_key = "mph"
    mph_mult = 1.609344
    knot_key = "knots"
    knot_mult = 1.852
    kmh_keys = ["km/h", "kph", "kmh", "kmph"]
    sidewalk = "sidewalk"

    has_sidewalk_list = ["both", "separate", "left", "right"]

    bridge = "bridge"
    tunnel = "tunnel"

    # Buildings
    churches_types = [
        "religious ",
        "cathedral",
        "chapel",
        "church",
        "kingdom_hall",
        "monastery",
        "mosque",
        "presbytery",
        "shrine",
        "synagogue",
        "temple",
    ]
    malls_types = ["commercial", "office", "retail", "supermarket"]
    factories_types = ["industrial", "warehouse"]
    houses_types = ["house", "semidetached_house", "trullo"]

    field_landuses = [
        "allotments",
        "aquaculture",
        "farmland",
        "farmyard",
        "greenhouse_horticulture",
        "orchard",
        "plant_nursery",
        "vineyard",
    ]

    field_crop = "crop"
    wheat_crop = "wheat"
    corn_crop = "corn"

    grass_landuses = [
        "grass",
        "meadow",
        "recreation_ground",
    ]

    developed_landuses = [
        "brownfield",
        "commercial",
        "construction",
        "garages",
        "industrial",
        "landfill",
        "quarry",
        "religious",
        "residential",
        "retail",
    ]

    leisure_landuses = [
        "village_green",
    ]

    surface = "surface"

    grass_surface = "grass"
    asphalt_surface = [
        "asphalt",
    ]
    tartan_surface = "tartan"
    compacted_surface = "compacted"
    sand_surface = "sand"
    beach = "beach"

    leisure = "leisure"
    playground = "playground"

    height = "height"
    levels = "building:levels"


class SwissAlti:
    @staticmethod
    def get_terrain_request_url(x: int, y: int):
        return (
            "https://data.geo.admin.ch/ch.swisstopo.swissalti3d/swissalti3d_2019_"
            + str(x // 1000)
            + "-"
            + str(y // 1000)
            + "/swissalti3d_2019_"
            + str(x // 1000)
            + "-"
            + str(y // 1000)
            + "_0.5_2056_5728.tif"
        )


class WFS:
    srtm_url = "https://data.geopf.fr/wms-r"
    srtm_version = "1.3.0"
    srtm_key_name = "ELEVATION.ELEVATIONGRIDCOVERAGE.SRTM3"
