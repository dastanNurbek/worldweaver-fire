# Experimental features

This tutorial is intended to show experimental features of the software

## Export

This section shows how to get export a scene after a run.

A few notes:

* The export script (located inside worldweaver.Utils.Export.export_scene_to_tileset) is very dependent on the whole scene and which assets are used. Should you develop new features, use new models, you probably need to edit the export script as well.
* Exporting means applying all geometry nodes and other modifiers, meaning turning everything in to real geometry. This might create a huge amount of vertices if used with assets that are not carefully chosen.
* Some procedural materials do not export correctly. We've chosen to edit them to simplify them and make them exportable. This is only done in the export script.

### Configuration

There is an `example_export.json` file packaged with the software.

It is a very small scene, part of Saint-Sauveur-sur-Tinée.

There are some key changes with previous files :

- The `export_scene` flag is set to true.
- The buildings use the `_box` assets, to make the models lighter because the base ones really are not optimized for exports.

You can use such modifications to tweak the configuration however you like (you still need to change the `base_folder` like other files).  

### Run

Run will work exactly as the [basic workflow](basic_workflow.md/#run). Just select the configuration you just generated for the run.

At the end of the run, the export script will be ran, applying all modifiers in the scene (to replace the geometrynodes by actual geometry), some materials will be simplified to be exported,
and a 3DTiles of the scene will be generated and stored in the project's folder.

## Subdense

As part of the SUBDENSE project, it is possible to visualise building changes in the 3D scene.

This feature is still experimental, and is currently only suited for French data from the east of the country.

### Fetching data

The data necessary for the run can be found [here](https://entrepot.recherche.data.gouv.fr/dataset.xhtml?persistentId=doi:10.57745/RFKKYX).

You can download it, and put it in the `Subdense_Data` folder in your working folder.
The result should be:

* <working_folder\>:
    * Subdense_Data
        * FR-STRA-FUA-France-BuildingChange-2011-2021.gpkg
        * FR-STR-FUA-Building-2011.gpkg
        * FR-STR-FUA-Evolution-2011-21.gpkg
        * FR-STR-FUA-Evolution-2021.gpkg
    * Logs
    * Projects
    * ...

### Configuration

There is an `example_subdense.json` file packaged with the software. 
It is a village in the suburbs of Strasbourg.

There are some key changes with previous files:
* The `input_data` type is set to `SUBDENSE`.
* The buildings use the `_proc` assets, to be able to change the building's colors depending on its change status.

You can use such modifications to tweak the configuration however you like (you still need to change the `base_folder` like other files).  

### Run

Run will work exactly as the [basic workflow](basic_workflow.md/#run). Just select the configuration you just generated for the run.

As a slight change, the goal of SUBDENSE runs is to be able to visualize building changes in a zone.

As such, buildings are placed inside sub collections depending on their change status, and have a color associated with them:

* `Stable`: no change. Light gray color.
* `Old`: were destroyed between the two dates. Red color.
* `New`:
    * `Appeared`: completly new building. Green color.
    * `Merged`: buildings that were separated are now one single building. Purple color.
    * `Recomposed`: combination of merging and splitting of buildings. Orange color.
