import bpy
import mathutils

def setup_camera_and_renderer():
    # render settings
    bpy.context.scene.render.image_settings.file_format = "JPEG"
    bpy.context.scene.render.image_settings.color_mode = "RGB"
    bpy.context.scene.render.image_settings.color_depth = "8"
    bpy.context.scene.render.resolution_x = 256
    bpy.context.scene.render.resolution_y = 256
    bpy.context.scene.render.use_persistent_data = True
    bpy.context.scene.render.engine = "CYCLES"
    bpy.context.scene.render.film_transparent = False
    bpy.context.scene.cycles.device = "CPU"
    bpy.context.scene.cycles.samples = 64

    # add light
    bpy.ops.object.light_add(type="SUN")
    sun_light = bpy.context.object
    sun_light.location = (10, 10, 10)
    sun_light.data.energy = 1  # Brightness

    # ground plane
    bpy.ops.mesh.primitive_plane_add()
    ground_plane = bpy.context.object
    ground_plane.name = "GroundPlane"
    ground_plane.dimensions = (100, 100, 0.01)
    ground_plane.location = (0, 0, 0)
    mat = bpy.data.materials.new(name="GroundPlaneMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs['Base Color'].default_value = (0.0, 0.0, 0.0, 1.0)
    ground_plane.data.materials.append(mat)

    # add camera
    bpy.ops.object.camera_add(location=(0, 0, 0))
    camera = bpy.context.active_object
    camera.data.lens = 18
    camera.name = "camera"
    camera.rotation_mode = "QUATERNION"
    bpy.context.scene.camera = camera
    cam_t = mathutils.Vector((0, 2, 3))
    direction = mathutils.Vector((0, 0, 0)) - cam_t
    cam_q = direction.to_track_quat('-Z', 'Y')
    camera.location = cam_t
    camera.rotation_quaternion = cam_q

