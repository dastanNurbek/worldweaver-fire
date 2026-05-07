import os
import math

from datetime import datetime

import bpy
from bpy import context as C, data as D, ops as O
import addon_utils

from timezonefinder import TimezoneFinder
import pytz

from worldweaver.Drivers.IGN.Utils import IGN

from worldweaver.Utils.Config import Config, CameraType, RenderDeviceType

from worldweaver.Utils.Logging import logger, stdout_redirected
import worldweaver.Utils.DataFiles as df

rendering_collection_name = "Rendering"
terrain_collection_name = "Terrain"
cars_collection_name = "Cars"
buildings_collection_name = "Buildings"
stable_buildings_collection_name = "Stable"
new_buildings_collection_name = "New"
appeared_buildings_collection_name = "Appeared"
recomposed_buildings_collection_name = "Recomposed"
merged_buildings_collection_name = "Merged"
old_buildings_collection_name = "Old"
base_collection_name = "Collection"
additionals_collection_name = "additionals"

sun_name = "Sun"

cameras = {
    CameraType.ORTHOGRAPHIC: "Camera_Ortho",
    CameraType.PERSPECTIVE: "Camera_Persp",
}


def check_is_sun_activated():
    """
    Checks if Sun Position addon is enabled, and if not, enables it.
    """
    try:
        sc = C.scene
        # Trying to access Sun Position addon to find out if it's activated or not
        a = sc.sun_pos_properties.latitude
    except Exception as _:
        logger.warn("Sun position addon was not enabled. Enabling it.")

        addon_utils.enable("sun_position", default_set=True)


# purge_orphans and clean_scene taken from https://github.com/CGArtPython/bpy_building_blocks_examples/blob/main/clean_scene/clean_scene_example_1.py
def purge_orphans():
    if bpy.app.version >= (3, 0, 0):
        bpy.ops.outliner.orphans_purge(
            do_local_ids=True, do_linked_ids=True, do_recursive=True
        )
    else:
        # call purge_orphans() recursively until there are no more orphan data blocks to purge
        result = bpy.ops.outliner.orphans_purge()
        if result.pop() != "CANCELLED":
            purge_orphans()


def clean_scene():
    """
    Removing all of the objects, collection, materials, particles,
    textures, images, curves, meshes, actions, nodes, and worlds from the scene
    """
    if bpy.context.active_object and bpy.context.active_object.mode == "EDIT":
        bpy.ops.object.editmode_toggle()

    for obj in bpy.data.objects:
        obj.hide_set(False)
        obj.hide_select = False
        obj.hide_viewport = False

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()

    collection_names = [col.name for col in bpy.data.collections]
    for name in collection_names:
        bpy.data.collections.remove(bpy.data.collections[name])

    # in the case when you modify the world shader
    world_names = [world.name for world in bpy.data.worlds]
    for name in world_names:
        bpy.data.worlds.remove(bpy.data.worlds[name])
    # create a new world data block
    bpy.ops.world.new()
    bpy.context.scene.world = bpy.data.worlds["World"]

    purge_orphans()


