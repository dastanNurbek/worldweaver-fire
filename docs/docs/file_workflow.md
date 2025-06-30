# Workflow for offline runs

## Preparation

If you are planning on using offline runs, first, you need to get the data needed for the application.
For this version, only data from IGN [https://www.geoportail.gouv.fr/](https://www.geoportail.gouv.fr/) is supported, though with adaptations the software could be adapted for different data providers.

IGN provides data for each Departement. For each zone you want to render, you need to 
download:

  - BD TOPO (terrain and infrastructure definition) [https://geoservices.ign.fr/bdtopo](https://geoservices.ign.fr/bdtopo)
  - RGE Alti (altitude raster) [https://geoservices.ign.fr/rgealti](https://geoservices.ign.fr/rgealti). Currently, the application only works with the 1m resolution dataset and not the 5m one.
  - BD ORTHO (orthorectified aerial view) [https://geoservices.ign.fr/bdortho](https://geoservices.ign.fr/bdortho). Only necessary if you want ortho images to texture the terrain
  - BD CARTO (landuse information) [https://geoservices.ign.fr/bdcarto](https://geoservices.ign.fr/bdcarto)
  - RPG (field plot information) [https://geoservices.ign.fr/rpg](https://geoservices.ign.fr/rpg). This data is grouped by region instead of departement by IGN, but it works the same. Just download the data for the region that contains the departement you're interested.

!!! note "About the data"

    Since the data is grouped by departements, the databases can be voluminous to download (RGE Alti is usually a couple of GB and BD Ortho can easily reach 50GB), and IGN servers are quite slow, it might take quite a while to get all the data for a departement

Once you have those datasets for each departement covered by the zone you want to render, you need to extract them so the software can read them. Command line helpers are available for that purpose in [Datafiles](datafiles.md)

## Configuration

Before you can render, you need to generate the configuration file for your run. 
Please look at the documentation for this in [Configuration Files Edition](conf.md).

Copy the `example_offline.json` and give it an appropriate name (or just edit it). 

Then:

 * Change the `base_folder` field to the value that reflects your setup. 
 * Change the `simulation_area` to whatever you want to render.

For example if you want the software to use the "/home/MyUser/data/worldweaver/maps" folder and generate a scene around  [this district of the city of Nice](https://www.openstreetmap.org/#map=15/43.68995/7.29527), the start of your configuration file will go from this:
```json
{
  "base_folder": "../../maps",
  "input_data": {
    "type": "FILE"
  },
  "simulation_area": {
    "window_type": "COORDS",
    "geo_window": {
      "x_min": 7.1,
      "y_min": 44.077,
      "x_max": 7.11,
      "y_max": 44.09,
      "crs_from": 4326
    }
  },
    ...
```
to this:
```json
{
  "base_folder": "/home/MyUser/data/worldweaver/maps",
  "input_data": {
    "type": "FILE"
  },
  "simulation_area": {
    "window_type": "COORDS",
    "geo_window": {
      "x_min": 7.29000,
      "y_min": 43.68350,
      "x_max": 7.31000,
      "y_max": 43.70000,
      "crs_from": 4326
    }
  },
    ...
```
## Run

Run will work exactly as the [basic workflow](basic_workflow.md/#run). Just select the configuration you just generated for the run.

