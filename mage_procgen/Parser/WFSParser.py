import os

import xml.etree.ElementTree as ET

import pandas as p
import geopandas as g

from owslib.wfs import WebFeatureService

import warnings


class WFSParser:

    number_matched = "numberMatched"
    number_returned = "numberReturned"
    GML_extension = ".gml"

    @staticmethod
    def load(
        wfs: WebFeatureService,
        folder: str,
        key: str,
        bbox: tuple[float, float, float, float],
        to_crs: int,
        required_columns: list,
    ) -> g.GeoDataFrame:

        file_index = 0
        data_files = []
        feature_returned = 0
        data_response = wfs.getfeature(typename=key, bbox=bbox)
        data_str = data_response.read()

        file_name = os.path.join(folder, f"{key}_{file_index}{WFSParser.GML_extension}")
        with open(file_name, "wb") as file:
            file.write(data_str)
            data_files.append(file_name)
            file_index += 1

        response_root = ET.fromstring(data_str)
        feature_returned += int(response_root.attrib[WFSParser.number_returned])
        feature_matched = int(response_root.attrib[WFSParser.number_matched])

        while feature_returned < feature_matched:
            # Fetch the rest of the data
            data_response = wfs.getfeature(
                typename=key, bbox=bbox, startindex=feature_returned
            )
            data_str = data_response.read()

            file_name = os.path.join(
                folder, f"{key}_{file_index}{WFSParser.GML_extension}"
            )
            with open(file_name, "wb") as file:
                file.write(data_str)
                data_files.append(file_name)
                file_index += 1
            response_root = ET.fromstring(data_str)
            feature_returned += int(response_root.attrib[WFSParser.number_returned])

        dataframes = []
        for data_file_name in data_files:
            # Suppressing warning that should not be raised
            # https://github.com/pandas-dev/pandas/issues/2841
            with warnings.catch_warnings():
                warnings.simplefilter(action="ignore", category=FutureWarning)
                df = g.read_file(filename=data_file_name)
                if len(df) > 0:
                    df_loc = df.to_crs(to_crs)
                    dataframes.append(df_loc)

        if len(dataframes) > 0:
            dataframe = p.concat(dataframes)
            return dataframe
        else:
            return g.GeoDataFrame(
                columns=required_columns, geometry="geometry", crs=to_crs
            )
