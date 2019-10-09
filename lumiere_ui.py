import bpy
import bmesh
from bpy.types import Panel, Operator, Menu
from bl_operators.presets import AddPresetBase
from bl_ui.utils import PresetPanel

from .lumiere_utils import (
	get_lumiere_dict,
	update_lumiere_dict,
	get_mat_name,
	)

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
def update_type_light(self, context):
	"""Change the selected light to a new one"""

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

		# Create a new light
		light = create_lamp(name = values['old_name'], type = new_type)
		light['Lumiere'] = lumiere_dict[values['old_name']]
		light.location = lumiere_dict[values['old_name']]["location"]
		light.rotation_euler = lumiere_dict[values['old_name']]["rotation"]

		update_lamp(light)

		bpy.data.meshes.remove(mesh, do_unlink=True, do_id_user=True, do_ui_user=True)

	del lumiere_dict[values['old_name']]

# -------------------------------------------------------------------- #
def update_softbox_rounding(self, context):
	"""Update the rounding value of the softbox"""
	light = context.active_object
	light.modifiers["Bevel"].width = light.Lumiere.softbox_rounding

# -------------------------------------------------------------------- #
def update_texture_scale(self, context):
	"""Update the texture scale"""
	light = context.active_object

	if light.type == 'MESH':
		me = light.data
		bm = bmesh.new()
		bm.from_mesh(me)

		uv_layer = bm.loops.layers.uv.active

		if light.Lumiere.lock_scale:
			scale_x = scale_y = light.Lumiere.img_scale / 2 + .5
		else:
			scale_x = (light.Lumiere.img_scale * light.Lumiere.scale_x) / 2 + .5
			scale_y = (light.Lumiere.img_scale * light.Lumiere.scale_y) / 2 + .5

		for f in bm.faces:
			f.loops[3][uv_layer].uv = (scale_x, scale_y)
			f.loops[2][uv_layer].uv = (1-scale_x, scale_y)
			f.loops[1][uv_layer].uv = (1-scale_x, 1-scale_y)
			f.loops[0][uv_layer].uv = (scale_x, 1-scale_y)
		bm.to_mesh(me)
	else:
		update_lamp(light)

# -------------------------------------------------------------------- #
def get_tilt(self):
	"""Rotate the light on the Z axis"""
	light = bpy.context.object
	return light.rotation_euler.to_matrix().to_euler('ZYX').z

def set_tilt(self, tilt):
	# https://blender.stackexchange.com/questions/118057/rotate-object-on-local-axis-using-a-slider
	light = bpy.context.object
	rot = light.rotation_euler.to_matrix().to_euler('ZYX')
	rot.z = tilt
	light.rotation_euler = rot.to_matrix().to_euler(light.rotation_mode)

# -------------------------------------------------------------------- #
def update_spherical_coordinate(self, context):
	"""Rotate the light vertically (pitch) and horizontally around the targeted point"""
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
def update_ratio(self,context):
	"""Update the ratio scale/energy"""
	light = context.object
	if light.Lumiere.ratio:
		if light.type == 'MESH':
			light.Lumiere.save_energy = (light.scale[0] * light.scale[1]) * light.Lumiere.energy

# -------------------------------------------------------------------- #
def update_lock_scale(self,context):
	"""Update the light energy using the scale xy of the light"""
	light = context.object

	if light.Lumiere.lock_scale:
		light.scale[0] = light.scale[1] = light.Lumiere.scale_xy
	else:
		light.scale[0] = light.Lumiere.scale_x
		light.scale[1] = light.Lumiere.scale_y

	update_texture_scale(self, context)

# -------------------------------------------------------------------- #
def update_scale_xy(self,context):
	"""Update the scale xy of the light"""
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
def update_scale(self,context):
	"""Update the x dimension of the light"""
	light = context.object

	if light.type == 'MESH':
		light.scale[0] = light.Lumiere.scale_x
		light.scale[1] = light.Lumiere.scale_y
		update_texture_scale(self, context)
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
def update_range(self,context):
	"""Update the distance of the light from the object target"""
	light = bpy.data.objects[self.id_data.name]

	light_loc = Vector(light.Lumiere.hit) + (Vector(light.Lumiere.direction) * light.Lumiere.range)
	light.location = Vector((light_loc[0], light_loc[1], light_loc[2]))
	track  = light.location - Vector(light.Lumiere.hit)
	rotaxis = (track.to_track_quat('Z','Y'))
	light.rotation_euler = rotaxis.to_euler()

