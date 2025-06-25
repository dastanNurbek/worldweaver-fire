# File System Usage

This page describes the file system used by the software.

## Structure

The software uses a few folders, all of which are contained in the `base_folder` indicated in the configuration files

  * ARRONDISSEMENT: Stores a shapefile of mainland France's regions (only used for offline uses, shapefile is packaged with the software)
  * Departements: Stores all the data used for offline runs. Should contain:
    * Folders whose names are the 2 digit of code of the department. Those folders can be generated with the help of [DataFiles](datafiles.md). Each should contain:
      * BDCARTO
      * BDORTHO
      * BDTOPO
      * RGEALTI
      * RPG
    * Textures: Folder in which terrain textures using ortho images are cached.
  * Logs: Stores the logs of the software. There are 2 log files, each containing the last run:
    * worldweaver.log: main log file
    * render.log: log file for Blender's render logs. Its main use is to avoid getting flooded with Blender's very verbous logs during headless runs.  
  * OCEAN: Stores a shapefile of the world's oceans (shapefile is packaged with the software)
  * Projects: Contains all outputs of runs. Each project folder contains:
    * The configuration file used to generate the run
    * Rendering: folder containing all the renders and semantic maps of the run
  * Rendering: Working folder. Mainly stores files used for flood calculation.

