import argparse
import sys

import bpy
import numpy as np
import colorsys
import mathutils

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

# parse args
args = parser.parse_args()

# clear the scene
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

# Adjust bevel_depth to change line thickness (set to 0 for no thickness)
bevel_depth = 0.02

# Load the npy array (shape: T x N x 3)
tracks = np.load(args.flow_path)
T, N, _ = tracks.shape
print(f"Loaded point cloud data with {T} frames and {N} points per frame.")

is_alive = np.ones((N, ), dtype=bool)
for i in range(T):
    points = tracks[i]
    is_alive = is_alive & (points < 1000).all(axis=1)
    points[~is_alive] = 1000.0

lengths = (tracks < 1000.0).all(axis=2).sum(axis=0)

samples = np.random.permutation(N)[:512]
# samples = np.argsort(lengths)[::-1][:32]
M = len(samples)

# Iterate over each point track (track index i from 0 to N-1)
for i in samples:
    # Create a new curve data block for a 3D polyline
    curve_data = bpy.data.curves.new(name=f"Track_{i}", type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.bevel_depth = bevel_depth  # gives the line some thickness
    
    # Add a polyline spline; one point is already there, so add T-1 additional points
    spline = curve_data.splines.new(type='POLY')
    
    # Assign coordinates to each point in the spline.
    points = []
    for j in range(T):
        pos = tracks[j, i, :]
        if (pos >= 1000.0).any():
            break
        else:
            x, y, z = pos
            points.append((x, y, z, 1.0))

    # print(f"Track {i} has {T} points.")
    T1  = len(points)
    print(f"Track {i} has {T1} points.")
    if T1 == 1:
        continue
    spline.points.add(T1-1)
    for j in range(T1):
        spline.points[j].co = points[j]

    # calc distance
    deltas = np.diff(points, axis=0)
    segment_distances = np.linalg.norm(deltas, axis=1)
    distance = np.sum(segment_distances)

    
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
    h = i / float(M)  # hue between 0 and 1
    r, g, b = colorsys.hsv_to_rgb(h, 1, 1)
    bsdf.inputs['Base Color'].default_value = (r, g, b, 1)
    bsdf.inputs['Emission Color'].default_value = (r, g, b, 1)
    bsdf.inputs["Emission Strength"].default_value = 0.5
    
    # Assign the material to the curve object
    if curve_obj.data.materials:
        curve_obj.data.materials[0] = mat
    else:
        curve_obj.data.materials.append(mat)

    # add keyframes
    visible_segment = 0.1
    curve_data.bevel_factor_start = 0.0
    curve_data.bevel_factor_end = 0.0 + visible_segment
    curve_data.keyframe_insert(data_path="bevel_factor_end", frame=0)
    curve_data.keyframe_insert(data_path="bevel_factor_start", frame=0)
    curve_obj.hide_viewport = False
    curve_obj.hide_render = False
    curve_obj.keyframe_insert(data_path="hide_viewport", frame=0)
    curve_obj.keyframe_insert(data_path="hide_render", frame=0)

    curve_data.bevel_factor_start = 1.0 - visible_segment
    curve_data.bevel_factor_end = 1.0
    curve_data.keyframe_insert(data_path="bevel_factor_end", frame=T1-1)
    curve_data.keyframe_insert(data_path="bevel_factor_start", frame=T1-1)
    # hide the curve
    curve_obj.hide_viewport = True
    curve_obj.hide_render = True
    curve_obj.keyframe_insert(data_path="hide_viewport", frame=T1)
    curve_obj.keyframe_insert(data_path="hide_render", frame=T1)


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

