# Starting your first run

## Configuration

Before you can render, you need to generate the configuration file for your run. 
Edit the `Config/base_config.json` file to set the `base_folder` to a value that suits you.

For example if you want the software to use the "/home/MyUser/data/worldweaver/maps" folder, the start of your configuration file will go from this:
```json
{
  "base_folder": "../../maps",
  "input_data": {
    "type": "OSM-SRTM"
  },
  "simulation_area": {
    "window_type": "COORDS",
    "geo_window": {
    "x_min": -8232499.0,
    "y_min": 4982071.8,
    "x_max": -8231604.3,
    "y_max": 4982668.9,
    "crs_from": 3857
    },
    ...
```
to this:
```json
{
  "base_folder": "/home/MyUser/data/worldweaver/maps",
  "input_data": {
    "type": "OSM-SRTM"
  },
  "simulation_area": {
    "window_type": "COORDS",
    "geo_window": {
    "x_min": -8232499.0,
    "y_min": 4982071.8,
    "x_max": -8231604.3,
    "y_max": 4982668.9,
    "crs_from": 3857
    },
    ...
```
For further info please look at the documentation for this in [Configuration Files Edition](conf.md).

## Run

### Inside Blender

Once the configuration file is done, to open Blender:

Get inside the virtual environment you used during the installation: 

```bash
source <path/to/virtual_env>/bin/activate
```
Then:
```bash
PYTHONPATH="$(python -c "import sys; print(\":\".join(sys.path))")" blender --python-use-system-env
```

You can then set the configuration file used by the plugin, either by going to `Edit->Preferences->Add-ons`, 
search for MAGE Procgen, and edit the *Configuration File Path* field. 

Alternatively, you can also do it by pressing `Ctrl + Shift + L` or go to `Object->WorldWeaver Config Select`.

Once the configuration file is set (you don't have to do it if the name of the file has not changed since the last run),
you can run the plugin by either pressing `Ctrl + Shift + M` or go to `Object->WorldWeaver`.

While the program is running, you will not be able to see or do anything inside Blender, 
but you can follow the progression through the logs in the terminal you used to start Blender. 
A log file will also be created in a "Logs" folder inside the `base_folder` described in the configuration file.

Once the run is finished, you will be able to see the scene and will have a project folder containing a sample rendering (see [File System](filesystem.md))

### Headless mode

Get inside the virtual environment you used during the installation: 

```bash
source <path/to/virtual_env>/bin/activate
```

Then start the run:

```bash
python <path/to/worldweaver>/headless_script.py --config <path/to/worldweaver>/worldweaver/Config/base_config.json
```

While the program is running you can follow the progression through the logs in the terminal.
A log file will also be created in a "Logs" folder inside the `base_folder` described in the configuration file.

Once the run is finished, you will be able to see the scene and will have a project folder containing a sample rendering (see [File System](filesystem.md))
