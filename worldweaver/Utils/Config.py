from dataclasses import dataclass
from enum import StrEnum
from typing import Union


class WindowTypes(StrEnum):
    TOWN = "TOWN"
    FILE = "FILE"
    COORDS = "COORDS"


class CameraType(StrEnum):
    ORTHOGRAPHIC = "ORTHOGRAPHIC"
    PERSPECTIVE = "PERSPECTIVE"


class RenderDeviceType(StrEnum):
    CPU = "CPU"
    GPU = "GPU"


@dataclass
class RenderObjectConfig:
    geometry_node_file: str
    geometry_node_name: str
    tagging_index: int


@dataclass
class BuildingRendererConfig:
    geometry_node_file: str
    geometry_node_name: str
    tagging_index: int
    default_levels_min: int
    default_levels_max: int


@dataclass
class HouseRendererConfig:
    geometry_node_file: str
    geometry_node_name: str
    tagging_index: int
    default_height_min: int
    default_height_max: int
    roof_slope: float


@dataclass
class RoadRendererConfig:
    geometry_node_file: str
    geometry_node_name: str
    car_collection_info_node_name: str
    road_tagging_index: int
    car_tagging_index: int


@dataclass
class BridgeRendererConfig:
    geometry_node_file: str
    geometry_node_name: str
    tagging_index: int
    bridge_group_name: str


@dataclass
class TerrainRendererConfig:
    geometry_node_file: str
    adaptation_node_name: str
    tagging_node_name: str
    decorating_node_name: str
    base_material_name: str
    tagged_material_name: str
    tagging_index: int
    decor_tagging_index: int


@dataclass
class CoordsGeoWindowConfig:
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    crs_from: int


@dataclass
class GeoWindowConfig:
    window_type: str
    geo_window: CoordsGeoWindowConfig
    town_id: str
    window_shapefile: str


@dataclass
class OutputConfig:
    export_img: bool
    export_scene: bool
    device_type: str
    camera_type: str
    tile_size: int
    ground_sampling_distance: float
    time_of_day: float = 10.5
    sky_strength: float = 1.0


@dataclass
class FloodConfig:
    activate: bool
    flood_height: float
    flood_cell_size: float


@dataclass
class FireConfig:
    activate: bool
    ignition_points: list[list[float]]  # [[lon, lat], ...] in WGS84 degrees; empty = random
    fire_cell_size: float
    fire_threshold: float
    tagging_index: int
    seed: int | None = None  # None = random each run
    save_pre_fire_render: bool = False
    pre_fire_time_of_day: float | None = None  # None = use rendering.output.time_of_day
    pre_fire_sky_strength: float | None = None  # None = use rendering.output.sky_strength


@dataclass
class TerrainConfig:
    terrain_resolution: float
    use_sat_img: bool


@dataclass
class RenderingConfig:

    output: OutputConfig
    building_render_config: BuildingRendererConfig
    house_render_config: HouseRendererConfig
    church_render_config: BuildingRendererConfig
    factory_render_config: BuildingRendererConfig
    mall_render_config: BuildingRendererConfig
    flood_render_config: RenderObjectConfig
    placeholder_forest_render_config: RenderObjectConfig
    pretty_forest_render_config: RenderObjectConfig
    road_render_config: RoadRendererConfig
    bridge_render_config: BridgeRendererConfig
    water_render_config: RenderObjectConfig
    terrain_render_config: TerrainRendererConfig


@dataclass
class Config:
    base_folder: str
    data_source: str
    geo_window: GeoWindowConfig
    terrain: TerrainConfig
    flood: FloodConfig
    fire: FireConfig
    rendering: RenderingConfig


# Union of types used for type hints of BaseRenderer, whose child classes might have different configurations
BaseRenderConfig = Union[
    RenderObjectConfig, BuildingRendererConfig, HouseRendererConfig
]
