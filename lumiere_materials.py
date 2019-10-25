import bpy
import os
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

#---Create a new material for cycles Engine.
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
#---Texture Coordinate
	coord = mat.node_tree.nodes.new(type = 'ShaderNodeTexCoord')
	coord.location = (-2260.0, -360.0)

#---Mapping Node
	gradmap = mat.node_tree.nodes.new(type="ShaderNodeMapping")
	gradmap.name = "Gradient map"
	mat.node_tree.links.new(coord.outputs[2], gradmap.inputs[0])
	gradmap.vector_type = "TEXTURE"
	gradmap.location = (-1920, -580)

#---Gradient Node Linear
	linear_grad = mat.node_tree.nodes.new(type="ShaderNodeTexGradient")
	mat.node_tree.links.new(gradmap.outputs[0], linear_grad.inputs[0])
	linear_grad.location = (-1560, -640)

#---Color Ramp Node
	colramp = mat.node_tree.nodes.new(type="ShaderNodeValToRGB")
	mat.node_tree.links.new(linear_grad.outputs[0], colramp.inputs['Fac'])
	colramp.color_ramp.elements[0].color = (1,1,1,1)
	colramp.inputs[0].default_value = 0
	colramp.location = (-1380, -640)

#---Invert Node
	edge_invert = mat.node_tree.nodes.new(type="ShaderNodeInvert")
	edge_invert.name = "Edges invert"
	mat.node_tree.links.new(coord.outputs[0], edge_invert.inputs[1])
	edge_invert.location = (-2100.0, 400.0)

#---Multiply Node
	edge_mult1 = mat.node_tree.nodes.new(type="ShaderNodeMixRGB")
	edge_mult1.name = "Edges Multiply1"
	edge_mult1.blend_type = 'MULTIPLY'
	edge_mult1.inputs[0].default_value = 1
	mat.node_tree.links.new(edge_invert.outputs[0], edge_mult1.inputs[1])
	mat.node_tree.links.new(coord.outputs[0], edge_mult1.inputs[2])
	edge_mult1.location = (-1920.0, 400.0)

#---Separate Node
	edge_sep = mat.node_tree.nodes.new(type="ShaderNodeSeparateXYZ")
	edge_sep.name = "Edges Separate"
	mat.node_tree.links.new(edge_mult1.outputs[0], edge_sep.inputs[0])
	edge_sep.location = (-1740.0, 440.0)

#---Value Node
	edge_value = mat.node_tree.nodes.new(type="ShaderNodeValue")
	edge_value.name = "Edges value"
	edge_value.outputs[0].default_value = 4
	edge_value.location = (-1740.0, 260.0)

#---Multiply Node 2
	edge_mult2 = mat.node_tree.nodes.new(type="ShaderNodeMath")
	edge_mult2.name = "Edges Multiply2"
	edge_mult2.operation = 'MULTIPLY'
	mat.node_tree.links.new(edge_sep.outputs[0], edge_mult2.inputs[0])
	mat.node_tree.links.new(edge_value.outputs[0], edge_mult2.inputs[1])
	edge_mult2.location = (-1560.0, 580.0)

#---Multiply Node 3
	edge_mult3 = mat.node_tree.nodes.new(type="ShaderNodeMath")
	edge_mult3.name = "Edges Multiply3"
	edge_mult3.operation = 'MULTIPLY'
	mat.node_tree.links.new(edge_sep.outputs[1], edge_mult3.inputs[0])
	mat.node_tree.links.new(edge_value.outputs[0], edge_mult3.inputs[1])
	edge_mult3.location = (-1560.0, 380.0)

#---Multiply Node 4
	edge_mult4 = mat.node_tree.nodes.new(type="ShaderNodeMath")
	edge_mult4.name = "Edges Multiply4"
	edge_mult4.operation = 'MULTIPLY'
	mat.node_tree.links.new(edge_mult2.outputs[0], edge_mult4.inputs[0])
	mat.node_tree.links.new(edge_mult3.outputs[0], edge_mult4.inputs[1])
	edge_mult4.location = (-1380.0, 580.0)

#---Power
	edge_power = mat.node_tree.nodes.new(type="ShaderNodeMath")
	edge_power.name = "Edges Power"
	edge_power.operation = 'POWER'
	mat.node_tree.links.new(edge_value.outputs[0], edge_power.inputs[0])
	edge_power.inputs[1].default_value = 0.5
	edge_power.location = (-1380.0, 340.0)

