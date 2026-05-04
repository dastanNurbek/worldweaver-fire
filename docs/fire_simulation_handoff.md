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
2. `TerrainRenderer.__config_tagging_node` → applies burnt ground texture
3. Object Index render pass → semantic tag value `8`

---

## Remaining Todo List

### 1. `worldweaver/Assets/Forests.blend` + `Forests_pretty.blend` — Blender edit
Add burnt area socket to **both** GN setups (`Forest_pine` in `Forests.blend`, `Forest` in `Forests_pretty.blend`):
- New Object input socket (e.g. `Socket_10`) for the BurntArea mesh
- Wire: `Geometry Proximity` → blend with `Noise Texture` (world Position) → threshold → `Separate Geometry`
- Burnt branch: `Instance on Points` with **burnt bark tree collection** (leafless, charred material)
- Unburnt branch: `Instance on Points` with normal tree collection
- `Join Geometry` both branches → output

### 2. `worldweaver/Assets/Terrain.blend` — Blender edit
In the `TerrainTagging` geometry node group:
- Add node named **`"Compute Proximity Burnt"`** (same pattern as existing `"Compute Proximity Grass"` etc.)
- Input socket index `2` receives the BurntArea object reference
- Apply scorched/charred ground material where proximity distance < threshold

### 3. `worldweaver/Renderer/ForestRenderer.py`
Update `__config_geometry_node` to accept and pass the BurntArea object:
```python
def __config_geometry_node(self, road_object, building_object, terrain_object, ray_length, burnt_area_object):
    node = D.objects[self._mesh_name].modifiers[self.geometry_node_name]
    node["Socket_4"] = road_object
    node["Socket_6"] = building_object
    node["Socket_8"] = terrain_object
    node["Socket_3"] = ray_length
    node["Socket_10"] = burnt_area_object   # new — socket name TBD after Blender edit
```

### 4. `worldweaver/Renderer/TerrainRenderer.py`
Update `__config_tagging_node` to accept and pass the BurntArea object:
```python
def __config_tagging_node(self, ..., burnt_object):
    ...
    node_tree.nodes["Compute Proximity Burnt"].inputs[2].default_value = burnt_object
```

### 5. `worldweaver/Manager/RenderManager.py`
- Import `FireRenderer`
- Instantiate in `__init__`: `self.fire_renderer = FireRenderer.FireRenderer(terrain_data, tagging_index=8)`
- Add `draw_fire()` method:
```python
def draw_fire(self, fire_data):
    self.fire_renderer.render(fire_data, self.window.center, rendering_collection_name)
```
- In `draw_decor()`, pass BurntArea to both:
```python
self.forests_renderer._ForestRenderer__config_geometry_node(
    self.road_renderer.get_mesh_obj(),
    self.building_footprint_renderer.get_mesh_obj(),
    self.terrain_renderer.get_mesh_obj(),
    get_camera(CameraType.ORTHOGRAPHIC).location[2] * 2,
    self.fire_renderer.get_mesh_obj(),   # new
)
```
- In `draw_terrain()`, pass BurntArea to terrain tagging:
```python
self.terrain_renderer._TerrainRenderer__config_tagging_node(
    ...,
    burnt_object=self.fire_renderer.get_mesh_obj(),   # new
)
```

### 6. `worldweaver/Utils/Config.py`
Add `FireConfig` dataclass and update `Config`:
```python
@dataclass
class FireConfig:
    activate: bool
    ignition_points: list[list[float]]  # [[lon, lat], ...] in WGS84 degrees; empty = random
    fire_cell_size: float
    fire_threshold: float
    tagging_index: int

@dataclass
class Config:
    ...
    fire: FireConfig   # add this field
```

### 7. `worldweaver/Config/config.json`
Add fire block:
```json
"fire": {
    "activate": false,
    "ignition_points": [],
    "fire_cell_size": 5,
    "fire_threshold": 100,
    "tagging_index": 8
}
```

### 8. `worldweaver/main.py`
- Load `fire` config into `FireConfig`
- Reproject `ignition_points` from WGS84 degrees to scene CRS (use geopandas, same pattern as GeoWindow CRS conversion)
- Call `FireProcessor.burn(...)` if `fire.activate`
- Call `render_manager.draw_fire(fire_data)` after `draw_terrain()`, before `draw_decor()`

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

---

## Relevant Existing Files

| File | Role |
|---|---|
| `worldweaver/Processor/FloodProcessor.py` | Template for FireProcessor — same Dijkstra structure |
| `worldweaver/Renderer/FloodRenderer.py` | Shows GN-loading pattern (FireRenderer does NOT follow this) |
| `worldweaver/Renderer/HiddenPolygonRenderer.py` | Actual pattern FireRenderer follows |
| `worldweaver/Renderer/ForestRenderer.py` | Needs `burnt_area_object` added to `__config_geometry_node` |
| `worldweaver/Renderer/TerrainRenderer.py` | Needs `burnt_object` added to `__config_tagging_node` (line 413) |
| `worldweaver/Manager/RenderManager.py` | Central wiring — `draw_flood()` at line 290 is the template for `draw_fire()` |
| `worldweaver/Utils/Config.py` | Add `FireConfig` dataclass here |
| `worldweaver/Config/config.json` | Add `"fire"` block here |
