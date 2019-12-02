import bpy
import os
import sys

from math import (
	degrees,
	radians,
	sin,
	cos,
	)
from mathutils import (
	Vector,
	Matrix,
	Quaternion,
	Euler,
	)

# Softbox
#########################################################################################################
def softbox_mat(light):
	"""Cycles material nodes for the Softbox light"""

	# Create a new material for cycles Engine.
	if bpy.context.scene.render.engine != 'CYCLES':
		bpy.context.scene.render.engine = 'CYCLES'

	if light.active_material is None:
		mat = bpy.data.materials.new(light.name)

		# Use nodes by default
		mat.use_nodes = True

	# Assign the material to the light
	light.active_material = mat

	# Clear node tree
	mat.node_tree.nodes.clear()

#### GRADIENTS ###
	# Texture Coordinate
	coord = mat.node_tree.nodes.new(type = 'ShaderNodeTexCoord')
	coord.location = (-2260.0, -360.0)

	# Mapping Node
	gradmap = mat.node_tree.nodes.new(type="ShaderNodeMapping")
	gradmap.name = "Gradient map"
	mat.node_tree.links.new(coord.outputs[2], gradmap.inputs[0])
	gradmap.vector_type = "TEXTURE"
	gradmap.location = (-1920, -580)

	# Gradient Node Linear
	linear_grad = mat.node_tree.nodes.new(type="ShaderNodeTexGradient")
	mat.node_tree.links.new(gradmap.outputs[0], linear_grad.inputs[0])
	linear_grad.location = (-1740, -640)

	# Color Ramp Node
	colramp = mat.node_tree.nodes.new(type="ShaderNodeValToRGB")
	mat.node_tree.links.new(linear_grad.outputs[0], colramp.inputs['Fac'])
	colramp.color_ramp.elements[0].color = (1,1,1,1)
	colramp.inputs[0].default_value = 0
	colramp.location = (-1560, -640)

	# Invert Node
	edge_invert = mat.node_tree.nodes.new(type="ShaderNodeInvert")
	edge_invert.name = "Edges invert"
	mat.node_tree.links.new(coord.outputs[0], edge_invert.inputs[1])
	edge_invert.location = (-2100.0, 400.0)

	# Multiply Node
	edge_mult1 = mat.node_tree.nodes.new(type="ShaderNodeMixRGB")
	edge_mult1.name = "Edges Multiply1"
	edge_mult1.blend_type = 'MULTIPLY'
	edge_mult1.inputs[0].default_value = 1
	mat.node_tree.links.new(edge_invert.outputs[0], edge_mult1.inputs[1])
	mat.node_tree.links.new(coord.outputs[0], edge_mult1.inputs[2])
	edge_mult1.location = (-1920.0, 400.0)

	# Separate Node
	edge_sep = mat.node_tree.nodes.new(type="ShaderNodeSeparateXYZ")
	edge_sep.name = "Edges Separate"
	mat.node_tree.links.new(edge_mult1.outputs[0], edge_sep.inputs[0])
	edge_sep.location = (-1740.0, 440.0)

	# Value Node
	edge_value = mat.node_tree.nodes.new(type="ShaderNodeValue")
	edge_value.name = "Edges value"
	edge_value.outputs[0].default_value = 4
	edge_value.location = (-1740.0, 260.0)

	# Multiply Node 2
	edge_mult2 = mat.node_tree.nodes.new(type="ShaderNodeMath")
	edge_mult2.name = "Edges Multiply2"
	edge_mult2.operation = 'MULTIPLY'
	mat.node_tree.links.new(edge_sep.outputs[0], edge_mult2.inputs[0])
	mat.node_tree.links.new(edge_value.outputs[0], edge_mult2.inputs[1])
	edge_mult2.location = (-1560.0, 580.0)

	# Multiply Node 3
	edge_mult3 = mat.node_tree.nodes.new(type="ShaderNodeMath")
	edge_mult3.name = "Edges Multiply3"
	edge_mult3.operation = 'MULTIPLY'
	mat.node_tree.links.new(edge_sep.outputs[1], edge_mult3.inputs[0])
	mat.node_tree.links.new(edge_value.outputs[0], edge_mult3.inputs[1])
	edge_mult3.location = (-1560.0, 380.0)

	# Multiply Node 4
	edge_mult4 = mat.node_tree.nodes.new(type="ShaderNodeMath")
	edge_mult4.name = "Edges Multiply4"
	edge_mult4.operation = 'MULTIPLY'
	mat.node_tree.links.new(edge_mult2.outputs[0], edge_mult4.inputs[0])
	mat.node_tree.links.new(edge_mult3.outputs[0], edge_mult4.inputs[1])
	edge_mult4.location = (-1380.0, 580.0)

	# Power
	edge_power = mat.node_tree.nodes.new(type="ShaderNodeMath")
	edge_power.name = "Edges Power"
	edge_power.operation = 'POWER'
	mat.node_tree.links.new(edge_value.outputs[0], edge_power.inputs[0])
	edge_power.inputs[1].default_value = 0.5
	edge_power.location = (-1380.0, 340.0)

	# Color Ramp Node
	edge_colramp = mat.node_tree.nodes.new(type="ShaderNodeValToRGB")
	edge_colramp.name = "Edges ColRamp"
	mat.node_tree.links.new(edge_mult4.outputs[0], edge_colramp.inputs['Fac'])
	edge_colramp.color_ramp.interpolation = 'B_SPLINE'
	edge_colramp.color_ramp.elements[0].color = (0,0,0,1)
	edge_colramp.inputs[0].default_value = 0
	# edge_colramp.color_ramp.elements.new(1)
	edge_colramp.color_ramp.elements[1].color = (1,1,1,1)
	edge_colramp.location = (-1200, 540)

	# Multiply Node 5
	edge_mult5 = mat.node_tree.nodes.new(type="ShaderNodeMath")
	edge_mult5.name = "Edges Multiply5"
	edge_mult5.operation = 'MULTIPLY'
	mat.node_tree.links.new(edge_colramp.outputs[0], edge_mult5.inputs[0])
	mat.node_tree.links.new(edge_power.outputs[0], edge_mult5.inputs[1])
	edge_mult5.location = (-920.0, 440.0)

	# Mix Edges / Color for reflection only
	refl_mix_color_edges = mat.node_tree.nodes.new(type = 'ShaderNodeMixRGB')
	refl_mix_color_edges.name = "Reflect_Mix_Color_Edges"
	refl_mix_color_edges.blend_type = 'MULTIPLY'
	refl_mix_color_edges.inputs[0].default_value = 1
	refl_mix_color_edges.inputs['Color1'].default_value = [1,1,1,1]
	refl_mix_color_edges.inputs['Color2'].default_value = [1,1,1,1]
	mat.node_tree.links.new(edge_mult5.outputs[0], refl_mix_color_edges.inputs[1])
	refl_mix_color_edges.location = (-700, 360)

	# Mix Color Edges for lighting
	mix_color_edges = mat.node_tree.nodes.new(type = 'ShaderNodeMixRGB')
	mix_color_edges.name = "Mix_Color_Edges"
	mix_color_edges.blend_type = 'MULTIPLY'
	mix_color_edges.inputs[0].default_value = 1
	mix_color_edges.inputs['Color1'].default_value = [1,1,1,1]
	mix_color_edges.inputs['Color2'].default_value = [1,1,1,1]
	mix_color_edges.location = (-720, -180)

	# Light path
	reflect_light_path = mat.node_tree.nodes.new(type = 'ShaderNodeLightPath')
	reflect_light_path.name = "Reflect Light Path"
	reflect_light_path.location = (-220, 380)

