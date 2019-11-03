import bpy
import os
import json
import sys

from .lumiere_utils import (
	raycast_light,
	export_props_light,
	export_props_group,
	get_lumiere_dict,
	update_lumiere_dict,
	)

from .lumiere_draw import (
	draw_callback_2d,
	draw_callback_3d,
	)

from .lumiere_lights import (
	create_softbox,
	)

from .lumiere_materials import (
	update_mat,
	)
from .lumiere_lights import (
	create_softbox,
	create_lamp,
	)

from bpy.types import Operator

from mathutils import (
	Vector,
	Matrix,
	Quaternion,
	Euler,
	)

from math import (
	sin,
	cos,
	pi,
	)


# -------------------------------------------------------------------- #
# Preset Menu
class LUMIERE_OT_PresetPopup(Operator):
	'''Export/Import Preset'''
	bl_idname = "lumiere.preset_popup"
	bl_label = "Export/Import Preset"

	group: bpy.props.StringProperty()

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
			self.import_light(context, select_item)
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
			op_add.action = 'IMPORT'
			op_add.arg = "Import to scene"
			row = col2.row(align=True)
			op_del = row.operator("custom.list_action", emboss=False, icon='REMOVE', text="")
			op_del.action = 'REMOVE'
			op_del.arg = "Remove from list"

		if (context.active_object is not None):
			if ("Lumiere" in str(context.active_object.users_collection)) \
			and len(list(context.scene.collection.children['Lumiere'].objects)) > 0 and context.view_layer.objects.active.name in context.scene.collection.children['Lumiere'].all_objects :

				row = col.row()
				if len(context.view_layer.objects.selected) > 1:
					row.prop(self, "group", text="Group", expand=False)
					op = row.operator("object.export_light", text ="", emboss=False, icon="ADD")
					op.name = self.group
				else:
					row.prop(light, "name", text="Light", expand=False)
					op = row.operator("object.export_light", text ="", emboss=False, icon="ADD")
					op.name = light.name

	def invoke(self, context, event):
		context.scene.Lumiere_lights_list.clear()
		my_dict = get_lumiere_dict()

		for key, value in my_dict.items():
		#---Fill the items for the light
			item = context.scene.Lumiere_lights_list.add()
			if key.startswith("Group_"):
				item.name = key[6:]
				item.num = str(len(value))
			else:
				item.name = key
				item.num = "1"

		return context.window_manager.invoke_popup(self)

# -------------------------------------------------------------------- #
class LUMIERE_OT_export_light(Operator):
	"""Export the current light data in JSON format"""

	bl_idname = "object.export_light"
	bl_label = "Export light"

	name : bpy.props.StringProperty()

	def execute(self, context):
		current_file_path = __file__
		current_file_dir = os.path.dirname(__file__)
		light = context.active_object
		light_selected = []

	#---Try to open the Lumiere export dictionary
		try:
			with open(current_file_dir + "\\" + "lumiere_dictionary.json", 'r', encoding='utf-8') as file:
				my_dict = json.load(file)
				file.close()
		except Exception:
			print("Warning, dict empty, creating a new one.")
			my_dict = {}

		# list(context.scene.collection.children['Lumiere'].objects)
		for obj in context.view_layer.objects.selected:
			if obj in list(context.scene.collection.children['Lumiere'].objects):
				light_selected.append(obj)

		if len(light_selected) > 1:
			lumiere_dict = export_props_group(self, context, self.name, light_selected)
		else:
			lumiere_dict = export_props_light(self, context, light)

		my_dict.update(lumiere_dict)

		with open(current_file_dir + "\\" + "lumiere_dictionary.json", "w", encoding='utf-8') as file:
			json.dump(my_dict, file, sort_keys=True, indent=4, ensure_ascii=False)

		file.close()
		message = "Light exported"
		self.report({'INFO'}, message)
		return {'FINISHED'}


