import bpy
from bpy.types import Panel, Operator, Menu
from bl_operators.presets import AddPresetBase

from .lumiere_materials import (
	update_mat,
	softbox_mat,
	lamp_mat,
	update_lamp,
	)

from .lumiere_lights import (
	create_softbox,
	create_lamp,
	)

from math import (
	degrees,
	radians,
	sin,
	cos,
	sqrt,
	atan2,
	acos,
	pi,
	)

from mathutils import (
	Vector,
	Matrix,
	Quaternion,
	Euler,
	)

from bpy.props import (
	IntProperty,
	FloatProperty,
	EnumProperty,
	PointerProperty,
	FloatVectorProperty,
	StringProperty,
	BoolProperty,
	)

# -------------------------------------------------------------------- #
"""Change the selected light to a new one"""
def update_type_light(self, context):

	light = context.object
	values = {}
	lumiere_dict = {}
	lumiere_dict[light.name] = light['Lumiere'].to_dict()
	lumiere_dict[light.name]['location'] = light.location.copy()
	lumiere_dict[light.name]['rotation'] = light.rotation_euler.copy()

	# Save values for the new light
	values['old_name'] = light.name
	values['old_type'] = light.Lumiere.light_type.upper()

#-- The light is a lamp to be replaced by a mesh
	if light.type == "LIGHT":
		if light.Lumiere.light_type == "Softbox":
			lamp = bpy.data.lights[light.data.name]
			bpy.data.lights.remove(lamp, do_unlink=True, do_id_user=True, do_ui_user=True)
			if values['old_name'] in bpy.data.objects:
				for ob in  bpy.data.objects:
					if ob.data.name == values['old_name']:
						light = ob
			else:
				light = create_softbox(values['old_name'])
				light.data.name = values['old_name']
				light['Lumiere'] = lumiere_dict[values['old_name']]
				light.location = lumiere_dict[values['old_name']]["location"]
				light.rotation_euler = lumiere_dict[values['old_name']]["rotation"]
				update_mat(self, context)
		else:
			if values['old_type'] != context.object.data.type:
				context.object.data.type = values['old_type']

#-- The light is a mesh to be replaced by a lamp
	elif light.type == "MESH" and light.Lumiere.light_type != "Softbox":
		new_type = light.Lumiere.light_type

		# Delete the old mesh from the collection
		mesh = bpy.data.meshes[light.data.name]
		bpy.data.meshes.remove(mesh, do_unlink=True, do_id_user=True, do_ui_user=True)

		# Create a new light
		light = create_lamp(name = values['old_name'], type = new_type)
		light['Lumiere'] = lumiere_dict[values['old_name']]
		light.location = lumiere_dict[values['old_name']]["location"]
		light.rotation_euler = lumiere_dict[values['old_name']]["rotation"]


	if light.Lumiere.light_type != "Softbox":
		# Update nodes
		update_lamp(light)

	del lumiere_dict[values['old_name']]

# -------------------------------------------------------------------- #
"""Update the rounding value of the softbox"""
def update_softbox_rounding(self, context):
	light = context.active_object
	light.modifiers["Bevel"].width = light.Lumiere.softbox_rounding

# -------------------------------------------------------------------- #
"""Rotate the light on the Z axis"""
def get_tilt(self):
	light = bpy.context.object
	return light.rotation_euler.to_matrix().to_euler('ZYX').z

def set_tilt(self, tilt):
	# https://blender.stackexchange.com/questions/118057/rotate-object-on-local-axis-using-a-slider
	light = bpy.context.object
	rot = light.rotation_euler.to_matrix().to_euler('ZYX')
	rot.z = tilt
	light.rotation_euler = rot.to_matrix().to_euler(light.rotation_mode)

# -------------------------------------------------------------------- #
"""Rotate the light vertically (pitch) and horizontally around the targeted point"""
def update_spherical_coordinate(self, context):
	light = context.object

	r = light.Lumiere.range
	# θ theta is azimuthal angle, the angle of the rotation around the z-axis (aspect)
	theta = radians(light.Lumiere.rotation)
	# φ phi is the polar angle, rotated down from the positive z-axis (slope)
	phi = radians(light.Lumiere.pitch)

	#https://en.wikipedia.org/wiki/Spherical_coordinate_system
	x = r * sin(phi) * cos(theta) + light.Lumiere.hit[0]
	y = r * sin(phi) * sin(theta) + light.Lumiere.hit[1]
	z = r * cos(phi) + light.Lumiere.hit[2]

	light.location = Vector((x, y, z))
	track  = light.location - Vector(light.Lumiere.hit)
	rotaxis = (track.to_track_quat('Z','Y'))
	light.rotation_euler = rotaxis.to_euler()

	# Update direction for range update
	light.Lumiere.direction = light.matrix_world.to_quaternion() @ Vector((0.0, 0.0, 1.0))

