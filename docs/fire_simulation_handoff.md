# Forest Fire Simulation — Session Handoff

## What Was Built

### `worldweaver/Processor/FireProcessor.py` ✅
Dijkstra-based fire spread algorithm, modelled after `FloodProcessor`.

**`FireProcessor.burn()` signature:**
```python
def burn(
    geo_window: GeoWindow,
    forests: g.GeoDataFrame,
    wheatfields: g.GeoDataFrame,
    cornfields: g.GeoDataFrame,
    grass: g.GeoDataFrame,
    ignition_points: list[tuple[float, float]],  # in scene CRS, not degrees
    fire_cell_size: float,
    fire_threshold: float,
) -> tuple[np.ndarray, tuple, tuple, float]
    # returns (is_burnt, lower_left, upper_right, fire_cell_size)
```

**Key behaviours:**
- Rasterizes forests + wheatfields + cornfields + grass into a boolean `flammable_map` using `shapely.within` vectorized over a meshgrid
- If `ignition_points` is empty, picks a random flammable cell via `np.argwhere(flammable_map)`
- Graph edge cost: `1.0` (cardinal) or `√2` (diagonal) for flammable→flammable; `1e9` to non-flammable (effectively blocked)
- Per-cell noise map (±20%) applied to spread costs for organic fire boundary
- Runs `scipy dijkstra` from all ignition points simultaneously (`min_only=True`)
- Cells with distance ≤ `fire_threshold` AND inside `flammable_map` are marked burnt
- **Works in original CRS** (not pre-centered like FloodProcessor — centering happens in FireRenderer)

---

### `worldweaver/Renderer/FireRenderer.py` ✅
Builds the `BurntArea` mesh from FireProcessor output.

**Follows `HiddenPolygonRenderer` pattern** (NOT FloodRenderer):
- Flat mesh draped on terrain using `interpolate_z` + `center_point` per vertex
- `hide_render = True`, `hide_viewport = True` — invisible, pure spatial reference
- No geometry node, no `Fire.blend` needed
- `pass_index` set to `tagging_index` for semantic segmentation

**Constructor:** `FireRenderer(terrain_data, tagging_index: int)` — no `RenderObjectConfig`, no GN file.

**The BurntArea mesh serves three consumers:**
1. `ForestRenderer.__config_geometry_node` → culls/replaces trees
2. `TerrainRenderer.set_burnt_zone()` → applies burnt ground texture
3. Object Index render pass → semantic tag value `8`

---

### `worldweaver/Renderer/ForestRenderer.py` ✅
`__config_geometry_node` updated to accept and pass BurntArea (Socket_9), WheatFieldsZone (Socket_11), and CornFieldsZone (Socket_12):
```python
def __config_geometry_node(self, road_object, building_object, terrain_object, ray_length,
                            burnt_area_object, wheatfields_object, cornfields_object):
    node["Socket_4"] = road_object
    node["Socket_6"] = building_object
    node["Socket_8"] = terrain_object
    node["Socket_3"] = ray_length
    if burnt_area_object is not None:
        node["Socket_9"] = burnt_area_object
    node["Socket_11"] = wheatfields_object
    node["Socket_12"] = cornfields_object
```

---

### `worldweaver/Renderer/TerrainRenderer.py` ✅
- `set_burnt_zone(burnt_object)` method added — called only from `draw_fire()`, avoiding the phantom square when fire is off
- `Compute Proximity Burnt` input cleared to `None` on `__init__` to neutralise any placeholder in `Terrain.blend`
- `Compute Field ID Wheat` and `Compute Field ID Corn` nodes wired in `__config_tagging_node`

---

### `worldweaver/Manager/RenderManager.py` ✅
- `FireRenderer` imported, `self.fire_renderer = None` in `__init__`
- `draw_fire()` instantiates `FireRenderer`, renders BurntArea, calls `set_burnt_zone()`
- `draw_decor()` passes BurntArea, WheatFieldsZone, and CornFieldsZone to forests GN

---

### `worldweaver/Utils/Config.py` ✅
`FireConfig` dataclass added:
```python
@dataclass
class FireConfig:
    activate: bool
    ignition_points: list[list[float]]  # [[lon, lat], ...] in WGS84 degrees; empty = random
    fire_cell_size: float
    fire_threshold: float
    tagging_index: int
```

---

### `worldweaver/Config/config.json` ✅
```json
"fire": {
    "activate": false,
    "ignition_points": [],
    "fire_cell_size": 5,
    "fire_threshold": 100,
    "tagging_index": 8
}
```

