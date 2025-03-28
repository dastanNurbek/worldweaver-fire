"""
   Schema of what the dataframes need to have so that Renderers are able to work.
   Dataframes outputed by Drivers have to follow these schemas.
"""
from shapely import area, difference, intersects, contains

from mage_procgen.Utils.Utils import ZonesRenderingData, safe_overlay, OverlayType


class RenderingBuildingDataFrame:

    height = "height"
    number_floors = "Nb_floors"
    geometry = "geometry"


class RenderingRoadDataFrame:

    number_lanes = "Nb_lanes"
    position_rel_to_ground = "Position_rel_to_ground"
    width = "Width"
    urban = "Urban"
    geometry = "geometry"

    has_sidewalks = "has_sidewalks"
    has_guardrails = "has_guardrails"


def clean_zones(
    wheatfields,
    cornfields,
    grass,
    developed,
    tartan,
    compacted,
    asphalt,
    sand,
    paths,
):
    list_zones = [
        wheatfields,
        cornfields,
        grass,
        developed,
        tartan,
        compacted,
        asphalt,
        sand,
    ]

    for zone_a_ind in range(len(list_zones)):
        zone_a = list_zones[zone_a_ind]
        for zone_b_ind in range(zone_a_ind + 1, len(list_zones)):

            if zone_a_ind == 0 and zone_b_ind == 1:
                continue

            zone_b = list_zones[zone_b_ind]

            # If either zone in empty, no point in comparing anything
            if zone_a.empty or zone_b.empty:
                continue

            zone_inter = safe_overlay(zone_a, zone_b, OverlayType.INTERSECTION)

            if not zone_inter.empty:
                new_geom_a = []
                for geom_a in zone_a.geometry:
                    new_geom_b = []
                    for geom_b in zone_b.geometry:
                        if intersects(geom_a, geom_b):
                            if contains(geom_a, geom_b):
                                geom_a = difference(geom_a, geom_b)
                            elif contains(geom_b, geom_a):
                                geom_b = difference(geom_b, geom_a)
                            elif area(geom_a) <= area(geom_b):
                                geom_b = difference(geom_b, geom_a)
                            else:
                                geom_a = difference(geom_a, geom_b)

                        new_geom_b.append(geom_b)

                    new_geom_a.append(geom_a)
                    zone_b = zone_b.set_geometry(new_geom_b)
                    list_zones[zone_b_ind] = zone_b

                zone_a = zone_a.set_geometry(new_geom_a)
                list_zones[zone_a_ind] = zone_a

    return ZonesRenderingData(
        wheatfields=list_zones[0],
        cornfields=list_zones[1],
        grass=list_zones[2],
        developed=list_zones[3],
        tartan=list_zones[4],
        compacted=list_zones[5],
        asphalt=list_zones[6],
        sand=list_zones[7],
        paths=paths,
    )
