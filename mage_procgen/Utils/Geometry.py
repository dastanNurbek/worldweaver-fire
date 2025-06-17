from mage_procgen.Utils.Logging import logger


def center_point(point: tuple[float, float, float], center: tuple[float, float, float]):
    """
    Calculates the coordinates of a point relative to the center of the scene.
    :param point: The point to center
    :param center: The center of the scene
    :return: The coordinates relative to the center of the scene
    """

    return (point[0] - center[0], point[1] - center[1], point[2] - center[2])


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
        logger.error(f"Point is outside of terrain: x={x} + y={y}")
        return 0

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
