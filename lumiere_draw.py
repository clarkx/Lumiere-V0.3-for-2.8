import bpy
import blf

from mathutils import Vector
from .lumiere_utils import (
	draw_circle,
	create_2d_circle,
	draw_shader,
	)
from bpy_extras import view3d_utils
from bpy_extras.view3d_utils import (
	region_2d_to_vector_3d,
	region_2d_to_location_3d,
	location_3d_to_region_2d,
)

# -------------------------------------------------------------------- #
def draw_callback_2d(self, context):
	region = context.region
	rv3d = context.region_data

	# Draw text to indicate that Lumiere is active
	text = "- Lumiere -"
	xt = int(region.width / 2.0)
	blf.size(0, 24, 72)
	blf.shadow(0, 3, 0, 0, 0, 1)
	blf.shadow_offset(0,0,0)
	blf.enable(0,blf.SHADOW)
	blf.position(0, xt - blf.dimensions(0, text)[0] / 2, 40 , 0)
	blf.draw(0, text)
	blf.disable(0,blf.SHADOW)

	# Create a circle using a tri fan
	if self.light_selected and (context.active_object is not None):
		light = context.active_object
		color = context.preferences.themes[0].view_3d.object_active
		circle_hit = location_3d_to_region_2d(region, rv3d, light.Lumiere.hit)
		circle_radius = (circle_hit[0] + 4, circle_hit[1] + 4)
		steps = 8

		tris_coords, indices = draw_circle(circle_hit, circle_radius, steps)
		draw_shader(self, color, 1.0, 'TRI_FAN', tris_coords, size=1)

		if self.shadow:
			circle_hit = location_3d_to_region_2d(region, rv3d, light.Lumiere.shadow)
			circle_radius = (circle_hit[0] + 3, circle_hit[1] + 3)
			tris_coords, indices = draw_circle(circle_hit, circle_radius, steps)
			draw_shader(self, color, 1.0, 'TRI_FAN', tris_coords, size=1)

		# Draw circle on boundingbox center of the targer object
		elif light.Lumiere.reflect_angle == "Estimated" and light.parent:
				circle_hit = location_3d_to_region_2d(region, rv3d, light.Lumiere.bbox_center)
				circle_radius = (circle_hit[0] + 3, circle_hit[1] + 3)
				steps = 8
				tris_coords, indices = draw_circle(circle_hit, circle_radius, steps)
				draw_shader(self, color, 1, 'TRI_FAN', tris_coords, size=1)
# -------------------------------------------------------------------- #
# Opengl draw on screen
def draw_callback_3d(self, context):
	region = context.region
	rv3d = context.region_data

	if self.light_selected and (context.active_object is not None):
		light = context.active_object
		color = context.preferences.themes[0].view_3d.object_active
		if self.action == "shadow":
			coords = [list(light.Lumiere.shadow), list(light.location)]
		else:
			coords = [list(light.Lumiere.hit), list(light.location)]
		draw_shader(self, color, 1, 'LINES', coords, size=2)

# -------------------------------------------------------------------- #
def draw_target_px(self, context, event):
	"""Get the brightest pixel """

	if context.area == self.lumiere_area :
		color = context.preferences.themes[0].view_3d.object_active
		uv_x, uv_y = self.mouse_path
		x, y = (event.mouse_x - context.region.x, event.mouse_y - context.region.y)

		verts, indices = create_2d_circle(20, 20, rotation=0, center_x=x, center_y=y)
		draw_shader(self, color, 1.0, 'LINE_LOOP', verts[1:], size=2)