#---Color Ramp Node
	edge_colramp = mat.node_tree.nodes.new(type="ShaderNodeValToRGB")
	edge_colramp.name = "Edges ColRamp"
	mat.node_tree.links.new(edge_mult4.outputs[0], edge_colramp.inputs['Fac'])
	edge_colramp.color_ramp.interpolation = 'B_SPLINE'
	edge_colramp.color_ramp.elements[0].color = (0,0,0,1)
	edge_colramp.inputs[0].default_value = 0
	# edge_colramp.color_ramp.elements.new(1)
	edge_colramp.color_ramp.elements[1].color = (1,1,1,1)
	edge_colramp.location = (-1200, 540)

#---Multiply Node 5
	edge_mult5 = mat.node_tree.nodes.new(type="ShaderNodeMath")
	edge_mult5.name = "Edges Multiply5"
	edge_mult5.operation = 'MULTIPLY'
	mat.node_tree.links.new(edge_colramp.outputs[0], edge_mult5.inputs[0])
	mat.node_tree.links.new(edge_power.outputs[0], edge_mult5.inputs[1])
	edge_mult5.location = (-920.0, 440.0)

#---Mix Edges / Color for reflection only
	refl_mix_color_edges = mat.node_tree.nodes.new(type = 'ShaderNodeMixRGB')
	refl_mix_color_edges.name = "Reflect_Mix_Color_Edges"
	refl_mix_color_edges.blend_type = 'MULTIPLY'
	refl_mix_color_edges.inputs[0].default_value = 1
	refl_mix_color_edges.inputs['Color1'].default_value = [1,1,1,1]
	refl_mix_color_edges.inputs['Color2'].default_value = [1,1,1,1]
	mat.node_tree.links.new(edge_mult5.outputs[0], refl_mix_color_edges.inputs[1])
	refl_mix_color_edges.location = (-700, 360)

#---Mix Color Edges for lighting
	mix_color_edges = mat.node_tree.nodes.new(type = 'ShaderNodeMixRGB')
	mix_color_edges.name = "Mix_Color_Edges"
	mix_color_edges.blend_type = 'MULTIPLY'
	mix_color_edges.inputs[0].default_value = 1
	mix_color_edges.inputs['Color1'].default_value = [1,1,1,1]
	mix_color_edges.inputs['Color2'].default_value = [1,1,1,1]
	mix_color_edges.location = (-720, -180)

#---Light path
	reflect_light_path = mat.node_tree.nodes.new(type = 'ShaderNodeLightPath')
	reflect_light_path.name = "Reflect Light Path"
	reflect_light_path.location = (-220, 380)

#### IMAGE TEXTURE ###

#---Mapping Node
	textmap = mat.node_tree.nodes.new(type="ShaderNodeMapping")
	textmap.name = "Texture map"
	mat.node_tree.links.new(coord.outputs[2], textmap.inputs[0])
	textmap.vector_type = "TEXTURE"
	textmap.location = (-1920, 160)

#---Image Texture
	texture = mat.node_tree.nodes.new(type = 'ShaderNodeTexImage')
	mat.node_tree.links.new(textmap.outputs[0], texture.inputs[0])
	texture.projection = 'FLAT'
	texture.extension = 'REPEAT'
	texture.location = (-1560, 160)

#---Invert Node
	texture_invert = mat.node_tree.nodes.new(type="ShaderNodeInvert")
	texture_invert.name = "Texture invert"
	texture_invert.inputs[0].default_value = 0
	mat.node_tree.links.new(texture.outputs[0], texture_invert.inputs[1])
	texture_invert.location = (-1280.0, 140.0)

#---Mix Texture / Color for reflection only
	refl_mix_color_text = mat.node_tree.nodes.new(type = 'ShaderNodeMixRGB')
	refl_mix_color_text.name = "Reflect_Mix_Color_Text"
	refl_mix_color_text.blend_type = 'MULTIPLY'
	refl_mix_color_text.inputs[0].default_value = 1
	refl_mix_color_text.inputs['Color1'].default_value = [1,1,1,1]
	refl_mix_color_text.inputs['Color2'].default_value = [1,1,1,1]
	mat.node_tree.links.new(refl_mix_color_edges.outputs[0], refl_mix_color_text.inputs[1])
	refl_mix_color_text.location = (-500, 240)