# -------------------------------------------------------------------- #
"""Update the ratio scale/energy"""
def update_ratio(self,context):
	light = context.object
	if light.Lumiere.ratio:
		if light.type == 'MESH':
			light.Lumiere.save_energy = (light.scale[0] * light.scale[1]) * light.Lumiere.energy
		else:
			light.Lumiere.save_energy =  (light.data.size * light.data.size_y) * light.Lumiere.energy

# -------------------------------------------------------------------- #
"""Update the light energy using the scale xy of the light"""
def update_lock_scale(self,context):
	light = context.object

	if light.Lumiere.lock_scale:
		light.scale[0] = light.scale[1] = light.Lumiere.scale_xy
	else:
		light.scale[0] = light.Lumiere.scale_x
		light.scale[1] = light.Lumiere.scale_y

# -------------------------------------------------------------------- #
"""Update the scale xy of the light"""
def update_scale_xy(self,context):
	light = context.object

	if light.type == 'MESH':
		light.scale[0] = light.scale[1] = light.Lumiere.scale_xy
		light.Lumiere.scale_x = light.Lumiere.scale_y = light.Lumiere.scale_xy
	else:
		light.data.size = light.data.size_y = light.Lumiere.scale_xy

	if light.Lumiere.ratio:
		light.Lumiere.energy = light.Lumiere.save_energy / (light.scale[0] * light.scale[1])

	if light.scale[0] < 0.001:
		light.scale[0] = 0.001
	if light.scale[1] < 0.001:
		light.scale[1] = 0.001

# -------------------------------------------------------------------- #
"""Update the x dimension of the light"""
def update_scale(self,context):
	light = context.object

	if light.type == 'MESH':
		light.scale[0] = light.Lumiere.scale_x
		light.scale[1] = light.Lumiere.scale_y
	else:
		light.data.size = light.Lumiere.scale_x
		light.data.size_y = light.Lumiere.scale_y

	if light.Lumiere.ratio:
		light.Lumiere.energy = light.Lumiere.save_energy / (light.scale[0] * light.scale[1])

	if light.scale[0] < 0.001:
		light.scale[0] = 0.001
	if light.scale[1] < 0.001:
		light.scale[1] = 0.001

# -------------------------------------------------------------------- #
"""Update the distance of the light from the object target"""
def update_range(self,context):
	light = context.active_object

	light_loc = Vector(light.Lumiere.hit) + (Vector(light.Lumiere.direction) * light.Lumiere.range)
	light.location = Vector((light_loc[0], light_loc[1], light_loc[2]))
	track  = light.location - Vector(light.Lumiere.hit)
	rotaxis = (track.to_track_quat('Z','Y'))
	light.rotation_euler = rotaxis.to_euler()

# -------------------------------------------------------------------- #
"""Target only this object"""
def target_poll(self, object):
	if object.data.name not in bpy.context.scene.collection.children['Lumiere'].all_objects:
		return object

# -------------------------------------------------------------------- #
"""Show only this light and hide all the other"""
def select_only(self, context):
	light = context.active_object

#---Active only the visible light
	context.scene.objects.active = bpy.data.objects[light.name]
	bpy.context.view_layer.objects.active = bpy.data.objects[light.name]
#---Deselect and hide all the lights in the scene and show the active light
	for ob in bpy.context.scene.objects:
			ob.select = False
			if ob.type != 'EMPTY' and ob.data.name.startswith("Lumiere") and (ob.name != light.name) and light.Lumiere.show:
				if light.Lumiere.select_only:
					if ob.Lumiere.show: ob.Lumiere.show = False
				else:
					if not ob.Lumiere.show: ob.Lumiere.show = True

#---Select only the visible light
	light.select = True

# -------------------------------------------------------------------- #
## Items

"""Define the different items for the color choice of lights"""
def items_color_type(self, context):
	light = context.active_object

	if light.Lumiere.light_type == "Softbox":
		items = {
				("Color", "Color", "", 0),
				("Linear", "Linear", "", 1),
				("Spherical", "Spherical", "", 2),
				("Reflector", "Reflector", "", 3),
				}
	else:
		items = {
				("Color", "Color", "", 0),
				("Gradient", "Gradient", "", 1),
				}

	return items


# -------------------------------------------------------------------- #
## Properties
class LumiereObj(bpy.types.PropertyGroup):

