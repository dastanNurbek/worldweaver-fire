import math

from shapely.geometry import Polygon, LineString, Point

from mage_procgen.Utils.Logging import logger
from mage_procgen.Utils.Utils import GeoWindow

default_thickness = 4
default_lane_nbr = 2
default_direction_code = 0
max_point_distance = 1000
directions = ["Double sens", "Sens direct", "Sens inverse"]

# TODO: check if it has any use.
def polygonise(
    poly_line: LineString,
    thickness: float,
    lane_nbr: int,
    direction: str,
    restrict_to_town: bool,
    window: GeoWindow,
) -> Polygon:

    translation_module = (
        (thickness / 2) if not math.isnan(thickness) else (default_thickness / 2)
    )

    polys = []

    direction_code = (
        directions.index(direction)
        if direction in directions
        else default_direction_code
    )

    lane_count = int(lane_nbr) if not math.isnan(lane_nbr) else default_lane_nbr

    lanes = {}
    lanes_previous_segment = {}
    translation_fractions = [
        x / lane_count for x in range(1 - lane_count, lane_count + 1, 2)
    ]

    is_first_point = True
    is_first_segment = True
    previous_point = None

    for point in poly_line.coords:

        if not is_first_point:

            current_segment = (previous_point, point)

            current_normale = normal(current_segment)

            # Adding the 4 new points
            if is_first_segment:
                p1 = (
                    current_segment[0][0] + current_normale[0] * translation_module,
                    current_segment[0][1] + current_normale[1] * translation_module,
                )
                p2 = (
                    current_segment[1][0] + current_normale[0] * translation_module,
                    current_segment[1][1] + current_normale[1] * translation_module,
                )
                p3 = (
                    current_segment[1][0] - current_normale[0] * translation_module,
                    current_segment[1][1] - current_normale[1] * translation_module,
                )
                p4 = (
                    current_segment[0][0] - current_normale[0] * translation_module,
                    current_segment[0][1] - current_normale[1] * translation_module,
                )

                polys.append([p1, p2, p3, p4, p1])

                # Lanes
                for fraction in translation_fractions:
                    lane_p1 = (
                        current_segment[0][0]
                        + current_normale[0] * fraction * translation_module,
                        current_segment[0][1]
                        + current_normale[1] * fraction * translation_module,
                    )
                    lane_p2 = (
                        current_segment[1][0]
                        + current_normale[0] * fraction * translation_module,
                        current_segment[1][1]
                        + current_normale[1] * fraction * translation_module,
                    )

                    # Lanes being shapely lines, they cannot be windowed like other objects so we have to do it here
                    skip_point = False
                    if restrict_to_town:
                        new_point = Point(lane_p1[0], lane_p1[1])
                        town_poly = window.dataframe.geometry[0]
                        skip_point = not new_point.within(town_poly)

                    if not skip_point:
                        lanes[fraction] = [lane_p1, lane_p2]
                    else:
                        lanes[fraction] = []
                    lanes_previous_segment[fraction] = (lane_p1, lane_p2)

                is_first_segment = False
            else:

                previous_quadri = polys[-1]

                # 4 points of the new quadri
                p1 = (
                    current_segment[0][0] + current_normale[0] * translation_module,
                    current_segment[0][1] + current_normale[1] * translation_module,
                )
                p2 = (
                    current_segment[1][0] + current_normale[0] * translation_module,
                    current_segment[1][1] + current_normale[1] * translation_module,
                )
                p3 = (
                    current_segment[1][0] - current_normale[0] * translation_module,
                    current_segment[1][1] - current_normale[1] * translation_module,
                )
                p4 = (
                    current_segment[0][0] - current_normale[0] * translation_module,
                    current_segment[0][1] - current_normale[1] * translation_module,
                )

                # Finding the correct intersection of the current quadri and the previous one
                inters1 = line_intersection(
                    (previous_quadri[0], previous_quadri[1]), (p1, p2)
                )
                inters2 = line_intersection(
                    (previous_quadri[2], previous_quadri[3]), (p3, p4)
                )

                # In some edge cases, almost straight segments create very far points.
                # In those cases, using the points of the new poly is a very fair approximation.
                inters1_distance = math.sqrt(
                    (inters1[0] - p1[0]) * (inters1[0] - p1[0])
                    + (inters1[1] - p1[1]) * (inters1[1] - p1[1])
                )
                if inters1_distance > max_point_distance:
                    inters1 = p1

                inters2_distance = math.sqrt(
                    (inters2[0] - p4[0]) * (inters2[0] - p4[0])
                    + (inters2[1] - p4[1]) * (inters2[1] - p4[1])
                )
                if inters2_distance > max_point_distance:
                    inters2 = p4

                # Modifying the previous polygon
                polys[-1][1] = inters1
                polys[-1][2] = inters2

                polys.append([inters1, p2, p3, inters2, inters1])

                # Lanes
                for fraction in translation_fractions:
                    lane_p1 = (
                        current_segment[0][0]
                        + current_normale[0] * fraction * translation_module,
                        current_segment[0][1]
                        + current_normale[1] * fraction * translation_module,
                    )
                    lane_p2 = (
                        current_segment[1][0]
                        + current_normale[0] * fraction * translation_module,
                        current_segment[1][1]
                        + current_normale[1] * fraction * translation_module,
                    )

                    # Finding the correct intersection of the current segment and the previous one
                    inters = line_intersection(
                        (
                            lanes_previous_segment[fraction][0],
                            lanes_previous_segment[fraction][1],
                        ),
                        (lane_p1, lane_p2),
                    )

                    # In some edge cases, almost straight segments create very far points.
                    # In those cases, using the points of the new poly is a very fair approximation.
                    inters_distance = math.sqrt(
                        (inters[0] - lane_p1[0]) * (inters[0] - lane_p1[0])
                        + (inters[1] - lane_p1[1]) * (inters[1] - lane_p1[1])
                    )
                    if inters_distance > max_point_distance:
                        inters = lane_p1

                    # Lanes being shapely lines, they cannot be windowed like other objects so we have to do it here
                    skip_point = False
                    if restrict_to_town:
                        new_point = Point(lane_p2[0], lane_p2[1])
                        town_poly = window.dataframe.geometry[0]
                        skip_point = not new_point.within(town_poly)

                    if not skip_point:
                        if len(lanes[fraction]) > 0:
                            lanes[fraction] = lanes[fraction][:-1] + [inters, lane_p2]
                        else:
                            lanes[fraction] = [inters, lane_p2]
                    lanes_previous_segment[fraction] = (lane_p1, lane_p2)
        else:
            is_first_point = False

        previous_point = point

    road_polygons = [Polygon(poly_points) for poly_points in polys]

    if direction_code == 2:
        # Flip all
        for fraction in lanes.keys():
            lanes[fraction].reverse()
    if direction_code == 0:
        # Flip < 0
        for fraction in lanes.keys():
            if fraction < 0:
                lanes[fraction].reverse()

    lanes_lines = [LineString(lane) for lane in lanes.values()]

    return (road_polygons, lanes_lines)


