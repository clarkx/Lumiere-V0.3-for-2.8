import bpy

from mathutils import (
	Vector,
	Matrix,
	Quaternion,
	Euler,
	)

from .lumiere_materials import (
	softbox_mat,
	lamp_mat,
	)

# -------------------------------------------------------------------- #
# Softbox
def create_softbox(softbox_name = "Lumiere"):
	"""Create the panel light with modifiers"""

	lumiere_collection = bpy.context.scene.collection.children['Lumiere']
	# Set Lumiere as the active layer collection
	bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection.children['Lumiere']
	# Add a primitive plane in the active collection
	bpy.ops.mesh.primitive_plane_add(size=1.0, calc_uvs=False, align='VIEW', enter_editmode=False, \
									location=(0.0, 0.0, 0.0), rotation=(0.0, 0.0, 90.0))
	bpy.ops.object.editmode_toggle()
	bpy.ops.uv.smart_project(angle_limit=66, island_margin=0, user_area_weight=0)
	bpy.ops.uv.reset()
	bpy.ops.object.editmode_toggle()
	light = bpy.context.view_layer.objects.active
	light.name = softbox_name
	lumiere_collection = bpy.context.scene.collection.children['Lumiere']

	# Select the light and make it active
	bpy.ops.object.select_all(action='DESELECT')
	light.select_set(state=True)
	light_selected = True
	bpy.context.view_layer.objects.active = bpy.data.objects[light.name]

	# Add the material
	softbox_mat(light)
	mat = light.active_material

	# Change the visibility
	light.display_type = 'WIRE'
	light.show_transparent = True
	light.show_wire = True
	light.cycles_visibility.camera = False
	light.cycles_visibility.shadow = False

	# Add Bevel
	light.modifiers.new("Bevel", type='BEVEL')
	light.modifiers["Bevel"].use_only_vertices = True
	light.modifiers["Bevel"].use_clamp_overlap = True
	light.modifiers["Bevel"].loop_slide = True
	light.modifiers["Bevel"].width = .25
	light.modifiers["Bevel"].segments = 5
	light.modifiers["Bevel"].profile = .5
	light.modifiers["Bevel"].show_expanded = False

	return(light)

# -------------------------------------------------------------------- #
# Blender Light
"""Create a blender light"""
def create_lamp(type, name = "Lumiere"):
	# Create the lamp
	light_data = bpy.data.lights.new(name = name, type = type.upper())
	light = bpy.data.objects.new(name = name, object_data = light_data)

	# Add the light to the collection
	lumiere_collection = bpy.context.scene.collection.children['Lumiere']
	lumiere_collection.objects.link(light)

	# Initialize MIS / Type / Name
	light.data.cycles.use_multiple_importance_sampling = True

	# Select and active the light
	bpy.ops.object.select_all(action='DESELECT')
	light.select_set(state=True)
	light_selected = True
	bpy.context.view_layer.objects.active = light
	light.Lumiere.light_type = type

	# Create nodes
	lamp_mat(light)

	return(light)

# -------------------------------------------------------------------- #
# Utilities
def get_mat_name():
	"""Return the name of the material of the light"""
	light = bpy.context.object
	mat_name = light.name
	if bpy.context.object.type == 'MESH':
		mat = light.active_material
	else:
		mat = bpy.data.lights[light.data.name].name

	return(mat_name, mat)
