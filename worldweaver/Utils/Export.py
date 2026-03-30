import os
from pathlib import Path

import numpy as np

from py3dtiles.tileset import TileSet, Tile, BoundingVolumeBox

import bpy
from bpy import data as D, context as C, ops as O

from worldweaver.Utils.Logging import logger
import worldweaver.Utils.DataFiles as df
from worldweaver.Utils.Rendering import (
    additionals_collection_name,
    buildings_collection_name,
)


def srgb_to_linearrgb(c):
    if c < 0:
        return 0
    elif c < 0.04045:
        return c / 12.92
    else:
        return ((c + 0.055) / 1.055) ** 2.4


def hex_to_rgb(h, alpha=1):
    r = (h & 0xFF0000) >> 16
    g = (h & 0x00FF00) >> 8
    b = h & 0x0000FF
    return tuple([srgb_to_linearrgb(c / 0xFF) for c in (r, g, b)] + [alpha])


def apply_mods_building(building_obj):
    if len(building_obj.modifiers) > 0:
        try:
            C.view_layer.objects.active = building_obj  # Set the active object
            O.object.modifier_apply(modifier=building_obj.modifiers[0].name)
        except Exception as e:
            logger.warn(f"Error processing {building_obj.name}", exc_info=e)


def export_scene_to_tileset(project_path: str):

    logger.info("Beginning exporting the scene")

    # Terrain

    terrain_obj = D.objects["Terrain_0"]

    C.view_layer.objects.active = terrain_obj
    O.object.modifier_apply(modifier="TerrainMove")
    terrain_obj.modifiers.clear()
    terrain_obj.active_material_index = 0
    bpy.ops.object.material_slot_remove()
    mat = bpy.data.materials.new(name="Terrain_Export")
    mat.use_nodes = True
    mat_node = mat.node_tree.nodes["Principled BSDF"]
    # Color
    mat_node.inputs[0].default_value = hex_to_rgb(0x1E3300)
    # Roughness
    mat_node.inputs[2].default_value = 1
    # IOR
    mat_node.inputs[3].default_value = 1
    # IOR, but is not exported into the glb sadly
    # mat_node.inputs[3].default_value = 1

    terrain_obj.data.materials.append(mat)
    terrain_obj.active_material_index = 0

    # Buildings
    for building in D.collections[buildings_collection_name].objects:
        apply_mods_building(building)

    for building_sub_collection in D.collections[buildings_collection_name].children:
        for building in building_sub_collection.objects:
            apply_mods_building(building)

    # Bridges
    bridge_obj = D.objects["Bridges"]
    if len(bridge_obj.data.vertices) > 0:
        try:
            C.view_layer.objects.active = bridge_obj
            O.object.modifier_apply(modifier="GeometryNodes")
            bridge_obj.active_material_index = 0
            bpy.ops.object.material_slot_remove()
            mat_bridge = bpy.data.materials.new(name="Bridge_Export")

            bridge_obj.data.materials.append(mat_bridge)
            bridge_obj.active_material_index = 0
        except Exception as e:
            logger.warn(f"Error processing Bridges", exc_info=e)

    # Water
    waters = ["Still_Water", "Flowing_Water", "Ocean_Water"]
    for water_name in waters:
        water_obj = D.objects[water_name]
        if len(water_obj.data.vertices) > 0:
            C.view_layer.objects.active = water_obj
            O.object.modifier_apply(modifier=water_obj.modifiers[0].name)

    # Forests
    forest_obj = D.objects["Forest"]
    if len(forest_obj.data.vertices) > 0:
        try:
            C.view_layer.objects.active = forest_obj
            O.object.modifier_apply(modifier=forest_obj.modifiers[0].name)
        except Exception as e:
            logger.warn(f"Error processing Forests", exc_info=e)

    # Roads
    roads_obj = D.objects["Roads.001"]
    if len(roads_obj.data.vertices) > 0:
        C.view_layer.objects.active = roads_obj
        O.object.modifier_apply(modifier=roads_obj.modifiers[0].name)

        try:
            # This material only appears if there are guardrails
            mat_index = roads_obj.data.materials.keys().index("Metal grey")
            roads_obj.active_material_index = mat_index
            metal_mat = roads_obj.active_material
            nodes = metal_mat.node_tree.nodes
            bsdf = metal_mat.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
            links = metal_mat.node_tree.links
            link = links.new(bsdf.outputs[0], nodes["Material Output"].inputs[0])
            # Color
            bsdf.inputs[0].default_value = hex_to_rgb(0x808080)
            # Metallic
            bsdf.inputs[1].default_value = 1
            # Roughness
            bsdf.inputs[2].default_value = 1
        except:
            pass

        # Sidewalks
        mat_index = roads_obj.data.materials.keys().index("Next_sidewalks 1_Realistic")
        roads_obj.active_material_index = mat_index
        sidewalk_mat = roads_obj.active_material
        nodes = sidewalk_mat.node_tree.nodes
        bsdf = sidewalk_mat.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        links = sidewalk_mat.node_tree.links
        link = links.new(bsdf.outputs[0], nodes["Material Output"].inputs[0])
        # Color
        bsdf.inputs[0].default_value = hex_to_rgb(0x737373)
        # Roughness
        bsdf.inputs[2].default_value = 1

        # Brick line (to remove)
        mat_index = roads_obj.data.materials.keys().index("Next_brick line 1_Realistic")
        roads_obj.active_material_index = mat_index
        bpy.ops.object.material_slot_remove()

        # Asphalt
        mat_index = roads_obj.data.materials.keys().index("Next_Asphalt_Realistic")
        roads_obj.active_material_index = mat_index
        asphalt_mat = roads_obj.active_material
        nodes = asphalt_mat.node_tree.nodes
        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        links = asphalt_mat.node_tree.links
        link = links.new(bsdf.outputs[0], nodes["Material Output"].inputs[0])
        # Color
        bsdf.inputs[0].default_value = hex_to_rgb(0x252525)
        # Roughness
        bsdf.inputs[2].default_value = 1

        # Empty. need to remove
        roads_obj.active_material_index = len(roads_obj.data.materials) - 2
        empty_mat = roads_obj.active_material
        if empty_mat is None:
            bpy.ops.object.material_slot_remove()

        # White line
        mat_index = roads_obj.data.materials.keys().index(
            "Next_Asphalt line white _Realistic"
        )
        roads_obj.active_material_index = mat_index
        wl_mat = roads_obj.active_material
        nodes = wl_mat.node_tree.nodes
        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        links = wl_mat.node_tree.links
        link = links.new(bsdf.outputs[0], nodes["Material Output"].inputs[0])
        bsdf.inputs[0].default_value = hex_to_rgb(0xE7E7E7)

        mod_decimate = roads_obj.modifiers.new("", "DECIMATE")
        mod_decimate.ratio = 0.1
        O.object.modifier_apply(modifier=roads_obj.modifiers[0].name)

    adds = [x for x in D.collections[additionals_collection_name].objects]
    with bpy.context.temp_override(
        selected_objects=D.collections[additionals_collection_name].objects
    ):
        O.object.delete()

    export_folder = df.setup_export_folder(project_path)

    # bpy.ops.export_scene.gltf(filepath="/home/AVerstraete/Work/scraps/subdense/scene/building_0_auto.glb",use_selection=True)
    export_file = os.path.join(export_folder, df.export_glb_file)
    bpy.ops.export_scene.gltf(filepath=export_file)

    logger.info(f"Exported scene to {export_file}")

    logger.info("Creating tileset")

    tileset = TileSet()

    tileset_filepath = Path(os.path.join(export_folder, "tileset.json"))
    tileset.geometric_error = 0
    tileset.root_tile.geometric_error = 500

    bound_points = D.objects["Terrain_0"].bound_box

    x_min = min([x[0] for x in bound_points])
    x_max = max([x[0] for x in bound_points])

    y_min = min([x[1] for x in bound_points])
    y_max = max([x[1] for x in bound_points])

    z_min = min([x[2] for x in bound_points])
    z_max = max([x[2] for x in bound_points])

    center = [0, 0, (z_min + z_max) / 2]

    x_half_axis = [max(abs(x_min), abs(x_max)), 0, 0]

    y_half_axis = [0, max(abs(y_min), abs(y_max)), 0]

    z_half_axis = [0, 0, (z_max - z_min) / 2]

    bounding_box = BoundingVolumeBox.from_list(
        [*center, *x_half_axis, *y_half_axis, *z_half_axis]
    )

    tileset.root_tile.bounding_volume = bounding_box

    tileset.root_tile.set_refine_mode("REPLACE")

    tileset.root_tile.transform = np.resize(
        np.array([1, 0, 0, 0, 0, 0, -1, 0, 0, 1, 0, 0, 0, 0, 0, 1]), [4, 4]
    )

    child_tile = Tile()
    child_tile.bounding_volume = bounding_box
    child_tile.geometric_error = 0
    child_tile.set_refine_mode("REPLACE")
    child_tile.content_uri = Path("scene.glb")
    tileset.root_tile.add_child(child_tile)

    tileset.write_as_json(tileset_filepath)

    logger.info(f"Tileset written at {tileset_filepath}")