def normal(
    line: tuple[tuple[float, float], tuple[float, float]]
) -> tuple[float, float]:
    """
    Calculates the normalized normal to the line
    :param line:  the line you want to normal of
    :return: the normalized normal of the vector
    """

    dx = line[1][0] - line[0][0]
    dy = line[1][1] - line[0][1]

    normal_vector = (-dy, dx)

    normal_norm = norm2d(normal_vector)

    return (normal_vector[0] / normal_norm, normal_vector[1] / normal_norm)


def norm2d(vector):
    return math.sqrt(vector[0] * vector[0] + vector[1] * vector[1])


def line_intersection(
    line1: tuple[tuple[float, float], tuple[float, float]],
    line2: tuple[tuple[float, float], tuple[float, float]],
) -> tuple[float, float]:
    xdiff = (line1[0][0] - line1[1][0], line2[0][0] - line2[1][0])
    ydiff = (line1[0][1] - line1[1][1], line2[0][1] - line2[1][1])

    def det(a, b):
        return a[0] * b[1] - a[1] * b[0]

    div = det(xdiff, ydiff)
    if div == 0:
        # Most times it's when lines are aligned and share a point.
        # In that case, returning the common point is completly valid.
        if line1[0] == line2[0] or line1[0] == line2[1]:
            return line1[0]
        elif line1[1] == line2[0] or line1[1] == line2[1]:
            return line1[1]
        else:
            # TODO: Better treatment of this: idealy should detect that the two lines are the same, and return something
            logger.error(
                "line_intersection: lines do not intersect: "
                + str(line1)
                + " ; "
                + str(line2)
            )
            return 0, 0

    d = (det(*line1), det(*line2))
    x = det(d, xdiff) / div
    y = det(d, ydiff) / div
    return x, y


