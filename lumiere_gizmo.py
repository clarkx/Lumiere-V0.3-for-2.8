import bpy
from mathutils import (
	Matrix,
	Vector,
	)

from math import (
	degrees,
	radians,
	)

from .lumiere_op import (
	OpStatus,
	)

from bpy.types import (
	GizmoGroup,
	Gizmo,
	)
from math import sqrt

class LUMIERE_GGT_3dgizmo(GizmoGroup):
	bl_idname = "LUMIERE_GGT_3dgizmo"
	bl_label = "Lumiere widget"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'WINDOW'
	bl_options = {'3D', 'PERSISTENT'}

	@classmethod
	def poll(cls, context):
		light = context.object
		if (context.active_object is not None):
			if ("Lumiere" in str(context.active_object.users_collection)) \
			and len(list(context.scene.collection.children['Lumiere'].objects)) > 0 :
				return context.view_layer.objects.active.name in context.scene.collection.children['Lumiere'].all_objects
		else:
			return False

	def setup(self, context):
		light = context.object
		context.area.tag_redraw()

		color_select = context.preferences.themes[0].view_3d.object_selected
		color_active = context.preferences.themes[0].view_3d.object_active
		scale_basis = 0.07
		color_alpha = 1
		color_highlight = 0.8
		alpha_highlight = 1
		line_width = 5
		line_length = .4

		#-- HIT Gizmo
		gz_hit = self.gizmos.new("GIZMO_GT_move_3d")
		gz_hit.target_set_operator("lumiere.ray_operator")
		gz_hit.draw_options={"FILL", "ALIGN_VIEW"}
		gz_hit.scale_basis = scale_basis
		gz_hit.color = color_active
		gz_hit.alpha = color_alpha
		gz_hit.color_highlight = color_select
		gz_hit.alpha_highlight = alpha_highlight
		gz_hit.line_width = 3
		self.hit_widget = gz_hit

		#-- RANGE Gizmo
		gz_range = self.gizmos.new("GIZMO_GT_arrow_3d")
		gz_range.draw_style = 'BOX' #('NORMAL', 'CROSS', 'BOX', 'CONE')
		gz_range.scale_basis = .8
		gz_range.color = color_active
		gz_range.alpha = color_alpha
		gz_range.color_highlight = color_select
		gz_range.alpha_highlight = alpha_highlight
		gz_range.line_width = 0
		gz_range.length  = 0
		self.range_widget = gz_range

		#-- SCALE_XY / SCALE_Y Gizmo
		gz_scale = self.gizmos.new("GIZMO_GT_arrow_3d")
		gz_scale.draw_style = 'BOX' #('NORMAL', 'CROSS', 'BOX', 'CONE')
		gz_scale.scale_basis = 0.12
		gz_scale.color =  color_active
		gz_scale.alpha = color_alpha
		gz_scale.color_highlight = color_select
		gz_scale.alpha_highlight = alpha_highlight
		gz_scale.line_width = line_width
		self.scale_widget = gz_scale

		#-- SCALE_X Gizmo
		gz_scale_x = self.gizmos.new("GIZMO_GT_arrow_3d")
		gz_scale_x.draw_style = 'BOX' #('NORMAL', 'CROSS', 'BOX', 'CONE')
		gz_scale_x.target_set_prop('offset', light.Lumiere, 'scale_x')
		gz_scale_x.scale_basis = 0.12
		gz_scale_x.color =  color_active
		gz_scale_x.alpha = color_alpha
		gz_scale_x.color_highlight = color_select
		gz_scale_x.alpha_highlight = alpha_highlight
		gz_scale_x.line_width = line_width
		self.scale_x_widget = gz_scale_x

		#-- BBOX Gizmo
		bbox_circle = self.gizmos.new("GIZMO_GT_move_3d")
		bbox_circle.draw_options={"FILL", "ALIGN_VIEW"}
		bbox_circle.scale_basis = scale_basis
		bbox_circle.hide_select = True
		self.bbox_circle_widget = bbox_circle

		gz_bbox_x = self.gizmos.new("GIZMO_GT_arrow_3d")
		gz_bbox_x.color  = context.preferences.themes[0].user_interface.axis_x
		gz_bbox_x.length  = line_length
		self.bbox_x_widget = gz_bbox_x

		gz_bbox_y = self.gizmos.new("GIZMO_GT_arrow_3d")
		gz_bbox_y.color  = context.preferences.themes[0].user_interface.axis_y
		gz_bbox_y.length  = line_length
		self.bbox_y_widget = gz_bbox_y

		gz_bbox_z = self.gizmos.new("GIZMO_GT_arrow_3d")
		gz_bbox_z.color  = context.preferences.themes[0].user_interface.axis_z
		gz_bbox_z.length  = line_length
		self.bbox_z_widget = gz_bbox_z


	def draw_prepare(self, context):
		light = context.object
		region = context.region

		self.range_widget.target_set_prop('offset', light.Lumiere, 'range')

		if light.type != "MESH":
			self.scale_x_widget.hide = True
			self.scale_widget.hide = True
		else:
			self.scale_x_widget.hide = False
			self.scale_widget.hide = False

		if light.Lumiere.lock_scale:
			self.scale_x_widget.hide = True
			self.scale_widget.target_set_prop('offset', light.Lumiere, 'scale_xy')
		else:
			self.scale_x_widget.hide = False
			self.scale_widget.target_set_prop('offset', light.Lumiere, 'scale_y')

		mat_hit = Matrix.Translation((light.Lumiere.hit))
		mat_rot = light.rotation_euler.to_matrix()
		hit_matrix = mat_hit @ mat_rot.to_4x4()
		mat_rot_x = Matrix.Rotation(radians(90.0), 4, 'Y')
		mat_rot_y = Matrix.Rotation(radians(90.0), 4, 'X')

		self.hit_widget.matrix_basis = hit_matrix.normalized()
		self.range_widget.matrix_basis = hit_matrix.normalized()
		self.scale_widget.matrix_basis = light.matrix_world.normalized() @ mat_rot_y
		self.scale_x_widget.matrix_basis = light.matrix_world.normalized() @ mat_rot_x

		if light.Lumiere.reflect_angle == "2" and OpStatus.running == False: #"Estimated"
			mat_bbox = Matrix.Translation((light.Lumiere.bbox_center))
			mat_bbox_x = Matrix.Rotation(radians(90.0), 4, 'Y')
			mat_bbox_y = Matrix.Rotation(radians(-90.0), 4, 'X')

			if light.Lumiere.auto_bbox_center:
				self.bbox_circle_widget.hide = True
				self.bbox_x_widget.hide = True
				self.bbox_y_widget.hide = True
				self.bbox_z_widget.hide = True
			else:
				self.bbox_circle_widget.hide = False
				self.bbox_x_widget.hide = False
				self.bbox_y_widget.hide = False
				self.bbox_z_widget.hide = False

			def get_bbox_x():
				light = bpy.context.object
				return light.Lumiere.bbox_center[0]

			def set_bbox_x(bbox_x):
				light = bpy.context.object
				global_bbox_center = light.Lumiere.bbox_center
				global_bbox_center[0] = bbox_x

			def get_bbox_y():
				light = bpy.context.object
				return light.Lumiere.bbox_center[1]

			def set_bbox_y(bbox_y):
				light = bpy.context.object
				global_bbox_center = light.Lumiere.bbox_center
				global_bbox_center[1] = bbox_y

			def get_bbox_z():
				light = bpy.context.object
				return light.Lumiere.bbox_center[2]

			def set_bbox_z(bbox_z):
				light = bpy.context.object
				global_bbox_center = light.Lumiere.bbox_center
				global_bbox_center[2] = bbox_z

			self.bbox_circle_widget.matrix_basis = mat_bbox.normalized()

			self.bbox_x_widget.target_set_handler('offset', get=get_bbox_x, set=set_bbox_x)
			self.bbox_x_widget.matrix_basis = mat_bbox.normalized() @ mat_bbox_x
			self.bbox_x_widget.matrix_basis.col[3][0] = light.Lumiere.bbox_center[0] - self.bbox_x_widget.target_get_value("offset")[0]

			self.bbox_y_widget.target_set_handler('offset', get=get_bbox_y, set=set_bbox_y)
			self.bbox_y_widget.matrix_basis = mat_bbox.normalized() @ mat_bbox_y
			self.bbox_y_widget.matrix_basis.col[3][1] = light.Lumiere.bbox_center[1] - self.bbox_y_widget.target_get_value("offset")[0]

			self.bbox_z_widget.target_set_handler('offset', get=get_bbox_z, set=set_bbox_z)
			self.bbox_z_widget.matrix_basis = mat_bbox.normalized()
			self.bbox_z_widget.matrix_basis.col[3][2] = light.Lumiere.bbox_center[2] - self.bbox_z_widget.target_get_value("offset")[0]
		else:
			self.bbox_circle_widget.hide = True
			self.bbox_x_widget.hide = True
			self.bbox_y_widget.hide = True
			self.bbox_z_widget.hide = True
# Register
# -------------------------------------------------------------------- #
#

classes = [
	LUMIERE_GGT_3dgizmo,
	]

def register():
	from bpy.utils import register_class
	for cls in classes:
		print("CLASSE: ", cls)
		register_class(cls)

def unregister():
	from bpy.utils import unregister_class
	for cls in reversed(classes):
		unregister_class(cls)
