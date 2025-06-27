import argparse
import os
import sys

# bpy has to be imported here because it enables to import things like mathutils later.
import bpy
from bpy import context as C


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", type=str, help="Config file path")
    # script_name = __file__
    # print("script name:", script_name)
    # arguments, unknown = parser.parse_known_args(sys.argv[sys.argv.index(script_name)+1:])
    # For blender
    # arguments, unknown = parser.parse_known_args(sys.argv[sys.argv.index("--") + 1 :])

    # For bpy
    arguments, unknown = parser.parse_known_args(sys.argv)

    if not os.path.isfile(arguments.config):
        parser.error("Config file does not exist")

    return arguments, unknown


arguments, unknown = parse_arguments()

print("--config : %s" % arguments.config)

print("\nAll arguments:")
print(sys.argv)

print("\nRecognized Arguments:")
print(arguments)

print("\nUnknown Arguments:")
print(unknown)

from worldweaver import main as mpm

# For blender
# filepath = C.preferences.addons["module_worldweaver"].preferences.filepath
# mpm.main(filepath)

# For bpy
mpm.main(arguments.config)

# For blender
# ./blender --background --python /home/AVerstraete/Work/worldweaver/headless_script.py -- --config /home/AVerstraete/Work/worldweaver/worldweaver/Config/base_config.json

# For bpy
# python headless_script.py --config /home/AVerstraete/Work/worldweaver/worldweaver/Config/base_config.json