#### IMAGE TEXTURE ###

	# Mapping Node
	textmap = mat.node_tree.nodes.new(type="ShaderNodeMapping")
	textmap.name = "Texture map"
	mat.node_tree.links.new(coord.outputs[2], textmap.inputs[0])
	textmap.vector_type = "TEXTURE"
	textmap.location = (-1920, 160)

	# Image Texture
	texture = mat.node_tree.nodes.new(type = 'ShaderNodeTexImage')
	mat.node_tree.links.new(textmap.outputs[0], texture.inputs[0])
	texture.projection = 'FLAT'
	texture.extension = 'REPEAT'
	texture.location = (-1740, 160)

	# Invert Node
	texture_invert = mat.node_tree.nodes.new(type="ShaderNodeInvert")
	texture_invert.name = "Texture invert"
	texture_invert.inputs[0].default_value = 0
	mat.node_tree.links.new(texture.outputs[0], texture_invert.inputs[1])
	texture_invert.location = (-1460.0, 140.0)

	# Mix Texture / Color for reflection only
	refl_mix_color_text = mat.node_tree.nodes.new(type = 'ShaderNodeMixRGB')
	refl_mix_color_text.name = "Reflect_Mix_Color_Text"
	refl_mix_color_text.blend_type = 'MULTIPLY'
	refl_mix_color_text.inputs[0].default_value = 1
	refl_mix_color_text.inputs['Color1'].default_value = [1,1,1,1]
	refl_mix_color_text.inputs['Color2'].default_value = [1,1,1,1]
	mat.node_tree.links.new(refl_mix_color_edges.outputs[0], refl_mix_color_text.inputs[1])
	refl_mix_color_text.location = (-500, 240)

	# Mix Color Texture for lighting
	mix_color_text = mat.node_tree.nodes.new(type = 'ShaderNodeMixRGB')
	mix_color_text.name = "Mix_Color_Text"
	mix_color_text.blend_type = 'MULTIPLY'
	mix_color_text.inputs[0].default_value = 1
	mix_color_text.inputs['Color1'].default_value = [1,1,1,1]
	mix_color_text.inputs['Color2'].default_value = [1,1,1,1]
	mat.node_tree.links.new(mix_color_edges.outputs[0], mix_color_text.inputs[2])
	mix_color_text.location = (-500, -80)

#### COLOR ###

	# RGB Node
	color = mat.node_tree.nodes.new(type = 'ShaderNodeRGB')
	mat.node_tree.links.new(color.outputs[0], mix_color_edges.inputs[2])
	mat.node_tree.links.new(color.outputs[0], refl_mix_color_edges.inputs[2])
	color.location = (-1560, -400)

	# Blackbody
	blackbody = mat.node_tree.nodes.new(type = 'ShaderNodeBlackbody')
	blackbody.location = (-1400, -500)

#### IES ###

	# Mapping Node
	ies_map = mat.node_tree.nodes.new(type="ShaderNodeMapping")
	ies_map.name = "Ies map"
	mat.node_tree.links.new(coord.outputs[3], ies_map.inputs[0])
	ies_map.vector_type = "TEXTURE"
	ies_map.location = (-1920, -200)
	ies_map.inputs[1].default_value[2] = 0.5

	# Mapping File texture
	ies = mat.node_tree.nodes.new(type="ShaderNodeTexIES")
	ies.name = "IES Texture"
	mat.node_tree.links.new(ies_map.outputs[0], ies.inputs[0])
	ies.mode = 'INTERNAL'
	ies.inputs[1].default_value = light.Lumiere.energy
	ies.location = (-1740, -200)

	# Math MULTIPLY
	ies_math_mul = mat.node_tree.nodes.new(type = 'ShaderNodeMath')
	ies_math_mul.name = "IES Math"
	mat.node_tree.links.new(ies.outputs[0], ies_math_mul.inputs[0])
	ies_math_mul.inputs[1].default_value = 0.01
	ies_math_mul.operation = 'MULTIPLY'
	ies_math_mul.location = (-1560, -200)

#### INTENSITY ###

	# Light Falloff
	falloff = mat.node_tree.nodes.new(type = 'ShaderNodeLightFalloff')
	falloff.inputs[0].default_value = 10
	mat.node_tree.links.new(ies_math_mul.outputs[0], falloff.inputs[0])
	falloff.location = (-720, -440)

	# Texture Emission Node
	texture_emit = mat.node_tree.nodes.new(type = 'ShaderNodeEmission')
	texture_emit.name = "Emit texture"
	texture_emit.inputs[0].default_value = bpy.context.active_object.Lumiere.light_color
	mat.node_tree.links.new(refl_mix_color_text.outputs[0], texture_emit.inputs[0])
	mat.node_tree.links.new(falloff.outputs[0], texture_emit.inputs[1])
	texture_emit.location = (-220, 20)

	# Color Emission Node
	color_emit = mat.node_tree.nodes.new(type = 'ShaderNodeEmission')
	color_emit.name = "Emit color"
	color_emit.inputs[0].default_value = bpy.context.active_object.Lumiere.light_color
	mat.node_tree.links.new(mix_color_text.outputs[0], color_emit.inputs[0])
	color_emit.location = (-220, -160)

#### FALLOFF from Metin Seven ###

	# Ligth Path
	falloff_path = mat.node_tree.nodes.new(type = 'ShaderNodeLightPath')
	falloff_path.name = "Fallof light path"
	falloff_path.location = (-1080, -680)

	# Math DIVIDE
	falloff_divide = mat.node_tree.nodes.new(type = 'ShaderNodeMath')
	falloff_divide.name = "Falloff divide"
	falloff_divide.inputs[1].default_value = 20
	falloff_divide.operation = 'DIVIDE'
	mat.node_tree.links.new(falloff_path.outputs[7], falloff_divide.inputs[0])
	falloff_divide.location = (-900, -680)

	# Color Ramp Node
	falloff_colramp = mat.node_tree.nodes.new(type="ShaderNodeValToRGB")
	falloff_colramp.name = "Falloff colRamp"
	mat.node_tree.links.new(falloff_divide.outputs[0], falloff_colramp.inputs['Fac'])
	falloff_colramp.color_ramp.interpolation = 'LINEAR'
	falloff_colramp.color_ramp.elements[0].color = (1,1,1,1)
	falloff_colramp.inputs[0].default_value = 0
	falloff_colramp.color_ramp.elements[1].color = (1,1,1,1)
	falloff_colramp.location = (-720, -620)

	# Math MULTIPLY
	falloff_multiply = mat.node_tree.nodes.new(type = 'ShaderNodeMath')
	falloff_multiply.name = "Falloff multiply"
	falloff_multiply.operation = 'MULTIPLY'
	mat.node_tree.links.new(falloff.outputs[0], falloff_multiply.inputs[0])
	mat.node_tree.links.new(falloff_colramp.outputs[0], falloff_multiply.inputs[1])
	mat.node_tree.links.new(falloff_multiply.outputs[0], color_emit.inputs[1])
	falloff_multiply.location = (-440, -440)