# -------------------------------------------------------------------- #
def target_poll(self, object):
	"""Target only this object"""
	if object.data.name not in bpy.context.scene.collection.children['Lumiere'].all_objects:
		return object

# -------------------------------------------------------------------- #
def select_only(self, context):
	"""Show only this light and hide all the other"""
	light = bpy.data.objects[self.id_data.name]

#---Active only the visible light
	context.view_layer.objects.active = light

#---Deselect and hide all the lights in the scene and show the active light
	bpy.ops.object.select_all(action='DESELECT')
	for ob in context.scene.collection.children['Lumiere'].objects:
		if ob.name != light.name:
			if light.Lumiere.select_only:
				ob.hide_viewport = False
			else:
				ob.hide_viewport = True

#---Select only the visible light
	light.select_set(True)

# -------------------------------------------------------------------- #
## Items

def items_color_type(self, context):
	"""Define the different items for the color choice of lights"""

	if bpy.data.objects[self.id_data.name].type == "MESH":
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
class LightsProp(bpy.types.PropertyGroup):
	name : StringProperty(
						name="Description",
						description="Description.",
						)
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
						  soft_min=0.001, soft_max=100.0,
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
						  soft_min=0.001, soft_max=100.0,
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
						  unit='LENGTH',
						  update=update_range,
						  )

