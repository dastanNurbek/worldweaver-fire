# WorldWeaver Documention 

WorldWeaver is a Blender add-on and python package that takes geographical data and uses them to create a 3D scene, 
generates a flood and then produces annotated images from that scene.

It currently works on data from the [French National Geographic Institute](https://www.ign.fr/), [openstreetmap](https://www.openstreetmap.org/), and [swissALTI3D](https://www.swisstopo.admin.ch/fr/modele-altimetrique-swissalti3d), and has a lot of parameters to customize the window, assets, and flood.

| Data source                 | Geographic coverage | Terrain source resolution | Terrain basemap        | Offline mode |
|-----------------------------|---------------------|---------------------------|------------------------|--------------|
| IGN Files                   | Mainland France     | 1m                        | Landuse or ortho image | Yes          |
| IGN Stream                  | Mainland France     | 1m                        | Landuse or ortho image | No           |
| OpenStreetMap + SRTM        | Worldwide           | 25m                       | Landuse                | No           |
| OpenStreetMap + SwissAlti3D | Switzerland         | .5m                       | Landuse                | No           |


Base documentation:

* [Setup](install.md)
* [First run](basic_workflow.md)

Advanced documentation:

* [Working offline](file_workflow.md)
* [Advanced features](advanced_workflow.md)
* [Assets use](assets.md)
* [Dev documentation](dev.md)
