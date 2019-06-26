import bpy
import bgl
import gpu
from gpu_extras.batch import batch_for_shader
from bpy_extras import view3d_utils
from mathutils import Vector, Matrix, Quaternion, Euler

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

# -------------------------------------------------------------------- #
def raycast_light(self, event, context, range, ray_max=1000.0):
	"""Compute the location and rotation of the light from the angle or normal of the targeted face off the object"""
	length_squared = 0
	scene = context.scene
	light = context.active_object
	rv3d = context.region_data
	region = context.region
	coord = (event.mouse_region_x, event.mouse_region_y)
	light.Lumiere.use_modal = True

#---Get the ray from the viewport and mouse
	# Direction vector from the viewport to 2d coord
	view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, (coord))
	# 3d view origin vector from the region
	ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, (coord))
	# Define a default direction vector
	ray_target = ray_origin + view_vector

	depsgraph =  context.evaluated_depsgraph_get()
#---Select the targeted object
	def visible_objects_and_duplis():
		if light.Lumiere.target :
			obj_trgt = light.Lumiere.target
			yield (obj_trgt, obj_trgt.matrix_world.copy())
		else:
			for dup in depsgraph.object_instances:
				if dup.object.type == 'MESH':
					if dup.object.name not in context.scene.collection.children['Lumiere'].all_objects:
						if dup.is_instance:
							yield (dup.instance_object, dup.instance_object.matrix_world.copy())
						else:
							yield (dup.object.original, dup.object.original.matrix_world.copy())


#---Cast the ray to the targeted object
	def obj_ray_cast(obj_trgt, matrix):
	#---Get the ray direction from the view angle to the targeted object
		matrix_inv = matrix.inverted()
		ray_origin_obj = matrix_inv @ ray_origin
		ray_target_obj = matrix_inv @ ray_target
		ray_direction_obj = ray_target_obj - ray_origin_obj

	#---Cast the ray
		success, hit, normal, face_index = obj_trgt.ray_cast(ray_origin_obj, ray_direction_obj)

		if success:
			return success, hit, normal
		else:
			return None, None, None

#---Find the closest object
	# best_length_squared = ray_max * ray_max
	best_length_squared = -1.0
	best_obj = None

#---Find the position of the light using the reflect angle and the object targeted normal
	for obj_trgt, matrix_trgt in visible_objects_and_duplis():
		success, hit, normal = obj_ray_cast(obj_trgt, matrix_trgt)

		if success is not None :
			# Get the normal of the face from the targeted object
			normal = matrix_trgt.to_3x3().inverted().transposed() @ normal
			normal.normalize()

		#---Define the direction based on the normal of the targeted object, the view angle or the bounding box
			if light.Lumiere.reflect_angle == "0":
				self.reflect_angle = "Accurate"
				reflect_dir = (view_vector).reflect(normal)
			elif light.Lumiere.reflect_angle == "1":
				self.reflect_angle = "Normal"
				reflect_dir = normal
			elif light.Lumiere.reflect_angle == "2":
				self.reflect_angle = "Estimated"
				local_bbox_center = 0.125 * sum((Vector(b) for b in obj_trgt.bound_box), Vector())
				global_bbox_center = obj_trgt.matrix_world @ local_bbox_center
				reflect_dir = (matrix_trgt @ hit) - global_bbox_center
				reflect_dir.normalize()

		#---Define light location : Hit + Direction + Range
			light_loc = (matrix_trgt @ hit) + (reflect_dir * range)

			length_squared = ((matrix_trgt @ hit) - ray_origin).length_squared

			if best_obj is None or length_squared < best_length_squared:
				best_obj = obj_trgt
				best_length_squared = length_squared
				_matrix_trgt = matrix_trgt
				_hit = hit
				_light_loc = light_loc
				_direction = reflect_dir

			#---Parent the light to the target object
				light.parent = obj_trgt
				light.matrix_parent_inverse = matrix_trgt.inverted()

#---Define location, rotation and scale
	if length_squared > 0 :
		if self.shift :
			# track  = light.location - Vector(_hit)
			rotaxis = (_hit.to_track_quat('Z','Y')).to_euler()
		else :
			rotaxis = (_direction.to_track_quat('Z','Y')).to_euler()
			light.location = Vector((_light_loc[0], _light_loc[1], _light_loc[2]))

		light.Lumiere.hit = (_matrix_trgt @ _hit)
		light.Lumiere.direction = _direction
		light.rotation_euler = rotaxis

#---Update rotation and pitch for spherical coordinate
		x,y,z = light.location - Vector((light.Lumiere.hit))
		r = sqrt(x**2 + y**2 + z**2)
		theta = atan2(y, x)
		if degrees(theta) < 0:
			theta = radians(degrees(theta) + 360)
		light.Lumiere.rotation = degrees(theta)
		phi = acos( z / r )
		light.Lumiere.pitch = degrees(phi)

# -------------------------------------------------------------------- #
def create_2d_circle(self, step, radius, rotation = 0, center_x=0, center_y=0):
	""" Create the vertices of a 2d circle at (0,0) """
	#https://stackoverflow.com/questions/8487893/generate-all-the-points-on-the-circumference-of-a-circle
	indices = []

	verts = [(center_x, center_y)] + [(
			cos(2*pi / step*x + rotation)*radius + center_x,
			sin(2*pi / step*x + rotation)*radius + center_y
			) for x in range(0, step+1)]

	for idx in range(len(verts) - 1):
		i1 = idx+1
		i2 = idx+2 if idx+2 <= step else 1
		indices.append((0,i1,i2))

	return(verts, indices)

# -------------------------------------------------------------------- #
def draw_circle(self, center_circle, radius_circle, steps):
	""" Return the coordinates + indices of a circle using a triangle fan """
	indices = []
	center_x, center_y = center_circle
	radiusx = radius_circle[0] - center_circle[0]
	radiusy = radius_circle[1] - center_circle[1]
	radius = sqrt(radiusx**2 + radiusy**2)
	rotation = radians(radius_circle[1] - center_circle[1]) / 2
	# steps = int(360 / steps)

	# Get the vertices of a 2d circle
	verts, indices = create_2d_circle(self, steps, radius, rotation, center_x, center_y)

	return(verts, indices)


# -------------------------------------------------------------------- #
def draw_shader(self, color, alpha, type, coords, size=1, indices=None):
	""" Create a batch for a draw type """
	bgl.glEnable(bgl.GL_BLEND)
	bgl.glEnable(bgl.GL_LINE_SMOOTH)
	bgl.glPointSize(size)
	bgl.glLineWidth(size)
	try:
		if len(coords[0])>2:
			shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
		else:
			shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
		batch = batch_for_shader(shader, type, {"pos": coords}, indices=indices)
		shader.bind()
		shader.uniform_float("color", (color[0], color[1], color[2], alpha))
		batch.draw(shader)
		bgl.glLineWidth(1)
		bgl.glPointSize(1)
		bgl.glDisable(bgl.GL_LINE_SMOOTH)
		bgl.glDisable(bgl.GL_BLEND)
	except:
		exc_type, exc_value, exc_traceback = sys.exc_info()
		self.report({'ERROR'}, str(exc_value))