---

### `worldweaver/Loader/ConfigLoader.py` ✅
Full fire config loading block added, mirroring the flood pattern.

---

### `worldweaver/main.py` ✅
- `ignition_points` reprojected from WGS84 to scene CRS via geopandas
- `FireProcessor.burn()` called if `fire.activate`
- `render_manager.draw_fire(fire_data)` called after `draw_terrain()`
- Per-tile burnt area PNG export: crops `is_burnt` to camera tile bounds, resamples to output GSD using `scipy.ndimage.zoom`, saves as `<timestamp>_burnt.png`

---

### `worldweaver/Assets/Forests.blend` + `Forests_pretty.blend` ✅
- Socket_9 (`BurntArea_Obj`): Geometry Proximity → Noise Texture blend → threshold → Separate Geometry → burnt/normal Instance on Points branches → Join Geometry
- Socket_11 (`WheatFields_Obj`): excludes tree spawning inside wheat field polygons
- Socket_12 (`CornFields_Obj`): excludes tree spawning inside corn field polygons

---

### `worldweaver/Assets/Terrain.blend` ✅
In the `TerrainTagging` geometry node group:
- `"Compute Proximity Burnt"`: input socket index `2` receives BurntArea; applies scorched material where proximity < threshold
- `"Compute Field ID Wheat"`: input socket index `2` receives WheatFieldsZone; samples `field_id` attribute and stores on terrain
- `"Compute Field ID Corn"`: same for CornFieldsZone

---

### `worldweaver/Renderer/ZoneRenderer.py` ✅
`FieldZoneRenderer` added — stores a `field_id` integer face attribute per polygon so each field can be identified in the shader editor via an Attribute node:
- `WheatFieldRenderer` and `CornFieldRenderer` subclass it

---

---

## Key Architecture Decisions

| Decision | Reason |
|---|---|
| FireProcessor works in original CRS | GeoDataFrames (forests, zones) are in original CRS; centering happens in FireRenderer via `center_point` |
| FireRenderer hides mesh (`hide_render=True`) | Burnt material is in Terrain.blend tagging GN — no need for a visible BurntArea surface |
| No `Fire.blend` needed | BurntArea is a spatial reference only, like zone meshes (WheatFieldsZone, GrassZone, etc.) |
| Burnt zone tagging index = `8` | Next available after 0=terrain, 2=water, 3=forest, 4=road, 5=car, 6=building, 7=decor |
| Terrain.blend node name = `"Compute Proximity Burnt"` | Matches existing convention (`"Compute Proximity Grass"`, `"Compute Proximity Sand"`, etc.) |
| Both `Forests.blend` and `Forests_pretty.blend` need edits | Pretty version used for image export, placeholder for 3D/viewport export |
| `ignition_points` empty list = random ignition | Random cell sampled from `np.argwhere(flammable_map)` — always lands on valid flammable cell |
| `ignition_points` in config as `[lon, lat]` degrees | More human-readable than projected CRS coords; reprojection done in `main.py` |
| `set_burnt_zone()` separate from `__config_tagging_node` | Tagging node runs at draw_terrain() time before BurntArea exists; burnt zone set later from draw_fire() |
| Cost noise ±20% on fire spread graph | Avoids geometric wavefront edge at threshold cutoff — produces organic boundary |
| Burnt map exported as PNG per tile | Cropped to camera tile bounds + resampled to GSD; aligned with RGB/semantic images without Blender |

---

## Relevant Existing Files

| File | Role |
|---|---|
| `worldweaver/Processor/FloodProcessor.py` | Template for FireProcessor — same Dijkstra structure |
| `worldweaver/Renderer/FloodRenderer.py` | Shows GN-loading pattern (FireRenderer does NOT follow this) |
| `worldweaver/Renderer/HiddenPolygonRenderer.py` | Actual pattern FireRenderer follows |
| `worldweaver/Renderer/ForestRenderer.py` | BurntArea on Socket_9, WheatFields on Socket_11, CornFields on Socket_12 |
| `worldweaver/Renderer/TerrainRenderer.py` | set_burnt_zone() at line ~464; Compute Field ID nodes in __config_tagging_node |
| `worldweaver/Manager/RenderManager.py` | draw_fire() and draw_decor() wiring |
| `worldweaver/Utils/Config.py` | FireConfig dataclass |
| `worldweaver/Config/config.json` | fire block |