#### REFLECTOR ###

	# Diffuse Node
	diffuse = mat.node_tree.nodes.new(type = 'ShaderNodeBsdfDiffuse')
	diffuse.inputs[0].default_value = bpy.context.active_object.Lumiere.light_color
	mat.node_tree.links.new(color.outputs[0], diffuse.inputs[0])
	diffuse.location = (500, -220)

#### BACKFACE ###

	# Geometry Node : Backface
	backface = mat.node_tree.nodes.new(type = 'ShaderNodeNewGeometry')
	backface.location = (500, 400)

	# Transparent Node
	trans = mat.node_tree.nodes.new(type="ShaderNodeBsdfTransparent")
	trans.inputs[0].default_value = (1,1,1,1)
	trans.location = (500, 160)

#### MIX ###

	# Mix Shader Node 1 - COLOR / TEXTURE
	mix1 = mat.node_tree.nodes.new(type="ShaderNodeMixShader")
	#Light path reflection
	mat.node_tree.links.new(reflect_light_path.outputs[5], mix1.inputs[0])
	mat.node_tree.links.new(color_emit.outputs[0], mix1.inputs[1])
	mat.node_tree.links.new(texture_emit.outputs[0], mix1.inputs[2])
	mix1.location = (180, 40)

	# Mix Shader Node 3 - BACKFACE
	mix3 = mat.node_tree.nodes.new(type="ShaderNodeMixShader")
	#Link Backface
	mat.node_tree.links.new(backface.outputs[6], mix3.inputs[0])
	mat.node_tree.links.new(trans.outputs[0], mix3.inputs[1])
	mat.node_tree.links.new(mix1.outputs[0], mix3.inputs[2])
	mix3.location = (760, 80)

#### OUTPUT ###

	# Output Shader Node
	output = mat.node_tree.nodes.new(type = 'ShaderNodeOutputMaterial')
	output.location = (960, 80)
	output.select
	#Link them together
	mat.node_tree.links.new(mix3.outputs[0], output.inputs['Surface'])


# Update material
# -------------------------------------------------------------------- #
def update_mat(self, context):
	"""Update the material nodes of the lights"""

	# Get the light
	light = context.object
	if context.scene.Lumiere.link_to_light:
		light = context.scene.Lumiere.link_to_light

	# Softbox Light
	if light.type == "MESH":

		mat = get_mat_name()
		reflect_light_path = mat.node_tree.nodes["Reflect Light Path"]
		invert = mat.node_tree.nodes["Texture invert"]
		mix_col_text = mat.node_tree.nodes["Mix_Color_Text"]
		refl_mix_col_text = mat.node_tree.nodes["Reflect_Mix_Color_Text"]
		mix_col_edges = mat.node_tree.nodes["Mix_Color_Edges"]
		refl_mix_col_edges = mat.node_tree.nodes["Reflect_Mix_Color_Edges"]
		texture_map = mat.node_tree.nodes["Texture map"]
		texture_emit = mat.node_tree.nodes["Emit texture"]
		color_emit = mat.node_tree.nodes["Emit color"]
		blackbody_color = mat.node_tree.nodes["Blackbody"]
		rgb_color = mat.node_tree.nodes["RGB"]
		ies_map = mat.node_tree.nodes["Ies map"]
		ies = mat.node_tree.nodes["IES Texture"]
		diffuse = mat.node_tree.nodes["Diffuse BSDF"]
		img_text = mat.node_tree.nodes['Image Texture']
		falloff = mat.node_tree.nodes["Light Falloff"]
		falloff_multiply = mat.node_tree.nodes["Falloff multiply"]
		ies = mat.node_tree.nodes["IES Texture"]
		ies_math = mat.node_tree.nodes["IES Math"]
		mix1 = mat.node_tree.nodes["Mix Shader"]
		mix2 = mat.node_tree.nodes["Mix Shader.001"]
		colramp = mat.node_tree.nodes["ColorRamp"]
		coord = mat.node_tree.nodes["Texture Coordinate"]
		texture_mapping = mat.node_tree.nodes["Texture map"]
		gradient_mapping = mat.node_tree.nodes["Gradient map"]
		gradient_type = mat.node_tree.nodes["Gradient Texture"]

		color_emit.inputs[0].default_value = light.Lumiere.light_color
		rgb_color.outputs[0].default_value = light.Lumiere.light_color
		diffuse.inputs[0].default_value = light.Lumiere.light_color
		blackbody_color.inputs[0].default_value = light.Lumiere.blackbody
		falloff.inputs[0].default_value = light.Lumiere.energy
		ies.inputs[1].default_value = light.Lumiere.energy
			# Link Emit
		mat.node_tree.links.new(mix1.outputs[0], mix2.inputs[2])

		# Image Texture options
		if light.Lumiere.material_menu =="Texture":
			if light.Lumiere.img_name != "" :
				img_text.image = bpy.data.images[light.Lumiere.img_name]
				mat.node_tree.links.new(invert.outputs[0], refl_mix_col_text.inputs[2])
				if not light.Lumiere.img_reflect_only:
					mat.node_tree.links.new(invert.outputs[0], mix_col_text.inputs[1])
				else:
					if mix_col_text.inputs[1].links:
						mat.node_tree.links.remove(mix_col_text.inputs[1].links[0])

			else:
				if refl_mix_col_text.inputs[2].links:
					mat.node_tree.links.remove(refl_mix_col_text.inputs[2].links[0])

		# IES Texture options
		elif light.Lumiere.material_menu == "IES":
			ies_map.inputs[3].default_value[2] = light.Lumiere.ies_scale
			if light.Lumiere.ies_name != "" :
				ies.ies = bpy.data.texts[light.Lumiere.ies_name]
				mat.node_tree.links.new(ies_math.outputs[0], texture_emit.inputs[1])
			else:
				ies.ies = None
				if texture_emit.inputs[1].links:
					mat.node_tree.links.remove(texture_emit.inputs[1].links[0])

			if not light.Lumiere.ies_reflect_only:
				mat.node_tree.links.new(ies_math.outputs[0], falloff.inputs[0])
			else:
				if falloff.inputs[0].links:
					mat.node_tree.links.remove(falloff.inputs[0].links[0])

			# Linear Gradients
		if light.Lumiere.color_type == "Linear":
			gradient_type.gradient_type = "LINEAR"
			mat.node_tree.links.new(coord.outputs[2], gradient_mapping.inputs[0])
			mat.node_tree.links.new(gradient_type.outputs[0], colramp.inputs[0])
			mat.node_tree.links.new(colramp.outputs[0], mix_col_edges.inputs[2])
			mat.node_tree.links.new(colramp.outputs[0], refl_mix_col_edges.inputs[2])

			# Gradients links
			gradient_mapping.inputs[2].default_value[2] = radians(0)
			gradient_mapping.inputs[1].default_value[0] = 0
			gradient_mapping.inputs[1].default_value[1] = 0

			if light.Lumiere.rotate_ninety:
				gradient_mapping.inputs[2].default_value[2] = radians(90)


			# Spherical Gradients
		elif light.Lumiere.color_type == "Spherical":
			gradient_type.gradient_type = "SPHERICAL"
			mat.node_tree.links.new(coord.outputs[3], gradient_mapping.inputs[0])
			mat.node_tree.links.new(gradient_type.outputs[0], colramp.inputs[0])
			mat.node_tree.links.new(colramp.outputs[0], mix_col_edges.inputs[2])
			mat.node_tree.links.new(colramp.outputs[0], refl_mix_col_edges.inputs[2])
			gradient_mapping.inputs[2].default_value[2] = radians(0)


			# Color
		elif light.Lumiere.color_type == "Color":
			mat.node_tree.links.new(rgb_color.outputs[0], mix_col_edges.inputs[2])
			mat.node_tree.links.new(rgb_color.outputs[0], refl_mix_col_edges.inputs[2])

			# Blackbody
		elif light.Lumiere.color_type == "Blackbody":
			mat.node_tree.links.new(blackbody_color.outputs[0], mix_col_edges.inputs[2])
			mat.node_tree.links.new(blackbody_color.outputs[0], refl_mix_col_edges.inputs[2])

			# Reflector
		elif light.Lumiere.color_type == "Reflector":
				# Link Diffuse
			mat.node_tree.links.new(diffuse.outputs[0], mix2.inputs[2])

				# Transparent Node to black
			mat.node_tree.nodes["Transparent BSDF"].inputs[0].default_value = (0,0,0,1)

		if light.Lumiere.falloff_type == '0':
			# Quadratic
			mat.node_tree.links.new(falloff.outputs[0], falloff_multiply.inputs[0])
		elif light.Lumiere.falloff_type == '1':
			# Linear
			mat.node_tree.links.new(falloff.outputs[1], falloff_multiply.inputs[0])
		elif light.Lumiere.falloff_type == '2':
			# Constant
			mat.node_tree.links.new(falloff.outputs[2], falloff_multiply.inputs[0])

		# Blender Lamps
	else:

		# Get the material nodes of the lamp
		mat = light.data

		update_lamp(light)

