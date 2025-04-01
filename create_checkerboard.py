import bpy
import os

# Path to the checkerboard image (adjust if needed)
image_path = "./data/checkerboard_10.png"  # Assumes it's in the same directory as the .blend file

# Clean up
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Create a cube and scale it to make it thin (like a flat tile)
bpy.ops.mesh.primitive_cube_add(size=1)
cube = bpy.context.object
cube.name = "ThinFloor"
thickness = 0.01
cube.scale = (100, 100, thickness)
cube.location = (0, 0, thickness/2)

# Apply the scale
bpy.ops.object.transform_apply(scale=True)

# Create a new material
material = bpy.data.materials.new(name="CheckerboardMaterial")
material.use_nodes = True
cube.data.materials.append(material)

# Get the node tree
nodes = material.node_tree.nodes
links = material.node_tree.links

# Clear existing nodes
for node in nodes:
    nodes.remove(node)

# Create required nodes
output_node = nodes.new(type="ShaderNodeOutputMaterial")
output_node.location = (400, 0)

principled_node = nodes.new(type="ShaderNodeBsdfPrincipled")
principled_node.location = (200, 0)
links.new(principled_node.outputs["BSDF"], output_node.inputs["Surface"])

image_node = nodes.new(type="ShaderNodeTexImage")
image_node.location = (-200, 0)

# Load the image
img_abs_path = bpy.path.abspath(image_path)
if os.path.exists(img_abs_path):
    image_node.image = bpy.data.images.load(img_abs_path)
else:
    print(f"Image not found at {img_abs_path}")

# Add UV and Mapping nodes for texture repetition
tex_coord_node = nodes.new(type="ShaderNodeTexCoord")
tex_coord_node.location = (-600, 0)

mapping_node = nodes.new(type="ShaderNodeMapping")
mapping_node.location = (-400, 0)
mapping_node.inputs["Scale"].default_value = (20, 20, 20)  # Adjust if you want to repeat it

# Link all nodes
links.new(tex_coord_node.outputs["UV"], mapping_node.inputs["Vector"])
links.new(mapping_node.outputs["Vector"], image_node.inputs["Vector"])
links.new(image_node.outputs["Color"], principled_node.inputs["Base Color"])

# Unwrap the cube's UVs
bpy.context.view_layer.objects.active = cube
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.uv.smart_project()
bpy.ops.object.mode_set(mode='OBJECT')

print("Thin cube with checkerboard texture applied!")