#---Strength of the light
	energy : FloatProperty(
						   name="Strength",
						   description="Strength of the light",
						   min=0.001, max=900000000000.0,
						   soft_min=0.0, soft_max=100.0,
						   default=10,
						   precision=0,
						   step=.2,
						   subtype='NONE',
						   unit='NONE',
						   update=update_mat
						   )

#---Rotate the light around Z
	rotation : FloatProperty(
						  name="Rotation",
						  description="Rotate the light horizontally around the target",
						  min=-0.1,
						  max=360.1,
						  step=20,
						  update=update_spherical_coordinate,
						  # get=get_rotation,
						  # set=set_rotation,
						  )

#---Rotate the light horizontally
	tilt : FloatProperty(
						  name="Tilt",
						  description="Rotate the light along it's Z axis",
						  step=20,
						  unit='ROTATION',
						  get=get_tilt,
						  set=set_tilt,
						  )

#---Rotate the light vertically
	pitch : FloatProperty(
						  name="Pitch",
						  description="Rotate the light vertically around the target",
						  min=0.0,
						  max=180,
						  step=20,
						  update=update_spherical_coordinate,
						  )

#---Scale the light
	scale_xy : FloatProperty(
						  name="Scale",
						  description="Scale the light",
						  min=0.0001, max=100000,
						  soft_min=0.001, soft_max=100.0,
						  step=5,
						  default=1,
						  precision=2,
						  update=update_scale_xy,
						  )

#---Scale the light on x
	scale_x : FloatProperty(
						  name="Scale x",
						  description="Scale the light on x",
						  min=0.0001, max=100000,
						  soft_min=0.001, soft_max=10.0,
						  step=1,
						  default=1,
						  precision=2,
						  update=update_scale,
						  )

#---Scale the light on y
	scale_y : FloatProperty(
						  name="Scale y",
						  description="Scale the light on y",
						  min=0.0001, max=100000,
						  soft_min=0.001, soft_max=10.0,
						  step=5,
						  default=1,
						  precision=2,
						  update=update_scale,
						  )

#---Range of the light from the targeted object
	range : FloatProperty(
						  name="Range",
						  description="Distance from the object",
						  min=0.001, max=100000,
						  soft_min=0.01, soft_max=50.0,
						  default=2,
						  precision=2,
						  # subtype='DISTANCE',
						  unit='LENGTH',
						  update=update_range,
						  )

#---Compute the reflection angle from the normal of the target or from the view of the screen.
	reflect_angle : EnumProperty(name="Reflection",
						  description="Compute the light position from the angle view or the normal of the object.\n"+\
						  "\u2022 Accurate : The light will be positioned in order for its reflection to be under the cursor.\n"+\
						  "\u2022 Normal : The light will be positioned in parallel to the normal of the face of the targeted object.\n"+\
						  "\u2022 Estimated : The light will be positioned always facing the center of the bounding box.\n"+\
						  "Selected",
						  items=(
						  ("0", "Accurate", "", 0),
						  ("1", "Normal", "", 1),
						  ("2", "Bound", "", 2),
						  ),
						  default="2")

#---List of lights to change the selected one to
	light_type : EnumProperty(name="Light type:",
								description="List of lights sources:\n"+
								"\u2022 Panel : Panel object with an emission shader\n"+
								"\u2022 Point : Emit light equally in all directions\n"+
								"\u2022 Sun : Emit light in a given direction\n"+
								"\u2022 Spot : Emit light in a cone direction\n"+
								"\u2022 Area : Emit light from a square or rectangular area\n"+
								"\u2022 Import : Import your previous saved Light / Group lights\n"+
								"Selected",
								items =(
								("Softbox", "Softbox", "", "MESH_PLANE", 0),
								("Point", "Point", "", "LIGHT_POINT", 1),
								("Sun", "Sun", "", "LIGHT_SUN", 2),
								("Spot", "Spot", "", "LIGHT_SPOT", 3),
								("Area", "Area", "", "LIGHT_AREA", 4),
								),
								update = update_type_light
								)


#---Define how light intensity decreases over distance
	falloff_type : EnumProperty(name="Falloff",
							  description="Define how light intensity decreases over distance.\n"+
							  "Quadratic: Representation of how light attenuates in the real world.\n"+
							  "Linear   : Distance to the light have a slower decrease in intensity.\n"+
							  "Constant : Useful for distant light sources like the sun or sky.\n"+
							  "Selected",
							  items=(
							  ("0", "Quadratic falloff", "", 0),
							  ("1", "Linear falloff", "", 1),
							  ("2", "Constant falloff", "", 2),
							  ),
							  default='0',
							  update=update_mat)