# -------------------------------------------------------------------- #
def lamp_mat(light):
	"""Cycles material nodes for blender lights"""

	# Create a new material for cycles Engine.
	bpy.context.scene.render.engine = 'CYCLES'
	mat = bpy.data.materials.new(light.name)

	# Clear default nodes
	light.data.use_nodes = True
	light.data.node_tree.nodes.clear()

	# Texture Coordinate
	coord = light.data.node_tree.nodes.new(type = 'ShaderNodeTexCoord')
	coord.location = (-1300.0, 280.0)

#### TEXTURE ###
	# Mapping Texture Node
	textmap = light.data.node_tree.nodes.new(type="ShaderNodeMapping")
	light.data.node_tree.links.new(coord.outputs[1], textmap.inputs[0])
	textmap.vector_type = "POINT"
	textmap.name = "Texture Mapping"
	textmap.inputs[1].default_value[0] = 0.5
	textmap.inputs[1].default_value[1] = 0.5
	textmap.location = (-1100.0, 860.0)

	# Image Texture
	texture = light.data.node_tree.nodes.new(type = 'ShaderNodeTexImage')
	light.data.node_tree.links.new(textmap.outputs[0], texture.inputs[0])
	texture.projection_blend = 0
	texture.projection = 'FLAT'
	texture.extension = 'CLIP'
	texture.location = (-920.0, 800.0)

	# Invert Node
	invert = light.data.node_tree.nodes.new(type="ShaderNodeInvert")
	invert.name = "Texture invert"
	light.data.node_tree.links.new(texture.outputs[0], invert.inputs[1])
	invert.location = (-640.0, 740.0)

#### IES ###
	# Mapping
	ies_map = light.data.node_tree.nodes.new(type="ShaderNodeMapping")
	light.data.node_tree.links.new(coord.outputs[1], ies_map.inputs[0])
	ies_map.vector_type = "TEXTURE"
	ies_map.name = "IES map"
	ies_map.location = (-1100.0, 480.0)

	# IES
	ies = light.data.node_tree.nodes.new(type="ShaderNodeTexIES")
	ies.name = "IES"
	ies.mode = 'INTERNAL'
	light.data.node_tree.links.new(ies_map.outputs[0], ies.inputs[0])
	ies.location = (-920.0, 360.0)

	# IES Math MULTIPLY
	ies_math = light.data.node_tree.nodes.new(type = 'ShaderNodeMath')
	ies_math.name = "IES Math"
	light.data.node_tree.links.new(ies.outputs[0], ies_math.inputs[0])
	ies_math.inputs[1].default_value = 0.01
	ies_math.operation = 'MULTIPLY'
	ies_math.location = (-740, 360)

#### GRADIENT AREA LIGHT###
	# Geometry Node
	geom = light.data.node_tree.nodes.new(type="ShaderNodeNewGeometry")
	geom.location = (-1300, -220)

	# Dot Product
	dotpro = light.data.node_tree.nodes.new("ShaderNodeVectorMath")
	dotpro.operation = 'DOT_PRODUCT'
	light.data.node_tree.links.new(geom.outputs[1], dotpro.inputs[0])
	light.data.node_tree.links.new(geom.outputs[4], dotpro.inputs[1])
	dotpro.name = "Dot Product"
	dotpro.location = (-920.0, -180.0)

#### GRADIENT POINT / SPOT LIGHT ###
	# Mapping Gradient Node
	gradmap = light.data.node_tree.nodes.new(type="ShaderNodeMapping")
	light.data.node_tree.links.new(coord.outputs[1], gradmap.inputs[0])
	gradmap.vector_type = "TEXTURE"
	gradmap.name = "Gradient Mapping"
	gradmap.inputs[2].default_value[1] = radians(90)
	gradmap.location = (-1100.0, 100.0)

	# Gradient Node Quadratic
	quad_grad = light.data.node_tree.nodes.new(type="ShaderNodeTexGradient")
	light.data.node_tree.links.new(gradmap.outputs[0], quad_grad.inputs[0])
	quad_grad.location = (-920, 20)

