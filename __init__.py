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

bl_info = {
	"name": "Lumiere",
	"author": "Clarkx",
	"description": "Interactive Lighting add-on for Blender.",
	"version": (0, 1),
	"blender": (2, 80, 0),
	"location": "3D View",
	"warning": "",
	"wiki_url": "",
	"support": 'COMMUNITY',
	"category": "Object"
	}



import imp

from . import lumiere_ui
imp.reload(lumiere_ui)
from . import lumiere_materials
imp.reload(lumiere_materials)
from . import lumiere_utils
imp.reload(lumiere_utils)
from . import lumiere_lights
imp.reload(lumiere_lights)
from . import lumiere_op
imp.reload(lumiere_op)
from . import lumiere_draw
imp.reload(lumiere_draw)
from . import lumiere_gizmo
imp.reload(lumiere_gizmo)

import bpy
import os
import shutil

presets_folder = bpy.utils.script_paths("presets")
addons_folder = bpy.utils.script_paths("addons")
Lumiere_presets = os.path.join(presets_folder[0], 'object', 'Lumiere_presets')
# if not os.path.isdir(Lumiere_presets):
# 	# makedirs() will also create all the parent folders (like "object")
# 	os.makedirs(Lumiere_presets)
# 	# Get a list of all the files in your bundled presets folder
# 	files = os.listdir(my_bundled_presets)
# 	# Copy them
# 	[shutil.copy2(os.path.join(my_bundled_presets, f), my_presets) for f in files]

# register
##################################


def register():
	lumiere_gizmo.register()
	lumiere_op.register()
	lumiere_ui.register()
	print("Registered Lumiere")

def unregister():
	lumiere_ui.unregister()
	lumiere_op.unregister()
	lumiere_gizmo.unregister()
	print("Unregistered Lumiere")
