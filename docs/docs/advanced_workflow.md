# Advanced features

This tutorial is intended as a jumping point for more advanced features such as asset modifications, flood etc.

## Configuration

Before you can render, you need to generate the configuration file for your run. 
Please look at the documentation for this in [Configuration Files Edition](conf.md).

There is an `example_advanced.json` file packaged with the software.

Inside, you will see a few differences with the `example_file.json`:

* The `input_data` is set to "OSM-CH". This means it uses both openstreetmap and SwissAlti3D data.
* The `geo_window` has a different crs (it's the code for LV95, which is Switzerland's choice for its geo data). The coordinates in this example file describe a ~1km² part of the city of Bern.
* There is a `flood` section, whose `activate` is set to True. This means the software will generate a flood in this scene (see [Flood](flood.md))
* There is a `placeholder_forest_render` section inside `rendering/objects`. This means that for scene, the default asset for placeholder trees (described in `base_config.json`) will be overriden by whatever is described in this `placeholder_forest_render` section.

You can use such modifications to tweak the configuration however you like. 

## Run

Run will work exactly as the [basic workflow](basic_workflow.md/#run). Just select the configuration you just generated for the run.
