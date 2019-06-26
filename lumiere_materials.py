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
"""Cycles material nodes for the Softbox light"""
def softbox_mat(light):
	print("CREATE MATERIAL SOFTBOX")

#---Create a new material for cycles Engine.
	if bpy.context.scene.render.engine != 'CYCLES':
		bpy.context.scene.render.engine = 'CYCLES'

	print("LIGHT MAT: ", light.active_material)

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

#### EDGES ###

# TEST 3
#
# #---Mix Color Texture
# 	mix_edges = mat.node_tree.nodes.new(type = 'ShaderNodeMixRGB')
# 	mix_edges.name = "mix_edges"
# 	mix_edges.blend_type = 'MIX'
# 	mix_edges.inputs[0].default_value = 0.5
# 	mix_edges.inputs['Color1'].default_value = [1,1,1,1]
# 	mix_edges.inputs['Color2'].default_value = [0,0,0,1]
# 	mat.node_tree.links.new(coord.outputs[3], mix_edges.inputs[1])
# 	mix_edges.location = (-1360, 340)
#
# #---Grandient Node Spherical
# 	grad_edges = mat.node_tree.nodes.new(type="ShaderNodeTexGradient")
# 	mat.node_tree.links.new(mix_edges.outputs[0], grad_edges.inputs[0])
# 	grad_edges.gradient_type = 'SPHERICAL'
# 	grad_edges.location = (-1180, 300)
#
# #---Color Ramp Node Edges
# 	colramp_edges = mat.node_tree.nodes.new(type="ShaderNodeValToRGB")
# 	colramp_edges.name = "colramp_edges"
# 	mat.node_tree.links.new(grad_edges.outputs[1], colramp_edges.inputs['Fac'])
# 	colramp_edges.color_ramp.elements[0].color = (0,0,0,1)
# 	colramp_edges.inputs[0].default_value = 0
# 	colramp_edges.location = (-1000, 360)

# TEST 2

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

# TEST 1

# #---Mapping Node
# 	edgemap = mat.node_tree.nodes.new(type="ShaderNodeMapping")
# 	edgemap.name = "Edges map"
# 	edgemap.translation[0] = 0.5
# 	edgemap.translation[1] = 0.5
# 	mat.node_tree.links.new(coord.outputs[2], edgemap.inputs[0])
# 	edgemap.vector_type = "TEXTURE"
# 	edgemap.location = (-1540, 840)
#
# #---Grandient Node Quadratic
# 	edge_grad = mat.node_tree.nodes.new(type="ShaderNodeTexGradient")
# 	mat.node_tree.links.new(edgemap.outputs[0], edge_grad.inputs[0])
# 	edge_grad.gradient_type = 'QUADRATIC_SPHERE'
# 	edge_grad.location = (-1180, 760)
#
# #---Color Ramp Node
# 	edge_colramp = mat.node_tree.nodes.new(type="ShaderNodeValToRGB")
# 	mat.node_tree.links.new(edge_grad.outputs[0], edge_colramp.inputs['Fac'])
# 	edge_colramp.color_ramp.interpolation = 'B_SPLINE'
# 	edge_colramp.color_ramp.elements[0].color = (0,0,0,1)
# 	edge_colramp.inputs[0].default_value = 0
# 	edge_colramp.color_ramp.elements.new(1)
# 	edge_colramp.color_ramp.elements[1].color = (1,1,1,1)
# 	edge_colramp.location = (-1000, 760)
#
#---Light path
	reflect_light_path = mat.node_tree.nodes.new(type = 'ShaderNodeLightPath')
	reflect_light_path.name = "Reflect Light Path"
	reflect_light_path.location = (-220, 380)
#
# #---Light path Math ADD
# 	edge_math = mat.node_tree.nodes.new(type = 'ShaderNodeMath')
# 	edge_math.name = "Edge math"
# 	mat.node_tree.links.new(edge_light_path.outputs[5], edge_math.inputs[0])
# 	edge_math.inputs[0].default_value = -1
# 	edge_math.inputs[1].default_value = -1
# 	edge_math.operation = 'ADD'
# 	edge_math.location = (-960, 500)
#
# #---Math SUBTRACT
# 	edges_math_sub = mat.node_tree.nodes.new(type = 'ShaderNodeMath')
# 	edges_math_sub.name = "Edges math sub"
# 	mat.node_tree.links.new(edge_colramp.outputs[0], edges_math_sub.inputs[0])
# 	mat.node_tree.links.new(edge_math.outputs[0], edges_math_sub.inputs[1])
# 	edges_math_sub.operation = 'SUBTRACT'
# 	edges_math_sub.location = (-720, 680)
#
# #---Emission Node Edges
# 	edges_emit = mat.node_tree.nodes.new(type = 'ShaderNodeEmission')
# 	edges_emit.name = "Emit edges"
# 	edges_emit.inputs[0].default_value = (0, 0, 0, 1)
# 	edges_emit.inputs[1].default_value = 0
# 	edges_emit.location = (-720, 500)