#---Compute the reflection angle from the normal of the target or from the view of the screen.
	reflect_angle : EnumProperty(name="Reflection",
						  description="Compute the light position from the angle view or the normal of the object.\n"+\
						  "\u2022 Accurate : The light will be positioned in order for its reflection to be under the cursor.\n"+\
						  "\u2022 Normal : The light will be positioned in perpendicular to the normal of the face of the targeted object.\n"+\
						  "\u2022 Estimated : The light will be positioned always facing the center of the bounding box.\n"+\
						  "Selected",
						  items=(
						  ("0", "Accurate", "", 0),
						  ("1", "Normal", "", 1),
						  ("2", "Estimated", "", 2),
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
								default="Softbox",
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

#---BoundingBox center of the targeted object
	bbox_center : FloatVectorProperty(
							   name="bbox_center",
							   description="BoundingBox center of the targeted object.",
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
								"\u2022 Options: Define how light intensity decreases over distance and multiple important sample\n"+
								"Selected",
								items = {
										("Color", "Color", "Color", "COLOR", 0),
										("Texture", "Texture", "Texture", "FILE_IMAGE", 1),
										("IES", "IES", "IES","OUTLINER_OB_LIGHT", 2),
										("Options", "Options", "Options","PREFERENCES", 3),
										},
								)

#---Name of image texture
	ies_name : StringProperty(
							  name="Name of the image texture",
							  update=update_mat)

#---Name of image texture
	img_name : StringProperty(
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
							  update=update_texture_scale)

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

#---Lock scale on x and y
	lock_scale : BoolProperty(name = "Lock scale on x and y",
						description = "Lock scale on x and y",
						default=True,
						update=update_lock_scale,
						)

#---Enable / Disable the manual position of bbox center
	auto_bbox_center : BoolProperty(name = "Bbox center",
						description = "Enable / Disable the manual position of bbox center",
						default=True)

#---Enable / Disable the gizmos
	gizmo : BoolProperty(name = "Gizmo",
						description = "Enable / Disable the gizmos",
						default=False)

#---Show only this light and hide all the others.
	select_only : BoolProperty(name="Select Only",
							   description="Show only this light and hide all the others",
							   default=True,
							   update=select_only)

# -------------------------------------------------------------------- #
class ALL_LIGHTS_UL_list(bpy.types.UIList):
	def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
		object = data
		if self.layout_type in {'DEFAULT', 'COMPACT'}:
			split = layout.split(factor=0.2)
			split.label(text="%d" % (index))
			split.prop(item, "name", text="", toggle=False, emboss=False, icon_value=icon, icon="BLANK1")
		elif self.layout_type in {'GRID'}:
			pass


# -------------------------------------------------------------------- #
def seListIndexFunction(self, value):
	print("CHANGE INDEX")
# -------------------------------------------------------------------- #
class CUSTOM_OT_actions(Operator):
	"""Move items up and down, add and remove"""
	bl_idname = "custom.list_action"
	bl_label = "Import/Remove"
	bl_description = "Import or remove from the list"
	bl_options = {'REGISTER'}

	action: bpy.props.EnumProperty(
		description="Import/Export options.\nSelected",
		items=(
			('REMOVE', "Remove", ""),
			('ADD', "Add", "")))


	arg: bpy.props.StringProperty()


	@classmethod
	def description(cls, context, props):
		return "Preset: " + props.arg

	def add_light(self, context):
		scn = context.scene
		idx = scn.Lumiere_lights_list_index
		light_from_dict = self.my_dict[scn.Lumiere_lights_list[idx].name]

		if light_from_dict["Lumiere"]["light_type"] == "Softbox":
			light = create_softbox(scn.Lumiere_lights_list[idx].name)

		light["Lumiere"] = light_from_dict["Lumiere"]
		light.location = light_from_dict["location"]
		light.rotation_euler = light_from_dict["rotation"]
		light.scale = light_from_dict["scale"]

		update_mat(self, context)


	def remove_light(self, context):

		list = context.scene.Lumiere_lights_list
		list_index = context.scene.Lumiere_lights_list_index

		my_dict = get_lumiere_dict()
		self.report({'INFO'}, "Light " + list[list_index].name + " deleted from the list")
		my_dict.pop(list[list_index].name, None)
		list.remove(list_index)
		list_index -= 1
		update_lumiere_dict(my_dict)


	def invoke(self, context, event):
		scn = context.scene
		idx = scn.Lumiere_lights_list_index
		self.my_dict = get_lumiere_dict()

		try:
			item = scn.Lumiere_lights_list[idx]
		except IndexError:
			pass
		else:
			if self.action == 'ADD':
				self.add_light(context)
			elif self.action == 'REMOVE':
				self.remove_light(context)

		return {"FINISHED"}

# -------------------------------------------------------------------- #
# Preset Menu
class LUMIERE_OT_ExportPopup(Operator):
	'''Add a Sampling Preset'''
	bl_idname = "lumiere.export_popup"
	bl_label = "Add Sampling Preset"

	def draw_props(self, labelname):
		layout = self.layout
		c = layout.column()
		row = c.row()
		split = row.split(factor=0.25)
		c = split.column()
		c.label(text=labelname)
		split = split.split()
		self.column = split.column()

	def execute(self, context):
		try:
			select_item = scene.Lumiere_lights_list[scene.Lumiere_lights_list_index].name
			self.add_light(context, select_item)
		except:
			exc_type, exc_value, exc_traceback = sys.exc_info()
			self.report({'ERROR'}, str(exc_value))

		return {"FINISHED"}

	def check(self, context):
		return True

	def draw(self, context):
		scene = context.scene
		light = context.active_object
		layout = self.layout

	#---Export individual light
		col = layout.column()
		row = col.row()
		if len(context.scene.Lumiere_lights_list) > 0:
			row.template_list("ALL_LIGHTS_UL_list", "",context.scene, "Lumiere_lights_list", context.scene, "Lumiere_lights_list_index", rows=2)
			col2 = row.column(align=True)
			op_add = col2.operator("custom.list_action", emboss=False, icon='IMPORT', text="")
			op_add.action = 'ADD'
			op_add.arg = "Import to scene"
			row = col2.row(align=True)
			op_del = row.operator("custom.list_action", emboss=False, icon='REMOVE', text="")
			op_del.action = 'REMOVE'
			op_del.arg = "Remove from list"

		if (context.active_object is not None):
			if ("Lumiere" in str(context.active_object.users_collection)) \
			and len(list(context.scene.collection.children['Lumiere'].objects)) > 0 and context.view_layer.objects.active.name in context.scene.collection.children['Lumiere'].all_objects :

				row = col.row()
				row.prop(light, "name", text="Name", expand=False)
				row.operator("object.export_light", text ="", emboss=False, icon="ADD")

	def invoke(self, context, event):
		context.scene.Lumiere_lights_list.clear()
		my_dict = get_lumiere_dict()

		for key, value in my_dict.items():

		#---Fill the items for the light
			item = context.scene.Lumiere_lights_list.add()
			item.name = key

		return context.window_manager.invoke_popup(self)

# -------------------------------------------------------------------- #
## Parent panel
class POLL_PT_Lumiere:
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"

	@classmethod
	def poll(cls, context):
		if (context.active_object is not None):
			if ("Lumiere" in str(context.active_object.users_collection)) \
			and len(list(context.scene.collection.children['Lumiere'].objects)) > 0 :
				return context.view_layer.objects.active.name in context.scene.collection.children['Lumiere'].all_objects
		else:
			return False

# -------------------------------------------------------------------- #

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
		row.operator("lumiere.ray_operator", text="", emboss=False, icon="MOUSE_LMB_DRAG")
		row.operator("lumiere.export_popup", text="", emboss=False, icon="PRESET")
		# row.separator()

	def draw(self, context):
		light = context.active_object

		layout = self.layout
		layout.use_property_split = True # Active single-column layout
		layout.use_property_decorate = False  # No animation.
		flow = layout.grid_flow(row_major=True, columns=0, even_columns=True, even_rows=False, align=True)
		col = flow.column(align=True)
		col.ui_units_x = 7

		row = col.row(align=True)
		row.enabled = False if (light.Lumiere.ratio \
		and light.Lumiere.light_type in ("Softbox")) else True
		row.prop(light.Lumiere, "energy", text="Energy", slider = True)
		col.prop(light.Lumiere, "light_type", text="Light type")
		row = col.row(align=True)
		row.prop(light.Lumiere, "reflect_angle", text="Position")
		if light.Lumiere.reflect_angle == "2": #"Estimated"
			row.prop(light.Lumiere, "auto_bbox_center", text="", emboss=True, icon='AUTO')

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

	def draw_header_preset(self, context):
		light = context.active_object
		layout = self.layout
		col = layout.column(align=False)
		row = col.row(align=True)
		row.prop(light.Lumiere, "select_only", text="", icon='VIS_SEL_11' if light.Lumiere.select_only else 'VIS_SEL_01')
		row.separator()

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

# -------------------------------------------------------------------- #

class MESH_MATERIALS_PT_Lumiere(POLL_PT_Lumiere, Panel):
	bl_idname = "MESH_MATERIALS_PT_Lumiere"
	bl_label = "Material"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Lumiere"

	@classmethod
	def poll(cls, context):
		if (POLL_PT_Lumiere.poll(context)) :
			return context.view_layer.objects.active.type == 'MESH'

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
		img_texture = mat.node_tree.nodes["Image Texture"]
		invert = mat.node_tree.nodes["Texture invert"].inputs[0]
		falloff = mat.node_tree.nodes["Light Falloff"].inputs[1]

		layout = self.layout
		layout.use_property_split = True # Active single-column layout
		layout.use_property_decorate = False  # No animation.
		flow = layout.grid_flow(row_major=True, columns=0, even_columns=True, even_rows=False, align=True)
		col = layout.column(align=False)
		col = col.column(align=False)
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
			col.prop(light.Lumiere, "img_scale", text="Scale")
			col.prop(invert, "default_value", text="Invert")
			col.prop(img_texture, "extension", text="Repeat")
			col.prop(light.Lumiere, "img_reflect_only", text="Reflection only")


		elif light.Lumiere.material_menu == 'IES':
			row = col.row(align=True)
			row.prop_search(light.Lumiere, "ies_name", bpy.data, "texts", text="", icon="OUTLINER_OB_LIGHT")
			op = row.operator("text.open", text='', icon='FILEBROWSER')
			op.filter_python = False
			op.filter_text = False
			op.filter_folder = False
			col.prop(light.Lumiere, "ies_scale", text="Scale")
			col.prop(light.Lumiere, "ies_reflect_only", text="Reflection only")
		else :
			col.prop(light.Lumiere, "falloff_type", text="Falloff")
			col.prop(falloff, "default_value", text="Smooth")
			col.prop(mat.cycles, "sample_as_light", text='MIS')
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

	def draw_header_preset(self, context):
		light = context.active_object
		layout = self.layout
		col = layout.column(align=False)
		row = col.row(align=True)
		row.prop(light.Lumiere, "select_only", text="", icon='VIS_SEL_11' if light.Lumiere.select_only else 'VIS_SEL_01')
		row.separator()

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
		img_texture = light.data.node_tree.nodes["Image Texture"]
		falloff = light.data.node_tree.nodes["Light Falloff"].inputs[1]

		layout = self.layout
		layout.use_property_split = True # Active single-column layout
		layout.use_property_decorate = False  # No animation.
		flow = layout.grid_flow(row_major=True, columns=0, even_columns=True, even_rows=False, align=True)
		col = flow.column(align=False)
		col.ui_units_x = 7
		col = col.column(align=True)
		if light.Lumiere.material_menu == "Texture":
			row = col.row(align=True)
			row.prop_search(light.Lumiere, "img_name", bpy.data, "images", text="")
			row.operator("image.open",text='', icon='FILEBROWSER')
			col = col.column(align=True)
			row = col.row(align=True)
			row.prop(light.Lumiere, "img_scale", text="Scale")
			row = col.row(align=True)
			row.prop(light.Lumiere, "img_invert", text="Invert")
			row = col.row(align=True)
			row.prop(img_texture, "extension", text="Repeat")

		elif light.Lumiere.material_menu == 'IES':
			row = col.row(align=True)
			row.prop_search(light.Lumiere, "ies_name", bpy.data, "texts", text="", icon="OUTLINER_OB_LIGHT")
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
		else :
			col.prop(light.Lumiere, "falloff_type", text="Falloff")
			col.prop(falloff, "default_value", text="Smooth")
			col.prop(light.data.cycles, "cast_shadow", text='Shadow')
			col.prop(light.data.cycles, "use_multiple_importance_sampling", text='MIS')
			col.prop(light.cycles_visibility, "diffuse", text='Diffuse')
			col.prop(light.cycles_visibility, "glossy", text='Specular')
		col = flow.column(align=True)
		col.ui_units_x = 7


# -------------------------------------------------------------------- #
## Operator
class OPERATOR_PT_Lumiere(Panel):
	bl_idname = "OPERATOR_PT_Lumiere"
	bl_label = "Lumiere"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Lumiere"

	@classmethod
	def poll(cls, context):
		if (context.active_object is not None):
			if ("Lumiere" in str(context.active_object.users_collection)) \
			and len(list(context.scene.collection.children['Lumiere'].objects)) > 0 :
				return context.view_layer.objects.active.name not in context.scene.collection.children['Lumiere'].all_objects
		return True


	def draw_header_preset(self, context):
		layout = self.layout
		col = layout.column(align=False)
		row = col.row(align=True)
		row.operator("lumiere.export_popup", text="", emboss=False, icon="PRESET")

	def draw(self, context):

		layout = self.layout
		layout.use_property_split = True # Active single-column layout
		layout.use_property_decorate = False  # No animation.
		flow = layout.grid_flow(row_major=True, columns=0, even_columns=True, even_rows=False, align=True)
		col = flow.column(align=True)
		col.ui_units_x = 7
		col.operator("lumiere.ray_operator", text="CREATE", icon='BLANK1')

# -------------------------------------------------------------------- #
## Register


classes = [
	CUSTOM_OT_actions,
	ALL_LIGHTS_UL_list,
	LUMIERE_OT_ExportPopup,
	MAIN_PT_Lumiere,
	MESH_OPTIONS_PT_Lumiere,
	MESH_MATERIALS_PT_Lumiere,
	LAMP_OPTIONS_PT_Lumiere,
	LAMP_MATERIALS_PT_Lumiere,
	OPERATOR_PT_Lumiere,
	LumiereObj,
	LightsProp,
	]


def register():
	from bpy.utils import register_class
	for cls in classes:
		print("CLASSE: ", cls)
		register_class(cls)
	bpy.types.Object.Lumiere = bpy.props.PointerProperty(type=LumiereObj)
	bpy.types.Scene.Lumiere_lights_list = bpy.props.CollectionProperty(type=LightsProp)
	bpy.types.Scene.Lumiere_lights_list_index = bpy.props.IntProperty(name = "Index", default = 0)
	# bpy.types.Scene.Lumiere_lights_list_index = bpy.props.IntProperty(name = "Index", default = 0, update=seListIndexFunction)


def unregister():
	from bpy.utils import unregister_class
	for cls in reversed(classes):
		unregister_class(cls)
	del bpy.types.Object.Lumiere
	del bpy.types.Scene.Lumiere_lights_list
	del bpy.types.Scene.Lumiere_lights_list_index
