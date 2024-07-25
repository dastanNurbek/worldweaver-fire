from bpy import data as D

from mage_procgen.Renderer.BaseRenderer import BaseRenderer


class StillWaterRenderer(BaseRenderer):
    _mesh_name = "Still_Water"


class FlowingWaterRenderer(BaseRenderer):
    _mesh_name = "Flowing_Water"

    def get_mesh_obj(self):
        return D.objects[self._mesh_name]
