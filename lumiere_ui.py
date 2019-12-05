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
		light = create_lamp(type = new_type, name = values['old_name'])
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
def update_rotation_pitch(self,context):
	"""Update the location and rotation of the sun based on time, latitude and longitude"""
	light = bpy.data.objects[self.id_data.name]

	update_spherical_coordinate(self,context,light=bpy.data.objects[self.id_data.name])

	# Update the shadow location
	if context.scene.is_running == False:
		light.parent.hide_viewport = True
		result, hit_location, _, _, _, _ = context.scene.ray_cast(context.view_layer, light.location, (Vector(light.Lumiere.hit) - light.location))

		if result:
			light.Lumiere.shadow = hit_location
		else:
			light.Lumiere.shadow = (0,0,0)
		light.parent.hide_viewport = False


# -------------------------------------------------------------------- #
def update_link_to_light(self,context):
	"""Update light position if light is link or not """

	if context.scene.Lumiere.link_to_light:
		if context.scene.Lumiere.env_type == "Sky":
			update_env_hour(self,context)
		context.scene.Lumiere.link_to_light.Lumiere.lock_img = True
		context.scene.Lumiere.save_linked_light = context.scene.Lumiere.link_to_light
	else :
		context.scene.Lumiere.save_linked_light.Lumiere.lock_img = False
		update_spherical_coordinate(self,context,light=context.scene.Lumiere.save_linked_light)

# -------------------------------------------------------------------- #
def update_spherical_coordinate(self, context, light=None):
	"""Rotate the light vertically (pitch) and horizontally around the targeted point"""

	if light is None:
		light = bpy.data.objects[self.id_data.name]

	r = light.Lumiere.range
	# θ theta is azimuthal angle, the angle of the rotation around the z-axis (aspect)
	theta = radians(light.Lumiere.rotation)
	# φ phi is the polar angle, rotated down from the positive z-axis (slope)
	phi = radians(light.Lumiere.pitch)

	light.location = cartesian_coordinates(r, theta, phi, light.Lumiere.hit)
	
	if context.scene.is_running :
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
def update_light_hour(self,context):
	"""Update the location and rotation of the sun based on time, latitude and longitude"""
	if context.scene.Lumiere.link_to_light is not None:
		light = context.scene.Lumiere.link_to_light
		light.Lumiere.light_mode = "Sky"

		light.location , light.rotation_euler = getSunPosition(localTime = context.scene.Lumiere.env_hour, latitude = context.scene.Lumiere.env_latitude, longitude = context.scene.Lumiere.env_longitude, northOffset = 0.00, utcZone = 0, month = context.scene.Lumiere.env_month, day = context.scene.Lumiere.env_day, year = context.scene.Lumiere.env_year, distance = light.Lumiere.range)

		update_sky(self, context, light.rotation_euler, light)

# -------------------------------------------------------------------- #
def update_env_hour(self,context):
	"""Update the location and rotation of the sun based on time, latitude and longitude"""

	if context.scene.Lumiere.link_to_light is not None:
		update_light_hour(self,context)
	else:
		location , rotation = getSunPosition(localTime = context.scene.Lumiere.env_hour, latitude = context.scene.Lumiere.env_latitude, longitude = context.scene.Lumiere.env_longitude, northOffset = 0.00, utcZone = 0, month = context.scene.Lumiere.env_month, day = context.scene.Lumiere.env_day, year = context.scene.Lumiere.env_year, distance = 1)

		update_sky(self, context, rotation)

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

	if light.Lumiere.light_mode == "Sky":
		update_light_hour(self, context)
	else:
		light_loc = Vector(light.Lumiere.hit) + (Vector(light.Lumiere.direction) * light.Lumiere.range)
		light.location = Vector((light_loc[0], light_loc[1], light_loc[2]))
		track  = light.location - Vector(light.Lumiere.hit)
		rotaxis = (track.to_track_quat('Z','Y'))
		light.rotation_euler = rotaxis.to_euler()

# -------------------------------------------------------------------- #
def target_poll(self, object):
	"""Target only this object"""

	if object.name not in bpy.context.scene.collection.children['Lumiere'].all_objects:
		return object

# -------------------------------------------------------------------- #
def link_light_poll(self, object):
	"""Link only this light"""

	if object.name in bpy.context.scene.collection.children['Lumiere'].all_objects:
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

	if light.Lumiere.light_mode == "Sky":
		light.Lumiere.blackbody = 5300
		update_light_hour(self, context)