#### ALL LIGHTS ###

	# Color Ramp
	colramp = light.data.node_tree.nodes.new(type="ShaderNodeValToRGB")
	colramp.color_ramp.elements[0].color = (1,1,1,1)
	light.data.node_tree.links.new(dotpro.outputs[1], colramp.inputs[0])
	colramp.location = (-740.0, 100.0)

	# Light Falloff
	falloff = light.data.node_tree.nodes.new(type = 'ShaderNodeLightFalloff')
	light.data.node_tree.links.new(ies_math.outputs[0], falloff.inputs[0])
	falloff.inputs[0].default_value = 10
	falloff.location = (-100.0, 120.0)

	# RGB Node
	color = light.data.node_tree.nodes.new(type = 'ShaderNodeRGB')
	color.location = (-100.0, 760.0)

	# Blackbody : Horizon daylight kelvin temperature for sun
	blackbody = light.data.node_tree.nodes.new("ShaderNodeBlackbody")
	blackbody.inputs[0].default_value = 4000
	blackbody.location = (-100.0, 560.0)

	# Mix Color Texture
	mix_color_text = light.data.node_tree.nodes.new(type = 'ShaderNodeMixRGB')
	mix_color_text.name = "Mix_Color_Text"
	mix_color_text.blend_type = 'MULTIPLY'
	mix_color_text.inputs[0].default_value = 1
	mix_color_text.inputs['Color1'].default_value = [1,1,1,1]
	mix_color_text.inputs['Color2'].default_value = [1,1,1,1]
	mix_color_text.location = (-100, 440)

#### FALLOFF from Metin Seven ###

	# Ligth Path
	falloff_path = light.data.node_tree.nodes.new(type = 'ShaderNodeLightPath')
	falloff_path.name = "Fallof light path"
	falloff_path.location = (-460, -160)

	# Math DIVIDE
	falloff_divide = light.data.node_tree.nodes.new(type = 'ShaderNodeMath')
	falloff_divide.name = "Falloff divide"
	falloff_divide.inputs[1].default_value = 20
	falloff_divide.operation = 'DIVIDE'
	light.data.node_tree.links.new(falloff_path.outputs[7], falloff_divide.inputs[0])
	falloff_divide.location = (-280, -160)

	# Color Ramp Node
	falloff_colramp = light.data.node_tree.nodes.new(type="ShaderNodeValToRGB")
	falloff_colramp.name = "Falloff colRamp"
	light.data.node_tree.links.new(falloff_divide.outputs[0], falloff_colramp.inputs['Fac'])
	falloff_colramp.color_ramp.interpolation = 'LINEAR'
	falloff_colramp.color_ramp.elements[0].color = (1,1,1,1)
	falloff_colramp.inputs[0].default_value = 0
	falloff_colramp.color_ramp.elements[1].color = (1,1,1,1)
	falloff_colramp.location = (-100, -100)

	# Math MULTIPLY
	falloff_multiply = light.data.node_tree.nodes.new(type = 'ShaderNodeMath')
	falloff_multiply.name = "Falloff multiply"
	falloff_multiply.operation = 'MULTIPLY'
	light.data.node_tree.links.new(falloff.outputs[0], falloff_multiply.inputs[1])
	light.data.node_tree.links.new(falloff_colramp.outputs[0], falloff_multiply.inputs[0])
	falloff_multiply.location = (200, 140)

#### OUTPUT ###

	# Emission Node
	emit = light.data.node_tree.nodes.new(type = 'ShaderNodeEmission')
	## EEVEE doesn't work with nodes, use data color instead.
	emit.inputs[0].default_value = (1,1,1,1)
	light.data.node_tree.links.new(falloff_multiply.outputs[0], emit.inputs[1])
	emit.location = (360.0, 320.0)

	# Output Shader Node
	output = light.data.node_tree.nodes.new(type = 'ShaderNodeOutputLight')
	output.location = (540.0, 300.0)

	#Link them together
	light.data.node_tree.links.new(emit.outputs[0], output.inputs['Surface'])

# -------------------------------------------------------------------- #
def update_lamp(light):
	"""Update the material nodes of the blender lights"""

	mat = light.data

	falloff = mat.node_tree.nodes["Light Falloff"]
	# Falloff doesn't work with sun lamp
	emit = mat.node_tree.nodes["Emission"]
	if light.Lumiere.light_type == "Sun":
		light.data.node_tree.links.new(falloff.outputs[0], emit.inputs[1])
		emit_falloff = mat.node_tree.nodes["Emission"]
	else:
		emit_falloff = mat.node_tree.nodes["Falloff multiply"]
		light.data.node_tree.links.new(emit_falloff.outputs[0], emit.inputs[1])

	blackbody_color = mat.node_tree.nodes["Blackbody"]
	rgb = mat.node_tree.nodes["RGB"]
	ies = mat.node_tree.nodes["IES"]
	ies_map = mat.node_tree.nodes["IES map"]
	ies_math = mat.node_tree.nodes["IES Math"]
	colramp = mat.node_tree.nodes['ColorRamp']
	gradient = mat.node_tree.nodes["Gradient Texture"]
	area_grad = mat.node_tree.nodes["Dot Product"]
	mix_color_text =  mat.node_tree.nodes["Mix_Color_Text"]
	img_text = mat.node_tree.nodes['Image Texture']
	invert = mat.node_tree.nodes['Texture invert']
	coord = mat.node_tree.nodes['Texture Coordinate']
	texture_mapping = mat.node_tree.nodes['Texture Mapping']
	geometry = mat.node_tree.nodes['Geometry']

	rgb.outputs[0].default_value = light.Lumiere.light_color
	blackbody_color.inputs[0].default_value = light.Lumiere.blackbody
	ies.inputs[1].default_value = light.Lumiere.energy

	#--EEVEE
	falloff.inputs[0].default_value = light.Lumiere.energy
	mat.energy = light.Lumiere.energy
	mat.color = (1,1,1) #light.Lumiere.light_color[:3]

		# IES Texture options
	if light.Lumiere.material_menu == "IES":
		ies_map.inputs[3].default_value[2] = light.Lumiere.ies_scale
		if light.Lumiere.ies_name != "" :
			ies.ies = bpy.data.texts[light.Lumiere.ies_name]
			mat.node_tree.links.new(ies_math.outputs[0], falloff.inputs[0])
		else:
			ies.ies = None

		# Color for all the light
	if light.Lumiere.color_type == "Color":
		mat.node_tree.links.new(rgb.outputs[0], emit.inputs[0])

		# Color for all the light
	elif light.Lumiere.color_type == "Blackbody":
		mat.node_tree.links.new(blackbody_color.outputs[0], emit.inputs[0])

		# SPOT / POINT
	if light.Lumiere.light_type in ("Spot", "Point", "Area"):
		mat.node_tree.links.new(ies_math.outputs[0], falloff.inputs[0])

		if light.Lumiere.material_menu =="Texture" and light.Lumiere.img_name != "":
			mat.node_tree.links.new(invert.outputs[0], mix_color_text.inputs[1])
			mat.node_tree.links.new(mix_color_text.outputs[0], emit.inputs[0])
			texture_mapping.inputs[3].default_value[0] = texture_mapping.inputs[3].default_value[1] = light.Lumiere.img_scale
			if light.Lumiere.light_type == "Area" :
				mat.node_tree.links.new(geometry.outputs[5], texture_mapping.inputs[0])
				texture_mapping.inputs[1].default_value[0] = texture_mapping.inputs[1].default_value[1] = - ((light.Lumiere.img_scale - 1) * .5)
			else:
				mat.node_tree.links.new(coord.outputs[1], texture_mapping.inputs[0])
				texture_mapping.inputs[1].default_value[0] = .5
				texture_mapping.inputs[1].default_value[1] = .5

			if light.Lumiere.img_name != "":
				img_text.image = bpy.data.images[light.Lumiere.img_name]
			invert.inputs[0].default_value = light.Lumiere.img_invert

			# mat.node_tree.links.new(coord.outputs[1], texture_mapping.inputs[0])
		elif light.Lumiere.material_menu =="Texture" and light.Lumiere.img_name == "":
			if mix_color_text.inputs[1].links:
				mat.node_tree.links.remove(mix_color_text.inputs[1].links[0])

		if light.Lumiere.color_type == "Gradient":
			if light.Lumiere.light_type == "Area" :
				mat.node_tree.links.new(area_grad.outputs[1], colramp.inputs[0])
			else:
				mat.node_tree.links.new(gradient.outputs[1], colramp.inputs[0])
			mat.node_tree.links.new(colramp.outputs[0], mix_color_text.inputs[2])
			mat.node_tree.links.new(mix_color_text.outputs[0], emit.inputs[0])
			## Color data are multiplied, reset it !
			mat.color = (1,1,1)

		if light.Lumiere.falloff_type == '0':
			# Quadratic
			mat.node_tree.links.new(falloff.outputs[0], emit_falloff.inputs[1])
		elif light.Lumiere.falloff_type == '1':
			# Linear
			mat.node_tree.links.new(falloff.outputs[1], emit_falloff.inputs[1])
		elif light.Lumiere.falloff_type == '2':
			# Constant
			mat.node_tree.links.new(falloff.outputs[2], emit_falloff.inputs[1])


