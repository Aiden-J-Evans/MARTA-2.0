import bpy # type: ignore



def init():
  """Initialize the scene"""
  bpy.ops.object.select_all(action="DESELECT")
  bpy.data.objects['Cube'].select_set(True)
  bpy.ops.object.delete()
  open_json()

def open_json():
   print("opening")

def render_floor_plain(location=(0, 0, 0), scale=(10, 10, 1), image_path="", tile_size=(1, 1)):
  """
  Renders the floor plain from a local image
  
  Args:
    location (tuple): Represents the vector coodinates of the plain.
    scale (tuple): Represents the vector scale of the plain.
    image_path (str): The local path to the base image of the plain.
    tile_size (tuple): The tilesize for the image displayed on the plain.
  """

  # Delete existing plane if it exists
  if "Floor" in bpy.data.objects:
      bpy.data.objects["Floor"].select_set(True)
      bpy.ops.object.delete()
  
  # Create a new plane
  bpy.ops.mesh.primitive_plane_add(size=1, location=location)
  floor = bpy.context.active_object
  floor.name = "Floor"
  
  # Scale the plane to desired size
  floor.scale = scale
  
  # Create a new material
  mat = bpy.data.materials.new(name="FloorMaterial")
  mat.use_nodes = True
  nodes = mat.node_tree.nodes
  links = mat.node_tree.links
  
  # Clear default nodes
  for node in nodes:
      nodes.remove(node)
  
  # Create necessary nodes
  output_node = nodes.new(type='ShaderNodeOutputMaterial')
  output_node.location = 400, 0
  
  diffuse_node = nodes.new(type='ShaderNodeBsdfDiffuse')
  diffuse_node.location = 200, 0
  
  texture_node = nodes.new(type='ShaderNodeTexImage')
  texture_node.location = 0, 0
  if image_path:
      texture_node.image = bpy.data.images.load(image_path)
  
  tex_coord_node = nodes.new(type='ShaderNodeTexCoord')
  tex_coord_node.location = -600, 0
  
  mapping_node = nodes.new(type='ShaderNodeMapping')
  mapping_node.location = -300, 0
  mapping_node.inputs['Scale'].default_value = (scale[0] / tile_size[0], scale[1] / tile_size[1], 1)
  
  # Link nodes
  links.new(tex_coord_node.outputs['Generated'], mapping_node.inputs['Vector'])
  links.new(mapping_node.outputs['Vector'], texture_node.inputs['Vector'])
  links.new(texture_node.outputs['Color'], diffuse_node.inputs['Color'])
  links.new(diffuse_node.outputs['BSDF'], output_node.inputs['Surface'])
  
  # Assign material to the plane
  if floor.data.materials:
      floor.data.materials[0] = mat
  else:
      floor.data.materials.append(mat)

  # Apply UV mapping to tile the texture
  bpy.context.view_layer.objects.active = floor
  bpy.ops.object.mode_set(mode='EDIT')
  bpy.ops.uv.cube_project(cube_size=1.0)
  bpy.ops.object.mode_set(mode='OBJECT')

  return floor

def render_skybox(image_path=""):
  """
  Renders the skybox from an image

  Args:
    image_path (str): Local path of the image.
  
  
  
  """
    # Get the current scene
  scene = bpy.context.scene
  
  # Enable nodes on the world
  world = scene.world
  world.use_nodes = True
  tree = world.node_tree
  nodes = tree.nodes
  
  # Clear all nodes to start fresh
  for node in nodes:
      nodes.remove(node)
  
  # Create a background node
  background_node = nodes.new(type='ShaderNodeBackground')
  background_node.location = 0, 0
  
  # Create an environment texture node
  env_tex_node = nodes.new(type='ShaderNodeTexEnvironment')
  env_tex_node.location = -300, 0
  env_tex_node.image = bpy.data.images.load(image_path)
  
  # Create a texture coordinate node
  tex_coord_node = nodes.new(type='ShaderNodeTexCoord')
  tex_coord_node.location = -600, 0
  
  # Create a mapping node for rotation or translation adjustments
  mapping_node = nodes.new(type='ShaderNodeMapping')
  mapping_node.location = -450, 0
  
  # Create a world output node
  world_output_node = nodes.new(type='ShaderNodeOutputWorld')
  world_output_node.location = 300, 0
  
  # Link the nodes
  links = tree.links
  links.new(tex_coord_node.outputs['Generated'], mapping_node.inputs['Vector'])
  links.new(mapping_node.outputs['Vector'], env_tex_node.inputs['Vector'])
  links.new(env_tex_node.outputs['Color'], background_node.inputs['Color'])
  links.new(background_node.outputs['Background'], world_output_node.inputs['Surface'])

def add_audio(audio_name, audio_path, start_frame=1, volume=0.5):
  """
  Imports given audio to blender
  
  Args:
      audio_name (string): name given to the audio, shown in blender
      audio_path (string): the local path to the imported audio
      start_frame (int): the frame to start the audio on
      volume (float): a float between 0-1 representing volume
  """
  scene = bpy.context.scene
  audio_strip = scene.sequence_editor.sequences.new_sound(name=audio_name, filepath=audio_path, channel=1, frame_start=start_frame)
  audio_strip.volume = volume
  

init()
render_floor_plain((0, 0, 0), (100, 100, 1), "C:/Users/aiden/Pictures/Camera Roll/test.jpg", (1, 1))