#---Mix Color Texture for lighting
	mix_color_text = mat.node_tree.nodes.new(type = 'ShaderNodeMixRGB')
	mix_color_text.name = "Mix_Color_Text"
	mix_color_text.blend_type = 'MULTIPLY'
	mix_color_text.inputs[0].default_value = 1
	mix_color_text.inputs['Color1'].default_value = [1,1,1,1]
	mix_color_text.inputs['Color2'].default_value = [1,1,1,1]
	mat.node_tree.links.new(mix_color_edges.outputs[0], mix_color_text.inputs[2])
	mix_color_text.location = (-500, -80)

#### COLOR ###

#---RGB Node
	color = mat.node_tree.nodes.new(type = 'ShaderNodeRGB')
	mat.node_tree.links.new(color.outputs[0], mix_color_edges.inputs[2])
	mat.node_tree.links.new(color.outputs[0], refl_mix_color_edges.inputs[2])
	color.location = (-1380, -400)

#---Blackbody
	blackbody = mat.node_tree.nodes.new(type = 'ShaderNodeBlackbody')
	blackbody.location = (-1220, -500)

#### IES ###

#---Mapping Node
	ies_map = mat.node_tree.nodes.new(type="ShaderNodeMapping")
	ies_map.name = "Ies map"
	mat.node_tree.links.new(coord.outputs[3], ies_map.inputs[0])
	ies_map.vector_type = "TEXTURE"
	ies_map.location = (-1920, -200)
	ies_map.inputs[1].default_value[2] = 0.5

#---Mapping File texture
	ies = mat.node_tree.nodes.new(type="ShaderNodeTexIES")
	ies.name = "IES Texture"
	mat.node_tree.links.new(ies_map.outputs[0], ies.inputs[0])
	ies.mode = 'INTERNAL'
	ies.inputs[1].default_value = light.Lumiere.energy
	ies.location = (-1560, -200)

#---Math MULTIPLY
	ies_math_mul = mat.node_tree.nodes.new(type = 'ShaderNodeMath')
	ies_math_mul.name = "IES Math"
	mat.node_tree.links.new(ies.outputs[0], ies_math_mul.inputs[0])
	ies_math_mul.inputs[1].default_value = 0.01
	ies_math_mul.operation = 'MULTIPLY'
	ies_math_mul.location = (-1380, -200)

#### INTENSITY ###

#---Light Falloff
	falloff = mat.node_tree.nodes.new(type = 'ShaderNodeLightFalloff')
	mat.node_tree.links.new(ies_math_mul.outputs[0], falloff.inputs[0])
	falloff.inputs[0].default_value = 10
	falloff.location = (-720, -440)

#---Texture Emission Node
	texture_emit = mat.node_tree.nodes.new(type = 'ShaderNodeEmission')
	texture_emit.name = "Emit texture"
	texture_emit.inputs[0].default_value = bpy.context.active_object.Lumiere.light_color
	mat.node_tree.links.new(refl_mix_color_text.outputs[0], texture_emit.inputs[0])
	mat.node_tree.links.new(falloff.outputs[0], texture_emit.inputs[1])
	texture_emit.location = (-220, 20)

#---Color Emission Node
	color_emit = mat.node_tree.nodes.new(type = 'ShaderNodeEmission')
	color_emit.name = "Emit color"
	color_emit.inputs[0].default_value = bpy.context.active_object.Lumiere.light_color
	mat.node_tree.links.new(mix_color_text.outputs[0], color_emit.inputs[0])
	mat.node_tree.links.new(falloff.outputs[0], color_emit.inputs[1])
	color_emit.location = (-220, -160)

#### REFLECTOR ###

#---Diffuse Node
	diffuse = mat.node_tree.nodes.new(type = 'ShaderNodeBsdfDiffuse')
	diffuse.inputs[0].default_value = bpy.context.active_object.Lumiere.light_color
	mat.node_tree.links.new(color.outputs[0], diffuse.inputs[0])
	diffuse.location = (500, -220)

#### BACKFACE ###

