# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import bpy
from bpy.props import StringProperty, BoolProperty
from bpy_extras.io_utils import ImportHelper

bl_info = {
    "name": "Shallow Water",
    "author": "Sebastien Bigot",
    "version": (0, 0, 1),
    "blender": (2, 72, 0),
    "location": "File > Import-Export",
    "description": "Add a shallow water body",
    "warning": "",
    "wiki_url": "http://ssrb.github.io",
    "category": "Import-Export",
}

class ImportShallowWaterBody(bpy.types.Operator, ImportHelper):
    """Import a Shallow Water Body"""
    bl_idname = "import_scene.shallow_water_body"
    bl_label = 'Import Shallow Water Body'
    bl_options = {'UNDO'}

    filename_ext = ".mesh"
    filter_glob = StringProperty(default="*.mesh", options={'HIDDEN'})

    separate_boundary_objects = BoolProperty(
            name="Create polyline objects for each boundary",
            description="In addition to the boundary vertex groups, create separate polyline objects for each boundary",
            default=True
            )

    import_bottom = BoolProperty(
            name="Import the bottom geometry",
            description="If a depth file is found, create a bottom geometry object",
            default=False
            )
    
    def execute(self, context):
        from . import shallow_water
        keywords = self.as_keywords(ignore=("filter_glob",))
        return shallow_water.load(self, context, **keywords)

# Add to a menu
def menu_func_import(self, context):
    self.layout.operator(ImportShallowWaterBody.bl_idname, text="Shallow Water Body (.mesh)")

def register():
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_file_import.append(menu_func_import)

def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.INFO_MT_file_import.remove(menu_func_import)