#---Object the light will always target
	target : PointerProperty(type=bpy.types.Object,
							   name="Target",
							   description="Object the light will always target.",
							   poll=target_poll,
							   )
# -------------------------------------------------------------------- #
## Materials

#---Base Color of the light
	light_color : FloatVectorProperty(
									 name = "Color",
									 description="Base Color of the light",
									 subtype = "COLOR",
									 size = 4,
									 min = 0.0,
									 max = 1.0,
									 default = (0.8,0.8,0.8,1.0),
									 update=update_mat
									 )

#---List of color options
	color_type : EnumProperty(name="Colors",
							  	description="Colors options:\n"+
								"\u2022 Gradient: Gradient color emission\n"+
								"\u2022 Color: Single color emission\n"+
								"\u2022 Reflector: No emission\n"+
								"Selected",
								items=items_color_type,
								update=update_mat,
								)

#---List of color options
	material_menu : EnumProperty(name="Material",
							  	description="Material options:\n"+
								"\u2022 Color / Gradient: Base Color of the light\n"+
								"\u2022 Texture: Image texture emission\n"+
								"\u2022 IES: Real world lights intensity distribution\n"+
								"\u2022 Falloff: Define how light intensity decreases over distance\n"+
								"Selected",
								items = {
										("Color", "Color", "", "COLOR", 0),
										("Texture", "Texture", "", "FILE_IMAGE", 1),
										("IES", "IES", "","PROP_CON", 2),
										("Falloff", "Falloff", "","OUTLINER_OB_LIGHT", 3),
										},
								)

#---Name of image texture
	img_name : StringProperty(
							  name="Name of the image texture",
							  update=update_mat)

#---Name of image texture
	ies_name : StringProperty(
							  name="Name of the image texture",
							  update=update_mat)

#---Texture used for lighting or reflecton only.
	img_reflect_only : BoolProperty(
							 name="Reflection only",
							 description="Use the texture only in the reflection or for the light.",
							 default=True,
							 update=update_mat)

#---Rotate the texture on 90°
	rotate_ninety : BoolProperty(default=False,
								description="Rotate the texture on 90°",
								update=update_mat)

#---ImLock image scale on x and y
	img_lock_scale : BoolProperty(name = "Lock",
						description = "Lock image scale on x and y",
						default=True,
						)

#---Scale image texture.
	img_scale : FloatProperty(
							  name="Scale image texture",
							  description="Scale the image texture.",
							  min=0, max=999.0,
							  default=1,
							  precision=2,
							  subtype='NONE',
							  unit='NONE',
							  update=update_mat)

#---Scale IES.
	ies_scale : FloatProperty(
							  name="Scale IES",
							  description="Scale the IES.",
							  min=0, max=2,
							  default=1,
							  precision=2,
							  subtype='NONE',
							  unit='NONE',
							  update=update_mat)

#---IES used for lighting or reflecton only.
	ies_reflect_only : BoolProperty(
							 name="Reflection only",
							 description="Use the IES only in the reflection or for the light.",
							 default=True,
							 update=update_mat)

#---Invert the color of the image.
	img_invert : FloatProperty(
							  name="Invert",
							  description="Inverts the colors in the input image, producing a negative.",
							  min=0, max=1.0,
							  default=0,
							  precision=2,
							  subtype='NONE',
							  unit='NONE',
							  update=update_mat)
# -------------------------------------------------------------------- #
## Parameters

#---rounding of the softbox. 1 = round
	softbox_rounding : FloatProperty(
								name="Round",
								description="rounding of the softbox.\n0 = Square\n1 = Round",
								min=0, max=1.0,
								default=0.25,
								precision=2,
								subtype='NONE',
								unit='NONE',
								update=update_softbox_rounding
								)

#---Vector hit point on target object
	hit : FloatVectorProperty(
							name="Hit",
							description="Vector hit point on target object",
							)

#---Vector direction toward targeted object
	direction : FloatVectorProperty(
							name="Direction",
							description="Vector direction toward targeted object",
							)

#---Used for ratio between scale and energy
	save_energy : FloatProperty(
						   name="Save energy",
						   )

#---Enable / Disable the ratio between scale/energy
	ratio : BoolProperty(name = "Ratio",
						description = "Enable / Disable the ratio between scale/energy",
						default=False,
						update=update_ratio,
						)

#---Enable / Disable the gizmos
	gizmo : BoolProperty(name = "Gizmo",
						description = "Enable / Disable the gizmos",
						default=False)

#---Lock scale on x and y
	lock_scale : BoolProperty(name = "Lock scale on x and y",
						description = "Lock scale on x and y",
						default=True,
						update=update_lock_scale,
						)