#### IMAGE TEXTURE ###

#---Mapping Node
	textmap = mat.node_tree.nodes.new(type="ShaderNodeMapping")
	textmap.name = "Texture map"
	mat.node_tree.links.new(coord.outputs[3], textmap.inputs[0])
	textmap.vector_type = "TEXTURE"
	textmap.location = (-1920, 160)

#---Image Texture
	texture = mat.node_tree.nodes.new(type = 'ShaderNodeTexImage')
	mat.node_tree.links.new(textmap.outputs[0], texture.inputs[0])
	texture.projection = 'BOX'
	texture.extension = 'CLIP'
	texture.location = (-1560, 160)

#---Invert Node
	texture_invert = mat.node_tree.nodes.new(type="ShaderNodeInvert")
	texture_invert.name = "Texture invert"
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


# #---Bright / Contrast
# 	bright = mat.node_tree.nodes.new(type = 'ShaderNodeBrightContrast')
# 	mat.node_tree.links.new(texture.outputs[0], bright.inputs[0])
# 	bright.location = (-1280, 60)
#
# #---Gamma
# 	gamma = mat.node_tree.nodes.new(type = 'ShaderNodeGamma')
# 	mat.node_tree.links.new(bright.outputs[0], gamma.inputs[0])
# 	gamma.location = (-1100, 40)
#
# #---Hue / Saturation / Value
# 	hue = mat.node_tree.nodes.new(type = 'ShaderNodeHueSaturation')
# 	mat.node_tree.links.new(gamma.outputs[0], hue.inputs[4])
# 	hue.location = (-920, 80)

#---Math SUBTRACT
	# text_math_sub = mat.node_tree.nodes.new(type = 'ShaderNodeMath')
	# text_math_sub.name = "Texture math sub"
	# mat.node_tree.links.new(hue.outputs[0], text_math_sub.inputs[0])
	# mat.node_tree.links.new(edge_light_path.outputs[5], text_math_sub.inputs[1])
	# text_math_sub.operation = 'SUBTRACT'
	# text_math_sub.location = (-720, 320)

#### COLOR ###

#---RGB Node
	color = mat.node_tree.nodes.new(type = 'ShaderNodeRGB')
	mat.node_tree.links.new(color.outputs[0], mix_color_edges.inputs[2])
	mat.node_tree.links.new(color.outputs[0], refl_mix_color_edges.inputs[2])
	color.location = (-1380, -400)

#---Blackbody
	blackbody = mat.node_tree.nodes.new(type = 'ShaderNodeBlackbody')
	blackbody.location = (-1220, -500)

#---Mix Color Edges
	# mix_color_edges = mat.node_tree.nodes.new(type = 'ShaderNodeMixRGB')
	# mix_color_edges.name = "Mix_Color_Edges"
	# mix_color_edges.blend_type = 'MULTIPLY'
	# mix_color_edges.inputs[0].default_value = 1
	# mix_color_edges.inputs['Color1'].default_value = [1,1,1,1]
	# mix_color_edges.inputs['Color2'].default_value = [1,1,1,1]
	# mat.node_tree.links.new(edge_mult5.outputs[0], mix_color_edges.inputs[1])
	# mat.node_tree.links.new(color.outputs[0], mix_color_edges.inputs[2])
	# mix_color_edges.location = (-720, -300)

#### IES ###

#---Mapping Node
	ies_map = mat.node_tree.nodes.new(type="ShaderNodeMapping")
	ies_map.name = "Ies map"
	mat.node_tree.links.new(coord.outputs[3], ies_map.inputs[0])
	ies_map.vector_type = "TEXTURE"
	ies_map.location = (-1920, -200)
	ies_map.translation[2] = 0.5

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

# #---Mix Shader Node 2 - EDGES
# 	mix2 = mat.node_tree.nodes.new(type="ShaderNodeMixShader")
# 	#Light path reflection
# 	mat.node_tree.links.new(edges_math_sub.outputs[0], mix2.inputs[0])
# 	mat.node_tree.links.new(edges_emit.outputs[0], mix2.inputs[1])
# 	mat.node_tree.links.new(mix1.outputs[0], mix2.inputs[2])
# 	mix2.location = (240, 100)

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
	# mat.node_tree.nodes["Emission"].inputs[1].default_value = 1
	#Link them together
	mat.node_tree.links.new(mix3.outputs[0], output.inputs['Surface'])