# -------------------------------------------------------------------- #
class PRESET_OT_actions(Operator):
	"""Add or remove preset from ights"""
	bl_idname = "custom.list_action"
	bl_label = "Import/Remove"
	bl_description = "Import or remove from the list"
	bl_options = {'REGISTER'}

	action: bpy.props.EnumProperty(
		description="Import/Export options.\nSelected",
		items=(
			('REMOVE', "Remove", ""),
			('IMPORT', "Import", "")))


	arg: bpy.props.StringProperty()


	@classmethod
	def description(cls, context, props):
		return "Preset: " + props.arg

	def import_light(self, context):
		scn = context.scene
		list = context.scene.Lumiere_lights_list
		list_index = context.scene.Lumiere_lights_list_index

		if int(list[list_index].num) > 1:
			light_from_dict = self.my_dict["Group_" + scn.Lumiere_lights_list[list_index].name]
			for light in light_from_dict:
				self.create_light(context, light_from_dict[light], light)
		else:
			light_from_dict = self.my_dict[scn.Lumiere_lights_list[list_index].name]
			self.create_light(context, light_from_dict, scn.Lumiere_lights_list[list_index].name)


	def create_light(self, context, light_from_dict, light_name):
		scn = context.scene
		list_index = context.scene.Lumiere_lights_list_index

		if light_from_dict["Lumiere"]["light_type"] == "Softbox":
			light = create_softbox(light_name)
			colramp = mat.node_tree.nodes['ColorRamp'].color_ramp
		else:
			light = create_lamp(light_name, light_from_dict["Lumiere"]["light_type"])
			colramp = light.data.node_tree.nodes["ColorRamp"].color_ramp
			if light.data.type == "AREA" :
				light.data.shape = light_from_dict['shape']

		light["Lumiere"] = light_from_dict["Lumiere"]
		light.location = light_from_dict["location"]
		light.rotation_euler = light_from_dict["rotation"]
		light.scale = light_from_dict["scale"]
		light.Lumiere.light_type = light_from_dict["Lumiere"]["light_type"]
		light.Lumiere.scale_x = light.Lumiere.scale_x

		# Gradient
		if light.Lumiere.color_type in ("Linear", "Spherical", "Gradient"):
			colramp.interpolation = light_from_dict['interpolation']
			i = 0
			for key, value in sorted(light_from_dict['gradient'].items()) :
				if i > 1:
					colramp.elements.new(float(key))
				colramp.elements[i].position = float(key)
				colramp.elements[i].color[:] = value
				i += 1

		update_mat(self, context)


	def remove_light(self, context):
		list = context.scene.Lumiere_lights_list
		list_index = context.scene.Lumiere_lights_list_index

		if int(list[list_index].num) > 1:
			self.report({'INFO'}, "Group " + list[list_index].name + " deleted from the list")
			self.my_dict.pop("Group_"+list[list_index].name, None)
		else:
			self.report({'INFO'}, "Light " + list[list_index].name + " deleted from the list")
			self.my_dict.pop(list[list_index].name, None)

		list.remove(list_index)
		list_index -= 1
		update_lumiere_dict(self.my_dict)


	def invoke(self, context, event):
		scn = context.scene
		idx = scn.Lumiere_lights_list_index
		self.my_dict = get_lumiere_dict()

		try:
			item = scn.Lumiere_lights_list[idx]
		except IndexError:
			pass
		else:
			if self.action == 'IMPORT':
				self.import_light(context)
			elif self.action == 'REMOVE':
				self.remove_light(context)

		return {"FINISHED"}

# -------------------------------------------------------------------- #
class OpStatus(object):
	"""Operator status : Running or not"""
	running = False

	def __init__(cls, value):
		cls.value = running