#---Modal operator running
	use_modal : BoolProperty(name = "Use modal",
						description = "Modal operator running",
						default=False,
						)

# -------------------------------------------------------------------- #
# # Preset Menu
# class LUMIERE_PT_presets(PresetMenu):
#     bl_label = "Studio Presets"
#     preset_subdir = "studio_lights"
#     preset_operator = "script.execute_preset"
#     preset_add_operator = "studio_lights.preset_add"
#     COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_EEVEE', 'BLENDER_WORKBENCH'}

# -------------------------------------------------------------------- #
## Parent panel
class POLL_PT_Lumiere:
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"

	@classmethod
	def poll(cls, context):
		if (context.active_object is not None):
			if ("Lumiere" in str(context.active_object.users_collection)) \
			and len(list(context.scene.collection.children['Lumiere'].objects)) > 0 : # \
			# and context.view_layer.objects.active.type == 'MESH':
				return context.view_layer.objects.active.name in context.scene.collection.children['Lumiere'].all_objects
		else:
			return False


class MAIN_PT_Lumiere(POLL_PT_Lumiere, Panel):
	bl_idname = "MAIN_PT_Lumiere"
	bl_label = "Main"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Lumiere"

	def draw_header_preset(self, context):
		layout = self.layout
		col = layout.column(align=False)
		row = col.row(align=True)
		row.operator("lumiere.ray_operator", text="", icon="MOUSE_LMB_DRAG")
		row.separator()

	def draw(self, context):
		light = context.active_object

		layout = self.layout
		layout.use_property_split = True # Active single-column layout
		layout.use_property_decorate = False  # No animation.
		flow = layout.grid_flow(row_major=True, columns=0, even_columns=True, even_rows=False, align=True)
		col = flow.column(align=True)
		col.ui_units_x = 7

		row = col.row(align=True)
		# row.operator("lumiere.ray_operator", text="", icon="OUTLINER_OB_LIGHT")#PARTICLE_DATA / MOUSE_MMB / OUTLINER_OB_LIGHT
		row.enabled = False if (light.Lumiere.ratio \
		and light.Lumiere.light_type in ("Softbox", "Area")) else True
		row.prop(light.Lumiere, "energy", text="Energy", slider = True)
		col.prop(light.Lumiere, "light_type", text="Light type")
		col.prop(light.Lumiere, "reflect_angle", text="Position")


# -------------------------------------------------------------------- #
## Softbox Sub panel
class MESH_OPTIONS_PT_Lumiere(POLL_PT_Lumiere, Panel):
	bl_idname = "MESH_OPTIONS_PT_Lumiere"
	bl_label = "Options"
	# bl_parent_id = "MAIN_PT_Lumiere"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Lumiere"

	@classmethod
	def poll(cls, context):
		if (POLL_PT_Lumiere.poll(context)) :
			return context.view_layer.objects.active.type == 'MESH'

	def draw(self, context):
		light = context.active_object
		mat = get_mat_name()

		layout = self.layout
		layout.use_property_split = True # Active single-column layout
		layout.use_property_decorate = False  # No animation.
		flow = layout.grid_flow(row_major=True, columns=0, even_columns=True, even_rows=False, align=True)
		col = flow.column(align=False)
		col.ui_units_x = 7
		col = col.column(align=True)
		col.prop(light.Lumiere, "target", text="Target")
		col.prop(light.Lumiere, "range", text="Range")
		col.separator()

		col = flow.column(align=False)
		col.ui_units_x = 7
		col = col.column(align=True)
		row = col.row(align=True)
		if light.Lumiere.lock_scale:
			row.prop(light.Lumiere, "scale_xy", text="Scale xy")
			row.prop(light.Lumiere, "lock_scale", text="", emboss=False, icon='DECORATE_LOCKED')

		if not light.Lumiere.lock_scale:
			row = col.row(align=True)
			row.prop(light.Lumiere, "scale_x", text="Scale X")
			row.prop(light.Lumiere, "lock_scale", text="", emboss=False, icon='DECORATE_UNLOCKED')
			row = col.row(align=True)
			row.prop(light.Lumiere, "scale_y", text="Y")
			row.prop(light.Lumiere, "lock_scale", text="", emboss=False, icon='DECORATE_UNLOCKED')
		col.prop(light.Lumiere, "ratio", text="Keep ratio")

		col = flow.column(align=False)
		col.ui_units_x = 7
		col = col.column(align=True)
		col.prop(light.Lumiere, "rotation", text="Rotation")
		col.prop(light.Lumiere, "tilt", text="Tilt")
		col.prop(light.Lumiere, "pitch", text="Pitch")
		col.separator()

		col = flow.column(align=False)
		col.ui_units_x = 7
		col = col.column(align=True)
		col.prop(light.Lumiere, "softbox_rounding", text="Round Shape")
		col.prop(light.modifiers["Bevel"], "segments", text="Segments", slider=False)
		col.separator()

		soft_edges1 = mat.node_tree.nodes["Edges ColRamp"].color_ramp.elements[0]
		soft_edges2 = mat.node_tree.nodes["Edges ColRamp"].color_ramp.elements[1]
		edges_value = mat.node_tree.nodes["Edges value"].outputs[0]
		col = col.column(align=True)
		col.prop(edges_value, "default_value", text="Soft edges", slider=False)
		row = col.row(align=True)
		row.prop(soft_edges1, "position", text='Edges')
		row.prop(soft_edges2, "position", text='')
		col.separator()