# -------------------------------------------------------------------- #
def update_env_texture_hdr(self, context):
	"""Add a sky texture for the solar angle"""
	light = context.object

	if context.scene.Lumiere.env_hdr_name == "":
		context.scene.Lumiere.link_hdr_to_light = False
		if context.scene.Lumiere.env_reflect_name == "":
			context.scene.Lumiere.link_to_light = None

	if context.scene.Lumiere.link_to_light and context.scene.Lumiere.link_hdr_to_light:
		light = context.scene.Lumiere.link_to_light

		diff = context.scene.Lumiere.env_hdr_rotation - context.scene.Lumiere.env_hdr_to_pxl
		if diff < -360:
			light.Lumiere.rotation = diff + 360
		elif diff > 360:
			light.Lumiere.rotation = diff - 360
		else:
			light.Lumiere.rotation = diff

		if context.scene.Lumiere.env_reflect_name != "":
			context.scene.Lumiere.env_reflect_rotation = context.scene.Lumiere.env_reflect_to_pxl - 90 + degrees(light.rotation_euler.z)
	update_world(self, context)

# -------------------------------------------------------------------- #
def update_env_texture_reflect(self, context):
	"""Add a sky texture for the solar angle"""

	if context.scene.Lumiere.env_reflect_name == "":
		context.scene.Lumiere.link_reflect_to_light = False
		if context.scene.Lumiere.env_hdr_name == "":
			context.scene.Lumiere.link_to_light = None

	if context.scene.Lumiere.link_to_light and context.scene.Lumiere.link_reflect_to_light:
		light = context.scene.Lumiere.link_to_light
		diff = context.scene.Lumiere.env_reflect_rotation - context.scene.Lumiere.env_reflect_to_pxl
		if diff < -360:
			light.Lumiere.rotation = diff + 360
		elif diff > 360:
			light.Lumiere.rotation = diff - 360
		else:
			light.Lumiere.rotation = diff
	update_world(self, context)

