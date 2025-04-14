"""
   Schema of what the dataframes need to have so that Renderers are able to work.
   Dataframes outputed by Drivers have to follow these schemas.
"""


class RenderingDataFrame:
    geometry = "geometry"


class RenderingBuildingDataFrame:

    height = "height"
    number_floors = "Nb_floors"
    geometry = "geometry"


class RenderingRoadDataFrame:

    number_lanes = "Nb_lanes"
    geometry = "geometry"
    has_sidewalks = "has_sidewalks"
    has_guardrails = "has_guardrails"
    is_bridge = "is_bridge"
    is_tunnel = "is_tunnel"