# -------------------------------------------------------------------- #
def create_world(self, context):
	"""Cycles material nodes for the woorld environment light"""

	# Create a new world if not exist
	world = ""

	for w in bpy.data.worlds:
		if w.name == "Lumiere_world":
			world = bpy.data.worlds['Lumiere_world']
			context.scene.world = world

	if world == "":
		context.scene.world = bpy.data.worlds.new("Lumiere_world")
		world = context.scene.world

	world.use_nodes= True
	world.node_tree.nodes.clear()

	# Use multiple importance sampling for the world
	context.scene.world.cycles.sample_as_light = True

	# Texture Coordinate
	coord = world.node_tree.nodes.new(type = 'ShaderNodeTexCoord')
	coord.location = (-1660.0, 200.0)

	# Mapping Node HDRI
	textmap = world.node_tree.nodes.new(type="ShaderNodeMapping")
	textmap.vector_type = "POINT"
	world.node_tree.links.new(coord.outputs[0], textmap.inputs[0])
	textmap.location = (-1480.0, 460.0)

	# Mapping Node Reflection
	reflectmap = world.node_tree.nodes.new(type="ShaderNodeMapping")
	reflectmap.vector_type = "POINT"
	world.node_tree.links.new(coord.outputs[0], reflectmap.inputs[0])
	reflectmap.location = (-1480.0, 60.0)

#### BLUR ###
	# Blur from  Bartek Skorupa : Source https://www.youtube.com/watch?v=kAUmLcXhUj0&feature=youtu.be&t=23m58s

	# Noise Texture
	noisetext = world.node_tree.nodes.new(type="ShaderNodeTexNoise")
	noisetext.inputs[2].default_value = 1000
	noisetext.inputs[3].default_value = 16
	noisetext.inputs[4].default_value = 200
	noisetext.location = (-1300.0, -100.0)

	# Substract
	substract = world.node_tree.nodes.new(type="ShaderNodeMixRGB")
	substract.blend_type = 'SUBTRACT'
	substract.inputs[0].default_value = 1
	world.node_tree.links.new(noisetext.outputs[1], substract.inputs['Color1'])
	substract.location = (-1120.0, -120.0)

	# Add
	add = world.node_tree.nodes.new(type="ShaderNodeMixRGB")
	add.blend_type = 'ADD'
	add.inputs[0].default_value = 0
	world.node_tree.links.new(reflectmap.outputs[0], add.inputs['Color1'])
	world.node_tree.links.new(substract.outputs[0], add.inputs['Color2'])
	add.location = (-940.0, 80.0)

#### HDR texture ###

	# Environment Texture
	envtext = world.node_tree.nodes.new(type = 'ShaderNodeTexEnvironment')
	world.node_tree.links.new(textmap.outputs[0], envtext.inputs[0])
	envtext.location = (-1300, 460)

	# Bright / Contrast
	bright = world.node_tree.nodes.new(type = 'ShaderNodeBrightContrast')
	world.node_tree.links.new(envtext.outputs[0], bright.inputs[0])
	bright.location = (-1020, 420)

	# Gamma
	gamma = world.node_tree.nodes.new(type = 'ShaderNodeGamma')
	world.node_tree.links.new(bright.outputs[0], gamma.inputs[0])
	gamma.location = (-840, 400)

	# Hue / Saturation / Value
	hue = world.node_tree.nodes.new(type = 'ShaderNodeHueSaturation')
	hue.name = "Hdr hue"
	world.node_tree.links.new(gamma.outputs[0], hue.inputs[4])
	hue.location = (-660, 460)

	# Exposure value
	hdr_exposure_val = world.node_tree.nodes.new(type = 'ShaderNodeValue')
	hdr_exposure_val.name = "Hdr exposure value"
	hdr_exposure_val.outputs[0].default_value = 0
	hdr_exposure_val.location = (-840.0, 260.0)

	# Exposure power
	hdr_exposure_pow = world.node_tree.nodes.new(type = 'ShaderNodeMath')
	hdr_exposure_pow.name = "Hdr exposure power"
	hdr_exposure_pow.operation = 'POWER'
	hdr_exposure_pow.inputs[0].default_value = 2
	world.node_tree.links.new(hdr_exposure_val.outputs[0], hdr_exposure_pow.inputs[1])
	hdr_exposure_pow.location = (-660.0, 260.0)

	# Exposure Hue Multiply
	hdr_exposure_multiply = world.node_tree.nodes.new("ShaderNodeMixRGB")
	hdr_exposure_multiply.blend_type = 'MULTIPLY'
	hdr_exposure_multiply.name = "Hdr exposure multiply"
	hdr_exposure_multiply.inputs[0].default_value = 1
	world.node_tree.links.new(hue.outputs[0], hdr_exposure_multiply.inputs[1])
	world.node_tree.links.new(hdr_exposure_pow.outputs[0], hdr_exposure_multiply.inputs[2])
	hdr_exposure_multiply.location = (-440.0, 380.0)