# -------------------------------------------------------------------- #
def update_env_type(self, context):
	"""Add a sky texture for the solar angle"""

	if not bpy.data.worlds.get("Lumiere_world"):
		create_world(self, context)

	if context.scene.Lumiere.env_type == "Sky":
		update_env_hour(self,context)
		update_world(self, context)

	elif context.scene.Lumiere.env_type == "Texture":
		update_world(self, context)

	elif context.scene.Lumiere.env_type == "None":
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
		if bpy.data.objects[self.id_data.name].Lumiere.light_type == "Sun":
			items = {
					("Color", "Color", "", 0),
					("Blackbody", "Blackbody", "", 1),
					}
		else:
			items = {
					("Color", "Color", "", 0),
					("Blackbody", "Blackbody", "", 1),
					("Gradient", "Gradient", "", 2),
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
## Snene Properties
class LumiereScn(bpy.types.PropertyGroup):
#---Main menu options
	main_menu : EnumProperty(name="Main menu",
								description="Lighting options:\n"+
								"\u2022 Light: Light options\n"+
								"\u2022 World: World options\n"+
								"Selected",
								items = {
										("Light", "Light", "Light", "LIGHT", 0),
										("World", "World", "World","WORLD", 1),
										},
								default=None,
								)

#---List of environment options
	env_type : EnumProperty(name="Environment",
								description="Environment options:\n"+
								"\u2022 Sky texture: Use the internal sky texture for background\n"+
								"\u2022 Image texture: Use HDRI for background\n"+
								"Selected",
								items = {
										("Sky", "Sky", "Sky", 0),
										("Texture", "Environment", "Texture", 1),
										("None", "None", "None", 2),
										},
								default = "None",
								update=update_env_type,
								)
# TEXTURE

#---Name of the light the environment is linked to
	link_to_light : PointerProperty(
							  type=bpy.types.Object,
							  name="Name of the light the environment is linked to",
							  poll=link_light_poll,
							  update=update_link_to_light,
							  )
# HDRI
#---Name of the environment image texture
	env_hdr_name : StringProperty(
							  name="Name of the environment image texture",
							  update=update_env_texture_hdr,
							  )

#---Rotation of the environment image on Z axis.
	env_hdr_rotation : FloatProperty(
								  name="HDRI rotation",
								  description="Rotation of the environment image on Z axis.",
								  min= -360, max= 360,
								  default=0,
								  update=update_env_texture_hdr,
								  )

#---Rotation of the environment image on Z axis.
	env_hdr_to_pxl : FloatProperty(
								  name="HDRI to pixel rotation",
								  description="Rotation of the environment image on Z axis.",
								  min= -360, max= 360,
								  default=0,
								  )

#---Lock the light to the Hdr image.
	link_hdr_to_light : BoolProperty(name="Toggle lock Hdr",
							   description="Lock the light to the Hdr image",
							   default=False,
							   # update=update_env_texture_reflect,
							   )

# REFLECTION
#---Use another texture for reflection.
	env_reflect_toggle : BoolProperty(name="Toggle reflection",
							   description="Use another image texture for reflection",
							   default=False,
							   update=update_env_texture_reflect)

#---Name of the background image texture
	env_reflect_name : StringProperty(
							  name="Name of the background / reflection image texture",
							  update=update_env_texture_reflect,
							  )

#---Rotation of the reflection image on Z axis.
	env_reflect_rotation : FloatProperty(
								  name="Reflection rotation",
								  description="Rotation of the reflection image on Z axis.",
								  min= -360, max= 360,
								  default=0,
								  update=update_env_texture_reflect,
								  )

#---Rotation of the environment image on Z axis.
	env_reflect_to_pxl : FloatProperty(
								  name="HDRI to pixel rotation",
								  description="Rotation of the environment image on Z axis.",
								  min= -360, max= 360,
								  default=0,
								  )


#---Lock the light to the reflection image.
	link_reflect_to_light : BoolProperty(name="Toggle lock Hdr",
							   description="Lock the light to the Hdr image",
							   default=False,
							   )

# SKY
#---Sun contribution
	env_sun_contrib : FloatProperty(
						   name="Sun",
						   min=0, max=100,
						   default=0,
						   update=update_world)

#---Sun size
	env_sun_size : FloatProperty(
						   name="Sun size",
						   min=0, max=100,
						   default=0,
						   update=update_world)

#---Sky contribution
	env_sky_contrib : FloatProperty(
						   name="Sky",
						   min=0, max=1000,
						   default=5,
						   update=update_world)

#---Sun position: Latitude
	env_latitude : FloatProperty(
						   name="Latitude",
						   min=-89.9, max=89.9,
						   default=48.87,
						   update=update_env_hour)

#---Sun position: Longitude
	env_longitude : FloatProperty(
						   name="Longitude",
						   min=-180, max=180,
						   default=2.67,
						   update=update_env_hour)

#---Sun position: Month
	env_month : IntProperty(
						   name="Month",
						   min=1, max=12,
						   default=time.localtime().tm_mon,
						   update=update_env_hour)

#---Sun position: Day
	env_day : IntProperty(
						   name="Day",
						   min=1, max=31,
						   default=time.localtime().tm_mday,
						   update=update_env_hour)

#---Sun position: Year
	env_year : IntProperty(
						   name="Year",
						   min=1800, max=4000,
						   default=time.localtime().tm_year,
						   update=update_env_hour)

#---Sun position: Hour
	env_hour : FloatProperty(
						   name="Hour",
						   min=0, max=23.59,
						   subtype='TIME',
						   unit='TIME',
						   default=time.localtime().tm_hour,
						   update=update_env_hour,
						   )

#---List of lights
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
								)

#---Name of the light linked before unlock
	save_linked_light : PointerProperty(
							  type=bpy.types.Object,
							  name="Name of the light linked before unlock",
							  )
# -------------------------------------------------------------------- #
## Properties
class LumiereObj(bpy.types.PropertyGroup):

#---Strength of the light
	energy : FloatProperty(
						   name="Strength",
						   description="Strength of the light",
						   min=0.001, max=900000000000.0,
						   soft_min=0.001, soft_max=100.0,
						   default=10,
						   step=20000,
						   precision=2,
						   # subtype='DISTANCE',
						   unit='POWER',
						   update=update_mat
						   )

#---Rotate the light around Z
	rotation : FloatProperty(
						  name="Rotation",
						  description="Rotate the light horizontally around the target",
						  min=-360,
						  max=360,
						  # min=-0.1,
						  # max=360.1,
						  step=20,
						  update=update_rotation_pitch,
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
						  update=update_rotation_pitch,
						  )