# -------------------------------------------------------------------- #
class LUMIERE_OT_ray_operator(Operator):
	bl_idname = "lumiere.ray_operator"
	bl_label = "Lighting operator"
	bl_description = "Click to enter in interactive lighting mode"
	bl_options = {'REGISTER', 'UNDO'}


	@classmethod
	def poll(cls, context):
		return context.area.type == 'VIEW_3D' and context.mode == 'OBJECT'

	def __init__(self):
		self.draw_handle_2d = None
		self.draw_handle_3d = None
		self.light_selected = False
		self.shift = False
		self.ctrl = False
		self.lmb = False
		self.is_running = False
		self.create_collection()

	def invoke(self, context, event):
		args = (self, context)
		preferences = context.preferences
		self.addon_prefs = preferences.addons[__package__].preferences
		self.lumiere_context = context
		if context.space_data.type == 'VIEW_3D':
			self.lumiere_area = context.area
		self.enable_cursor = context.space_data.overlay.show_cursor
		self.enable_navigate = context.space_data.show_gizmo_navigate
		self.enable_tool = context.space_data.show_gizmo_tool
		self.relat_lines = context.space_data.overlay.show_relationship_lines

		self.register_handlers(args, context)
		context.window_manager.modal_handler_add(self)
		return {"RUNNING_MODAL"}

	def register_handlers(self, args, context):
		if self.is_running == False:
			OpStatus.running = True
			self.is_running = True
			self.draw_handle_2d = bpy.types.SpaceView3D.draw_handler_add(draw_callback_2d, args, "WINDOW", "POST_PIXEL")
			self.draw_handle_3d = bpy.types.SpaceView3D.draw_handler_add(draw_callback_3d, args, "WINDOW", "POST_VIEW")

	def unregister_handlers(self, context):
		bpy.types.SpaceView3D.draw_handler_remove(self.draw_handle_2d, "WINDOW")
		bpy.types.SpaceView3D.draw_handler_remove(self.draw_handle_3d, "WINDOW")
		self.draw_handle_2d = None
		self.draw_handle_3d = None
		OpStatus.running = False

		if context.view_layer.active_layer_collection.name == "Lumiere":
			context.view_layer.active_layer_collection = context.view_layer.layer_collection

	def modal(self, context, event):
		# Find the limit of the view3d region
		check_region(self,context,event)

		# Is the object selected is from Lumiere collection
		check_light_selected(self, context)

		# Hide 3d cursor
		if self.in_view_3d:
			context.space_data.overlay.show_cursor = False
			context.space_data.show_gizmo_navigate = False
			context.space_data.show_gizmo_tool = False
			context.space_data.overlay.show_relationship_lines = False

		try:
			# Shift press
			self.shift = True if event.shift else False

			# Ctrl press
			self.ctrl = True if event.ctrl else False

			if context.area != self.lumiere_area:
				self.is_running = False
				self.unregister_handlers(context)
				return {'CANCELLED'}

			if event.type in {"ESC", "RIGHTMOUSE"} :
				self.unregister_handlers(context)

				# State of 3d cursor before Lumiere
				context.space_data.overlay.show_cursor = self.enable_cursor
				context.space_data.show_gizmo_navigate = self.enable_navigate
				context.space_data.show_gizmo_tool = self.enable_tool
				context.space_data.overlay.show_relationship_lines = self.relat_lines
				self.is_running = False

				return {'CANCELLED'}

			# Left mouse button press
			elif event.type == 'LEFTMOUSE' and self.in_view_3d:
				self.lmb = event.value == 'PRESS'

			# Allow navigation
			elif event.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'} or event.type.startswith("NUMPAD"):
				return {'PASS_THROUGH'}

			# Left mouse button pressed with an object from Lumiere collection
			if self.lmb and self.in_view_3d:
				context.scene.cycles.preview_pause = self.addon_prefs.render_pause
				if self.light_selected :
					# Raycast to move the light compared to the targeted object
					raycast_light(self, event, context, context.object.Lumiere.range)
				else:
					create_softbox()

				return {'RUNNING_MODAL'}
			else:
				if self.addon_prefs.render_pause:
					context.scene.cycles.preview_pause = False
					# Hack to update cycles
					context.view_layer.objects.active = context.active_object
			return {"PASS_THROUGH"}

		except:
			print("\n[Lumiere ERROR]\n")
			import traceback
			traceback.print_exc()
			self.unregister_handlers(context)

			self.report({'WARNING'},
						"Operation finished. (Check the console for more info)")

			return {'FINISHED'}

	def finish(self):
		return {"FINISHED"}

	def create_collection(self):
		# Create a new collection and link it to the scene.
		if 'Lumiere' not in bpy.context.scene.collection.children.keys() :
			_lumiere_coll = bpy.data.collections.new("Lumiere")
			bpy.context.scene.collection.children.link(_lumiere_coll)



# Utilities
###############################################
# Get the region area where the operator is used
def check_region(self,context,event):
	if context.area != None:
		if context.area.type == "VIEW_3D" :
			for region in context.area.regions:
				if region.type == "TOOLS":
					t_panel = region
				elif region.type == "UI":
					ui_panel = region

			view_3d_region_x = Vector((context.area.x + t_panel.width, context.area.x + context.area.width - (ui_panel.width+1)))
			view_3d_region_y = Vector((context.region.y, context.region.y + context.region.height))

			if (event.mouse_x > view_3d_region_x[0] and event.mouse_x < view_3d_region_x[1] \
			and event.mouse_y > view_3d_region_y[0] and event.mouse_y < view_3d_region_y[1]):
				self.in_view_3d = True
				return True
			else:
				self.in_view_3d = False
				return False

		else:
			self.in_view_3d = False
			return False

# Check if the object selected is a light from Lumiere
def check_light_selected(self, context):
	if (context.view_layer.objects.active is not None):
			if context.view_layer.objects.active.name in context.scene.collection.children['Lumiere'].all_objects:
				self.light_selected = True
			else:
				self.light_selected = False


# -------------------------------------------------------------------- #
## Register

classes = [
	LUMIERE_OT_export_light,
	LUMIERE_OT_ray_operator,
	PRESET_OT_actions,
	LUMIERE_OT_PresetPopup,
	]

def register():
	from bpy.utils import register_class
	for cls in classes:
		register_class(cls)

def unregister():
	from bpy.utils import unregister_class
	for cls in reversed(classes):
		unregister_class(cls)
