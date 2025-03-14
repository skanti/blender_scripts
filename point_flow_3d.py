import argparse
import json

import math
import os
import sys
import time
from typing import List

import bpy
import numpy as np

from mathutils import Matrix, Quaternion, Vector


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

# parse args
args = parser.parse_args()

# clear the scene
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

# Load the NumPy file. It is assumed to be of shape (T, N, 3)
data = np.load(args.flow_path)
T, N, _ = data.shape
print(f"Loaded point cloud data with {T} frames and {N} points per frame.")

# --- CREATE INITIAL MESH OBJECT ---
# Create a new mesh using the points from the first frame.
mesh = bpy.data.meshes.new("PointCloudMesh")
# Convert the first frame’s points (NumPy array) to a list of tuples.
vertices = [tuple(v) for v in data[0]]
mesh.from_pydata(vertices, [], [])
mesh.update()

# Create an object from the mesh and link it to the current collection.
pc_obj = bpy.data.objects.new("PointCloud", mesh)
bpy.context.collection.objects.link(pc_obj)

# set up geometry nodes for point instance
gn_mod = pc_obj.modifiers.new(name="PointInstancer", type='NODES')
node_group = bpy.data.node_groups.new("PointInstancerTree", 'GeometryNodeTree')
gn_mod.node_group = node_group
interface = node_group.interface

# Remove any default nodes.
for node in node_group.nodes:
    node_group.nodes.remove(node)

# Create the input nodes
node_input = node_group.nodes.new("NodeGroupInput")
node_input.location = (-300, 0)
geo_socket_in = node_group.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
geo_socket_in.attribute_domain = "POINT"

# create output node
node_output = node_group.nodes.new("NodeGroupOutput")
node_output.location = (300, 0)
geo_socket_out = node_group.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
geo_socket_out.attribute_domain = "POINT"

# Create a Point Instance node to instance the sphere at every point.
point_instance = node_group.nodes.new("GeometryNodeInstanceOnPoints")
point_instance.location = (0, 0)

ico_node =node_group.nodes.new(type="GeometryNodeMeshIcoSphere") #add ico
ico_node.inputs['Radius'].default_value=0.02
ico_node.inputs['Subdivisions'].default_value=4

# link the nodes
node_group.links.new(ico_node.outputs["Mesh"], point_instance.inputs['Instance']) #link input positions to points
node_group.links.new(node_input.outputs["Geometry"], point_instance.inputs["Points"])
node_group.links.new(point_instance.outputs["Instances"], node_output.inputs["Geometry"])

# frame change handler
def update_point_cloud(scene):
    current_frame = scene.frame_current
    # Use (frame - 1) as an index into the data array (assuming frames start at 1).
    index = min(max(current_frame - 1, 0), T - 1)
    new_positions = data[index]
    
    # Update each vertex in the mesh with the new position.
    for i, vertex in enumerate(pc_obj.data.vertices):
        vertex.co = new_positions[i]
    pc_obj.data.update()

bpy.app.handlers.frame_change_pre.clear()
# Register our handler so that it runs before each frame change.
bpy.app.handlers.frame_change_pre.append(update_point_cloud)

# --- SET FRAME RANGE ---
scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = T

print("Point cloud animation script setup complete.")
