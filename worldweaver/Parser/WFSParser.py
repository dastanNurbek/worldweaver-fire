import xml.etree.ElementTree as ET
import json

import pandas as p
import geopandas as g

from owslib.wfs import WebFeatureService


class WFSParser:

    number_matched = "numberMatched"
    number_returned = "numberReturned"
    GML_extension = ".gml"

    @staticmethod
    def load(
        wfs: WebFeatureService,
        key: str,
        bbox: tuple[float, float, float, float],
        to_crs: int,
        required_columns: list,
    ) -> g.GeoDataFrame:

        dataframes = []
        feature_returned = 0
        data_response = wfs.getfeature(typename=key, bbox=bbox, outputFormat='application/json')
        # also possible :
        # data_response = wfs.getfeature(typename=key, bbox=bbox, outputFormat='GML2')
        # but for some reason the resulting df does not have a crs
        data_str = data_response.read()

        df = g.read_file(data_str)
        if not df.empty:
            df_loc = df.to_crs(to_crs)
            dataframes.append(df_loc)

        response_root = json.loads(data_str)
        feature_returned += int(response_root[WFSParser.number_returned])
        feature_matched = int(response_root[WFSParser.number_matched])

        while feature_returned < feature_matched:
            # Fetch the rest of the data
            data_response = wfs.getfeature(
                typename=key, bbox=bbox, startindex=feature_returned, outputFormat='application/json'
            )
            data_str = data_response.read()

            df = g.read_file(data_str)
            if not df.empty:
                df_loc = df.to_crs(to_crs)
                dataframes.append(df_loc)

            response_root = json.loads(data_str)
            feature_returned += int(response_root[WFSParser.number_returned])

        if len(dataframes) > 0:
            dataframe = p.concat(dataframes)
            return dataframe
        else:
            return g.GeoDataFrame(
                columns=required_columns, geometry="geometry", crs=to_crs
            )