def center_point(point: tuple[float, float, float], center: tuple[float, float, float]):

    return (point[0] - center[0], point[1] - center[1], point[2] - center[2])


def point_2d_almost_equal(a, b, tolerance):
    return math.isclose(a.x, b.x, abs_tol=tolerance) and math.isclose(
        a.y, b.y, abs_tol=tolerance
    )


def point_2d_in_collection(a, col, tolerance):
    for point in col:
        if point_2d_almost_equal(a, point, tolerance):
            return True
    return False


def point_2d_value_in_dict(a, col, tolerance):
    for point in col.keys():
        if point_2d_almost_equal(a, point, tolerance):
            return col[point]
    raise KeyError("Point2D not in collection: " + str(a))


def interpolate_z(terrain_data, x, y):
    """
    Finds the z coordinate corresponding to the (x,y) point in the input using bilinear interpolation
    :param terrain_data: list of TerrainData containing the terrain altitudes
    :param x: the x coordinate of the point
    :param y: the y coordinate of the point
    :return: the corresponding z coordinate of the point
    """

    current_terrain = None

    for terrain in terrain_data:
        is_point_in_terrain = True
        is_point_in_terrain &= x >= terrain.x_min
        is_point_in_terrain &= x < terrain.x_max
        is_point_in_terrain &= y >= terrain.y_min
        is_point_in_terrain &= y < terrain.y_max

        if is_point_in_terrain:
            current_terrain = terrain
            break

    if current_terrain is None:
        # Should never happen
        return 0
        # raise ValueError(
        #    "Point is outside of terrain: x=" + str(x) + ", y=" + str(y)
        # )

    point_offset_x = x - current_terrain.x_min
    point_offset_y = y - current_terrain.y_min

    # Index of the point in the grid to the lower left of the current point
    ll_index_x = int(point_offset_x / current_terrain.resolution)
    ll_index_y = int(point_offset_y / current_terrain.resolution)

    in_cell_offset_x = point_offset_x % current_terrain.resolution
    in_cell_offset_y = point_offset_y % current_terrain.resolution

    if ll_index_x == (current_terrain.nbcol - 1):
        # If x index is at max, we cannt use the point to its right for interpolation
        if ll_index_y == (current_terrain.nbrow - 1):
            # If y index is at max, we cannt use the point above for interpolation
            z_ll = current_terrain.data.values[ll_index_y][ll_index_x]

            to_return = z_ll

            if to_return <= current_terrain.no_data:
                return 0
            else:
                return to_return
        else:
            z_ll = current_terrain.data.values[ll_index_y][ll_index_x]
            z_ul = current_terrain.data.values[ll_index_y + 1][ll_index_x]

            to_return = in_cell_offset_y * z_ul + (1 - in_cell_offset_y) * z_ll

            if to_return <= current_terrain.no_data:
                return 0
            else:
                return to_return

    elif ll_index_y == (current_terrain.nbrow - 1):
        # If y index is at max, we cannt use the point above for interpolation
        z_ll = current_terrain.data.values[ll_index_y][ll_index_x]
        z_lr = current_terrain.data.values[ll_index_y][ll_index_x + 1]

        to_return = in_cell_offset_x * z_lr + (1 - in_cell_offset_x) * z_ll

        if to_return <= current_terrain.no_data:
            return 0
        else:
            return to_return
    else:
        z_ll = current_terrain.data.values[ll_index_y][ll_index_x]
        z_ul = current_terrain.data.values[ll_index_y + 1][ll_index_x]
        z_ur = current_terrain.data.values[ll_index_y + 1][ll_index_x + 1]
        z_lr = current_terrain.data.values[ll_index_y][ll_index_x + 1]

        z_l = in_cell_offset_x * z_lr + (1 - in_cell_offset_x) * z_ll
        z_u = in_cell_offset_x * z_ur + (1 - in_cell_offset_x) * z_ul

        to_return = in_cell_offset_y * z_u + (1 - in_cell_offset_y) * z_l

        if to_return <= current_terrain.no_data:
            return 0
        else:
            return to_return
