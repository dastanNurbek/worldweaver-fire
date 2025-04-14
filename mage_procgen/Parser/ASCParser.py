import os

from dataclasses import dataclass

import pandas as p
import numpy as np

from mage_procgen.Utils.Logging import logger


@dataclass
class ASCData:
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    resolution: float
    nbcol: int
    nbrow: int
    no_data: float
    data: p.DataFrame


class ASCParser:
    @staticmethod
    def load(
        file_path: str,
    ) -> ASCData:
        file_data = p.read_csv(file_path)

        # Number of columns must be read in dataframe.columns, the rest is in the rows ...
        nbcols = int(file_data.columns[0].split(" ")[-1])
        nbrows = int(file_data.values[0][0].split(" ")[-1])

        # The x_min and y_min indicated are those of the envelope of the raster,
        # while we're concerned abt the center pixel which is (0.5,0.5) away.
        x_min = float(file_data.values[1][0].split(" ")[-1]) + 0.5
        y_min = float(file_data.values[2][0].split(" ")[-1]) + 0.5

        resolution = float(file_data.values[3][0].split(" ")[-1])
        no_data = float(file_data.values[4][0].split(" ")[-1])
        x_max = x_min + resolution * nbcols
        y_max = y_min + resolution * nbrows

        # Cleaning the data
        file_data = file_data.drop([0, 1, 2, 3, 4])

        terrain_pts_list = []

        for line in file_data.values:
            point_list = [float(x) for x in line[0].split(" ")[1:]]
            terrain_pts_list.append(point_list)

        terrain_im_array = np.array(terrain_pts_list)
        # Flipping terrain Y axis to ease up use.
        terrain_im_array = np.flip(terrain_im_array, axis=0)
        terrain_data = p.DataFrame(terrain_im_array)

        logger.info(f"Loaded slab: {os.path.basename(file_path)}")

        return ASCData(
            x_min=x_min,
            y_min=y_min,
            x_max=x_max,
            y_max=y_max,
            resolution=resolution,
            nbcol=nbcols,
            nbrow=nbrows,
            no_data=no_data,
            data=terrain_data,
        )