#### Reflection texture ###

	# Reflection Texture
	reflectext = world.node_tree.nodes.new(type = 'ShaderNodeTexEnvironment')
	world.node_tree.links.new(add.outputs[0], reflectext.inputs[0])
	reflectext.location = (-760, 80)

	# Bright / Contrast
	bright2 = world.node_tree.nodes.new(type = 'ShaderNodeBrightContrast')
	world.node_tree.links.new(reflectext.outputs[0], bright2.inputs[0])
	bright2.location = (-480, 40)

	# Gamma
	gamma2 = world.node_tree.nodes.new(type = 'ShaderNodeGamma')
	world.node_tree.links.new(bright2.outputs[0], gamma2.inputs[0])
	gamma2.location = (-300, 20)

	# Hue / Saturation / Value
	hue2 = world.node_tree.nodes.new(type = 'ShaderNodeHueSaturation')
	world.node_tree.links.new(gamma2.outputs[0], hue2.inputs[4])
	hue2.name = "Reflect hue"
	hue2.location = (-120, 80)

	# Exposure value
	reflect_exposure_val = world.node_tree.nodes.new(type = 'ShaderNodeValue')
	reflect_exposure_val.name = "Reflect exposure value"
	reflect_exposure_val.outputs[0].default_value = 0
	reflect_exposure_val.location = (-300.0, 180.0)

	# Exposure power
	reflect_exposure_pow = world.node_tree.nodes.new(type = 'ShaderNodeMath')
	reflect_exposure_pow.name = "Reflect exposure power"
	reflect_exposure_pow.operation = 'POWER'
	reflect_exposure_pow.inputs[0].default_value = 2
	world.node_tree.links.new(reflect_exposure_val.outputs[0], reflect_exposure_pow.inputs[1])
	reflect_exposure_pow.location = (-120.0, 260.0)

	# Exposure Hue Multiply
	reflect_exposure_multiply = world.node_tree.nodes.new("ShaderNodeMixRGB")
	reflect_exposure_multiply.blend_type = 'MULTIPLY'
	reflect_exposure_multiply.name = "Reflect exposure multiply"
	reflect_exposure_multiply.inputs[0].default_value = 1
	world.node_tree.links.new(hue2.outputs[0], reflect_exposure_multiply.inputs[1])
	world.node_tree.links.new(reflect_exposure_pow.outputs[0], reflect_exposure_multiply.inputs[2])
	reflect_exposure_multiply.location = (80.0, 100.0)

	# Light path
	lightpath = world.node_tree.nodes.new(type = 'ShaderNodeLightPath')
	lightpath.location = (120, 620)

	# Math
	math = world.node_tree.nodes.new(type = 'ShaderNodeMath')
	math.use_clamp = True
	math.operation = 'ADD'
	world.node_tree.links.new(lightpath.outputs[0], math.inputs[0])
	world.node_tree.links.new(lightpath.outputs[3], math.inputs[1])
	math.location = (300, 460)

	# Background 01
	background1 = world.node_tree.nodes.new(type = 'ShaderNodeBackground')
	background1.inputs[0].default_value = (0.8,0.8,0.8,1.0)
	background1.name = "Hdr background"
	background1.location = (300, 260)

	# Background 02
	background2 = world.node_tree.nodes.new(type = 'ShaderNodeBackground')
	background2.name = "Reflect background"
	background2.inputs[0].default_value = (0,0,0,1.0)
	background2.location = (300, 120)

#### SKY ###

	# Sky texture
	sky = world.node_tree.nodes.new(type = 'ShaderNodeTexSky')
	sky.location = (-940.0, -140.0)

	# Sky Contribution
	sky_contrib = world.node_tree.nodes.new(type = 'ShaderNodeMath')
	sky_contrib.operation = 'ADD'
	sky_contrib.name = "Sky contribution"
	sky_contrib.inputs[1].default_value = 4.5
	sky_contrib.location = (-480.0, -100.0)
	world.node_tree.links.new(sky.outputs[0], sky_contrib.inputs[0])

	# Sun Geometry
	sun_geo = world.node_tree.nodes.new(type = 'ShaderNodeNewGeometry')
	sun_geo.name = "Sun geometry"
	sun_geo.location = (-1380.0, -380.0)

	# Sun Normal
	sun_normal = world.node_tree.nodes.new(type = 'ShaderNodeNormal')
	sun_normal.name = "Sun normal"
	world.node_tree.links.new(sun_geo.outputs[0], sun_normal.inputs[0])
	sun_normal.location = (-1200.0, -380.0)

	# Sun Value
	sun_value = world.node_tree.nodes.new(type = 'ShaderNodeValue')
	sun_value.name = "Sun value"
	sun_value.outputs[0].default_value = 0.99999
	sun_value.location = (-1380.0, -620.0)

	# Sun Size
	sun_size = world.node_tree.nodes.new(type = 'ShaderNodeMath')
	sun_size.name = "Sun size"
	sun_size.operation = 'MULTIPLY'
	sun_size.inputs[0].default_value = 50
	sun_size.use_clamp = False
	sun_size.location = (-1380.0, -740.0)

	# Value Power
	value_power = world.node_tree.nodes.new(type = 'ShaderNodeMath')
	value_power.name = "Value power"
	value_power.operation = 'POWER'
	world.node_tree.links.new(sun_value.outputs[0], value_power.inputs[0])
	world.node_tree.links.new(sun_size.outputs[0], value_power.inputs[1])
	value_power.use_clamp = True
	value_power.location = (-1200.0, -580.0)

	# Sun Substract
	sun_substract = world.node_tree.nodes.new(type = 'ShaderNodeMath')
	sun_substract.name = "Sun substract"
	sun_substract.operation = 'SUBTRACT'
	world.node_tree.links.new(sun_normal.outputs[1], sun_substract.inputs[0])
	world.node_tree.links.new(value_power.outputs[0], sun_substract.inputs[1])
	sun_substract.location = (-1020.0, -380.0)

	# Sun Power
	sun_power = world.node_tree.nodes.new(type = 'ShaderNodeMath')
	sun_power.name = "Sun power"
	sun_power.operation = 'POWER'
	world.node_tree.links.new(sun_substract.outputs[0], sun_power.inputs[0])
	sun_power.inputs[1].default_value = 0.230
	sun_power.location = (-840.0, -380.0)

	# Sun Contribution
	sun_contrib = world.node_tree.nodes.new(type = 'ShaderNodeMath')
	sun_contrib.name = "Sun contribution"
	sun_contrib.operation = 'MULTIPLY'
	sun_contrib.inputs[0].default_value = 500
	sun_contrib.use_clamp = False
	sun_contrib.location = (-840.0, -560.0)

	# Sun Multiply
	sun_multiply = world.node_tree.nodes.new(type = 'ShaderNodeMath')
	sun_multiply.name = "Sun multiply"
	sun_multiply.operation = 'MULTIPLY'
	world.node_tree.links.new(sun_power.outputs[0], sun_multiply.inputs[0])
	world.node_tree.links.new(sun_contrib.outputs[0], sun_multiply.inputs[1])
	sun_multiply.inputs[1].default_value = 5000.0
	sun_multiply.location = (-660.0, -380.0)

	# Blackbody
	blackbody = world.node_tree.nodes.new("ShaderNodeBlackbody")
	blackbody.location = (-660.0, -580.0)

	# Color Sun Contribution
	col_sun_contrib = world.node_tree.nodes.new("ShaderNodeMixRGB")
	col_sun_contrib.blend_type = 'COLOR'
	col_sun_contrib.name = "Color Sun Contribution"
	col_sun_contrib.inputs[0].default_value = 1
	world.node_tree.links.new(sun_multiply.outputs[0], col_sun_contrib.inputs[1])
	world.node_tree.links.new(blackbody.outputs[0], col_sun_contrib.inputs[2])
	col_sun_contrib.location = (-480.0, -380.0)

	# Add Sun Contribution
	add_sun_contrib = world.node_tree.nodes.new("ShaderNodeMixRGB")
	add_sun_contrib.blend_type = 'ADD'
	add_sun_contrib.name = "Add Sun Contribution"
	add_sun_contrib.inputs[0].default_value = 1
	world.node_tree.links.new(sky.outputs[0], add_sun_contrib.inputs[1])
	world.node_tree.links.new(col_sun_contrib.outputs[0], add_sun_contrib.inputs[2])
	add_sun_contrib.location = (-300.0, -260.0)

	# Add Sun + Sky
	add_sun_sky = world.node_tree.nodes.new(type = 'ShaderNodeMath')
	add_sun_sky.operation = 'ADD'
	add_sun_sky.name = "Add Sun + Sky"
	add_sun_sky.inputs[0].default_value = 1
	world.node_tree.links.new(sky_contrib.outputs[0], add_sun_sky.inputs[0])
	world.node_tree.links.new(add_sun_contrib.outputs[0], add_sun_sky.inputs[1])
	add_sun_sky.location = (-120.0, -100.0)

	# Mix Shader Node
	mix = world.node_tree.nodes.new(type="ShaderNodeMixShader")
	world.node_tree.links.new(math.outputs[0], mix.inputs[0])
	world.node_tree.links.new(background1.outputs[0], mix.inputs[1])
	world.node_tree.links.new(background2.outputs[0], mix.inputs[2])
	mix.location = (480, 300)

	# Output
	output = world.node_tree.nodes.new("ShaderNodeOutputWorld")
	output.location = (660, 280)
	world.node_tree.links.new(background1.outputs[0], output.inputs[0])