def configure_scene(
    geo_center_deg: tuple[float, float], device_type: str, is_subdense_run: bool
):
    """
    Configures the Blender scene prior to drawing objects
    :param geo_center_deg: The coordinates of the center of the scene, in CRS 4326, to configure the position of the sun
    :param device_type: The device type for rendering. "CPU" or "GPU"
    :param is_subdense_run: Whether or not we need to create sub-collections for buildings
    """

    # TODO: Generates blender logs that maybe we should wrap ?
    clean_scene()

    base_collection = D.collections.new(base_collection_name)
    sc = C.scene
    sc.collection.children.link(base_collection)

    for a in C.screen.areas:
        if a.type == "VIEW_3D":
            for s in a.spaces:
                if s.type == "VIEW_3D":
                    # Setting clip end distance because our scene is very large
                    s.clip_end = 100000

                    # Setting the shading type
                    s.shading.type = "RENDERED"

    # Nishita sky texture on the World
    world = D.worlds["World"]
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()
    sky_node = nodes.new(type="ShaderNodeTexSky")
    sky_node.name = "Sky Texture"
    sky_node.sky_type = "NISHITA"
    sky_node.sun_disc = False
    sky_node.altitude = 5000
    sky_node.air_density = 0.3
    sky_node.location = (-300, 300)
    bg_node = nodes.new(type="ShaderNodeBackground")
    bg_node.location = (0, 300)
    output_node = nodes.new(type="ShaderNodeOutputWorld")
    output_node.location = (300, 300)
    links.new(sky_node.outputs["Color"], bg_node.inputs["Color"])
    links.new(bg_node.outputs["Background"], output_node.inputs["Surface"])

    # Sun and lighting
    sun_data = D.lights.new(name=sun_name, type="SUN")
    sun_object = D.objects.new(sun_name, sun_data)
    D.collections[base_collection_name].objects.link(sun_object)
    sun_data.energy = 10

    tzf = TimezoneFinder()
    tz = tzf.timezone_at(lng=geo_center_deg[0], lat=geo_center_deg[1])
    local = pytz.timezone(tz)

    date = datetime.now()
    dt = local.utcoffset(date)
    utc_offset = dt.seconds // 3600
    if utc_offset > 12:
        utc_offset = 12 - utc_offset

    try:
        sc = C.scene
        sc.sun_pos_properties.sun_object = sun_object
        sc.sun_pos_properties.latitude = geo_center_deg[1]
        sc.sun_pos_properties.longitude = geo_center_deg[0]
        # TODO: put date in cfg. we use mid june to get good lighting in northern hemisphere
        # EDIT: Trying a time most similar to SENTINEL 2
        sc.sun_pos_properties.day = 5
        sc.sun_pos_properties.month = 8
        sc.sun_pos_properties.year = 2025
        sc.sun_pos_properties.UTC_zone = utc_offset
        sc.sun_pos_properties.time = 10.5
        sc.sun_pos_properties.sky_texture = "Sky Texture"
        sc.sun_pos_properties.use_sky_texture = True
    except Exception as _:
        raise Exception(
            "Sun position addon is not enabled. Go to Blender's Preference -> Add-ons, and enable 'Lighting: Sun Position'."
        )

    # Persp Camera
    persp_camera_data = D.cameras.new(name=cameras[CameraType.PERSPECTIVE])
    persp_camera_object = D.objects.new(
        cameras[CameraType.PERSPECTIVE], persp_camera_data
    )
    D.collections[base_collection_name].objects.link(persp_camera_object)
    persp_camera_object.location = (0, 0, 1100)
    persp_camera_object.rotation_euler = (0, 0, 0)
    persp_camera_object.data.clip_end = 100000
    persp_camera_object.data.lens_unit = "FOV"
    persp_camera_object.data.angle = 10 * math.pi / 180

    # Ortho Camera
    ortho_camera_data = D.cameras.new(name=cameras[CameraType.ORTHOGRAPHIC])
    ortho_camera_object = D.objects.new(
        cameras[CameraType.ORTHOGRAPHIC], ortho_camera_data
    )
    D.collections[base_collection_name].objects.link(ortho_camera_object)
    ortho_camera_data.type = "ORTHO"
    ortho_camera_data.clip_end = 100000
    ortho_camera_object.location = (0, 0, 1100)
    ortho_camera_object.rotation_euler = (0, 0, 0)
    ortho_camera_data.ortho_scale = 200

    # Rendering
    sc.render.engine = "CYCLES"
    sc.cycles.device = device_type
    sc.cycles.samples = 50
    sc.view_settings.view_transform = "Standard"

    if device_type == RenderDeviceType.GPU:
        # Set the device_type
        C.preferences.addons["cycles"].preferences.compute_device_type = "CUDA"

    # Refreshing the device list to be able to set them
    # https://projects.blender.org/blender/blender/issues/60618
    C.preferences.addons["cycles"].preferences.get_devices()

    # Enabling devices
    for d in C.preferences.addons["cycles"].preferences.devices:
        if (device_type == RenderDeviceType.CPU and d["type"] == 0) or (
            device_type == RenderDeviceType.GPU and d["type"] == 1
        ):
            d["use"] = 1
        else:
            d["use"] = 0
        logger.info(
            f"Device name: {d['name']}, type: {d['type']}, use status: {d['use']}"
        )

    # Preparing collections
    rendering_collection = D.collections.new(rendering_collection_name)
    D.collections[base_collection_name].children.link(rendering_collection)

    terrain_collection = D.collections.new(terrain_collection_name)
    D.collections[rendering_collection_name].children.link(terrain_collection)

    cars_collection = D.collections.new(cars_collection_name)
    D.collections[rendering_collection_name].children.link(cars_collection)

    buildings_collection = D.collections.new(buildings_collection_name)
    D.collections[rendering_collection_name].children.link(buildings_collection)

    if is_subdense_run:
        stable_collection = D.collections.new(stable_buildings_collection_name)
        D.collections[buildings_collection_name].children.link(stable_collection)

        old_collection = D.collections.new(old_buildings_collection_name)
        D.collections[buildings_collection_name].children.link(old_collection)

        new_collection = D.collections.new(new_buildings_collection_name)
        D.collections[buildings_collection_name].children.link(new_collection)

        appeared_buildings_collection = D.collections.new(
            appeared_buildings_collection_name
        )
        D.collections[new_buildings_collection_name].children.link(
            appeared_buildings_collection
        )

        recomposed_buildings_collection = D.collections.new(
            recomposed_buildings_collection_name
        )
        D.collections[new_buildings_collection_name].children.link(
            recomposed_buildings_collection
        )

        merged_buildings_collection = D.collections.new(
            merged_buildings_collection_name
        )
        D.collections[new_buildings_collection_name].children.link(
            merged_buildings_collection
        )

    additional_collection = D.collections.new(additionals_collection_name)
    D.collections[base_collection_name].children.link(additional_collection)