#---Geometry Node : Backface
	backface = mat.node_tree.nodes.new(type = 'ShaderNodeNewGeometry')
	backface.location = (500, 400)

#---Transparent Node
	trans = mat.node_tree.nodes.new(type="ShaderNodeBsdfTransparent")
	trans.inputs[0].default_value = (1,1,1,1)
	trans.location = (500, 160)

#### MIX ###

#---Mix Shader Node 1 - COLOR / TEXTURE
	mix1 = mat.node_tree.nodes.new(type="ShaderNodeMixShader")
	#Light path reflection
	mat.node_tree.links.new(reflect_light_path.outputs[5], mix1.inputs[0])
	mat.node_tree.links.new(color_emit.outputs[0], mix1.inputs[1])
	mat.node_tree.links.new(texture_emit.outputs[0], mix1.inputs[2])
	mix1.location = (180, 40)

#---Mix Shader Node 3 - BACKFACE
	mix3 = mat.node_tree.nodes.new(type="ShaderNodeMixShader")
	#Link Backface
	mat.node_tree.links.new(backface.outputs[6], mix3.inputs[0])
	mat.node_tree.links.new(trans.outputs[0], mix3.inputs[1])
	mat.node_tree.links.new(mix1.outputs[0], mix3.inputs[2])
	mix3.location = (760, 80)

#### OUTPUT ###

#---Output Shader Node
	output = mat.node_tree.nodes.new(type = 'ShaderNodeOutputMaterial')
	output.location = (960, 80)
	output.select
	#Link them together
	mat.node_tree.links.new(mix3.outputs[0], output.inputs['Surface'])


# Update material
#########################################################################################################
def update_mat(self, context):
	"""Update the material nodes of the lights"""

	# Get the light
	light = context.object

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
		#---Link Emit
		mat.node_tree.links.new(mix1.outputs[0], mix2.inputs[2])

	#---Image Texture options
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

	#---IES Texture options
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

		#---Linear Gradients
		if light.Lumiere.color_type == "Linear":
			gradient_type.gradient_type = "LINEAR"
			mat.node_tree.links.new(coord.outputs[2], gradient_mapping.inputs[0])
			mat.node_tree.links.new(gradient_type.outputs[0], colramp.inputs[0])
			mat.node_tree.links.new(colramp.outputs[0], mix_col_edges.inputs[2])
			mat.node_tree.links.new(colramp.outputs[0], refl_mix_col_edges.inputs[2])

		#---Gradients links
			gradient_mapping.inputs[2].default_value[2] = radians(0)
			gradient_mapping.inputs[1].default_value[0] = 0
			gradient_mapping.inputs[1].default_value[1] = 0

			if light.Lumiere.rotate_ninety:
				gradient_mapping.inputs[2].default_value[2] = radians(90)


		#---Spherical Gradients
		elif light.Lumiere.color_type == "Spherical":
			gradient_type.gradient_type = "SPHERICAL"
			mat.node_tree.links.new(coord.outputs[3], gradient_mapping.inputs[0])
			mat.node_tree.links.new(gradient_type.outputs[0], colramp.inputs[0])
			mat.node_tree.links.new(colramp.outputs[0], mix_col_edges.inputs[2])
			mat.node_tree.links.new(colramp.outputs[0], refl_mix_col_edges.inputs[2])
			gradient_mapping.inputs[2].default_value[2] = radians(0)


		#---Color
		elif light.Lumiere.color_type == "Color":
			mat.node_tree.links.new(rgb_color.outputs[0], mix_col_edges.inputs[2])
			mat.node_tree.links.new(rgb_color.outputs[0], refl_mix_col_edges.inputs[2])

		#---Blackbody
		elif light.Lumiere.color_type == "Blackbody":
			mat.node_tree.links.new(blackbody_color.outputs[0], mix_col_edges.inputs[2])
			mat.node_tree.links.new(blackbody_color.outputs[0], refl_mix_col_edges.inputs[2])


		#---Reflector
		elif light.Lumiere.color_type == "Reflector":
			#---Link Diffuse
			mat.node_tree.links.new(diffuse.outputs[0], mix2.inputs[2])

			#---Transparent Node to black
			mat.node_tree.nodes["Transparent BSDF"].inputs[0].default_value = (0,0,0,1)

		if light.Lumiere.falloff_type == '0':
			# Quadratic
			mat.node_tree.links.new(falloff.outputs[0], color_emit.inputs[1])
		elif light.Lumiere.falloff_type == '1':
			# Linear
			mat.node_tree.links.new(falloff.outputs[1], color_emit.inputs[1])
		elif light.Lumiere.falloff_type == '2':
			# Constant
			mat.node_tree.links.new(falloff.outputs[2], color_emit.inputs[1])

	#---Blender Lamps
	else:

	#---Get the lamp or the softbox link to the duplivert
		light = context.object
	#---Get the material nodes of the lamp
		mat = light.data

		update_lamp(light)