#va chercher les presets dans le répertoire : C:\Blender\Official\2.8\blender-2.80\2.80\scripts\presets\cycles\sampling
#
# class LUMIERE_OT_AddLumierePreset(AddPresetBase, Operator):
#     '''Add a Sampling Preset'''
#     bl_idname = "lumiere.addlumierepreset"
#     bl_label = "Add Sampling Preset"
#     preset_menu = "MESH_MATERIALS_PT_Lumiere_presets"
#
#     preset_defines = [
#         # "cycles = bpy.context.scene.cycles"
#         "light = bpy.context.active_object"
#     ]
#
#     preset_values = [
#         "light.Lumiere.energy",
#         "light.Lumiere.light_color",
#         "light.Lumiere.texture_type",
#     ]
#
#     preset_subdir = "Lumiere"
#
#
# class MESH_MATERIALS_PT_Lumiere_presets(Menu):
# 	bl_label = "Lumiere Presets"
# 	# preset_subdir = "cycles/sampling"
# 	preset_subdir = "Lumiere"
# 	preset_operator = "script.execute_preset"
# 	preset_add_operator = "lumiere.addlumierepreset"
# 	COMPAT_ENGINES = {'CYCLES'}

class MESH_MATERIALS_PT_Lumiere(POLL_PT_Lumiere, Panel):
	bl_idname = "MESH_MATERIALS_PT_Lumiere"
	bl_label = "Material"
	# bl_parent_id = "MAIN_PT_Lumiere"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Lumiere"

	@classmethod
	def poll(cls, context):
		if (POLL_PT_Lumiere.poll(context)) :
			return context.view_layer.objects.active.type == 'MESH'
	#
	# def draw_header_preset(self, context):
	# 	MESH_MATERIALS_PT_Lumiere_presets.draw_panel_header(self.layout)

	def draw_header_preset(self, context):
		light = context.active_object
		layout = self.layout
		col = layout.column(align=False)
		row = col.row(align=True)
		row.prop(light.Lumiere, "material_menu", text="", expand=True)
		row.separator()

	def draw(self, context):
		light = context.active_object
		mat = get_mat_name()
		colramp = mat.node_tree.nodes['ColorRamp']
		ies = mat.node_tree.nodes["IES Texture"]
		bias = mat.node_tree.nodes["Texture invert"].inputs[0]
		col_reflector = mat.node_tree.nodes['Diffuse BSDF'].inputs[0]
		falloff = mat.node_tree.nodes["Light Falloff"].inputs[1]

		layout = self.layout
		layout.use_property_split = True # Active single-column layout
		layout.use_property_decorate = False  # No animation.
		flow = layout.grid_flow(row_major=True, columns=0, even_columns=True, even_rows=False, align=True)
		# col = flow.column(align=False)
		col = layout.column(align=False)
		# col.ui_units_x = 7
		col = col.column(align=False)
		# col.prop(light.Lumiere, "texture_type", text="")
		if light.Lumiere.material_menu == 'Color':
			col.prop(light.Lumiere, "color_type", text="", )
			if light.Lumiere.color_type in ('Color', 'Reflector'):
				col.prop(light.Lumiere, "light_color", text="Color")
			elif light.Lumiere.color_type == 'Linear':
				col.prop(light.Lumiere, "rotate_ninety", text="Rotate 90°", icon="FILE_REFRESH")
				col.template_color_ramp(colramp, "color_ramp", expand=True)
			elif light.Lumiere.color_type == 'Spherical':
				col.template_color_ramp(colramp, "color_ramp", expand=True)

		elif light.Lumiere.material_menu == 'Texture':
			row = col.row(align=True)
			row.prop_search(light.Lumiere, "img_name", bpy.data, "images", text="")
			row.operator("image.open",text='', icon='FILEBROWSER')
			# row = col.row(align=True)
			col.prop(light.Lumiere, "img_scale", text="Scale")
			col.prop(bias, "default_value", text="Bias")
			col.prop(light.Lumiere, "img_reflect_only", text="Reflection only")

		elif light.Lumiere.material_menu == 'IES':
			row = col.row(align=True)
			# row.prop_search(obj, "audioAction", context.scene, "audioFiles", icon='SPEAKER')
			row.prop_search(light.Lumiere, "ies_name", bpy.data, "texts", text="", icon="PROP_CON")
			op = row.operator("text.open", text='', icon='FILEBROWSER')
			op.filter_python = False
			op.filter_text = False
			op.filter_folder = False
			col.prop(light.Lumiere, "ies_scale", text="Scale")
			col.prop(light.Lumiere, "ies_reflect_only", text="Reflection only")
			# row = col.row(align=True)
			# row.prop(ies, "filepath", text="IES File")
		elif light.Lumiere.material_menu == 'Falloff':
			col.prop(light.Lumiere, "falloff_type", text="Falloff")
			col.prop(falloff, "default_value", text="Smooth")
		col = flow.column(align=True)
		col.ui_units_x = 7

