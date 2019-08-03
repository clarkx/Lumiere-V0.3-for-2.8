import bpy
from mathutils import (
	Matrix,
	Vector,
	)

from .lumiere_utils import (
	draw_circle,
	)

from math import (
	degrees,
	radians,
	)

from bpy.types import (
	GizmoGroup,
	Gizmo,
	)
from math import sqrt

custom_shape_verts, indices = draw_circle(Vector((0,0)), Vector((.3,.3)), 8)

class LUMIERE_GGT_gizmo(GizmoGroup):
	bl_idname = "LUMIERE_GGT_gizmo"
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
		color_select = context.preferences.themes[0].view_3d.object_selected
		color_active = context.preferences.themes[0].view_3d.object_active
		scale_basis = 0.07
		color_alpha = 1
		color_highlight = 0.8
		alpha_highlight = 1
		line_width = 5

		#-- HIT Gizmo
		gz_hit = self.gizmos.new("GIZMO_GT_move_3d")
		gz_hit.target_set_operator("lumiere.ray_operator")
		gz_hit.draw_options={"FILL", "ALIGN_VIEW"}
		gz_hit.scale_basis = scale_basis
		gz_hit.color =  color_active
		gz_hit.alpha = color_alpha
		gz_hit.color_highlight = color_select
		gz_hit.alpha_highlight = alpha_highlight
		gz_hit.line_width = 3
		self.hit_widget = gz_hit

	def refresh(self, context):
		light = context.object
		mat_hit = Matrix.Translation((light.Lumiere.hit))
		mat_rot = light.rotation_euler.to_matrix()
		hit_matrix = mat_hit @ mat_rot.to_4x4()
		self.hit_widget.matrix_basis = hit_matrix.normalized()

# Register
# -------------------------------------------------------------------- #
#

classes = [
	LUMIERE_GGT_gizmo,
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
