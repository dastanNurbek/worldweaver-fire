import os

import pandas as p

from dataclasses import dataclass


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

        # The x_min and y_min indicated are those of the enveloppe of the raster,
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

        terrain_data = p.DataFrame(terrain_pts_list)

        print("Loaded slab : " + os.path.basename(file_path))

        return ASCData(
            x_min,
            y_min,
            x_max,
            y_max,
            resolution,
            nbcols,
            nbrows,
            no_data,
            terrain_data,
        )