# -------------------------------------------------------------------- #
## Lamp Sub panel

class LAMP_OPTIONS_PT_Lumiere(POLL_PT_Lumiere, Panel):
	bl_idname = "LAMP_OPTIONS_PT_Lumiere"
	bl_label = "Options"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Lumiere"

	@classmethod
	def poll(cls, context):
		if (POLL_PT_Lumiere.poll(context)) :
			return context.view_layer.objects.active.type == 'LIGHT'

	def draw(self, context):
		light = context.active_object
		mat = get_mat_name()

		layout = self.layout
		layout.use_property_split = True # Active single-column layout
		layout.use_property_decorate = False  # No animation.
		flow = layout.grid_flow(row_major=True, columns=0, even_columns=True, even_rows=False, align=True)
		col = flow.column(align=False)
		col.ui_units_x = 7
		col = col.column(align=True)
		col.prop(light.Lumiere, "target", text="Target")
		col.prop(light.Lumiere, "range", text="Range")
		col.separator()

		col = flow.column(align=False)
		col.ui_units_x = 7
		col = col.column(align=True)

		if light.data.type == "AREA":
			col.prop(light.data, "shape", text="Shape")
			col = col.column(align=True)
			row = col.row(align=True)
			if light.Lumiere.lock_scale:
				row.prop(light.Lumiere, "scale_xy", text="Scale xy")
				row.prop(light.Lumiere, "lock_scale", text="", emboss=False, icon='DECORATE_LOCKED')

			if not light.Lumiere.lock_scale:
				row = col.row(align=True)
				row.prop(light.Lumiere, "scale_x", text="Scale x")
				row.prop(light.Lumiere, "lock_scale", text="", emboss=False, icon='DECORATE_UNLOCKED')
				row = col.row(align=True)
				row.prop(light.Lumiere, "scale_y", text="Scale y")
				row.prop(light.Lumiere, "lock_scale", text="", emboss=False, icon='DECORATE_UNLOCKED')
			col.prop(light.Lumiere, "ratio", text="Keep ratio")

		elif light.data.type == "SPOT":
			col.prop(light.data, "spot_size", text="Cone Size")
			col.prop(light.data, "spot_blend", text="Cone Blend")
			col.prop(light.data, "shadow_soft_size", text="Shadow")

		elif light.data.type == "POINT":
			col.prop(light.data, "shadow_soft_size", text="Shadow")

		elif light.data.type == "SUN":
			col.prop(light.data, "angle", text="Shadow")

		col.separator()

		col = flow.column(align=False)
		col.ui_units_x = 7
		col = col.column(align=True)
		col.prop(light.Lumiere, "rotation", text="Rotation")
		col.prop(light.Lumiere, "tilt", text="Tilt")
		col.prop(light.Lumiere, "pitch", text="Pitch")
		col.separator()
# -------------------------------------------------------------------- #

