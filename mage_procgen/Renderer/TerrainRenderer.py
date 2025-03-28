import os
import warnings

import bpy
import bmesh
from bpy import data as D, context as C, ops as O

from numpy import arange

from mage_procgen.Utils.Geometry import center_point
from mage_procgen.Utils.Logging import logger
from mage_procgen.Utils.Utils import GeoWindow


class TerrainRenderer:

    _mesh_name = "Terrain"

    _TerrainAdaptationGN = "TerrainMove"
    _TerrainTaggingGN = "TerrainTagging"
    _TerrainDecoratingGN = "TerrainDecorating"
    _BaseMaterialName = "Base_Terrain"
    _TaggedMaterialName = "Tagged_Terrain"
    _MaterialFile = "Terrain_2Tests.blend"
    _AssetsFolder = "Assets"

    def __init__(
        self,
        base_folder: str,
        render_resolution: float,
        file_resolution: float,
        use_sat_img: bool,
    ):

        self.base_folder = base_folder
        self.render_resolution = render_resolution
        self.file_resolution = file_resolution
        self.use_sat_img = use_sat_img
        if render_resolution / file_resolution != render_resolution // file_resolution:
            raise ValueError(
                "terrain render resolution has to be a multiple of file resolution"
            )

        _location = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__))
        )
        filepath = os.path.realpath(
            os.path.join(_location, "..", self._AssetsFolder, self._MaterialFile)
        )
        try:
            with bpy.data.libraries.load(filepath) as (data_from, data_to):
                data_to.materials = [self._BaseMaterialName, self._TaggedMaterialName]
                data_to.node_groups = [
                    self._TerrainAdaptationGN,
                    self._TerrainTaggingGN,
                    self._TerrainDecoratingGN,
                ]

            self._base_material = data_to.materials[0]
            self._tagged_material = data_to.materials[1]
            self.geometry_node_name = data_to.node_groups[0].name
            self.tagging_geometry_node_name = data_to.node_groups[1].name
            self.decorating_geometry_node_name = data_to.node_groups[2].name
        except Exception as _:
            raise Exception(
                f"Unable to load the terrain material from the file {filepath}"
            )

        # TODO: put pass index in config just like the others
        trashcan = (
            D.node_groups["Decorate_TrashCansOnPath"]
            .nodes["Object Info"]
            .inputs[0]
            .default_value
        )

        trashcan.pass_index = 1

        lamp = (
            D.node_groups["Decorate_LightsOnRoads"]
            .nodes["Object Info"]
            .inputs[0]
            .default_value
        )

        lamp.pass_index = 1

    def render(
        self,
        terrain_data,
        geo_window: GeoWindow,
        parent_collection_name,
    ):

        terrain_collection = D.collections[parent_collection_name]

        center = geo_window.center

        box = geo_window.bounds

        current_terrain = terrain_data[0]
        terrain_index = 0

        meshes = {
            x: TerrainMeshInfo(
                mesh=bmesh.new(),
                base_map_file=terrain_data[x].base_map_file,
                base_map_x_min=terrain_data[x].x_min,
                base_map_x_max=terrain_data[x].x_max,
                base_map_y_min=terrain_data[x].y_min,
                base_map_y_max=terrain_data[x].y_max,
            )
            for x in range(len(terrain_data))
        }
        meshes_points = {x: {} for x in range(len(terrain_data))}
        meshes_points_real_coords = {x: [] for x in range(len(terrain_data))}

        global_x_min = min([x.x_min for x in terrain_data])
        global_x_max = max([x.x_max for x in terrain_data])
        global_y_min = min([x.y_min for x in terrain_data])
        global_y_max = max([x.y_max for x in terrain_data])

        base_range_x = arange(global_x_min, global_x_max, self.render_resolution)
        range_x = []
        for x in base_range_x:
            if box[0] < x < box[2]:
                range_x.append(x)
        for terrain in terrain_data:
            if terrain.x_max not in range_x:
                if box[0] < terrain.x_max < box[2]:
                    range_x.append(terrain.x_max)
        range_x.append(box[0])
        range_x.append(box[2])
        range_x = list(set(range_x))
        range_x.sort()

        base_range_y = arange(global_y_min, global_y_max, self.render_resolution)
        range_y = []
        for y in base_range_y:
            if box[1] < y < box[3]:
                range_y.append(y)
        for terrain in terrain_data:
            if terrain.y_max not in range_y:
                if box[1] < terrain.y_max < box[3]:
                    range_y.append(terrain.y_max)
        range_y.append(box[1])
        range_y.append(box[3])
        range_y = list(set(range_y))
        range_y.sort()

        previous_terrain_line = None

        ind_y = 0

        for y in range_y:

            current_terrain_line = []

            ind_x = 0

            for x in range_x:

                # Box is not in terraindata but has to be displayed.
                # To that end, we make it so we search the first or last point actually in terraindata.
                # The points of the box will be placed at those point's Z coordinate
                point_query_x = x
                if ind_x == 0:
                    point_query_x = range_x[1]
                if ind_x == len(range_x) - 1:
                    point_query_x = range_x[-2]

                point_query_y = y
                if ind_y == 0:
                    point_query_y = range_y[1]
                if ind_y == len(range_y) - 1:
                    point_query_y = range_y[-2]

                # Checking if the current point is in the current dataset
                is_point_in_current_terrain = True
                is_point_in_current_terrain &= point_query_x >= current_terrain.x_min
                is_point_in_current_terrain &= point_query_x < current_terrain.x_max
                is_point_in_current_terrain &= point_query_y >= current_terrain.y_min
                is_point_in_current_terrain &= point_query_y < current_terrain.y_max

                if not is_point_in_current_terrain:

                    for terrain in terrain_data:
                        is_point_in_terrain = True
                        is_point_in_terrain &= point_query_x >= terrain.x_min
                        is_point_in_terrain &= point_query_x < terrain.x_max
                        is_point_in_terrain &= point_query_y >= terrain.y_min
                        is_point_in_terrain &= point_query_y < terrain.y_max

                        if is_point_in_terrain:
                            current_terrain = terrain
                            terrain_index = terrain_data.index(current_terrain)
                            break

                current_point_index_x = (
                    point_query_x - current_terrain.x_min
                ) / self.file_resolution
                current_point_index_y = (
                    point_query_y - current_terrain.y_min
                ) / self.file_resolution

                if (
                    current_point_index_x != int(current_point_index_x)
                    or current_point_index_x > current_terrain.nbcol
                    or current_point_index_y != int(current_point_index_y)
                    or current_point_index_y > current_terrain.nbrow
                    or current_point_index_x < 0
                    or current_point_index_y < 0
                ):
                    current_point_z = 0
                else:
                    current_point_z = current_terrain.data.values[
                        int(current_point_index_y)
                    ][int(current_point_index_x)]

                    if current_point_z <= current_terrain.no_data:
                        # "No Data" usually means out at sea
                        current_point_z = 0

                current_point_coords = [
                    x,
                    y,
                    current_point_z,
                ]

                current_terrain_line.append(current_point_coords)

                if previous_terrain_line is not None and ind_x > 0:

                    new_face_verts = [
                        current_terrain_line[ind_x],
                        current_terrain_line[ind_x - 1],
                        previous_terrain_line[ind_x - 1],
                        previous_terrain_line[ind_x],
                    ]

                    # Face has to be added to the terrain containing the lower left corner of the face
                    ll_point = previous_terrain_line[ind_x - 1]
                    ll_point_terrain_index = terrain_index
                    is_ll_point_in_current_terrain = True
                    is_ll_point_in_current_terrain &= (
                        ll_point[0] >= current_terrain.x_min
                    )
                    is_ll_point_in_current_terrain &= (
                        ll_point[0] < current_terrain.x_max
                    )
                    is_ll_point_in_current_terrain &= (
                        ll_point[1] >= current_terrain.y_min
                    )
                    is_ll_point_in_current_terrain &= (
                        ll_point[1] < current_terrain.y_max
                    )

                    if not is_ll_point_in_current_terrain:

                        for terrain in terrain_data:
                            is_ll_point_in_terrain = True
                            is_ll_point_in_terrain &= ll_point[0] >= terrain.x_min
                            is_ll_point_in_terrain &= ll_point[0] < terrain.x_max
                            is_ll_point_in_terrain &= ll_point[1] >= terrain.y_min
                            is_ll_point_in_terrain &= ll_point[1] < terrain.y_max

                            if is_ll_point_in_terrain:
                                ll_point_terrain_index = terrain_data.index(terrain)
                                break

                    new_face_mesh_verts = []
                    for pt in new_face_verts:
                        centered_pt = center_point(pt, center)
                        if centered_pt not in meshes_points[ll_point_terrain_index]:
                            meshes_points[ll_point_terrain_index][centered_pt] = meshes[
                                ll_point_terrain_index
                            ].mesh.verts.new(centered_pt)

                            meshes_points_real_coords[ll_point_terrain_index].append(pt)

                        new_face_mesh_verts.append(
                            meshes_points[ll_point_terrain_index][centered_pt]
                        )

                    face = meshes[ll_point_terrain_index].mesh.faces.new(
                        new_face_mesh_verts
                    )

                ind_x += 1

            previous_terrain_line = current_terrain_line

            ind_y += 1

        for index, mesh_info in meshes.items():

            mesh_name = self._mesh_name + "_" + str(index)
            mesh_data = D.meshes.new(mesh_name)

            mesh_info.mesh.to_mesh(mesh_data)
            mesh_info.mesh.free()
            mesh_obj = D.objects.new(mesh_data.name, mesh_data)
            terrain_collection.objects.link(mesh_obj)

            if self.use_sat_img:

                mesh_material = D.materials[self._BaseMaterialName].copy()
                if os.path.isfile(mesh_info.base_map_file):
                    try:
                        # TODO: this line triggers prints such as
                        # TIFFReadDirectory: Warning, Unknown field with tag 33550 (0x830e) encountered.
                        # TIFFReadDirectory: Warning, Unknown field with tag 33922 (0x8482) encountered.
                        # TIFFReadDirectory: Warning, Unknown field with tag 34735 (0x87af) encountered.
                        # TIFFReadDirectory: Warning, Unknown field with tag 34737 (0x87b1) encountered.
                        # Issue is described in https://stackoverflow.com/a/27609465 but unsure how to solve.
                        # It's not a python warning so cannot filter it. We could redirect stdout (or stderr, unsure which is used)
                        # During this load, or just filter those messages.
                        D.images.load(mesh_info.base_map_file)

                        mesh_material.node_tree.nodes["Basemap Image"].image = D.images[
                            os.path.basename(mesh_info.base_map_file)
                        ]
                    except Exception as e:
                        logger.exception(
                            "Couldn't add texture image to slab.", exc_info=e
                        )

                mesh_data.materials.append(mesh_material)
            else:
                mesh_material = D.materials[self._TaggedMaterialName]
                mesh_data.materials.append(mesh_material)

            base_map_size_x = mesh_info.base_map_x_max - mesh_info.base_map_x_min
            base_map_size_y = mesh_info.base_map_y_max - mesh_info.base_map_y_min
            uvlayer = mesh_obj.data.uv_layers.new(name="UVMap_Terrain")

            for face in mesh_obj.data.polygons:
                for v_ind in range(len(face.vertices)):
                    vertex_ind = face.vertices[v_ind]
                    vertex_real_coords = meshes_points_real_coords[index][vertex_ind]

                    vertex_coords_in_basemap = (
                        vertex_real_coords[0] - mesh_info.base_map_x_min,
                        vertex_real_coords[1] - mesh_info.base_map_y_min,
                    )

                    vertex_uv = (
                        vertex_coords_in_basemap[0] / base_map_size_x,
                        vertex_coords_in_basemap[1] / base_map_size_y,
                    )

                    # TODO: monitor this
                    if (
                        vertex_uv[0] > 1
                        or vertex_uv[0] < 0
                        or vertex_uv[1] > 1
                        or vertex_uv[1] < 0
                    ):
                        raise ValueError(
                            f"Invalid uv coords. Vertex coords: "
                            f"{vertex_real_coords}"
                            f". Vertex UV: "
                            f"{vertex_uv}"
                        )

                    vertex_loop_ind = face.loop_indices[v_ind]
                    uvlayer.data[vertex_loop_ind].uv = vertex_uv

        if len(D.collections[parent_collection_name].objects) > 1:
            # Merging all slabs of terrain into one object to enable shrinkwrap of road later
            bpy.ops.object.select_all(action="DESELECT")
            C.view_layer.objects.active = D.collections[parent_collection_name].objects[
                0
            ]
            for terrain_obj in D.collections[parent_collection_name].objects:
                terrain_obj.select_set(True)

            O.object.join()

        self.terrain_object = D.collections[parent_collection_name].objects[0]

        m = self.terrain_object.modifiers.new("", "NODES")
        m.name = self.geometry_node_name
        m.node_group = D.node_groups[self.geometry_node_name]
        if not self.use_sat_img:
            m2 = self.terrain_object.modifiers.new("", "NODES")
            m2.name = self.tagging_geometry_node_name
            m2.node_group = D.node_groups[self.tagging_geometry_node_name]

            m3 = self.terrain_object.modifiers.new("", "NODES")
            m3.name = self.decorating_geometry_node_name
            m3.node_group = D.node_groups[self.decorating_geometry_node_name]

    def config_geometry_node(
        self,
        road_object,
        water_object,
        still_water_object,
        ocean_object,
        building_object,
    ):
        node = self.terrain_object.modifiers[self.geometry_node_name]
        node["Socket_2"] = road_object
        node["Socket_4"] = water_object
        node["Socket_6"] = building_object
        node["Socket_8"] = still_water_object
        node["Socket_10"] = ocean_object

    def config_tagging_node(
        self,
        wheatfields_object,
        cornields_object,
        grass_object,
        developed_object,
        tartan_object,
        compacted_object,
        asphalt_object,
        sand_object,
        roads_object,
        path_object,
    ):
        if not self.use_sat_img:
            node_tree = D.node_groups[self._TerrainTaggingGN]
            node_tree.nodes["Compute Proximity Wheat Fields"].inputs[
                2
            ].default_value = wheatfields_object
            node_tree.nodes["Compute Proximity Corn Fields"].inputs[
                2
            ].default_value = cornields_object
            node_tree.nodes["Compute Proximity Grass"].inputs[
                2
            ].default_value = grass_object
            node_tree.nodes["Compute Proximity Developed"].inputs[
                2
            ].default_value = developed_object
            node_tree.nodes["Compute Proximity Tartan"].inputs[
                2
            ].default_value = tartan_object
            node_tree.nodes["Compute Proximity Compacted"].inputs[
                2
            ].default_value = compacted_object
            node_tree.nodes["Compute Proximity Asphalt"].inputs[
                2
            ].default_value = asphalt_object
            node_tree.nodes["Compute Proximity Sand"].inputs[
                2
            ].default_value = sand_object
            node_tree.nodes["Compute Proximity and Normal Roads"].inputs[
                4
            ].default_value = roads_object
            node_tree.nodes["Compute Edge Proximity Path"].inputs[
                4
            ].default_value = path_object
            node_tree.nodes["Compute Edge Proximity Field"].inputs[
                4
            ].default_value = wheatfields_object

    def get_mesh_obj(self):
        return self.terrain_object


class TerrainMeshInfo:
    def __init__(
        self,
        mesh,
        base_map_file,
        base_map_x_min,
        base_map_x_max,
        base_map_y_min,
        base_map_y_max,
    ):

        self.mesh = mesh
        self.base_map_file = base_map_file
        self.base_map_x_min = base_map_x_min
        self.base_map_x_max = base_map_x_max
        self.base_map_y_min = base_map_y_min
        self.base_map_y_max = base_map_y_max
