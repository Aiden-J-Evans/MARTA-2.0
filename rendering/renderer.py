import bpy
from mathutils import Vector
import os
import json
import math
import random

class AnimationHandler:
    def __init__(self, root_path, character_data, actions_list):
        self.root_path = root_path
        self.character_name = character_data['name']
        self.actions_list = actions_list
        self.target_armature = None
        self.idle_action_armature = None

    def clear_scene(self):
        """Delete all objects from the scene"""
        if bpy.context.active_object and bpy.context.active_object.mode == 'EDIT':
            bpy.ops.object.editmode_toggle()
            
        for obj in bpy.data.objects:
            obj.hide_set(False)
            obj.hide_select = False
            obj.hide_viewport = False
            
        for action in bpy.data.actions:
            bpy.data.actions.remove(action)
            
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete()
        
        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
            
    def load_rig(self, filepath: str, name: str):
        """Load an animation rig from an FBX file"""
        bpy.ops.import_scene.fbx(filepath=filepath)
        rig = bpy.context.active_object
        rig.name = name
        rig.show_in_front = True
        rig.animation_data.action.name = f'{name}_action'
        return rig

    def push_action_to_nla(self, armature, action_name, start_frame, sequence_end_frame):
        """Push down action to NLA"""
        idle_action_name = "idle_rig_action"
        # Ensure the armature is in OBJECT mode
        bpy.ops.object.mode_set(mode='OBJECT')

        
        # Find the action
        action = bpy.data.actions.get(action_name)
        if action is None:
            raise ValueError(f"Action '{action_name}' not found")
        
        idle_action = bpy.data.actions.get(idle_action_name)
        if idle_action is None:
            raise ValueError(f"Idle action '{idle_action_name}' not found")
        
        

        # Set the action to the armature
        if not armature.animation_data:
            armature.animation_data_create()
        armature.animation_data.action = action
        
        # Create or find the NLA track
        nla_tracks = armature.animation_data.nla_tracks
        if len(nla_tracks) == 0:
            nla_track = nla_tracks.new()
        else:
            nla_track = nla_tracks[0]
        
        # Push the action down to the NLA track
        nla_strip = nla_track.strips.new(action_name, int(start_frame), action)
        
        action_end_frame = nla_strip.frame_end

        # Clear the current action
        armature.animation_data.action = None

        if action_end_frame < sequence_end_frame and action_name != idle_action_name:
            idle_strip = nla_track.strips.new(idle_action_name, int(action_end_frame) + 1, idle_action)
            idle_strip.frame_end = sequence_end_frame
            idle_strip.action_frame_end = idle_strip.frame_end - idle_strip.frame_start
        elif action_end_frame > sequence_end_frame:
            nla_strip.frame_end = sequence_end_frame


        self.set_nla_strip_properties(self.target_armature, action_name)

        return nla_strip.frame_end




    def get_strip(self, rig, action_name):
        for track in rig.animation_data.nla_tracks:
            for strip in track.strips:
                if strip.name == action_name:
                    return strip
        print(f"No active NLA strip found for action '{action_name}'.")

    def set_nla_strip_properties(self, rig, action_name):
        strip = self.get_strip(rig, action_name)
        if strip:
            strip.extrapolation = 'NOTHING'
            strip.use_auto_blend = False
            print(f"Properties set for active NLA strip for action '{action_name}'.")

    def update_end_frame(self, sequence_list):
        """Update the end frame of the animation if it exceeds the default value."""
        total = 0   
        for action_name in sequence_list:
            strip = self.get_strip(self.target_armature, action_name)
            period = int(strip.frame_end - strip.frame_start)
            total += period
        total += 10  # adding extra frames
        bpy.context.scene.frame_end = total
        return total

    def get_cycle_offset(self, rig, action_name):
        """Get the amount that the armature moves with each animation cycle"""
        action = bpy.data.actions.get(action_name)
        if action is None:
            raise ValueError(f"Action '{action_name}' not found")
            
        start_pos = [0, 0, 0]
        end_pos = [0, 0, 0]
        for curve in action.fcurves:
            if "mixamorig:Hips" not in curve.data_path: continue
            if "location" not in curve.data_path: continue
            channel = curve.array_index
            
            start_pos[channel] = curve.keyframe_points[0].co.y
            end_pos[channel] = curve.keyframe_points[-1].co.y
            
        start_pos_world = Vector(start_pos) @ rig.matrix_world
        end_pos_world = Vector(end_pos) @ rig.matrix_world
        offset = [-(end_pos_world[i] - start_pos_world[i]) for i in range(3)]
        
        offset[2] = 0
        return Vector(offset)

    def organize_nla_sequences(self, sequence_list):
        """Organize sequences of animations in the NLA Editor for the target armature."""
        print("length of sequence list: " + str(len(sequence_list)))
        for index, action_name in enumerate(sequence_list):
            print("action name: " + action_name)
            print("index: " + str(index))
            if index != 0 and audio_frames[index-1][0] != last_frame:
                print(len(audio_frames))
                self.push_action_to_nla(self.target_armature, action_name, audio_frames[index-1][0], audio_frames[index][0])
            
        
        self.update_end_frame(sequence_list) 
            

    def organize_positions(self, armature, sequence_list):
        """Organize positions for sequences of animations in the NLA Editor."""
        location = Vector((0, 0, 0))

        # Ensure the armature has animation data
        if not armature.animation_data:
            armature.animation_data_create()

        # Ensure the armature has an action to hold keyframes
        if not armature.animation_data.action:
            armature.animation_data.action = bpy.data.actions.new(name="TempAction")

        action = armature.animation_data.action

        for action_name in sequence_list[1:]:  
            offset = self.get_cycle_offset(armature, action_name)
            end_location = location + offset

            strip = self.get_strip(armature, action_name)
            
            # Insert keyframes for start and end locations of the strip
            for frame, loc in [(strip.frame_start, location), (strip.frame_end, location), (strip.frame_end + 1, end_location)]:
                self.insert_location_keyframe(armature, frame, loc)

            location = end_location

    def insert_location_keyframe(self, armature, frame, location):
        """Insert a location keyframe for the armature at the specified frame."""
        armature.location = location
        armature.keyframe_insert(data_path="location", frame=frame)

    def add_audio(self):
        """Add audio strips to the sequencer based on the audio frames."""
        scene = bpy.data.scenes[0]

        # Ensure the scene's sequence editor exists
        if not scene.sequence_editor:
            scene.sequence_editor_create()

        sequence_editor = scene.sequence_editor

        # Add audio strips
        for frame, audio_path in audio_frames:
            if audio_path is not None:
                sequence_editor.sequences.new_sound(name=os.path.basename(audio_path), filepath=audio_path, channel=1, frame_start=frame)

    def create_cameras(self):
        """Create a camera for following the character"""
        char_cam_data = bpy.data.cameras.new(name='Character_Camera')
        char_camera = bpy.data.objects.new(name='Character_Camera', object_data=char_cam_data)
        bpy.context.collection.objects.link(char_camera)
        return char_camera

    def camera_follow_character(self, target_armature, camera_char, scene, dpgraph):
        """Follow a specific bone with the camera."""
    # I am using hip bone 
        target_armature = scene.objects.get('target_rig')
        target_armature = target_armature.evaluated_get(dpgraph)
        if camera_char and target_armature:
            # Get the location of the hips bone
            hips_bone = target_armature.pose.bones.get("mixamorig:Hips")
            if hips_bone:
                # Calculate the location of the hips bone in world space
                hips_location = target_armature.matrix_world @ hips_bone.head
                
                # Can adjust the distance through arguments depending upon the situation accordingly  
                distance_y = 10  # Distance along the Y-axis
                distance_z = 5  # Height above the hips bone
                
                # Calculate camera position
                camera_location = hips_location + Vector((0, -distance_y, distance_z))
                
                # Move the camera to the calculated position
                camera_char.location = camera_location
                print(f'Camera location: {hips_bone.head}')
                
                # Make the camera look at the hips bone
                direction = hips_location - camera_char.location
                rot_quat = direction.to_track_quat('-Z', 'Y')
                camera_char.rotation_euler = rot_quat.to_euler()
                
                # Adjust camera lens to broaden the view
                camera_char.data.angle = math.radians(70)  # Adjust angle as needed for wider view
            else:
                print("Hips bone not found")
        else:
            print("Camera or target armature not found")

    def frame_change_handler(self, scene, dpgraph):
        """Frame change handler to follow the character with the camera"""
        char_camera = scene.objects.get('Character_Camera')
        self.camera_follow_character(self.target_armature, char_camera, scene, dpgraph)
        print("Updating camera")

    def render_animation(self, root_path, sequence_list,output_filename ):
        """Render the animation to an MP4 file"""
        output_path = os.path.join(root_path, output_filename)
        scene = bpy.context.scene
        scene.render.image_settings.file_format = 'FFMPEG'
        scene.render.ffmpeg.format = 'MPEG4'
        scene.render.ffmpeg.codec = 'H264'
        scene.render.ffmpeg.constant_rate_factor = 'HIGH'
        scene.render.ffmpeg.ffmpeg_preset = 'GOOD'
        scene.render.filepath = output_path

        scene.render.ffmpeg.audio_codec = 'AAC'
        scene.render.ffmpeg.audio_bitrate = 192

        #scene.eevee.use_shadow = False  # For Eevee render engine
        scene.cycles.use_shadow = False  # For Cycles render engin

        # Set output settings
        scene.render.resolution_x = 1280
        scene.render.resolution_y = 720
        scene.render.resolution_percentage = 100
        scene.frame_start = 1
        scene.frame_end = self.update_end_frame(sequence_list) 

        

        # Set the active camera
        char_camera = bpy.data.objects.get('Character_Camera')
        if char_camera:
            bpy.context.scene.camera = char_camera
        else:
            print("No camera found. Rendering without setting an active camera.")

        # Render the animation
        bpy.ops.render.render(animation=True)

    def create_box_around_character(self):
        """Create a box around the character to absorb light"""
        Size = 40
        bpy.ops.mesh.primitive_cube_add(size=Size, location=(0, 0, Size / 2))
        self.box_object = bpy.context.active_object

    def set_box_properties(self, walls_color=(0.5, 0.7, 0.5, 1), floor_color=(0.82, 0.82, 0.82, 1), ceiling_color=(1, 1, 1, 1)):
        """Set properties of the box with specific materials and colors"""
        if not self.box_object:
            raise ValueError("Box object not found. Create the box first.")

        # Create materials
        walls = bpy.data.materials.new(name='walls')
        floor = bpy.data.materials.new(name='floor')
        ceiling = bpy.data.materials.new(name='ceiling')

        # Set the colors for the materials
        walls.diffuse_color = walls_color  # Default to soft green color
        floor.diffuse_color = floor_color  # Default to sober brown color
        ceiling.diffuse_color = ceiling_color  # Default to white color

        
        self.box_object.data.materials.append(walls)
        self.box_object.data.materials.append(floor)
        self.box_object.data.materials.append(ceiling)

        self.box_object.data.polygons[0].material_index = self.box_object.material_slots.find('walls')
        self.box_object.data.polygons[1].material_index = self.box_object.material_slots.find('walls')
        self.box_object.data.polygons[2].material_index = self.box_object.material_slots.find('walls')
        self.box_object.data.polygons[3].material_index = self.box_object.material_slots.find('walls')
        self.box_object.data.polygons[4].material_index = self.box_object.material_slots.find('floor')
        self.box_object.data.polygons[5].material_index = self.box_object.material_slots.find('ceiling')

        # Update the mesh to reflect changes
        self.box_object.data.update()

    def create_light(self, light_type='SUN', color=(1, 1, 1), energy=100):
        """Create a light source in the scene"""
        if not self.box_object:
            raise ValueError("Box object not found. Create the box first.")
        
        box_dimensions = self.box_object.dimensions
        box_location = self.box_object.location
        
        light_data = bpy.data.lights.new(name="Character_Light", type=light_type)
        light_data.color = color
        light_data.energy = energy
        light_object = bpy.data.objects.new(name="Character_Light", object_data=light_data)
        bpy.context.collection.objects.link(light_object)

        # Position the light inside the upper side of the box like a ceiling light
        light_object.location = (box_location.x, box_location.y, box_location.z - 2)

        # Point the light at the center of the box
        direction = Vector((box_location.x, box_location.y, box_location.z)) - light_object.location
        rot_quat = direction.to_track_quat('-Z', 'Y')
        light_object.rotation_euler = rot_quat.to_euler()

        return light_object


    def place_generated_objects(self):
        for path in object_paths:
            # Import the .obj file
            bpy.ops.wm.obj_import(filepath=path)
            
            # Get the imported object
            imported_objects = bpy.context.selected_objects
            if imported_objects:
                imported_obj = imported_objects[0]  # Assuming the first selected object is the one imported
                
                rand_x = random.uniform(-9, -7)
                rand_y = random.uniform(-9, 9)
                # Set the location of the imported object
                imported_obj.location = (rand_x, rand_y, 1)
            
    def run(self):
        self.clear_scene()

        # Load the main target armature
        target_fbx_path = os.path.join(self.root_path, f"{self.character_name}.fbx")
        self.target_armature = self.load_rig(target_fbx_path, 'target_rig')

        # Load and process each action
        for action_name in self.actions_list:
            action_fbx_path = os.path.join(self.root_path, f"{action_name}.fbx")
            rig_name = action_name.lower().replace(" ", "_") + "_rig"
            action_armature = self.load_rig(action_fbx_path, rig_name)
            action_armature.hide_set(True)
            
        self.idle_action_armature = self.load_rig(self.root_path + "\\Idle.fbx", "idle_action_rig")
        self.idle_action_armature.hide_set(True)

        
        # Organize the sequences and positions
        sequence_list = [f"{action.lower().replace(' ', '_')}_rig_action" for action in self.actions_list]
        self.organize_nla_sequences(sequence_list)
        self.organize_positions(self.target_armature, sequence_list)
        self.add_audio()
        self.create_box_around_character()
        self.set_box_properties()
        self.create_light()
        self.place_generated_objects()

        char_camera = self.create_cameras()
        #self.camera_follow_character(self.target_armature, char_camera)

        # Register the frame change handler to follow the character during animation
        bpy.app.handlers.frame_change_pre.clear()
        bpy.app.handlers.frame_change_post.clear()
        bpy.app.handlers.frame_change_post.append(lambda scene, dpgraph: self.frame_change_handler(scene, dpgraph))

        self.render_animation(self.root_path, sequence_list, "output.mp4")


# path to animation/character folder
root_path = os.getcwd() + "\\animations"

f = open(os.getcwd() + "\\frame_data.json")
frame_data = json.load(f)
audio_frames = []

character_data = {'name': 'Remy'}
actions_list = ["Idle"]

object_paths = [str(path) for path in os.listdir(os.getcwd() + '\\mesh_generation\\generated_objects')]

for sequence, data in frame_data.items():
    if sequence.isdigit():
        audio_frames.append([int(sequence), data["audio_path"]])

        for character, char_data in data['characters'].items():
            print(f'Loading: {character}')
            actions_list.append(char_data["animation"])

            print(f'Playing: {char_data["animation"]}')


last_frame = int(frame_data['end_frame'])
audio_frames.append([last_frame, None])

animation_handler = AnimationHandler(root_path, character_data, actions_list)
animation_handler.run()
