import argparse
import sys

import bpy
import numpy as np

# add sys path
sys.path.append(".")
import utils

class ArgumentParserBlender(argparse.ArgumentParser):
    def _get_argv_after_doubledash(self):
        try:
            idx = sys.argv.index("--")
            return sys.argv[idx + 1 :]  # the list after '--'
        except ValueError as e:  # '--' not in the list:
            raise e
            return []

    # overrides superclass
    def parse_args(self):
        return super().parse_args(args=self._get_argv_after_doubledash())

parser = ArgumentParserBlender()
parser.add_argument(
    "--flow_path",
    type=str,
    required=True,
    help="Path to 3D tracks (.npy)"
)
parser.add_argument(
    "--render",
    action="store_true",
    help="Should render?"
)

def create_mat():
    mat = bpy.data.materials.new(name="InstancedSphereMat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Clear the default nodes.
    nodes.clear()

    # Create shader nodes.
    output_node = nodes.new(type='ShaderNodeOutputMaterial')
    output_node.location = (300, 0)

    principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    principled.location = (0, 0)

    attribute_node = nodes.new(type='ShaderNodeAttribute')
    attribute_node.location = (-600, 0)
    attribute_node.attribute_name = "color"
    attribute_node.attribute_type = "INSTANCER"

    # add color ramp node
    color_ramp_node = nodes.new(type='ShaderNodeValToRGB')
    color_ramp_node.location = (-300, 0)
    color_ramp_node.color_ramp.color_mode = "HSV"
    color_ramp_node.color_ramp.hue_interpolation = "FAR"
    color_ramp_node.color_ramp.elements[0].color = (0.0, 0.0, 1.0, 1.0)
    color_ramp_node.color_ramp.elements[1].color = (1.0, 0.0, 0.0, 1.0)

    # connect attribute to ramp
    links.new(attribute_node.outputs["Color"], color_ramp_node.inputs["Fac"])

    # connect ramp to shader
    links.new(color_ramp_node.outputs["Color"], principled.inputs["Base Color"])
    links.new(color_ramp_node.outputs["Color"], principled.inputs["Emission Color"])
    principled.inputs["Emission Strength"].default_value = 1.0

    # connect shader to output
    links.new(principled.outputs["BSDF"], output_node.inputs["Surface"])

    return mat

# parse args
args = parser.parse_args()

# clear the scene
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

# Load the NumPy file. It is assumed to be of shape (T, N, 3)
tracks = np.load(args.flow_path)
T, N, _ = tracks.shape
print(f"Loaded point cloud tracks with {T} frames and {N} points per frame.")

is_alive = np.ones((N, ), dtype=bool)
for i in range(T):
    points = tracks[i]
    is_alive = is_alive & (points < 1000).all(axis=1)
    points[~is_alive] = 1000.0

# --- CREATE INITIAL MESH OBJECT ---
# Create a new mesh using the points from the first frame.
mesh = bpy.data.meshes.new("PointCloudMesh")
vertices = [tuple(v) for v in tracks[0]]
mesh.from_pydata(vertices, [], [])
mesh.update()

# Create an object from the mesh and link it to the current collection.
pc_obj = bpy.data.objects.new("PointCloud", mesh)
bpy.context.collection.objects.link(pc_obj)

# set up geometry nodes for point instance
gn_mod = pc_obj.modifiers.new(name="PointInstancer", type='NODES')
node_group = bpy.data.node_groups.new("PointInstancerTree", 'GeometryNodeTree')
gn_mod.node_group = node_group

# short cuts
nodes = node_group.nodes
links = node_group.links
interface = node_group.interface

# Remove any default nodes.
nodes.clear()

# Create the input nodes
node_input = nodes.new("NodeGroupInput")
node_input.location = (-300, 0)
geo_socket_in = interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
geo_socket_in.attribute_domain = "POINT"

# create output node
node_output = nodes.new("NodeGroupOutput")
node_output.location = (900, 0)
geo_socket_out = interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
geo_socket_out.attribute_domain = "POINT"

# Create a Point Instance node to instance the sphere at every point.
point_instance = nodes.new("GeometryNodeInstanceOnPoints")
point_instance.location = (0, 0)

# ico node
ico_node = nodes.new(type="GeometryNodeMeshIcoSphere") #add ico
ico_node.location = (-300, -300)
ico_node.inputs['Radius'].default_value = 0.01
ico_node.inputs['Subdivisions'].default_value=4

links.new(ico_node.outputs["Mesh"], point_instance.inputs['Instance']) #link input positions to points
links.new(node_input.outputs["Geometry"], point_instance.inputs["Points"])

# create arange
index_node = nodes.new(type="GeometryNodeInputIndex")
index_node.location = (0, -400)
math_node = nodes.new(type="ShaderNodeMath")
math_node.location = (300, -500)
math_node.operation = "DIVIDE"
math_node.inputs[1].default_value = N
links.new(index_node.outputs["Index"], math_node.inputs[0])

# store named attribute
named_attr_node= nodes.new(type="GeometryNodeStoreNamedAttribute")
named_attr_node.location = (400, 0)
named_attr_node.domain = "INSTANCE"
named_attr_node.inputs["Name"].default_value = "color"
links.new(point_instance.outputs["Instances"], named_attr_node.inputs["Geometry"])
links.new(math_node.outputs["Value"], named_attr_node.inputs["Value"])


# create material
mat = create_mat()

# material node
material_node = nodes.new("GeometryNodeSetMaterial")
material_node.location = (600, 0)
material_node.inputs["Material"].default_value = mat
links.new(named_attr_node.outputs["Geometry"], material_node.inputs["Geometry"])


# link the nodes
links.new(material_node.outputs["Geometry"], node_output.inputs["Geometry"])

# frame change handler
def update_point_cloud(scene):
    index = scene.frame_current
    pos_new = tracks[index]
    
    # Update each vertex in the mesh with the new position.
    for i, vertex in enumerate(pc_obj.data.vertices):
        vertex.co = pos_new[i]
    pc_obj.data.update()

bpy.app.handlers.frame_change_pre.clear()
# Register our handler so that it runs before each frame change.
bpy.app.handlers.frame_change_pre.append(update_point_cloud)

# ################### render ###################
scene = bpy.context.scene
scene.frame_start = 0
scene.frame_end = T-1
utils.setup_camera_and_renderer()
for i in range(T):
    bpy.context.scene.frame_set(i)
    bpy.context.scene.render.filepath = f"/tmp/track_{i:04d}.jpg"
    if args.render:
        bpy.ops.render.render(write_still=True)

