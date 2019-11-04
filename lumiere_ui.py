import bpy
import bmesh
import time
from bpy.types import Panel, Operator, Menu
from bl_operators.presets import AddPresetBase
from bl_ui.utils import PresetPanel

from .lumiere_utils import (
	get_lumiere_dict,
	update_lumiere_dict,
	get_mat_name,
	cartesian_coordinates,
	getSunPosition,
	update_sky,
	)

from .lumiere_materials import (
	update_mat,
	softbox_mat,
	lamp_mat,
	update_lamp,
	create_world,
	update_world,
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

	light = bpy.data.objects[self.id_data.name]

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
				light.Lumiere.scale_x = light.Lumiere.scale_x
				update_mat(self, context)
		else:
			if values['old_type'] != context.object.data.type:
				context.object.data.type = values['old_type']
				light.Lumiere.scale_x = light.Lumiere.scale_x

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
		light.Lumiere.scale_x = light.Lumiere.scale_x

		update_lamp(light)

		bpy.data.meshes.remove(mesh, do_unlink=True, do_id_user=True, do_ui_user=True)

	# Set default position to "Estimated"
	light.Lumiere.reflect_angle = "Estimated"

	del lumiere_dict[values['old_name']]

# -------------------------------------------------------------------- #
def update_softbox_rounding(self, context):
	"""Update the rounding value of the softbox"""
	light = bpy.data.objects[self.id_data.name]
	light.modifiers["Bevel"].width = light.Lumiere.softbox_rounding

# -------------------------------------------------------------------- #
def update_texture_scale(self, context):
	"""Update the texture scale"""
	light = bpy.data.objects[self.id_data.name]

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
	light = bpy.data.objects[self.id_data.name]
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
	light = bpy.data.objects[self.id_data.name]

	r = light.Lumiere.range
	# θ theta is azimuthal angle, the angle of the rotation around the z-axis (aspect)
	theta = radians(light.Lumiere.rotation)
	# φ phi is the polar angle, rotated down from the positive z-axis (slope)
	phi = radians(light.Lumiere.pitch)

	light.location = cartesian_coordinates(r, theta, phi, light.Lumiere.hit)

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
def update_hour(self,context):
	"""Update the scale xy of the light"""
	light = bpy.data.objects[self.id_data.name]

	getSunPosition(light, localTime = light.Lumiere.hour, latitude = light.Lumiere.latitude, longitude = light.Lumiere.longitude, northOffset = 0.00, utcZone = 0, month = light.Lumiere.month, day = light.Lumiere.day, year = light.Lumiere.year, distance = light.Lumiere.range)

	if light.Lumiere.sky_texture:
		update_sky(self, context)

# -------------------------------------------------------------------- #
def update_lock_scale(self,context):
	"""Update the scale xy of the light"""
	light = bpy.data.objects[self.id_data.name]

	if light.Lumiere.lock_scale:
		if light.type == 'MESH':
			light.scale[0] = light.scale[1] = light.Lumiere.scale_xy
			light.Lumiere.scale_x = light.Lumiere.scale_y = light.Lumiere.scale_xy
		elif light.data.type == "AREA" and light.data.shape not in ('SQUARE', 'DISK'):
			light.scale[0] = light.scale[1] = 1
			light.Lumiere.scale_x = light.Lumiere.scale_y = light.Lumiere.scale_xy
			light.data.size = light.data.size_y = light.Lumiere.scale_xy*2

	update_texture_scale(self, context)

# -------------------------------------------------------------------- #
def update_scale_xy(self,context):
	"""Update the scale xy of the light"""
	light = bpy.data.objects[self.id_data.name]

	if light.type == 'MESH':
		light.scale[0] = light.scale[1] = light.Lumiere.scale_xy
		light.Lumiere.scale_x = light.Lumiere.scale_y = light.Lumiere.scale_xy
		if light.Lumiere.ratio:
			light.Lumiere.energy = light.Lumiere.save_energy / (light.scale[0] * light.scale[1])

	else:
		if light.data.type == "SUN":
			light.data.angle = light.Lumiere.scale_xy
		elif light.data.type == "AREA":
			light.scale[0] = light.scale[1] = 1
			light.Lumiere.scale_x = light.Lumiere.scale_y = light.Lumiere.scale_xy
			light.data.size = light.data.size_y = light.Lumiere.scale_xy*2
		else:
			light.data.shadow_soft_size = light.Lumiere.scale_xy


	if light.scale[0] < 0.001:
		light.scale[0] = 0.001
	if light.scale[1] < 0.001:
		light.scale[1] = 0.001

# -------------------------------------------------------------------- #
def update_scale(self,context):
	"""Update the x dimension of the light"""
	light = bpy.data.objects[self.id_data.name]

	if light.type == 'MESH':
		light.scale[0] = light.Lumiere.scale_x*2
		light.scale[1] = light.Lumiere.scale_y*2
		update_texture_scale(self, context)
		if light.Lumiere.ratio:
			light.Lumiere.energy = light.Lumiere.save_energy / (light.scale[0] * light.scale[1])

	else:
		if light.data.type == "AREA":
			if light.data.shape not in ('SQUARE', 'DISK'):
				light.scale[0] = light.scale[1] = 1
				light.data.size = light.Lumiere.scale_x*2
				light.data.size_y = light.Lumiere.scale_y*2
			else:
				light.scale[0] = light.scale[1] = 1
				# light.Lumiere.scale_x = light.Lumiere.scale_y = light.Lumiere.scale_xy
				light.data.size = light.data.size_y = light.Lumiere.scale_xy*2
		else:
			light.data.shadow_soft_size = light.Lumiere.scale_xy


	if light.scale[0] < 0.001:
		light.scale[0] = 0.001
	if light.scale[1] < 0.001:
		light.scale[1] = 0.001

# -------------------------------------------------------------------- #
def update_range(self,context):
	"""Update the distance of the light from the object target"""
	light = bpy.data.objects[self.id_data.name]

	if light.Lumiere.light_type == "Sun" and light.Lumiere.reflect_angle == "Solar angle":
		update_hour(self, context)
	else:
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
def update_select_only(self, context):
	"""Show only this light and hide all the other"""
	light = bpy.data.objects[self.id_data.name]

	# Active only the visible light
	context.view_layer.objects.active = light

	# Deselect and hide all the lights in the scene and show the active light
	bpy.ops.object.select_all(action='DESELECT')
	for ob in context.scene.collection.children['Lumiere'].objects:
		if ob.name != light.name:
			if light.Lumiere.select_only:
				ob.hide_viewport = True
			else:
				ob.hide_viewport = False

	# Select only the visible light
	light.select_set(True)

# -------------------------------------------------------------------- #
def update_reflect_angle(self, context):
	"""Update the reflect angle position"""
	light = bpy.data.objects[self.id_data.name]

	if light.Lumiere.light_type == "Sun" and light.Lumiere.reflect_angle == "Solar angle":
		light.Lumiere.blackbody = 5300
		update_hour(self, context)

# -------------------------------------------------------------------- #
def update_sky_texture(self, context):
	"""Add a sky texture for the solar angle"""
	light = bpy.data.objects[self.id_data.name]

	if light.Lumiere.sky_texture:
		create_world(self, context)
		update_world()
		if light.Lumiere.light_type == "Sun" and light.Lumiere.reflect_angle == "Solar angle":
			light.Lumiere.energy = 3
			light.Lumiere.scale_xy = 0.05
			light.Lumiere.color_type = "Blackbody"
			update_hour(self,context)
		else:
			update_sky(self, context)
	else:
		bpy.data.worlds.remove(bpy.data.worlds['Lumiere_world'])


# -------------------------------------------------------------------- #
## Items

def items_color_type(self, context):
	"""Define the different items for the color choice of lights"""

	if bpy.data.objects[self.id_data.name].type == "MESH":
		items = {
				("Color", "Color", "", 0),
				("Linear", "Linear", "", 1),
				("Blackbody", "Blackbody", "", 2),
				("Spherical", "Spherical", "", 3),
				("Reflector", "Reflector", "", 4),
				}
	else:
		items = {
				("Color", "Color", "", 0),
				("Gradient", "Gradient", "", 1),
				("Blackbody", "Blackbody", "", 2),
				}

	return items

def items_reflect_angle(self, context):
	"""Define the different items for the color choice of lights"""
	light = bpy.data.objects[self.id_data.name]

	if light.Lumiere.light_type == "Sun":
		items = {
				("Estimated", "Estimated", "", 0),
				("Accurate", "Accurate", "", 1),
				("Normal", "Normal", "", 2),
				("Solar angle", "Solar angle", "", 3),
				}
	else:
		items = {
				("Estimated", "Estimated", "", 0),
				("Accurate", "Accurate", "", 1),
				("Normal", "Normal", "", 2),
				}

	return items

# -------------------------------------------------------------------- #
## Preferences
class LumiereAddonPreferences(bpy.types.AddonPreferences):
	"""Preferences for Lumiere"""

	bl_idname = __package__

#---Activate gizmos
	gizmos : BoolProperty(
							   name="Gizmos",
							   description="Activate the gizmos on the lights",
							   default=True)

#---Activate render pause
	render_pause : BoolProperty(
							   name="Render Pause",
							   description="Pause the render during interactive to save time",
							   default=False)

	def draw(self, context):
		layout = self.layout
		layout.prop(self, "gizmos")
		layout.prop(self, "render_pause")

# -------------------------------------------------------------------- #
class LightsProp(bpy.types.PropertyGroup):
	num : StringProperty(
						name="Number",
						description="Number of lights (useful for group)",
						)
	name : StringProperty(
						name="Name",
						description="Name of the light or group",
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
						  default=.5,
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
						  default=.5,
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
						  default=.5,
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
						  items = items_reflect_angle,
						  update = update_reflect_angle,
						  default=None,
						  )

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

#---Temperature of the light
	blackbody : FloatProperty(
								 name = "Blackbody",
								 description="Temperature of the light",
								 precision=1,
								 update=update_mat,
								 )

#---List of color options
	color_type : EnumProperty(name="Colors",
								description="Colors options:\n"+
								"\u2022 Gradient: Gradient color emission\n"+
								"\u2022 Color: Single color emission\n"+
								"\u2022 Reflector: No emission\n"+
								"\u2022 Blackbody: Spectrum of light emitted by any heated object\n"+
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
								"\u2022 World: Sky texture contribution\n"+
								"Selected",
								items = {
										("Color", "Color", "Color", "COLOR", 0),
										("Texture", "Texture", "Texture", "FILE_IMAGE", 1),
										("IES", "IES", "IES","OUTLINER_OB_LIGHT", 2),
										("Options", "Options", "Options","PREFERENCES", 3),
										("World", "World", "World","WORLD", 4),
										},
								default=None,
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

#---Lock image scale on x and y
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
							  min=0,
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
							   default=False,
							   update=update_select_only)

#---Sun position: Latitude
	latitude : FloatProperty(
						   name="Latitude",
						   min=-89.9, max=89.9,
						   default=48.87,
						   update=update_hour)

#---Sun position: Longitude
	longitude : FloatProperty(
						   name="Longitude",
						   min=-180, max=180,
						   default=2.67,
						   update=update_hour)

#---Sun position: Month
	month : IntProperty(
						   name="Month",
						   min=1, max=12,
						   default=time.localtime().tm_mon,
						   update=update_hour)

#---Sun position: Day
	day : IntProperty(
						   name="Day",
						   min=1, max=31,
						   default=time.localtime().tm_mday,
						   update=update_hour)

#---Sun position: Year
	year : IntProperty(
						   name="Year",
						   min=1800, max=4000,
						   default=time.localtime().tm_year,
						   update=update_hour)

#---Sun position: Hour
	hour : FloatProperty(
						   name="Hour",
						   min=0, max=23.59,
						   default=time.localtime().tm_hour,
						   update=update_hour)

#---Use sky texture with the solar angle.
	sky_texture : BoolProperty(name="Sky texture",
							   description="Use sky texture with the solar angle",
							   default=False,
							   update=update_sky_texture)

# -------------------------------------------------------------------- #
class ALL_LIGHTS_UL_list(bpy.types.UIList):
	def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
		object = data
		if self.layout_type in {'DEFAULT', 'COMPACT'}:
			split = layout.split(factor=0.2)
			split.label(text="%d" % (index))
			if int(item.num) > 1:
				split.prop(item, "name", text="", toggle=False, emboss=False, icon_value=icon, icon="GROUP")
			else:
				split.prop(item, "name", text="", toggle=False, emboss=False, icon_value=icon, icon="LIGHT")
			split.prop(item, "num", text="", toggle=False, emboss=False, icon_value=icon, icon="BLANK1")
		elif self.layout_type in {'GRID'}:
			pass

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
		row.operator("lumiere.preset_popup", text="", emboss=False, icon="PRESET")

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
		if light.Lumiere.reflect_angle == "Estimated":
			row.prop(light.Lumiere, "auto_bbox_center", text="", emboss=True, icon='AUTO')

# -------------------------------------------------------------------- #
## Softbox Sub panel
class MESH_OPTIONS_PT_Lumiere(POLL_PT_Lumiere, Panel):
	bl_idname = "MESH_OPTIONS_PT_Lumiere"
	bl_label = "Options"
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
		mat = get_mat_name(light)

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
		mat = get_mat_name(light)
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
			elif light.Lumiere.color_type == 'Blackbody':
				col.prop(light.Lumiere, "blackbody", text="Temperature", expand=True)

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

		elif light.Lumiere.material_menu == 'Options':
			col.prop(light.Lumiere, "falloff_type", text="Falloff")
			col.prop(falloff, "default_value", text="Smooth")
			col.prop(mat.cycles, "sample_as_light", text='MIS')

		else :
			col.prop(light.Lumiere, "sky_texture", text="Sky texture")
			if light.Lumiere.sky_texture:
				world = bpy.data.worlds['Lumiere_world']
				sky_color = world.node_tree.nodes["Sky Texture"]
				strength = world.node_tree.nodes["Background"].inputs[1]
				col.prop(sky_color, "turbidity", text="Turbidity")
				col.prop(sky_color, "ground_albedo", text="Albedo")
				col.prop(strength, "default_value", text="Strength")

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
		mat = get_mat_name(light)

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

		if light.data.type == "SUN" and light.Lumiere.reflect_angle == "Solar angle":
			col.prop(light.Lumiere, "scale_xy", text="Shadow")
			col.prop(light.Lumiere, "hour", text="Hour")
			col.prop(light.Lumiere, "latitude", text="Latitude")
			col.prop(light.Lumiere, "longitude", text="Longitude")
			col.prop(light.Lumiere, "month", text="Month")
			col.prop(light.Lumiere, "day", text="Day")
			col.prop(light.Lumiere, "year", text="Year")
		else:
			if light.data.type == "AREA":
				col.prop(light.data, "shape", text="Shape")
				col = col.column(align=True)
				row = col.row(align=True)
				if light.data.shape in ('SQUARE', 'DISK'):
					row.prop(light.Lumiere, "scale_xy", text="Scale xy")
				else:
					if light.Lumiere.lock_scale:
						row.prop(light.Lumiere, "scale_xy", text="Scale xy")
						row.prop(light.Lumiere, "lock_scale", text="", emboss=False, icon='DECORATE_LOCKED')

					else:
						row = col.row(align=True)
						row.prop(light.Lumiere, "scale_x", text="Scale x")
						row.prop(light.Lumiere, "lock_scale", text="", emboss=False, icon='DECORATE_UNLOCKED')
						row = col.row(align=True)
						row.prop(light.Lumiere, "scale_y", text="Scale y")
						row.prop(light.Lumiere, "lock_scale", text="", emboss=False, icon='DECORATE_UNLOCKED')

			elif light.data.type == "SPOT":
				col.prop(light.data, "spot_size", text="Cone Size")
				col.prop(light.data, "spot_blend", text="Cone Blend")
				col.prop(light.Lumiere, "scale_xy", text="Shadow")

			elif light.data.type == "POINT":
				col.prop(light.Lumiere, "scale_xy", text="Shadow")

			elif light.data.type == "SUN":
				col.prop(light.Lumiere, "scale_xy", text="Shadow")


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
				col = col.column(align=False)
				col.prop(light.Lumiere, "light_color", text="Color")
			elif light.Lumiere.color_type == 'Blackbody':
				col = col.column(align=False)
				col.prop(light.Lumiere, "blackbody", text="Temperature")

			elif light.Lumiere.color_type == 'Gradient':
				col.template_color_ramp(colramp, "color_ramp", expand=True)

		elif light.Lumiere.material_menu == 'Options':
			col.prop(light.Lumiere, "falloff_type", text="Falloff")
			col.prop(falloff, "default_value", text="Smooth")
			col.prop(light.data.cycles, "cast_shadow", text='Shadow')
			col.prop(light.data.cycles, "use_multiple_importance_sampling", text='MIS')
			col.prop(light.cycles_visibility, "diffuse", text='Diffuse')
			col.prop(light.cycles_visibility, "glossy", text='Specular')

		else :
			col.prop(light.Lumiere, "sky_texture", text="Sky texture")
			if light.Lumiere.sky_texture:
				world = bpy.data.worlds['Lumiere_world']
				sky_color = world.node_tree.nodes["Sky Texture"]
				strength = world.node_tree.nodes["Background"].inputs[1]
				col.prop(sky_color, "turbidity", text="Turbidity")
				col.prop(sky_color, "ground_albedo", text="Albedo")
				col.prop(strength, "default_value", text="Strength")

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
		row.operator("lumiere.preset_popup", text="", emboss=False, icon="PRESET")

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
	ALL_LIGHTS_UL_list,
	MAIN_PT_Lumiere,
	MESH_OPTIONS_PT_Lumiere,
	MESH_MATERIALS_PT_Lumiere,
	LAMP_OPTIONS_PT_Lumiere,
	LAMP_MATERIALS_PT_Lumiere,
	OPERATOR_PT_Lumiere,
	LumiereObj,
	LightsProp,
	LumiereAddonPreferences,
	]


def register():
	from bpy.utils import register_class
	for cls in classes:
		register_class(cls)
	bpy.types.Object.Lumiere = bpy.props.PointerProperty(type=LumiereObj)
	bpy.types.Scene.Lumiere_lights_list = bpy.props.CollectionProperty(type=LightsProp)
	bpy.types.Scene.Lumiere_lights_list_index = bpy.props.IntProperty(name = "Index", default = 0)


def unregister():
	from bpy.utils import unregister_class
	for cls in reversed(classes):
		unregister_class(cls)
	del bpy.types.Object.Lumiere
	del bpy.types.Scene.Lumiere_lights_list
	del bpy.types.Scene.Lumiere_lights_list_index
