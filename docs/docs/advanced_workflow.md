# Advanced features

This tutorial is intended as a jumping point for more advanced features such as asset modifications, flood etc.

## Configuration

Before you can render, you need to generate the configuration file for your run. 
Please look at the documentation for this in [Configuration Files Edition](conf.md).

There is an `example_advanced.json` file packaged with the software.

Inside, you will see a few differences with the `example_offline.json`:

* The `input_data` is set to "OSM-CH". This means it uses both openstreetmap and SwissAlti3D data.
* The `geo_window` has a different crs (it's the code for LV95, which is Switzerland's choice for its geo data). The coordinates in this example file describe a ~1km² part of the city of Bern.
* There is a `flood` section, whose `activate` is set to True. This means the software will generate a flood in this scene (see [Flood](flood.md))
* There is a `placeholder_forest_render` section inside `rendering/objects`. This means that for scene, the default asset for placeholder trees (described in `base_config.json`) will be overriden by whatever is described in this `placeholder_forest_render` section.

You can use such modifications to tweak the configuration however you like (you still need to change the `base_folder` like other files).  

```json
{
  "base_folder": "../../maps",
  "input_data": {
    "type": "OSM-CH"
  },
  "simulation_area": {
    "window_type": "COORDS",
    "geo_window": {
      "x_min": 2600536.3,
      "y_min": 1199198.5,
      "x_max": 2601636.9,
      "y_max": 1200065.4,
      "crs_from": 2056
    }
  },
  "terrain": {
    "terrain_resolution": 1,
    "use_orthoimage_as_basemap": false
  },
  "flood": {
    "activate": true,
    "flood_height": 10,
    "flood_cell_size": 1
  },
  "rendering": {
    "export_images": true,
    "device_type": "GPU",
    "camera_type": "ORTHOGRAPHIC",
    "ground_sampling_distance": 0.2,
    "tile_size": 512,
    "objects":
    {
      "placeholder_forest_render": {
      "geometry_node_file": "Forests.blend",
      "geometry_node_name": "Forest_feuillu",
      "tagging_index": 3
      }
    }
  }
}
```
Change the beginning to (for example):

```json
{
  "base_folder": "/home/MyUser/data/worldweaver/maps",
  "input_data": {
    "type": "OSM-CH"
  },
  "simulation_area": {
    "window_type": "COORDS",
    "geo_window": {
      "x_min": 2600536.3,
      "y_min": 1199198.5,
      "x_max": 2601636.9,
      "y_max": 1200065.4,
      "crs_from": 2056
    }
  },
```
## Run

Run will work exactly as the [basic workflow](basic_workflow.md/#run). Just select the configuration you just generated for the run.