#########################################################################################################
"""Update the material nodes of the blender lights"""
def update_lamp(light):

	mat = light.data

	falloff = mat.node_tree.nodes["Light Falloff"]
	emit = mat.node_tree.nodes["Emission"]
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

	#---IES Texture options
	if light.Lumiere.material_menu == "IES":
		ies_map.inputs[3].default_value[2] = light.Lumiere.ies_scale
		if light.Lumiere.ies_name != "" :
			ies.ies = bpy.data.texts[light.Lumiere.ies_name]
			mat.node_tree.links.new(ies_math.outputs[0], falloff.inputs[0])
		else:
			ies.ies = None

	#---Color for all the light
	if light.Lumiere.color_type == "Color":
		mat.node_tree.links.new(rgb.outputs[0], emit.inputs[0])


	#---Color for all the light
	elif light.Lumiere.color_type == "Blackbody":
		mat.node_tree.links.new(blackbody_color.outputs[0], emit.inputs[0])


	#---SPOT / POINT
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
			mat.node_tree.links.new(falloff.outputs[0], emit.inputs[1])
		elif light.Lumiere.falloff_type == '1':
			# Linear
			mat.node_tree.links.new(falloff.outputs[1], emit.inputs[1])
		elif light.Lumiere.falloff_type == '2':
			# Constant
			mat.node_tree.links.new(falloff.outputs[2], emit.inputs[1])


#########################################################################################################
"""Cycles material nodes for blender lights"""
def lamp_mat(light):

#---Create a new material for cycles Engine.
	bpy.context.scene.render.engine = 'CYCLES'
	mat = bpy.data.materials.new(light.name)


#---Clear default nodes
	light.data.use_nodes = True
	light.data.node_tree.nodes.clear()

#---Texture Coordinate
	coord = light.data.node_tree.nodes.new(type = 'ShaderNodeTexCoord')
	coord.location = (-1300.0, 280.0)

#### TEXTURE ###
#---Mapping Texture Node
	textmap = light.data.node_tree.nodes.new(type="ShaderNodeMapping")
	light.data.node_tree.links.new(coord.outputs[1], textmap.inputs[0])
	textmap.vector_type = "POINT"
	textmap.name = "Texture Mapping"
	textmap.inputs[1].default_value[0] = 0.5
	textmap.inputs[1].default_value[1] = 0.5
	textmap.location = (-1100.0, 800.0)

#---Image Texture
	texture = light.data.node_tree.nodes.new(type = 'ShaderNodeTexImage')
	light.data.node_tree.links.new(textmap.outputs[0], texture.inputs[0])
	texture.projection_blend = 0
	texture.projection = 'FLAT'
	texture.extension = 'CLIP'
	texture.location = (-740.0, 800.0)

#---Invert Node
	invert = light.data.node_tree.nodes.new(type="ShaderNodeInvert")
	invert.name = "Texture invert"
	light.data.node_tree.links.new(texture.outputs[0], invert.inputs[1])
	invert.location = (-460.0, 740.0)

#### IES ###
#---Mapping
	ies_map = light.data.node_tree.nodes.new(type="ShaderNodeMapping")
	light.data.node_tree.links.new(coord.outputs[1], ies_map.inputs[0])
	ies_map.vector_type = "TEXTURE"
	ies_map.name = "IES map"
	ies_map.location = (-1100.0, 480.0)

#---IES
	ies = light.data.node_tree.nodes.new(type="ShaderNodeTexIES")
	ies.name = "IES"
	ies.mode = 'INTERNAL'
	light.data.node_tree.links.new(ies_map.outputs[0], ies.inputs[0])
	ies.location = (-740.0, 360.0)