# -------------------------------------------------------------------- #
def update_world(self, context):
	"""Update the material nodes of the blender world environment"""
	light = bpy.context.object
	if context.scene.Lumiere.link_to_light:
		light = context.scene.Lumiere.link_to_light
	world = bpy.data.worlds['Lumiere_world']

	sky_color = world.node_tree.nodes["Sky Texture"]
	background1 = world.node_tree.nodes["Hdr background"]
	background2 = world.node_tree.nodes["Reflect background"]
	hdr_text = world.node_tree.nodes['Environment Texture']
	hdr_bright = world.node_tree.nodes['Bright/Contrast']
	hdr_gamma = world.node_tree.nodes['Gamma']
	hdr_exposure = world.node_tree.nodes['Hdr exposure multiply']
	reflect_exposure = world.node_tree.nodes['Reflect exposure multiply']
	reflect_text = world.node_tree.nodes['Environment Texture.001']
	lightpath = world.node_tree.nodes['Light Path']
	math_path = world.node_tree.nodes['Math']
	mix = world.node_tree.nodes['Mix Shader']
	output = world.node_tree.nodes["World Output"]
	sun_contrib = world.node_tree.nodes["Sun contribution"]
	sun_size = world.node_tree.nodes["Sun size"]
	sky_contrib = world.node_tree.nodes["Sky contribution"]
	add_sun_contrib = world.node_tree.nodes["Add Sun Contribution"]
	add_sun_sky = world.node_tree.nodes["Add Sun + Sky"]
	hdr_mapping = world.node_tree.nodes['Mapping']
	hdr_mapping.inputs[2].default_value[2] = -radians(context.scene.Lumiere.env_hdr_rotation)
	reflect_mapping = world.node_tree.nodes['Mapping.001']
	reflect_mapping.inputs[2].default_value[2] = -radians(context.scene.Lumiere.env_reflect_rotation)

	if context.scene.Lumiere.env_type == "Sky":
		world.node_tree.links.new(background1.outputs[0], output.inputs[0])
		world.node_tree.links.new(add_sun_contrib.outputs[0], background1.inputs[0])
		world.node_tree.links.new(add_sun_sky.outputs[0], background1.inputs[1])
		sun_contrib.inputs[1].default_value = bpy.context.scene.Lumiere.env_sun_contrib
		sun_size.inputs[1].default_value = bpy.context.scene.Lumiere.env_sun_size
		sky_contrib.inputs[1].default_value = bpy.context.scene.Lumiere.env_sky_contrib

	elif context.scene.Lumiere.env_type == "Texture":
		if background1.inputs[1].links:
			world.node_tree.links.remove(background1.inputs[1].links[0])
		if context.scene.Lumiere.env_hdr_name != "":
			world.node_tree.links.new(hdr_text.outputs[0], hdr_bright.inputs[0])
			world.node_tree.links.new(hdr_exposure.outputs[0], background1.inputs[0])
			world.node_tree.links.new(lightpath.outputs[0], math_path.inputs[0])
			world.node_tree.links.new(lightpath.outputs[3], math_path.inputs[1])
			world.node_tree.links.new(math_path.outputs[0], mix.inputs[0])
			hdr_text.image = bpy.data.images[context.scene.Lumiere.env_hdr_name]
			world.node_tree.links.new(background1.outputs[0], output.inputs[0])
		else:
			if background1.inputs[0].links:
				world.node_tree.links.remove(background1.inputs[0].links[0])
		if context.scene.Lumiere.env_reflect_toggle:
			world.node_tree.links.new(background2.outputs[0], mix.inputs[2])
			world.node_tree.links.new(mix.outputs[0], output.inputs[0])
			if context.scene.Lumiere.env_reflect_name != "":
				reflect_text.image = bpy.data.images[context.scene.Lumiere.env_reflect_name]
				world.node_tree.links.new(reflect_exposure.outputs[0], background2.inputs[0])
			else:
				if background2.inputs[0].links:
					world.node_tree.links.remove(background2.inputs[0].links[0])
		else:
			world.node_tree.links.new(background1.outputs[0], output.inputs[0])

	elif context.scene.Lumiere.env_type == "None":
		bpy.data.worlds.remove(bpy.data.worlds['Lumiere_world'])



# Utilities
# -------------------------------------------------------------------- #
"""Return the name of the material of the light"""
def get_mat_name():
	light = bpy.context.object
	if bpy.context.object.type == 'MESH':
		mat = light.active_material
	else:
		mat = bpy.data.lights[light.data.name]

	return(mat)
