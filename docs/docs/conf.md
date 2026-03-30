# Configuration file generation

The behavior of the software can be configured by json configuration files.

## Guidelines for configuration edition

For performances reasons, keep the window at a reasonable size (above 10 km² seems to be a bit big especially if there is flooding involved, and there is a hard limit of 20km²).

The terrain size and resolution will weight heavily on the performances, but having a scene that is large and detailed enough is also important to get realistic results especially if you use flooding.

If you modify assets, make sur they are not too polygon-heavy to avoid saturating Blender (especially for trees, because there can easily be a lot of them in a scene).

Some parts of the configuration are optional. If not present in the file, they will take the value of the default configuration file `base_config.json`. 
This file should not be edited except for the `base_folder`.

## Configuration file structure detail

  * `base_folder` is the path to the folder containing all the data the application will use. Should be the same for all of your files.

### Input Data:

  * `type` describes where the input data will come from. Can currently take 4 values:
    * "FILE" (France only): data is taken from IGN's open data files that you have to download and extract (see [Datafiles](datafiles.md) and [File Workflow](file_workflow.md)).
    * "STREAM" (France only): data is taken from IGN's geo servers .
    * "SUBDENSE" (France only): data is taken from IGN's geo servers and building change data from the [SUBDENSE project](https://hal.science/hal-04196186). Experimental feature. See [Dev doc](dev.md#subdense-data) for more info. 
    * "OSM-SRTM": data is taken from [OpenStreetMap](https://www.openstreetmap.org) using [Overpass](https://wiki.openstreetmap.org/wiki/Overpass_API).
    * "OSM-CH" (Switzerland only): data is taken from openstreetmap as well but the terrain is from [swissALTI3D](https://www.swisstopo.admin.ch/fr/modele-altimetrique-swissalti3d).

    !!! note "Issue with OSM"
    
        There is currently an issue preventing the fecthing of data from overpass. Please use a different data provider until a fix is found.

### Simulation Area:

  * `window_type` is used to determine how the window will be defined. Can take 3 values:
    * "COORDS": window will be taken be from the `geo_window` block.
    * "TOWN": window will be taken be from the `town` block.
    * "FILE": window will be taken be from the `shapefile` block.

  * `geo_window`: only required if `window_type` is "COORDS". Contains:
    * `x_min`, `x_max`, `y_min` and `y_max`: coordinates of the window
    * `crs_from` (optional): code of the CRS of the coordinates
      * `town`: only required if `window_type` is "TOWN". Contains:
        * `identifier`: An identifier of the town. Expected format is different depending of the input data type:
            * If using IGN data, should be the name of the town followed by the 2 digit code of the departement, for example "Loos-en-Gohelle 62" to select the town of [Loos-en-Gohelle](https://www.openstreetmap.org/relation/1113031) in the departement [62 (Pas-de-Calais)](https://www.openstreetmap.org/relation/7394#map=9/50.517/2.372).
            * If using OSM, it should just be the name of the town. In this case, the software gets the town geometry from an [Overpass](https://overpass-turbo.eu/#) query.

!!! note "Word of warning"

    It searches in openstreetmap database for towns in the whole world with such a name, and just picks the first result, so you might not get what you expect. You can try out the request yourself first to confirm that it will select the correct zone. The request is:

    ```
    nwr[name="<town_name>"][boundary=administrative][type=boundary][admin_level="8"];out;(way(r); >;);out skel;
    ```
      
  * `shapefile`: only required if `window_type` is "FILE". Contains:
    * `path`: Path of the shapefile describing the window


### Terrain:

  * `terrain_resolution`: Spatial resolution of the terrain in the render. Ideally it should be the same as the terrain raster data resolution to get the best ratio of accuracy vs performance, but it can be lowered for big scenes.
  * `use_orthoimage_as_basemap`: if True, the software will use BDORTHO images as texture for the terrain (only if using IGN data). If False, it will use a shader base on landuse info

### Flood (optional): 

  * `activate`: if True, will tell the software to generate a flood on the scene . For more precise info on how the flood is generated, go to [Flooding Algorithm](flood.md).
  * `flood_height`: Height of the flood in meters.
  * `flood_cell_size`: Spatial resolution of the flood.

### Rendering:

  * `export_images`: if True, will tell the software to generate png files from aerial views the scene. If False, will only render one sample image at the center of the scene.
  * `device_type`: Indicates on which hardware to render the scene. Can be "CPU" or "GPU" (preferred).
  * `camera_type`: Indicates which camera to use. Can be "PERSPECTIVE" or "ORTHOGRAPHIC" (preferred).
  * `ground_sampling_distance`: The size of a pixel, in m.
  * `tile_size`: The resolution of the output images.


#### Objects

All objets are optional. Here is the list of possible objects you can configure:

  * `building_render`: block configuring the "normal" buildings. Contains:
    * `geometry_node_file`: name of the Blender asset file for the object. It must be in the Assets folder. 
    * `geometry_node_name`: name of the geometry node setup for the object. For more info on how assets should be generated, go to [Assets Management](assets.md). 
    * `tagging_index`: index using which object will be tagged in the output semantic map.
    * `default_levels_min`: default value of the minimum levels of the geometry node (only used if there are no height or level value for the building in the input data)
    * `default_levels_max`: default value of the maximum levels of the geometry node (only used if there are no height or level value for the building in the input data)

  * `church_render`: block configuring the religious buildings. Contains:
    * `geometry_node_file`: name of the Blender asset file for the object. It must be in the Assets folder. 
    * `geometry_node_name`: name of the geometry node setup for the object. For more info on how assets should be generated, go to [Assets Management](assets.md). 
    * `tagging_index`: index using which object will be tagged in the output semantic map.
    * `default_levels_min`: default value of the minimum levels of the geometry node (only used if there are no height or level value for the building in the input data)
    * `default_levels_max`: default value of the maximum levels of the geometry node (only used if there are no height or level value for the building in the input data)

  * `factory_render`: block configuring the industrial buildings. Contains:
    * `geometry_node_file`: name of the Blender asset file for the object. It must be in the Assets folder. 
    * `geometry_node_name`: name of the geometry node setup for the object. For more info on how assets should be generated, go to [Assets Management](assets.md). 
    * `tagging_index`: index using which object will be tagged in the output semantic map.
    * `default_levels_min`: default value of the minimum levels of the geometry node (only used if there are no height or level value for the building in the input data)
    * `default_levels_max`: default value of the maximum levels of the geometry node (only used if there are no height or level value for the building in the input data)

  * `mall_render`: block configuring the commercial buildings. Contains:
    * `geometry_node_file`: name of the Blender asset file for the object. It must be in the Assets folder. 
    * `geometry_node_name`: name of the geometry node setup for the object. For more info on how assets should be generated, go to [Assets Management](assets.md). 
    * `tagging_index`: index using which object will be tagged in the output semantic map.
    * `default_levels_min`: default value of the minimum levels of the geometry node (only used if there are no height or level value for the building in the input data)
    * `default_levels_max`: default value of the maximum levels of the geometry node (only used if there are no height or level value for the building in the input data)

  * `house_render`: block configuring the houses. Contains:
    * `geometry_node_file`: name of the Blender asset file for the object. It must be in the Assets folder. 
    * `geometry_node_name`: name of the geometry node setup for the object. For more info on how assets should be generated, go to [Assets Management](assets.md). 
    * `tagging_index`: index using which object will be tagged in the output semantic map.
    * `default_height_min`: default value of the minimum height of the building (only used if there are no height or level value for the building in the input data)
    * `default_height_max`: default value of the maximum height of the building (only used if there are no height or level value for the building in the input data)
    * `roof_slope_degrees`: slope of the roof.

  * `flood_render`: block configuring the flood water. Contains:
    * `geometry_node_file`: name of the Blender asset file for the object. It must be in the Assets folder. 
    * `geometry_node_name`: name of the geometry node setup for the object. For more info on how assets should be generated, go to [Assets Management](assets.md). 
    * `tagging_index`: index using which object will be tagged in the output semantic map.

  * `placeholder_forest_render`: block configuring the "placeholder" trees. Contains:
    * `geometry_node_file`: name of the Blender asset file for the object. It must be in the Assets folder. 
    * `geometry_node_name`: name of the geometry node setup for the object. For more info on how assets should be generated, go to [Assets Management](assets.md). 
    * `tagging_index`: index using which object will be tagged in the output semantic map.

  * `pretty_forest_render`: block configuring the "pretty" trees. Contains:
    * `geometry_node_file`: name of the Blender asset file for the object. It must be in the Assets folder. 
    * `geometry_node_name`: name of the geometry node setup for the object. For more info on how assets should be generated, go to [Assets Management](assets.md). 
    * `tagging_index`: index using which object will be tagged in the output semantic map.

  * `road_render`: block configuring the roads. Contains:
    * `geometry_node_file`: name of the Blender asset file for the object. It must be in the Assets folder. 
    * `geometry_node_name`: name of the geometry node setup for the object. For more info on how assets should be generated, go to [Assets Management](assets.md).
    * `car_collection_info_node_name`: name of the collection containing the cars the will be added on the roads.
    * `tagging_index`: index using which object will be tagged in the output semantic map.
    * `car_tagging_index`: index using which cars will be tagged in the output semantic map.

  * `bridge_render`: block configuring the bridges. Contains:
    * `geometry_node_file`: name of the Blender asset file for the object. It must be in the Assets folder. 
    * `geometry_node_name`: name of the geometry node setup for the object. For more info on how assets should be generated, go to [Assets Management](assets.md).
    * `tagging_index`: index using which object will be tagged in the output semantic map.
    * `bridge_group_name`: name of the group containing the pillars of the bridges.

  * `water_render`: block configuring the water. Contains:
    * `geometry_node_file`: name of the Blender asset file for the object. It must be in the Assets folder. 
    * `geometry_node_name`: name of the geometry node setup for the object. For more info on how assets should be generated, go to [Assets Management](assets.md). 
    * `tagging_index`: index using which object will be tagged in the output semantic map.

  * `terrain_render`: block configuring the terrain. Contains:
    * `geometry_node_file`: name of the Blender asset file for the object. It must be in the Assets folder. 
    * `adaptation_node_name`: name of the geometry node setup to smooth the terrain beneath roads, water and buildings.
    * `tagging_node_name`: name of the geometry node setup to tag the terrain in order to texture it
    * `decorating_node_name`: name of the geometry node setup to decorate the terrain with objects like trashcans etc.
    * `base_material_name`: name of the material used if `use_orthoimage_as_basemap` is True.
    * `tagged_material_name`: name of the material used if `use_orthoimage_as_basemap` is False.
    * `tagging_index`: index using which terrain will be tagged in the output semantic map.
    * `decor_tagging_index`: index using which decor will be tagged in the output semantic map.