def match_collection(buildings_change_status):
    match buildings_change_status:
        case IGN.change_type_appeared:
            return appeared_buildings_collection_name
        case IGN.change_type_merged:
            return merged_buildings_collection_name
        case IGN.change_type_recomposed:
            return recomposed_buildings_collection_name
        case IGN.change_type_disappeared:
            return old_buildings_collection_name
        case IGN.change_type_stable:
            return stable_buildings_collection_name


def export_rendered_img(base_folder: str, render_folder: str, image_name: str):
    """
    Renders the scene and saves the rendered image to the designated location
    """
    sc = C.scene

    sc.render.filepath = os.path.join(render_folder, image_name + ".png")

    # Redirecting blender's render logs which are very voluminous (especially in headless mode) to another file
    with stdout_redirected(
        os.path.join(base_folder, df.log_folder, df.render_log_file)
    ):

        O.render.render(write_still=True)


def get_camera(camera_type: CameraType):
    """
    Returns the camera associated with the indicated type
    :param camera_type: The camera type
    :return: The Blender object of the camera
    """

    match camera_type:
        case CameraType.ORTHOGRAPHIC:
            return D.objects[cameras[CameraType.ORTHOGRAPHIC]]
        case CameraType.PERSPECTIVE:
            return D.objects[cameras[CameraType.ORTHOGRAPHIC]]
        case _:
            raise ValueError("Invalid camera type")


def setup_img_persp(resolution: float, pixel_size: float, center: tuple[float, float]):
    """
    Setups the scene and camera prior to rendering for perspective camera.
    :param resolution: The resolution of the image
    :param pixel_size: The pixel size of the image
    :param center: The center of the image
    """

    sc = C.scene
    sc.render.resolution_x = resolution
    sc.render.resolution_y = resolution

    camera = get_camera(CameraType.PERSPECTIVE)
    sc.camera = camera
    img_size = resolution * pixel_size
    camera_elevation = img_size / (2 * math.tan(camera.data.angle / 2))

    max_z = -math.inf

    # Calculating the maximum height of the scene, using terrain and buildings
    # TODO: Instead of this, should use a constant height flight path and REAL camera parameters
    terrain_collection = D.collections["Terrain"].objects
    for terrain in terrain_collection:
        terrain_box = terrain.bound_box
        z_coords = [v[2] for v in terrain_box]
        cur_z_max = max(z_coords)
        if cur_z_max > max_z:
            max_z = cur_z_max

    camera.location = (center[0], center[1], max_z + camera_elevation)


