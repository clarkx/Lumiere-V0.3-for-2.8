import bpy
import blf


from .lumiere_utils import (
	draw_circle,
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
	blf.position(0, xt - blf.dimensions(0, text)[0] / 2, 60 , 0)
	blf.draw(0, text)

	# Create a circle using a tri fan
	if self.light_selected:
		light = context.active_object
		color = light.Lumiere.light_color
		circle_hit = location_3d_to_region_2d(region, rv3d, light.Lumiere.hit)
		circle_radius = (circle_hit[0] + 4, circle_hit[1] + 4)
		steps = 8

		tris_coords, indices = draw_circle(self, circle_hit, circle_radius, steps)
		draw_shader(self, color, 1.0, 'TRI_FAN', tris_coords, size=1)

# -------------------------------------------------------------------- #
# Opengl draw on screen
def draw_callback_3d(self, context):
	region = context.region
	rv3d = context.region_data

	if self.light_selected:
		# Draw a line between the light and the target point
		light = context.active_object
		color = light.Lumiere.light_color
		coords = [list(light.Lumiere.hit), list(light.location)]
		draw_shader(self, color, 1, 'LINES', coords, size=2)
