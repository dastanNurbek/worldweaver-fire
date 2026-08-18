# WorldWeaver

![Blender](https://img.shields.io/badge/blender-%23F5792A.svg?style=for-the-badge&logo=blender&logoColor=white)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)

WorldWeaver is a [Blender](https://www.blender.org/) plugin and python package to create virtual worlds based on a mix of open geodata and procedural generation.

It currently works on data from the [French National Geographic Institute](https://www.ign.fr/), [openstreetmap](https://www.openstreetmap.org/), and [swissALTI3D](https://www.swisstopo.admin.ch/fr/modele-altimetrique-swissalti3d).

> **This is a modified fork of [WorldWeaver](https://github.com/geo-mage/worldweaver).** It adds a forest fire
> simulation that renders paired pre-fire / post-fire views of the same scene, with matching semantic
> segmentation masks, for generating synthetic wildfire datasets. See [Fork modifications](#fork-modifications).

## Fork modifications

### Fire simulation

* `Processor/FireProcessor.py` — fire spread computed as a Dijkstra shortest-path over a rasterized flammability
  map (forests, wheat fields, corn fields, grass). Paths and roads act as probabilistic barriers, per-cell noise
  keeps the fire boundary organic, and a configurable seed makes runs reproducible. Cells within `fire_threshold`
  of an ignition point are marked burnt.
* `Renderer/FireRenderer.py` — builds a hidden `BurntArea` mesh draped on the terrain. It drives three consumers:
  tree culling in the forest geometry nodes, the burnt ground texture in `TerrainRenderer`, and the object-index
  render pass used for semantic tagging.
* Pre/post-fire pairs — `save_pre_fire_render` renders the scene before ignition, optionally with its own lighting
  (`pre_fire_time_of_day`, `pre_fire_sun_strength`) so the two renders can differ in sun position.
* Rendering configs now expose `time_of_day` and `sun_strength`.

Fire is configured under the `fire` block of the config file:

```json
"fire": {
  "activate": true,
  "ignition_points": [],
  "fire_cell_size": 5,
  "fire_threshold": 100,
  "tagging_index": 8,
  "seed": 0,
  "save_pre_fire_render": true
}
```

Ignition points are given in the scene CRS, not in degrees. Leaving the list empty picks a random flammable cell,
with forest cells prioritized.

### Other changes

* IGN stream loading is more robust on flaky networks: retries on `LayerNotDefined`, proxy handling, request
  timeouts, and updated `wms-r` endpoint and `RGEALTI` layer names.
* Fixes to water surface triangle optimization, burnt-area and terrain texture variation, and forest density.

## Setup

WorldWeaver has been tested successfully with Blender 4.1. While it should support later versions, use at your own risk!

For practical details on how to setup the plugin, read the [documentation](https://mage.science/worldweaver/).

## License

WorldWeaver is licensed under the [CeCILL v2.1](https://cecill.info/licences/Licence_CeCILL_V2.1-en.html) license (compatible with GPL).

The modifications in this fork are distributed under the same CeCILL v2.1 license.

## Acknowledgements

/!\ TODO
WorldWeaver has been developed under the [ANR MAGE](https://mage.science) project funded by *Agence Nationale de la Recherche* (ANR-22-CE23-0010).

The fire simulation in this fork was developed by Dastan Nurbekuly as part of the master's thesis
*Procedural Generation of Synthetic Satellite Images for Wildfire Segmentation*, carried out in the Copernicus
Master in Digital Earth programme — co-funded by the European Union — jointly delivered by Paris Lodron
University of Salzburg and Université Bretagne Sud, in collaboration with the
[French National Geographic Institute (IGN)](https://www.ign.fr/).

WorldWeaver uses a few procedural assets and textures:

* [Buildify](https://paveloliva.gumroad.com/l/buildify)
* [PBG](https://superhivemarket.com/products/pbg-2)
* [This youtube tutorial for realistic water](https://www.youtube.com/watch?v=0SJ-__0gK_k)
* [Coan Tree Generator](https://coan.gumroad.com/l/treegen)
* [Next Street V3](https://superhivemarket.com/products/next-street)
* [FRG](https://superhivemarket.com/products/flex-road-generator)
* Free textures from [FreePBR](https://freepbr.com/), [ambientCG](https://ambientcg.com/), [Poliigon](https://www.poliigon.com/textures/free)