def setup_img_ortho(
    size_x: float, size_y: float, pixel_size: float, center: tuple[float, float]
) -> float:
    """
    Setups the scene and camera prior to rendering for ortho camera.
    :param size_x: The size of the image along the X axis
    :param size_y: The size of the image along the Y axis
    :param pixel_size: The pixel size of the image
    :param center: The center of the image
    :return: The Z coordinate of the camera
    """
    sc = C.scene
    sc.render.resolution_x = int(size_x // pixel_size)
    sc.render.resolution_y = int(size_y // pixel_size)

    size = max(size_x, size_y)

    camera = get_camera(CameraType.ORTHOGRAPHIC)
    sc.camera = camera
    camera.data.ortho_scale = size

    max_z = -math.inf

    # Calculating the maximum height of the scene, using terrain and buildings
    # TODO: check if there are edge cases where this does not hold
    terrain_collection = D.collections["Terrain"].objects
    for terrain in terrain_collection:
        terrain_box = terrain.bound_box
        z_coords = [v[2] for v in terrain_box]
        cur_z_max = max(z_coords)
        if cur_z_max > max_z:
            max_z = cur_z_max

    # Highest building in the world is ~800m and camera has to be above that
    camera_z = max_z + 1000

    camera.location = (center[0], center[1], camera_z)

    return camera_z


def setup_img_ortho_res(
    resolution: float, pixel_size: float, center: tuple[float, float]
) -> float:
    """
    Setups the scene and camera prior to rendering for ortho camera.
    :param resolution: The resolution of the image
    :param pixel_size: The pixel size of the image
    :param center: The center of the image
    :return: The Z coordinate of the camera
    """
    size = int(resolution * pixel_size)
    return setup_img_ortho(size, size, pixel_size, center)


def setup_compositing_height_map(base_folder: str):
    """
    Setups Blender's compositing for height map calculation
    :param base_folder: The folder in which the map will be exported
    """

    # Enabling compositing nodes
    D.scenes["Scene"].use_nodes = True

    # Enabling Z pass to be able to get the heightmap
    D.scenes["Scene"].view_layers["ViewLayer"].use_pass_z = True

    # Disabling object index pass (will need to be reactivated if we want to take objects other than terrain into account)
    D.scenes["Scene"].view_layers["ViewLayer"].use_pass_object_index = False

    # Adding the nodes to the node tree to get the setup we want
    scene = C.scene
    nodes = scene.node_tree.nodes
    nodes.clear()
    r_layers = nodes.new("CompositorNodeRLayers")

    # Depth map as an EXR file
    output_file = nodes.new("CompositorNodeOutputFile")
    output_file.format.file_format = "OPEN_EXR"
    output_file.base_path = os.path.join(base_folder, df.rendering, df.temp_folder)
    output_file.file_slots.remove(output_file.inputs[0])
    output_file.file_slots.new("depth_map")

    # Linking it
    links = scene.node_tree.links
    link = links.new(nodes["Render Layers"].outputs[2], output_file.inputs[0])


def setup_compositing_semantic_map(base_folder: str):
    """
    Setups Blender's compositing for semantic map generation
    :param base_folder: The folder in which the map will be exported
    """
    # Enabling compositing nodes
    D.scenes["Scene"].use_nodes = True

    # Disabling Z pass
    D.scenes["Scene"].view_layers["ViewLayer"].use_pass_z = False

    # Enabling object index pass to get the semantic map
    D.scenes["Scene"].view_layers["ViewLayer"].use_pass_object_index = True

    # Adding the nodes to the node tree to get the setup we want
    scene = C.scene
    nodes = scene.node_tree.nodes
    nodes.clear()
    r_layers = nodes.new("CompositorNodeRLayers")

    # Semantic map as a greyscale PNG
    output_file = nodes.new("CompositorNodeOutputFile")
    output_file.format.file_format = "PNG"
    output_file.format.color_mode = "BW"
    output_file.format.color_depth = "8"
    output_file.base_path = os.path.join(base_folder, df.rendering, df.temp_folder)
    output_file.file_slots.remove(output_file.inputs[0])
    output_file.file_slots.new("semantic_map")

    # Linking it
    norm = nodes.new("CompositorNodeNormalize")
    links = scene.node_tree.links
    link = links.new(nodes["Render Layers"].outputs[2], norm.inputs[0])
    link2 = links.new(norm.outputs[0], output_file.inputs[0])


def setup_compositing_render(folder: str, config: Config):
    """
    Setups Blender's compositing for rendering
    :param folder:
    :param config: The configuration of the run
    """

    # Enabling compositing nodes
    D.scenes["Scene"].use_nodes = use_nodes = True

    # Disabling Z pass
    D.scenes["Scene"].view_layers["ViewLayer"].use_pass_z = False

    # Enabling object index pass to get the semantic map
    D.scenes["Scene"].view_layers["ViewLayer"].use_pass_object_index = True

    # Adding the nodes to the node tree to get the setup we want
    scene = C.scene
    nodes = scene.node_tree.nodes
    nodes.clear()
    r_layers = nodes.new("CompositorNodeRLayers")

    # Semantic map as a greyscale PNG
    output_file = nodes.new("CompositorNodeOutputFile")
    output_file.format.file_format = "PNG"
    output_file.format.color_mode = "BW"
    output_file.format.color_depth = "8"
    output_file.base_path = folder

    # Normalizing the map to improve contrast
    objects_indexes = [
        config.rendering.building_render_config.tagging_index,
        config.rendering.house_render_config.tagging_index,
        config.rendering.church_render_config.tagging_index,
        config.rendering.factory_render_config.tagging_index,
        config.rendering.mall_render_config.tagging_index,
        config.rendering.flood_render_config.tagging_index,
        config.rendering.placeholder_forest_render_config.tagging_index,
        config.rendering.pretty_forest_render_config.tagging_index,
        config.rendering.road_render_config.road_tagging_index,
        config.rendering.road_render_config.car_tagging_index,
        config.rendering.bridge_render_config.tagging_index,
        config.rendering.water_render_config.tagging_index,
        config.rendering.terrain_render_config.tagging_index,
        config.rendering.terrain_render_config.decor_tagging_index,
    ]
    max_tagging_index = max(objects_indexes)

    math_node = nodes.new("CompositorNodeMath")
    math_node.inputs[1].default_value = max_tagging_index
    math_node.operation = "DIVIDE"

    # Linking it
    links = scene.node_tree.links
    link = links.new(nodes["Render Layers"].outputs[2], math_node.inputs[0])
    link2 = links.new(math_node.outputs[0], output_file.inputs[0])


def set_compositing_render_image_name(image_name):
    """
    Sets the name of the semantic map inside the compositing node tree
    :param image_name: The name of the semantic map
    """

    # The file name is tied to the input name of the node.
    # So we have to delete the previous input, add another one, and relink it to the correct node
    # If the setup_compositing_render() is modified, this will have to change too.
    output_file = D.scenes["Scene"].node_tree.nodes["File Output"]
    output_file.file_slots.remove(output_file.inputs[0])
    output_file.file_slots.new(image_name)
    math_node = D.scenes["Scene"].node_tree.nodes["Math"]
    links = D.scenes["Scene"].node_tree.links
    link2 = links.new(math_node.outputs[0], output_file.inputs[0])


def change_color(collection: str, color: tuple[float, float, float, float]):
    """
    Helper method to change the color of procedural buildings inside a collection.
    :param collection: The name of the collection you want to affect.
    :param color: The color of the buildings, as a tuple of 4 floats between 0 and 1 for R, G, B and A channels.
    """
    for obj in D.collections[collection].objects:
        if obj.name.startswith("House"):
            obj.modifiers[0]["Input_11"] = color
            obj.modifiers[0]["Input_13"] = color
        else:
            obj.modifiers[0]["Socket_0"] = color
        # Toggling visiblity of object for the changes to be applied in viewport
        obj.modifiers[0].show_viewport = False
        obj.modifiers[0].show_viewport = True
    # Toggling visiblity of collection for the changes to be applied in viewport
    D.collections[collection].hide_viewport = True
    D.collections[collection].hide_viewport = False