#---IES Math MULTIPLY
	ies_math = light.data.node_tree.nodes.new(type = 'ShaderNodeMath')
	ies_math.name = "IES Math"
	light.data.node_tree.links.new(ies.outputs[0], ies_math.inputs[0])
	ies_math.inputs[1].default_value = 0.01
	ies_math.operation = 'MULTIPLY'
	ies_math.location = (-560, 360)

#### GRADIENT AREA LIGHT###
#---Geometry Node
	geom = light.data.node_tree.nodes.new(type="ShaderNodeNewGeometry")
	geom.location = (-1300, -120)

#---Dot Product
	dotpro = light.data.node_tree.nodes.new("ShaderNodeVectorMath")
	dotpro.operation = 'DOT_PRODUCT'
	light.data.node_tree.links.new(geom.outputs[1], dotpro.inputs[0])
	light.data.node_tree.links.new(geom.outputs[4], dotpro.inputs[1])
	dotpro.name = "Dot Product"
	dotpro.location = (-740.0, -140.0)


#### GRADIENT POINT / SPOT LIGHT ###
#---Mapping Gradient Node
	gradmap = light.data.node_tree.nodes.new(type="ShaderNodeMapping")
	light.data.node_tree.links.new(coord.outputs[1], gradmap.inputs[0])
	gradmap.vector_type = "TEXTURE"
	gradmap.name = "Gradient Mapping"
	gradmap.inputs[2].default_value[1] = radians(90)
	gradmap.location = (-1100.0, 160.0)

#---Gradient Node Quadratic
	quad_grad = light.data.node_tree.nodes.new(type="ShaderNodeTexGradient")
	light.data.node_tree.links.new(gradmap.outputs[0], quad_grad.inputs[0])
	quad_grad.location = (-740, 20)

#### ALL LIGHTS ###

#---Color Ramp
	colramp = light.data.node_tree.nodes.new(type="ShaderNodeValToRGB")
	colramp.color_ramp.elements[0].color = (1,1,1,1)
	light.data.node_tree.links.new(dotpro.outputs[1], colramp.inputs[0])
	colramp.location = (-560.0, 100.0)

#---Light Falloff
	falloff = light.data.node_tree.nodes.new(type = 'ShaderNodeLightFalloff')
	light.data.node_tree.links.new(ies_math.outputs[0], falloff.inputs[0])
	falloff.inputs[0].default_value = 10
	falloff.location = (-20.0, 120.0)

#---RGB Node
	color = light.data.node_tree.nodes.new(type = 'ShaderNodeRGB')
	color.location = (-20.0, 760.0)

#---Blackbody : Horizon daylight kelvin temperature for sun
	blackbody = light.data.node_tree.nodes.new("ShaderNodeBlackbody")
	blackbody.inputs[0].default_value = 4000
	blackbody.location = (-20.0, 560.0)

#---Mix Color Texture
	mix_color_text = light.data.node_tree.nodes.new(type = 'ShaderNodeMixRGB')
	mix_color_text.name = "Mix_Color_Text"
	mix_color_text.blend_type = 'MULTIPLY'
	mix_color_text.inputs[0].default_value = 1
	mix_color_text.inputs['Color1'].default_value = [1,1,1,1]
	mix_color_text.inputs['Color2'].default_value = [1,1,1,1]
	mix_color_text.location = (-20, 440)

#---Emission Node
	emit = light.data.node_tree.nodes.new(type = 'ShaderNodeEmission')
	## EEVEE doesn't work with nodes, use data color instead.
	emit.inputs[0].default_value = (1,1,1,1)
	light.data.node_tree.links.new(falloff.outputs[0], emit.inputs[1])
	emit.location = (180.0, 320.0)

#---Output Shader Node
	output = light.data.node_tree.nodes.new(type = 'ShaderNodeOutputLight')
	output.location = (360.0, 300.0)

	#Link them together
	light.data.node_tree.links.new(emit.outputs[0], output.inputs['Surface'])

# Utilities
#########################################################################################################
"""Return the name of the material of the light"""
def get_mat_name():
	light = bpy.context.object
	if bpy.context.object.type == 'MESH':
		mat = light.active_material
	else:
		mat = bpy.data.lights[light.data.name]

	return(mat)