#---Scale the light
	scale_xy : FloatProperty(
						  name="Scale",
						  description="Scale the light",
						  min=0.0001, max=100000,
						  soft_min=0.001, soft_max=100.0,
						  unit='LENGTH',
						  # subtype='DISTANCE',
						  step=.001,
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
						  unit='LENGTH',
						  subtype='DISTANCE',
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
						  unit='LENGTH',
						  subtype='DISTANCE',
						  step=1,
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
						  items = (
						  ("Estimated", "Estimated", "", 0),
						  ("Accurate", "Accurate", "", 1),
						  ("Normal", "Normal", "", 2),
						  ),
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

#---List of modes the light can be linked to
	light_mode : EnumProperty(name="Light mode",
								items = {
										("Sky", "Sky", "Sky", 0),
										("Texture", "Texture", "Texture", 1),
										("None", "None", "None", 2),
										},
								default = "None",
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
								"Selected",
								items = {
										("Color", "Color", "Color", "COLOR", 0),
										("Texture", "Texture", "Texture", "FILE_IMAGE", 1),
										("IES", "IES", "IES","OUTLINER_OB_LIGHT", 2),
										("Options", "Options", "Options","PREFERENCES", 3),
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

#---Vector of the shadow
	shadow : FloatVectorProperty(
							name="Shadow",
							description="Vector of the shadow",
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

#---Lock/Unlock the light to the environment
	lock_img : BoolProperty(name="Lock/Unlock the light to the environment",
							)

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
		if context.scene.Lumiere.main_menu=="Light":
			if (context.active_object is not None):
				if ("Lumiere" in str(context.active_object.users_collection)) \
				and len(list(context.scene.collection.children['Lumiere'].objects)) > 0 :
					return context.view_layer.objects.active.name in context.scene.collection.children['Lumiere'].all_objects
			else:
				return False
		else:
			return True

# -------------------------------------------------------------------- #
class WORLD_PT_Lumiere_hdr_link(Panel):
	bl_label = "Link options"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'HEADER'

	@classmethod
	def poll(cls, context):
		return context.scene.Lumiere.env_hdr_name != "" and context.scene.Lumiere.link_to_light

	def draw(self, context):
		layout = self.layout
		scene = context.scene
		col = layout.column()

		if context.scene.Lumiere.link_to_light:
			light = context.scene.Lumiere.link_to_light

			if scene.Lumiere.env_hdr_name != "":
				op = col.operator("lumiere.select_pixel", text ='Align to Env', icon='EYEDROPPER')
				op.light = light.name
				op.img_name = context.scene.Lumiere.env_hdr_name
				op.img_type = "Hdr"
				op.img_size_x = bpy.data.images[context.scene.Lumiere.env_hdr_name].size[0]
				op.img_size_y = bpy.data.images[context.scene.Lumiere.env_hdr_name].size[1]

# -------------------------------------------------------------------- #
class WORLD_PT_Lumiere_refl_link(Panel):
	bl_label = "Link options"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'HEADER'

	@classmethod
	def poll(cls, context):
		return context.scene.Lumiere.env_reflect_name != "" and context.scene.Lumiere.link_to_light

	def draw(self, context):
		layout = self.layout
		scene = context.scene
		col = layout.column()
		if context.scene.Lumiere.link_to_light:
			light = context.scene.Lumiere.link_to_light

			if scene.Lumiere.env_reflect_name != "":
				op = col.operator("lumiere.select_pixel", text ='Align to Reflect', icon='EYEDROPPER')
				op.light = light.name
				op.img_name = context.scene.Lumiere.env_reflect_name
				op.img_type = "Reflect"
				op.img_size_x = bpy.data.images[context.scene.Lumiere.env_reflect_name].size[0]
				op.img_size_y = bpy.data.images[context.scene.Lumiere.env_reflect_name].size[1]

# -------------------------------------------------------------------- #
class WORLD_PT_Lumiere_hdr_options(Panel):
	bl_label = "Environment texture options"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'HEADER'

	def draw(self, context):
		layout = self.layout
		# layout.use_property_split = True
		scene = context.scene
		world = bpy.data.worlds['Lumiere_world']
		env_hdr_bright = world.node_tree.nodes["Bright/Contrast"].inputs[1]
		env_hdr_contrast = world.node_tree.nodes["Bright/Contrast"].inputs[2]
		env_hdr_gamma = world.node_tree.nodes["Gamma"].inputs[1]
		env_hdr_hue = world.node_tree.nodes["Hdr hue"].inputs[0]
		env_hdr_sat = world.node_tree.nodes["Hdr hue"].inputs[1]
		exposure = world.node_tree.nodes['Hdr exposure value'].outputs[0]

		col = layout.column()
		col.prop(env_hdr_bright, "default_value", text="Brightness")
		col.prop(env_hdr_contrast, "default_value", text="Contrast")
		col.prop(env_hdr_gamma, "default_value", text="Gamma")
		col.prop(env_hdr_hue, "default_value", text="Hue")
		col.prop(env_hdr_sat, "default_value", text="Saturation")
		col.prop(exposure, "default_value", text="Exposure")

# -------------------------------------------------------------------- #
class WORLD_PT_Lumiere_reflect_options(Panel):
	bl_label = "Reflection options"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'HEADER'

	def draw(self, context):
		layout = self.layout
		scene = context.scene
		world = bpy.data.worlds['Lumiere_world']
		env_reflect_blur = world.node_tree.nodes["Mix.001"].inputs[0]
		env_reflect_bright = world.node_tree.nodes["Bright/Contrast.001"].inputs[1]
		env_reflect_contrast = world.node_tree.nodes["Bright/Contrast.001"].inputs[2]
		env_reflect_gamma = world.node_tree.nodes["Gamma.001"].inputs[1]
		env_reflect_hue = world.node_tree.nodes["Reflect hue"].inputs[0]
		env_reflect_sat = world.node_tree.nodes["Reflect hue"].inputs[1]
		exposure = world.node_tree.nodes['Reflect exposure value'].outputs[0]
		col = layout.column()
		col.prop(env_reflect_bright, "default_value", text="Brightness")
		col.prop(env_reflect_contrast, "default_value", text="Contrast")
		col.prop(env_reflect_gamma, "default_value", text="Gamma")
		col.prop(env_reflect_hue, "default_value", text="Hue")
		col.prop(env_reflect_sat, "default_value", text="Saturation")
		col.prop(exposure, "default_value", text="Exposure")
		col.prop(env_reflect_blur, "default_value", text="Blur")

		col = layout.column()

# -------------------------------------------------------------------- #
class MAINWORLD_PT_Lumiere(Panel):
	bl_idname = "MAINWORLD_PT_Lumiere"
	bl_label = "World:"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Lumiere"

	def light_in_scene(self, context):
		if (context.active_object is not None) and "Lumiere" in str(context.active_object.users_collection) and len(list(context.scene.collection.children['Lumiere'].objects)) > 0:
			return True
		else:
			return False

	def draw_header_preset(self, context):
		scene = context.scene
		layout = self.layout
		col = layout.column(align=False)
		row = col.row(align=True)
		if self.light_in_scene(context):
			row.operator("lumiere.ray_operator", text="", emboss=False, icon="MOUSE_LMB_DRAG")
		row.prop(scene.Lumiere, "main_menu", text="", expand=True)
		row.operator("lumiere.preset_popup", text="", emboss=False, icon="PRESET")


	@classmethod
	def poll(cls, context):
		return context.scene.Lumiere.main_menu=="World"

	def draw(self, context):
		scene = context.scene
		layout = self.layout
		layout.use_property_split = True # Active single-column layout
		layout.use_property_decorate = False  # No animation.
		flow = layout.grid_flow(row_major=True, columns=0, even_columns=True, even_rows=False, align=True)
		col = flow.column(align=False)
		col.ui_units_x = 7
		row = col.row(align=True)
		col.prop(scene.Lumiere, "env_type", text="")
		if scene.Lumiere.env_type == "Texture":
			if context.scene.Lumiere.env_hdr_name !="" or context.scene.Lumiere.env_reflect_name !="" and len(list(context.scene.collection.children['Lumiere'].objects)) > 0:
				row = col.row(align=True)
				row.label(text="Link to :")
				row.prop(context.scene.Lumiere, "link_to_light", text="")

		elif scene.Lumiere.env_type == "Sky":
			world = bpy.data.worlds['Lumiere_world']
			sky_color = world.node_tree.nodes["Sky Texture"]
			col.prop(context.scene.Lumiere, "env_sun_contrib", text="Sun contribution")
			col.prop(context.scene.Lumiere, "env_sun_size", text="Sun size")
			col.prop(context.scene.Lumiere, "env_sky_contrib", text="Sky contribution")
			col.separator()
			col.prop(sky_color, "turbidity", text="Turbidity")
			col.prop(sky_color, "ground_albedo", text="Albedo")
			col.separator()
			col.prop(context.scene.Lumiere, "env_latitude", text="Latitude")
			col.prop(context.scene.Lumiere, "env_longitude", text="Longitude")
			col.separator()
			col.prop(context.scene.Lumiere, "env_hour", text="Hour")
			col.prop(context.scene.Lumiere, "env_day", text="Day")
			col.prop(context.scene.Lumiere, "env_month", text="Month")
			col.prop(context.scene.Lumiere, "env_year", text="Year")
			col.separator()
			if len(list(context.scene.collection.children['Lumiere'].objects)) > 0:
				row = col.row(align=True)
				row.label(text="Link to :")
				row.prop(context.scene.Lumiere, "link_to_light", text="")
# -------------------------------------------------------------------- #
class WORLD_PT_Lumiere_environment(Panel):
	bl_idname = "WORLD_PT_Lumiere_environment"
	bl_label = "Environment:"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Lumiere"

	def light_in_scene(self, context):
		if (context.active_object is not None) and "Lumiere" in str(context.active_object.users_collection) and len(list(context.scene.collection.children['Lumiere'].objects)) > 0:
			return True
		else:
			return False

	def draw_header_preset(self, context):
		scene = context.scene
		layout = self.layout
		col = layout.column(align=False)
		row = col.row(align=True)
		row.popover(panel="WORLD_PT_Lumiere_hdr_link", icon='LINKED' if context.scene.Lumiere.link_hdr_to_light else 'UNLINKED', text="")

	@classmethod
	def poll(cls, context):
		return context.scene.Lumiere.main_menu=="World" and context.scene.Lumiere.env_type=="Texture"

	def draw(self, context):
		scene = context.scene
		layout = self.layout
		layout.use_property_split = True # Active single-column layout
		layout.use_property_decorate = False  # No animation.
		flow = layout.grid_flow(row_major=True, columns=0, even_columns=True, even_rows=False, align=True)
		col = flow.column(align=False)
		col.ui_units_x = 7
		row = col.row(align=True)
		if scene.Lumiere.env_type == "Texture":
			row = col.row(align=True)
			world = bpy.data.worlds['Lumiere_world']
			env_hdr_strength = world.node_tree.nodes["Hdr background"].inputs[1]
			env_hdr_color = world.node_tree.nodes["Hdr background"].inputs[0]
			env_hdr_map = world.node_tree.nodes["Mapping"].inputs[2]
			row = col.row(align=True)
			row.prop_search(scene.Lumiere, "env_hdr_name", bpy.data, "images", text="")
			row.operator("image.open",text='', icon='FILEBROWSER')
			row.popover(panel="WORLD_PT_Lumiere_hdr_options", icon='PREFERENCES', text="")
			col.separator()
			col.prop(env_hdr_strength, "default_value", text="Strength")
			if scene.Lumiere.env_hdr_name != "":
				row = col.row(align=True)
				row.prop(scene.Lumiere, "env_hdr_rotation", text="Rotation")
			else:
				col.prop(env_hdr_color, "default_value", text="Color")

# -------------------------------------------------------------------- #
class WORLD_PT_Lumiere_reflection(Panel):
	bl_idname = "WORLD_PT_Lumiere_reflection"
	bl_label = "Reflection:"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Lumiere"

	def light_in_scene(self, context):
		if (context.active_object is not None) and "Lumiere" in str(context.active_object.users_collection) and len(list(context.scene.collection.children['Lumiere'].objects)) > 0:
			return True
		else:
			return False

	def draw_header_preset(self, context):
		scene = context.scene
		layout = self.layout
		col = layout.column(align=False)
		row = col.row(align=True)
		row.prop(scene.Lumiere, "env_reflect_toggle", text="")
		row.popover(panel="WORLD_PT_Lumiere_refl_link", icon='LINKED' if context.scene.Lumiere.link_reflect_to_light else 'UNLINKED', text="")

	@classmethod
	def poll(cls, context):
		return context.scene.Lumiere.main_menu=="World" and context.scene.Lumiere.env_type=="Texture"

	def draw(self, context):
		scene = context.scene
		layout = self.layout
		layout.use_property_split = True # Active single-column layout
		layout.use_property_decorate = False  # No animation.
		flow = layout.grid_flow(row_major=True, columns=0, even_columns=True, even_rows=False, align=True)
		col = flow.column(align=False)
		col.ui_units_x = 7
		if scene.Lumiere.env_reflect_toggle:
			world = bpy.data.worlds['Lumiere_world']
			env_reflect_strength = world.node_tree.nodes["Reflect background"].inputs[1]
			env_reflect_color = world.node_tree.nodes["Reflect background"].inputs[0]
			row = col.row(align=True)
			row.prop_search(scene.Lumiere, "env_reflect_name", bpy.data, "images", text="")
			row.operator("image.open",text='', icon='FILEBROWSER')
			row.popover(panel="WORLD_PT_Lumiere_reflect_options", icon='PREFERENCES', text="")
			col.separator()
			col.prop(env_reflect_strength, "default_value", text="Strength")
			if scene.Lumiere.env_reflect_name != "":
				row2 = col.row(align=True)
				if context.scene.Lumiere.link_to_light and scene.Lumiere.env_hdr_name != "":
					row2.enabled = False
				row2.prop(scene.Lumiere, "env_reflect_rotation", text="Rotation")
			else:
				col.prop(env_reflect_color, "default_value", text="Color")

# -------------------------------------------------------------------- #
class MAIN_PT_Lumiere(POLL_PT_Lumiere, Panel):
	bl_idname = "MAIN_PT_Lumiere"
	bl_label = "Light:"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Lumiere"

	def draw_header_preset(self, context):
		scene = context.scene
		layout = self.layout
		col = layout.column(align=False)
		row = col.row(align=True)
		row.operator("lumiere.ray_operator", text="", emboss=False, icon="MOUSE_LMB_DRAG")
		row.prop(scene.Lumiere, "main_menu", text="", expand=True)
		row.operator("lumiere.preset_popup", text="", emboss=False, icon="PRESET")

	@classmethod
	def poll(cls, context):
		if (POLL_PT_Lumiere.poll(context)) :
			return context.scene.Lumiere.main_menu=="Light"

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
		if (POLL_PT_Lumiere.poll(context)) and context.scene.Lumiere.main_menu=="Light" :
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
		col = col.column(align=False)
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

		col.separator()
		col = flow.column(align=False)
		col2 = flow.column(align=False)
		if light.Lumiere.lock_img == True :
			row = col.row(align=True)
			row.prop(context.scene.Lumiere, "link_to_light", text="Unlock to use:")
			col2.enabled = False
		col2.prop(light.Lumiere, "rotation", text="Rotation")
		col2.prop(light.Lumiere, "tilt", text="Tilt")
		col2.prop(light.Lumiere, "pitch", text="Pitch")
		col2.separator()

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
		if (POLL_PT_Lumiere.poll(context)) and context.scene.Lumiere.main_menu=="Light" :
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
		falloff_colramp = mat.node_tree.nodes['Falloff colRamp']
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
			col.template_color_ramp(falloff_colramp, "color_ramp", expand=True)
			col.separator()
			col.prop(light.Lumiere, "falloff_type", text="Falloff")
			col.prop(falloff, "default_value", text="Smooth")
			col.prop(mat.cycles, "sample_as_light", text='MIS')

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
		if (POLL_PT_Lumiere.poll(context)) and context.scene.Lumiere.main_menu=="Light" :
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
		col = col.column(align=False)
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
		col2 = flow.column(align=False)
		if light.Lumiere.lock_img == True :
			row = col.row(align=True)
			row.prop(context.scene.Lumiere, "link_to_light", text="Unlock to use:")
			col2.enabled = False
		col2.prop(light.Lumiere, "rotation", text="Rotation")
		col2.prop(light.Lumiere, "tilt", text="Tilt")
		col2.prop(light.Lumiere, "pitch", text="Pitch")
		col2.separator()
# -------------------------------------------------------------------- #

class LAMP_MATERIALS_PT_Lumiere(POLL_PT_Lumiere, Panel):
	bl_idname = "LAMP_MATERIALS_PT_Lumiere"
	bl_label = "Material"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Lumiere"

	@classmethod
	def poll(cls, context):
		if (POLL_PT_Lumiere.poll(context)) and context.scene.Lumiere.main_menu=="Light":
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
		falloff_colramp = light.data.node_tree.nodes["Falloff colRamp"]

		layout = self.layout
		layout.use_property_split = True # Active single-column layout
		layout.use_property_decorate = False  # No animation.
		flow = layout.grid_flow(row_major=True, columns=0, even_columns=True, even_rows=False, align=True)
		col = flow.column(align=False)
		col.ui_units_x = 7
		col = col.column()
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
			if light.data.type != "SUN":
				col.template_color_ramp(falloff_colramp, "color_ramp", expand=True)
				col.separator()
				col.prop(light.Lumiere, "falloff_type", text="Falloff")
				col.prop(falloff, "default_value", text="Smooth")
				col.separator()
			flow = col.column_flow()
			flow.prop(light.data.cycles, "cast_shadow", text='Shadow')
			flow.prop(light.data.cycles, "use_multiple_importance_sampling", text='MIS')
			flow.prop(light.cycles_visibility, "diffuse", text='Diffuse')
			flow.prop(light.cycles_visibility, "glossy", text='Specular')


# -------------------------------------------------------------------- #
## Operator
class OPERATOR_PT_Lumiere(Panel):
	bl_idname = "OPERATOR_PT_Lumiere"
	bl_label = "Light:"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Lumiere"

	@classmethod
	def poll(cls, context):
		if (context.active_object is not None):
			if ("Lumiere" in str(context.active_object.users_collection)) \
			and len(list(context.scene.collection.children['Lumiere'].objects)) > 0 :
				return context.view_layer.objects.active.name not in context.scene.collection.children['Lumiere'].all_objects
		return context.scene.Lumiere.main_menu=="Light"

	def draw_header_preset(self, context):
		layout = self.layout
		col = layout.column(align=False)
		row = col.row(align=True)
		row.prop(context.scene.Lumiere, "main_menu", text="", expand=True)
		row.operator("lumiere.preset_popup", text="", emboss=False, icon="PRESET")

	def draw(self, context):
		layout = self.layout
		layout.use_property_split = True # Active single-column layout
		layout.use_property_decorate = False  # No animation.
		flow = layout.grid_flow(row_major=True, columns=0, even_columns=True, even_rows=False, align=True)
		col = flow.column(align=True)
		col.ui_units_x = 7
		col.prop(context.scene.Lumiere, "light_type",  text="", expand=False)
		col.separator()
		op_ray = col.operator("lumiere.ray_operator", text="CREATE", icon='BLANK1')
		op_ray.light_type = context.scene.Lumiere.light_type


# -------------------------------------------------------------------- #
from bpy.app.handlers import persistent
@persistent
def anim(self):

	# bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
	bpy.context.scene.Lumiere.env_hour = 5 + (bpy.context.scene.frame_current * 0.05)
	bpy.context.view_layer.update()
	# bpy.context.scene.frame_set(bpy.context.scene.frame_current)

# -------------------------------------------------------------------- #
## Register
classes = [
	ALL_LIGHTS_UL_list,
	MAINWORLD_PT_Lumiere,
	WORLD_PT_Lumiere_environment,
	WORLD_PT_Lumiere_reflection,
	WORLD_PT_Lumiere_hdr_link,
	WORLD_PT_Lumiere_refl_link,
	WORLD_PT_Lumiere_hdr_options,
	WORLD_PT_Lumiere_reflect_options,
	MAIN_PT_Lumiere,
	MESH_OPTIONS_PT_Lumiere,
	MESH_MATERIALS_PT_Lumiere,
	LAMP_OPTIONS_PT_Lumiere,
	LAMP_MATERIALS_PT_Lumiere,
	OPERATOR_PT_Lumiere,
	LumiereObj,
	LumiereScn,
	LightsProp,
	LumiereAddonPreferences,
	]


def register():
	from bpy.utils import register_class
	for cls in classes:
		register_class(cls)
	bpy.app.handlers.frame_change_post.append(anim)
	bpy.types.Object.Lumiere = bpy.props.PointerProperty(type=LumiereObj)
	bpy.types.Scene.Lumiere = bpy.props.PointerProperty(type=LumiereScn)
	bpy.types.Scene.Lumiere_lights_list = bpy.props.CollectionProperty(type=LightsProp)
	bpy.types.Scene.Lumiere_lights_list_index = bpy.props.IntProperty(name = "Index", default = 0)


def unregister():
	from bpy.utils import unregister_class
	for cls in reversed(classes):
		unregister_class(cls)
	bpy.app.handlers.frame_change_post.remove(anim)
	del bpy.types.Object.Lumiere
	del bpy.types.Scene.Lumiere
	del bpy.types.Scene.Lumiere_lights_list
	del bpy.types.Scene.Lumiere_lights_list_index