#---RGB Color
	# color = mat.node_tree.nodes.new(type="ShaderNodeRGB")
	# color.location = (-940, -260)
	# mat.node_tree.links.new(color.outputs[0], edge_mix_color.inputs[1])
	# mat.node_tree.links.new(edge_mix_color.outputs[0], emit.inputs[0])
	# mat.node_tree.nodes["RGB"].outputs[0].default_value = (.8, .8, .8, 1)


# Update material
#########################################################################################################
"""Update the material nodes of the lights"""
def update_mat(self, context):

	# Get the light
	light = context.object #get_object(context, self.lightname)

	# Softbox Light
	if light.Lumiere.light_type == "Softbox":

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
		color_emit.inputs[0].default_value = light.Lumiere.light_color
		rgb_color = mat.node_tree.nodes["RGB"]
		rgb_color.outputs[0].default_value = light.Lumiere.light_color
		ies_map = mat.node_tree.nodes["Ies map"]
		ies = mat.node_tree.nodes["IES Texture"]
		diffuse = mat.node_tree.nodes["Diffuse BSDF"]
		diffuse.inputs[0].default_value = light.Lumiere.light_color
		img_text = mat.node_tree.nodes['Image Texture']
		falloff = mat.node_tree.nodes["Light Falloff"]
		falloff.inputs[0].default_value = light.Lumiere.energy
		ies = mat.node_tree.nodes["IES Texture"]
		ies.inputs[1].default_value = light.Lumiere.energy
		ies_math = mat.node_tree.nodes["IES Math"]
		mix1 = mat.node_tree.nodes["Mix Shader"]
		mix2 = mat.node_tree.nodes["Mix Shader.001"]
		colramp = mat.node_tree.nodes["ColorRamp"]
		coord = mat.node_tree.nodes["Texture Coordinate"]
		texture_mapping = mat.node_tree.nodes["Texture map"]
		gradient_mapping = mat.node_tree.nodes["Gradient map"]
		gradient_type = mat.node_tree.nodes["Gradient Texture"]
		#---Link Emit
		mat.node_tree.links.new(mix1.outputs[0], mix2.inputs[2])

	#---Image Texture options
		if light.Lumiere.material_menu =="Texture":
			if light.Lumiere.img_name != "" :
				img_text.image = bpy.data.images[light.Lumiere.img_name]
				texture_map.scale[1] = texture_map.scale[0] = light.Lumiere.img_scale
				texture_map.translation[1] = texture_map.translation[0] = - light.Lumiere.img_scale / 2
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
			ies_map.scale[2] = light.Lumiere.ies_scale
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
			mat.node_tree.links.new(gradient_type.outputs[0], colramp.inputs[0])
			mat.node_tree.links.new(colramp.outputs[0], mix_col_edges.inputs[2])
			mat.node_tree.links.new(colramp.outputs[0], refl_mix_col_edges.inputs[2])

		#---Gradients links
			gradient_mapping.rotation[2] = radians(0)
			gradient_mapping.translation[0] = 0
			gradient_mapping.translation[1] = 0

			if light.Lumiere.rotate_ninety:
				gradient_mapping.rotation[2] = radians(90)

		#---Spherical Gradients
		if light.Lumiere.color_type == "Spherical":
			gradient_type.gradient_type = "SPHERICAL"
			mat.node_tree.links.new(gradient_type.outputs[0], colramp.inputs[0])
			mat.node_tree.links.new(colramp.outputs[0], mix_col_edges.inputs[2])
			mat.node_tree.links.new(colramp.outputs[0], refl_mix_col_edges.inputs[2])
			gradient_mapping.rotation[2] = radians(0)
			gradient_mapping.translation[0] = 0.5
			gradient_mapping.translation[1] = 0.5


		#---Color
		elif light.Lumiere.color_type == "Color":
			mat.node_tree.links.new(rgb_color.outputs[0], mix_col_edges.inputs[2])
			mat.node_tree.links.new(rgb_color.outputs[0], refl_mix_col_edges.inputs[2])


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

	# mat = bpy.data.lamps["LAMP_" + self.lightname]
	# bpy.context.scene.render.engine = 'CYCLES'
	mat = light.data

	falloff = mat.node_tree.nodes["Light Falloff"]
	emit = mat.node_tree.nodes["Emission"]
	rgb = mat.node_tree.nodes["RGB"]
	ies = mat.node_tree.nodes["IES"]
	ies_map = mat.node_tree.nodes["IES map"]
	ies_math = mat.node_tree.nodes["IES Math"]
	colramp = mat.node_tree.nodes['ColorRamp']
	gradient = mat.node_tree.nodes["Gradient Texture"]
	area_grad = mat.node_tree.nodes["Dot Product"]
	mix_color_text =  mat.node_tree.nodes["Mix_Color_Text"]
	img_text = mat.node_tree.nodes['Image Texture']
	invert = mat.node_tree.nodes['Invert']
	coord = mat.node_tree.nodes['Texture Coordinate']
	texture_mapping = mat.node_tree.nodes['Texture Mapping']


	rgb.outputs[0].default_value = light.Lumiere.light_color
	# emit.inputs[0].default_value = light.Lumiere.light_color
	ies.inputs[1].default_value = light.Lumiere.energy
	# mat.node_tree.links.new(falloff.outputs[int(light.Lumiere.falloff_type)], emit.inputs[1])

	#--EEVEE
	falloff.inputs[0].default_value = light.Lumiere.energy
	mat.energy = light.Lumiere.energy
	mat.color = light.Lumiere.light_color[:3]
	# mat.shadow_buffer_soft = mat.shadow_soft_size


	#---IES Texture options
	if light.Lumiere.material_menu == "IES":
		ies_map.scale[2] = light.Lumiere.ies_scale
		if light.Lumiere.ies_name != "" :
			ies.ies = bpy.data.texts[light.Lumiere.ies_name]
			mat.node_tree.links.new(ies_math.outputs[0], falloff.inputs[0])
		else:
			ies.ies = None

	# #---Color for all the light
	if light.Lumiere.color_type == "Color":
		# if emit.inputs[0].links:
		# 	mat.node_tree.links.remove(emit.inputs[0].links[0])
		## EEVEE doesn't work with nodes, use data color instead.
		# mat.node_tree.links.new(rgb.outputs[0], emit.inputs[0])
		# if falloff.inputs[0].links:
		# 	mat.node_tree.links.remove(falloff.inputs[0].links[0])
		#
		if mix_color_text.inputs[2].links:
			mat.node_tree.links.remove(mix_color_text.inputs[2].links[0])


	#---SPOT / POINT
	if light.Lumiere.light_type in ("Spot", "Point", "AREA"):
		mat.node_tree.links.new(ies_math.outputs[0], falloff.inputs[0])

		if light.Lumiere.material_menu =="Texture" and light.Lumiere.img_name != "":
			mat.node_tree.links.new(invert.outputs[0], mix_color_text.inputs[1])
			mat.node_tree.links.new(mix_color_text.outputs[0], emit.inputs[0])
			texture_mapping.scale[0] = texture_mapping.scale[1] = light.Lumiere.img_scale
			if light.Lumiere.light_type == "AREA" :
				mat.node_tree.links.new(geometry.outputs[5], texture_mapping.inputs[0])
				texture_mapping.translation[0] = texture_mapping.translation[1] = - ((light.Lumiere.img_scale - 1) * .5)
			else:
				mat.node_tree.links.new(coord.outputs[1], texture_mapping.inputs[0])
				texture_mapping.translation[0] = .5
				texture_mapping.translation[1] = .5

			if light.Lumiere.img_name != "":
				img_text.image = bpy.data.images[light.Lumiere.img_name]
			invert.inputs[0].default_value = light.Lumiere.img_invert

			mat.node_tree.links.new(coord.outputs[1], texture_mapping.inputs[0])
		elif light.Lumiere.material_menu =="Texture" and light.Lumiere.img_name == "":
			if mix_color_text.inputs[1].links:
				mat.node_tree.links.remove(mix_color_text.inputs[1].links[0])

		if light.Lumiere.color_type == "Gradient":
			if light.Lumiere.light_type == "AREA" :
				mat.node_tree.links.new(area_grad.outputs[1], colramp.inputs[0])
			else:
				mat.node_tree.links.new(gradient.outputs[1], colramp.inputs[0])
			mat.node_tree.links.new(colramp.outputs[0], mix_color_text.inputs[2])
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
	# light = bpy.context.scene.objects.active
	# mat = get_mat_name()
	# Si area light, utiliser Parametric > Mapping (Point x=0 / y=0 / z=0)
	# Si autre, utiliser Normal > Mapping (Point x=0.5 / y=0.5 / z=0)

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
	textmap.translation[0] = 0.5
	textmap.translation[1] = 0.5
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
	gradmap.rotation[1] = radians(90)
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
	light.data.node_tree.links.new(invert.outputs[0], mix_color_text.inputs[0])
	mix_color_text.location = (-20, 440)

#---Emission Node
	emit = light.data.node_tree.nodes.new(type = 'ShaderNodeEmission')
	## EEVEE doesn't work with nodes, use data color instead.
	emit.inputs[0].default_value = (1,1,1,1)
	# emit.inputs[0].default_value = bpy.context.active_object.Lumiere.light_color
	# light.data.node_tree.links.new(color.outputs[0], emit.inputs[0])
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
