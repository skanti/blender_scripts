import argparse
import sys

import bpy
import numpy as np
import colorsys


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

# Adjust bevel_depth to change line thickness (set to 0 for no thickness)
bevel_depth = 0.01

# Load the npy array (shape: T x N x 3)
data = np.load(args.flow_path)
T, N, _ = data.shape

# Iterate over each point track (track index i from 0 to N-1)
for i in range(N):
    # Create a new curve data block for a 3D polyline
    curve_data = bpy.data.curves.new(name=f"Track_{i}", type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.bevel_depth = bevel_depth  # gives the line some thickness
    
    # Add a polyline spline; one point is already there, so add T-1 additional points
    spline = curve_data.splines.new(type='POLY')
    spline.points.add(T - 1)
    
    # Assign coordinates to each point in the spline.
    # Note: Each point coordinate is a 4D vector (x, y, z, w), so we set w=1.
    for j in range(T):
        x, y, z = data[j, i, :]
        spline.points[j].co = (x, y, z, 1)
    
    # Create a new object from the curve data and link it to the scene
    curve_obj = bpy.data.objects.new(name=f"Track_{i}", object_data=curve_data)
    bpy.context.scene.collection.objects.link(curve_obj)
    
    # Create a material for this track with a unique color.
    # Here we use the HSV color space so that each track gets a distinct hue.
    mat = bpy.data.materials.new(name=f"Mat_Track_{i}")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    
    # Calculate a unique color using the track index.
    h = i / float(N)  # hue between 0 and 1
    r, g, b = colorsys.hsv_to_rgb(h, 1, 1)
    bsdf.inputs['Base Color'].default_value = (r, g, b, 1)
    
    # Assign the material to the curve object
    if curve_obj.data.materials:
        curve_obj.data.materials[0] = mat
    else:
        curve_obj.data.materials.append(mat)