class LAMP_MATERIALS_PT_Lumiere(POLL_PT_Lumiere, Panel):
	bl_idname = "LAMP_MATERIALS_PT_Lumiere"
	bl_label = "Material"
	# bl_parent_id = "MAIN_PT_Lumiere"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Lumiere"

	@classmethod
	def poll(cls, context):
		if (POLL_PT_Lumiere.poll(context)) :
			return context.view_layer.objects.active.type == 'LIGHT'

	def draw_header_preset(self, context):
		light = context.active_object
		layout = self.layout
		col = layout.column(align=False)
		row = col.row(align=True)
		row.prop(light.Lumiere, "material_menu", text="", expand=True)
		row.separator()

	def draw(self, context):
		light = context.active_object
		mat = get_mat_name()
		ies = light.data.node_tree.nodes["IES"]
		colramp = light.data.node_tree.nodes["ColorRamp"]
		falloff = light.data.node_tree.nodes["Light Falloff"].inputs[1]

		layout = self.layout
		layout.use_property_split = True # Active single-column layout
		layout.use_property_decorate = False  # No animation.
		flow = layout.grid_flow(row_major=True, columns=0, even_columns=True, even_rows=False, align=True)
		col = flow.column(align=False)
		col.ui_units_x = 7
		col = col.column(align=True)
		if light.Lumiere.material_menu == "Texture":
			# col.prop(light.Lumiere, "texture_type", text="", )

			# if light.Lumiere.texture_type == 'Texture':
			row = col.row(align=True)
			row.prop_search(light.Lumiere, "img_name", bpy.data, "images", text="")
			row.operator("image.open",text='', icon='FILEBROWSER')
			col = col.column(align=True)
			row = col.row(align=True)
			row.prop(light.Lumiere, "img_scale", text="Scale")
			row = col.row(align=True)
			row.prop(light.Lumiere, "img_invert", text="Invert")

		elif light.Lumiere.material_menu == 'IES':
			row = col.row(align=True)
			# row.prop(ies, "filepath", text="IES File")
			row.prop_search(light.Lumiere, "ies_name", bpy.data, "texts", text="", icon="PROP_CON")
			op = row.operator("text.open", text='', icon='FILEBROWSER')
			op.filter_python = False
			op.filter_text = False
			op.filter_folder = False
			col.prop(light.Lumiere, "ies_scale", text="Scale")

		elif light.Lumiere.material_menu == 'Color':
			col.prop(light.Lumiere, "color_type", text="", )

			if light.Lumiere.color_type == 'Color':
				row = col.row(align=True)
				row.prop(light.Lumiere, "light_color", text="Color")
			elif light.Lumiere.color_type == 'Gradient':
				col.template_color_ramp(colramp, "color_ramp", expand=True)
		else:
			col.prop(light.Lumiere, "falloff_type", text="Falloff")
			col.prop(falloff, "default_value", text="Smooth")
		col = flow.column(align=True)
		col.ui_units_x = 7


# -------------------------------------------------------------------- #
## Operator
class OPERATOR_PT_Lumiere(Panel):
	bl_idname = "OPERATOR_PT_Lumiere"
	bl_label = "Lumiere"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	# bl_context = "object"
	bl_category = "Lumiere"

	@classmethod
	def poll(cls, context):
		if (context.active_object is not None):
			if ("Lumiere" in str(context.active_object.users_collection)) \
			and len(list(context.scene.collection.children['Lumiere'].objects)) > 0 :
				return context.view_layer.objects.active.name not in context.scene.collection.children['Lumiere'].all_objects
		return True

	def draw(self, context):

		layout = self.layout
		layout.use_property_split = True # Active single-column layout
		layout.use_property_decorate = False  # No animation.
		flow = layout.grid_flow(row_major=True, columns=0, even_columns=True, even_rows=False, align=True)
		col = flow.column(align=True)
		col.ui_units_x = 7
		# col.label(text="OPERATOR",icon='BLANK1')
		col.operator("lumiere.ray_operator", text="CREATE", icon='BLANK1')

# -------------------------------------------------------------------- #
## Utilities
"""Return the name of the material of the light"""
def get_mat_name():
	light = bpy.context.object
	if bpy.context.object.type == 'MESH':
		mat = light.active_material
	else:
		mat = bpy.data.lights[light.data.name].name

	return(mat)


# -------------------------------------------------------------------- #
## Register


classes = [
	MAIN_PT_Lumiere,
	# LUMIERE_PT_presets,
	# MESH_MATERIALS_PT_Lumiere_presets,
	# LUMIERE_OT_AddLumierePreset,
	MESH_OPTIONS_PT_Lumiere,
	MESH_MATERIALS_PT_Lumiere,
	LAMP_OPTIONS_PT_Lumiere,
	LAMP_MATERIALS_PT_Lumiere,
	OPERATOR_PT_Lumiere,
	LumiereObj,
	]


def register():
	from bpy.utils import register_class
	for cls in classes:
		print("CLASSE: ", cls)
		register_class(cls)
	bpy.types.Object.Lumiere = bpy.props.PointerProperty(type=LumiereObj)


def unregister():
	from bpy.utils import unregister_class
	for cls in reversed(classes):
		unregister_class(cls)
	del bpy.types.Object.Lumiere
