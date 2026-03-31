# WorldWeaver Dev Documention 

This page is desgined to help you edit, customize and improve this software.
It will describe the internal modules, their roles and interactions.

## Structure

The project is divided into a few folders:

  * Assets: Stores the blender assets for rendering.
  * Config: Stores the default configuration files.
  * Shapefiles: Stores shapefiles that the software needs.
  * Drivers: Python module. A Driver is an object that fetches data for a source and outputs a RenderingData that the software uses for the render.
  * Loader: Python module. Used to load files that the software might need using
  * Manager: Python module. High-level objects that handle a particular job.
  * Parser: Python module. Low-level objects that parse files
  * Processor: Python module. Objects that are used for processing and calculations
  * Renderer: Python module. Objects that directly interact with Blender's API to display the objects.
  * Utils: Python module. Dataclasses, utilities, constants ...
  * main.py: the main python file

## Lighting

The scene is lit using a [native Blender Add-on](https://docs.blender.org/manual/en/3.5/addons/lighting/sun_position.html).

Currently, the sun position is set to the 12/06/2025 at 12PM, located at the center of the scene, but it could be customized.

Likewise, the intensity of the light is fixed for now, but could be adjusted.

## Adding a new data source

If you want to use to software on data that is not currently supported, you will want to create you own Driver.

You can copy the structure of the existing ones (IGNDriver for IGN data and OSMDriver for openstreetmap data) as a template.

Ideally, your new driver module should contain:
  * A `Loader` class whose job is to fetch the data wherever it is (files, data streams ...)
  * A `Preprocessor` class whose job is to create a `RenderingData` from the input data, using rules that you will have to devise
  * A `Driver` class, that has to inherit from `BaseDriver`, whose job is to orchestrate the loading, parsing and preprocessing of the data.
  * Probably a few helper classes for parsing and preprocessing (api-specific constants, column names in geodataframes etc ...)

Once you have all this, you can just modify the `select_driver` method in `main.py` to reference your driver, and select your driver via the `input_data` field the json configuration file of your runs.

### Relevant documentation:

#### RenderingData

::: worldweaver.Utils.RenderingDataFrames.RenderingData

#### BaseDriver

::: worldweaver.Drivers.BaseDriver.BaseDriver

#### select_driver

::: worldweaver.main.select_driver


## Adding a new object to the Blender scene

If you want to modify the Blender scene by adding an object, you will need to:

  * Determine from which data this object would be created. Depending on the complexity of the task, this could mean just editing currently-existing `Preprocessors` or also finding a way to load new data inside the `Loaders`. 
  * Add a new field to `RenderingData` and fill it with this new object data. `RenderingData` also has a validation mecanism to ensure that it's well-constructed and will not pose issues down the line during rendering, so you will have to add validation for your new data as well. Note also that adding fields to `RenderingData` will break compatibility with the existing drivers if they are not modified.
  * Create a new `Renderer` for your object. Depending on the object there are a few examples that might be a good template inside the `Renderers` module.
  * Reference and instantiate this new `Renderer` inside the `RenderManager`, and call the `render` method of the `Renderer` using the new data you added to `RenderingData` 
  * If you want to use a Blender asset like other objects, you will have to create it. Again, there might be examples that you can draw inspiration from in the `Assets` folder depending on what you're trying to do.
  * If you want your `Renderer` or your asset to be customizable, you need to add a new block in the `RenderingConfig`, edit the `ConfigLoader` so it parses and fills this new block, and add this new block to your json configuration files.

### Relevant documentation:

#### RenderingData

::: worldweaver.Utils.RenderingDataFrames.RenderingData

### Example of an object path: Factories.

This section aims to give an example of how an object is processed throughout the software to be rendered in the Blender scene.

It will focus on a specific kind of building: `Factory`, which is a term that in the software refers to "buildings that have an industrial nature"

#### Input Data

For the IGN Data, buildings are extracted from the [BD TOPO](https://geoservices.ign.fr/bdtopo), either from files or data streams.

This building data is fetched and stored inside the `buildings` field of the `GeoData` object returned by the `Loader`.

The `GeoData` is then passed to the `IGNPreprocessor`, which holds the rule engine that splits buildings into the various categories recognized by the software.

In the `Factory` case, it looks inside the `buildings` dataframe, particularly inside a column that stores the "usage" of this building, and matches it with a list of tags that indicate the building has an "industrial" nature.

Then those filtered buildings are stored into the appropriate field of the `RenderingData` the preprocessor generates.

For the OSMData, the process is more or less the same, with slight variations due to both data providers not giving a 1:1 feature match.

#### Rendering

In order to render `Factories`, there is a dedicated `FactoryRenderer`, which inherits from the more general `BuildingRenderer`.

This `FactoryRenderer` is instantiated inside the `RenderManager` and fed the configuration that it needs (see [configuration](#configuration)).

Then, when the render of the scene happens, the `render` method of the `FactoryRenderer` is called to transform the data inside `RenderingData` into Blender objects.

In this example, for each dataframe entry, a face representing the building footprint is drawn at the surface of the terrain, and a modifier is placed on the face to transform it into a 3D Building (see [asset](#assets)), with a number of levels either taken from the input data or from the configuration (if the input data does not contain this info).

#### Assets

The asset for `Factories` is based on [Buildify](https://paveloliva.gumroad.com/l/buildify), and takes the footprint and transforms it into a 3D building.

The number of levels of the building can be set for each building, or attributed a random value inside a range.

#### Configuration

Configuring the rendering of `Factories` takes a few parameters (example taken from `base_config.json`):

```json
      ...
      "factory_render": {
        "geometry_node_file": "Factories.blend",
        "geometry_node_name": "Factories",
        "tagging_index": 6,
        "default_levels_min": 2,
        "default_levels_max": 5
      },
      ...
```

See [configuration documentation](conf.md#objects) for detailed definitions.

This configuration is parsed by the `ConfigLoader`, and used to create a `BuildingRendererConfig` that will be passed to the `FactoryRenderer`. 

## Subdense data

In the current version, worldweaver is able to process samples of subdense data, 
but this part is still in a work in progress and still has a few things it needs to be industrialised.

This section will provide a list to achieve this goal.

### Selecting appropriate colors

Currently, the buildings are rendered with different wall colors depending on their change status.

Those colors are in the BuildingRenderer.wall_colors dictionary. You can try different ones by changing them there.

Alternatively, once you generate a subdense scene, you can edit the colors using the Utils.Rendering.change_color method.

For example, in Blender's python interpreter, to change the color of stable buildings to black :

```python
from worldweaver.Utils.Rendering import change_color
change_color("Stable", (0,0,0,1))
```


### Harmonise attribute names

Currently, the only subdense database we have uses names like "ID_Building_2011" or "ID_Building_2021", 
which is very specific for this case and needs to be harmonized.

The precise fix for this will depend on the use cases:

* Will we want to use more than two timestamps for visualisations ?
* Will databases include more than two timestamps ?
* Will there be differences between data providers for subdense ? 

In any case, changes need to be done inside worldweaver.Drivers.IGN.Dataframes.BuildingChangeDataFrame

### Index file

Currently, we only have one database, covering the surroundings of Strasbourg.

If we want to do the same thing anywhere in france, we will need to know which database covers our desired window.

For this, an index file will probably be the best solution. 

Just like we do for the French departements using the ARRONDISSEMENT/ARRONDISSEMENT.shp file, 
we could create a file inside the subdense_data folder that maps geographical regions and databases.

Then, in the SubdenseLoader, we do just like in the FileLoader and load all parts of the database that interest us 
(in case our zone is covering more than one database)

### Using subdense data outside of France

Currently, we only planned for using subdense data inside of France.

But, if you have data for another region/country, you could modifiy worldweaver to use it.

Depending on how similar it is to what is already present, the amount of work might vary.

For example, if you are able to derive subdense data from OSM history, adding this data to the OSM workflow might be pretty easy.

On the other hand, if you want data from another country that is very different from IGN or OSM, you might want to use a completly new driver.

For guidance on this, please look at [Adding a new data source](dev.md#adding-a-new-data-source) .




