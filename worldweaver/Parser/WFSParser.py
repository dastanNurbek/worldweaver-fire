import xml.etree.ElementTree as ET

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
        data_response = wfs.getfeature(typename=key, bbox=bbox)
        data_str = data_response.read()

        df = g.read_file(data_str)
        if not df.empty:
            df_loc = df.to_crs(to_crs)
            dataframes.append(df_loc)

        response_root = ET.fromstring(data_str)
        feature_returned += int(response_root.attrib[WFSParser.number_returned])
        feature_matched = int(response_root.attrib[WFSParser.number_matched])

        while feature_returned < feature_matched:
            # Fetch the rest of the data
            data_response = wfs.getfeature(
                typename=key, bbox=bbox, startindex=feature_returned
            )
            data_str = data_response.read()

            df = g.read_file(data_str)
            if not df.empty:
                df_loc = df.to_crs(to_crs)
                dataframes.append(df_loc)

            response_root = ET.fromstring(data_str)
            feature_returned += int(response_root.attrib[WFSParser.number_returned])

        if len(dataframes) > 0:
            dataframe = p.concat(dataframes)
            return dataframe
        else:
            return g.GeoDataFrame(
                columns=required_columns, geometry="geometry", crs=to_crs
            )
