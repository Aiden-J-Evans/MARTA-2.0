import bpy
from mathutils import Vector
import os
import math

class AnimationHandler:
    def __init__(self, root_path, character_data, actions_dict):
        self.root_path = root_path
        self.character_name = character_data['name']
        self.actions_dict = actions_dict
        self.target_armature = None
        self.box_object = None
        self.end_frame_anim= None

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

    def organize_positions(self, sequence_list):
        """Organize positions for sequences of animations in the NLA Editor."""
        location = Vector((0, 0, 0))
        self.organize_nla_sequences(sequence_list)
        
        for action_name in sequence_list:  
            offset = self.get_cycle_offset(self.target_armature, action_name)
            end_location = location + offset

            strip = self.get_strip(self.target_armature, action_name)
                    
            bpy.context.scene.frame_set(int(strip.frame_start))
            self.target_armature.location = location
            bpy.ops.anim.keyframe_insert(type='LocRotScale')
            
            bpy.context.scene.frame_set(int(strip.frame_end))
            self.target_armature.location = location
            bpy.ops.anim.keyframe_insert(type='LocRotScale')
            
            bpy.context.scene.frame_set(int(strip.frame_end + 1))
            self.target_armature.location = end_location
            bpy.ops.anim.keyframe_insert(type='LocRotScale')
            location = end_location

    
    def organize_nla_sequences(self, target_armature, actions_dict):
        """Organize sequences of animations in the NLA Editor for the target armature."""
        
        new_actions_dict = {}
        anim_start = 1

        for action_name, frames in actions_dict.items():
            frame_start = frames[0]
            frame_end = frames[1]
            action_name = action_name.lower().replace(" ", "_") + "_rig_action"
            strip = self.get_strip(target_armature, action_name)
            original_period = int(strip.frame_end - strip.frame_start)
            required_period = frame_end - frame_start
            strip.frame_start = frame_start
            strip.frame_end = strip.frame_start + original_period

            if required_period > original_period:
                num_repeats = math.ceil(required_period / original_period)
                
                # Add original action to the new actions dictionary with original frame range
                original_action_name = action_name
                new_actions_dict[original_action_name] = (strip.frame_start, strip.frame_end)

                # Duplicate the action for the required number of times
                for i in range(num_repeats):
                    new_start_frame = strip.frame_end
                    new_end_frame = min(new_start_frame + original_period, frame_end)
                    new_action_name = f"{action_name}_{i + 1}"
                    new_actions_dict[new_action_name] = (new_start_frame, new_end_frame)
                    
                    # Create a new NLA strip for the duplicated action
                    new_strip_name = f"{action_name}_{i + 1}"
                    new_strip = target_armature.animation_data.nla_tracks[0].strips.new(name=new_strip_name, start=int(new_start_frame), action=strip.action)
                    
                    # Update the end frame of the original strip
                    new_strip.frame_end = new_end_frame
                    print(f"Frame end: {new_strip.frame_end}")
                    
                    if new_end_frame == frame_end:
                        break
            
            else:
                strip.frame_end = frame_end
                
                # Add the action to the new actions dictionary
                new_actions_dict[action_name] = (frame_start, frame_end)


        self.end_frame_anim=strip.frame_end
        return new_actions_dict
 
    def create_cameras(self):
        """Create a camera for following the character"""
        char_cam_data = bpy.data.cameras.new(name='Character_Camera')
        char_camera = bpy.data.objects.new(name='Character_Camera', object_data=char_cam_data)
        bpy.context.collection.objects.link(char_camera)
        return char_camera


    def camera_follow_character(self, target_armature, camera_char, scene, dpgraph,distance_y = 5 ,distance_z = 2):
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

        # Set output settings
        scene.render.resolution_x = 720
        scene.render.resolution_y = 460
        scene.render.resolution_percentage = 80
        scene.frame_start = 1
        scene.frame_end = self.end_frame_anim

        # Set the active camera
        char_camera = bpy.data.objects.get('Character_Camera')
        if char_camera:
            bpy.context.scene.camera = char_camera
        else:
            print("No camera found. Rendering without setting an active camera.")

        # Render the animation
        bpy.ops.render.render(animation=True)

    def create_box_around_character(self, Size = 40):
        """Create a box around the character to absorb light"""

        bpy.ops.mesh.primitive_cube_add(size=Size, location=(0, 0, Size / 2))
        self.box_object = bpy.context.active_object

    def set_box_properties(self, walls_color=(0.5, 0.7, 0.5, 1), floor_color=(0.6, 0.4, 0.2, 1), ceiling_color=(1, 1, 1, 1)):
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

    def run(self):
        self.clear_scene()
        character_path = os.path.join(self.root_path, 'characters')

        # Load the main target armature
        target_fbx_path = os.path.join(character_path, f"{self.character_name}.fbx")
        self.target_armature = self.load_rig(target_fbx_path, 'target_rig')
        
        animation_path = os.path.join(self.root_path, 'animations')

        # Load and process each action
        for action_name, frames in self.actions_dict.items():
            start_frame=frames[0]
            end_frame=frames[1]
            action_fbx_path = os.path.join(animation_path, f"{action_name}.fbx")
            rig_name = action_name.lower().replace(" ", "_") + "_rig"
            action_armature = self.load_rig(action_fbx_path, rig_name)
            action_armature.hide_set(True)
            self.push_action_to_nla(self.target_armature, f"{rig_name}_action")
            self.set_nla_strip_properties(self.target_armature, f"{rig_name}_action")
        
        # Organize the sequences and positions
        new_dict=self.organize_nla_sequences(self.target_armature, self.actions_dict)
        self.organize_positions(new_dict)

        char_camera = self.create_cameras()

        # Register the frame change handler to follow the character during animation
        bpy.app.handlers.frame_change_pre.clear()
        bpy.app.handlers.frame_change_post.clear()
        bpy.app.handlers.frame_change_post.append(lambda scene, dpgraph: self.frame_change_handler(scene, dpgraph))
        
        self.create_box_around_character()
        self.set_box_properties()

        self.create_light(light_type='SUN', color=(1, 1, 1), energy=10)
        
        # self.render_animation(self.root_path, sequence_list, output_filename)

        




# Example
root_path = r"C:\Users\PMLS\Desktop\blender stuff"
character_data = {'name': 'Boy (age 19 to 25)'}
actions_dict = {
    'Walking': (10, 60),  
    'Idle': (60, 90),  
}

animation_handler = AnimationHandler(root_path, character_data, actions_dict)
animation_handler.run()


///////////////////////////////////////////////////////////////////////

import bpy
from mathutils import Vector
import os
import math

class AnimationHandler:
    def __init__(self, root_path, character_data, actions_dict):
        self.root_path = root_path
        self.character_name = character_data['name']
        self.actions_dict = actions_dict
        self.target_armature = None
        self.box_object = None
        self.end_frame_anim= None

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
    
    

    def push_action_to_nla(self, armature, action_name):
        """Push down action to NLA"""
        
        # Find the action
        action = bpy.data.actions.get(action_name)
        if action is None:
            raise ValueError(f"Action '{action_name}' not found")
           
        # Set the action to the armature
        if not armature.animation_data:
            armature.animation_data_create()
        armature.animation_data.action = None
         
        # Create or find the NLA track
        nla_tracks = armature.animation_data.nla_tracks
        nla_track = nla_tracks.new()
        nla_track.name = action_name

        
        nla_strip = nla_track.strips.new(name=action_name , start=0, action=action)

        return nla_strip.frame_end

    def extract_action_name(self, full_action_name):
        """Extract action name until the word 'action'."""
        index = full_action_name.find("action")
        if index != -1:
            return full_action_name[:index + len("action")].strip()
        return full_action_name        



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
        


    def get_cycle_offset(self, rig, action_name):
        """Get the amount that the armature moves with each animation cycle"""
        
        action_name = self.extract_action_name(action_name)
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

    def insert_location_keyframe(self, armature, frame, location):
        """Insert a location keyframe for the armature at the specified frame."""
        armature.location = location
        armature.keyframe_insert(data_path="location", frame=frame)


    def organize_positions(self, armature, action_dict):
        """Organize positions for sequences of animations in the NLA Editor."""
        location = Vector((0, 0, 0))

        # Ensure the armature has animation data
        if not armature.animation_data:
            armature.animation_data_create()

        # Ensure the armature has an action to hold keyframes
        if not armature.animation_data.action:
            armature.animation_data.action = bpy.data.actions.new(name="TempAction")

        action = armature.animation_data.action

        for action_name, frames in action_dict.items():  
            
            offset = self.get_cycle_offset(armature, action_name)
            end_location = location + offset

            action_name = self.extract_action_name(action_name)
            strip = self.get_strip(armature, action_name)
            
            # Insert keyframes for start and end locations of the strip
            for frame, loc in [(strip.frame_start, location), (strip.frame_end, location), (strip.frame_end + 1, end_location)]:
                self.insert_location_keyframe(armature, frame, loc)

            location = end_location


    
    def organize_nla_sequences(self, target_armature, actions_dict):
        """Organize sequences of animations in the NLA Editor for the target armature."""
        
        new_actions_dict = {}
        anim_start = 1

        for action_name, frames in actions_dict.items():
            frame_start = frames[0]
            frame_end = frames[1]
            action_name = action_name.lower().replace(" ", "_") + "_rig_action"
            strip = self.get_strip(target_armature, action_name)
            original_period = int(strip.frame_end - strip.frame_start)
            required_period = frame_end - frame_start
            strip.frame_start = frame_start
            strip.frame_end = strip.frame_start + original_period

            if required_period > original_period:
                num_repeats = math.ceil(required_period / original_period)
                
                # Add original action to the new actions dictionary with original frame range
                original_action_name = action_name
                new_actions_dict[original_action_name] = (strip.frame_start, strip.frame_end)

                # Duplicate the action for the required number of times
                for i in range(num_repeats):
                    new_start_frame = strip.frame_end 
                    new_end_frame = min(new_start_frame + original_period, frame_end)
                    new_action_name = f"{action_name}_{i + 1}"
                    new_actions_dict[new_action_name] = (new_start_frame, new_end_frame)
                    
                    # Create a new NLA strip for the duplicated action
                    new_strip_name = f"{action_name}_{i + 1}"
                    new_strip = target_armature.animation_data.nla_tracks[0].strips.new(name=new_strip_name, start=int(new_start_frame), action=strip.action)
                    
                    # Update the end frame of the original strip
                    new_strip.frame_end = new_end_frame
                    print(f"Frame end: {new_strip.frame_end}")
                    
                    if new_end_frame == frame_end:
                        break
            
            else:
                strip.frame_end = frame_end
                
                # Add the action to the new actions dictionary
                new_actions_dict[action_name] = (frame_start, frame_end)


        self.end_frame_anim=strip.frame_end
        return new_actions_dict
 
 


    def run(self):
        self.clear_scene()
        character_path = os.path.join(self.root_path, 'characters')

        # Load the main target armature
        target_fbx_path = os.path.join(character_path, f"{self.character_name}.fbx")
        self.target_armature = self.load_rig(target_fbx_path, 'target_rig')
        
        animation_path = os.path.join(self.root_path, 'animations')

        # Load and process each action
        for action_name, frames in self.actions_dict.items():
            start_frame=frames[0]
            end_frame=frames[1]
            action_fbx_path = os.path.join(animation_path, f"{action_name}.fbx")
            rig_name = action_name.lower().replace(" ", "_") + "_rig"
            action_armature = self.load_rig(action_fbx_path, rig_name)
            action_armature.hide_set(True)
            self.push_action_to_nla(self.target_armature, f"{rig_name}_action")
            self.set_nla_strip_properties(self.target_armature, f"{rig_name}_action")
        
        # Organize the sequences and positions
        new_dict=self.organize_nla_sequences(self.target_armature, self.actions_dict)
        self.organize_positions1(self.target_armature, new_dict)

        
        # self.render_animation(self.root_path, sequence_list, output_filename)

        




# Example
root_path = r"C:\Users\PMLS\Desktop\blender stuff"
character_data = {'name': 'Boy (age 19 to 25)'}
actions_dict = {
    'Walking': (10, 60),  
    'Locking Hip Hop Dance        ': (60, 90), 
    
}

animation_handler = AnimationHandler(root_path, character_data, actions_dict)
animation_handler.run()  


//////////////////

# combined function
    def organize_nla_sequences(self, target_armature, actions_dict):
        """Organize sequences of animations in the NLA Editor for the target armature."""

        location = Vector((0, 0, 0))

        # Ensure the armature has animation data
        if not target_armature.animation_data:
            target_armature.animation_data_create()

        # Ensure the armature has an action to hold keyframes
        if not target_armature.animation_data.action:
            target_armature.animation_data.action = bpy.data.actions.new(name="TempAction")

        new_actions_dict = {}
        anim_start = 1

        for action_name, frames in actions_dict.items():
            frame_start = frames[0]
            frame_end = frames[1]
            action_name = action_name.lower().replace(" ", "_") + "_rig_action"
            strip = self.get_strip(target_armature, action_name)
            original_period = int(strip.frame_end - strip.frame_start)
            required_period = frame_end - frame_start
            strip.frame_start = frame_start
            strip.frame_end = strip.frame_start + original_period

            if required_period > original_period:
                num_repeats = math.ceil(required_period / original_period)
                
                # Add original action to the new actions dictionary with original frame range
                original_action_name = action_name
                new_actions_dict[original_action_name] = (strip.frame_start, strip.frame_end)

                # Duplicate the action for the required number of times
                for i in range(num_repeats):
                    new_start_frame = strip.frame_end 
                    new_end_frame = min(new_start_frame + original_period, frame_end)
                    new_action_name = f"{action_name}_{i + 1}"
                    new_actions_dict[new_action_name] = (new_start_frame, new_end_frame)
                    
                    # Create a new NLA strip for the duplicated action
                    new_strip_name = f"{action_name}_{i + 1}"
                    new_strip = target_armature.animation_data.nla_tracks[0].strips.new(name=new_strip_name, start=int(new_start_frame), action=strip.action)
                    
                    # Update the end frame of the original strip
                    new_strip.frame_end = new_end_frame
                    print(f"Frame end: {new_strip.frame_end}")
                    
                    if new_end_frame == frame_end:
                        break
            
            else:
                strip.frame_end = frame_end
                
                # Add the action to the new actions dictionary
                new_actions_dict[action_name] = (frame_start, frame_end)
            
            # Update action variable to the current strip's action
            action = strip.action
            
            start_pos = [0, 0, 0]
            end_pos = [0, 0, 0]
            for curve in action.fcurves:
                if "mixamorig:Hips" not in curve.data_path: continue
                if "location" not in curve.data_path: continue
                channel = curve.array_index
                
                start_pos[channel] = curve.keyframe_points[0].co.y
                end_pos[channel] = curve.keyframe_points[-1].co.y
                
            start_pos_world = Vector(start_pos) @ target_armature.matrix_world
            end_pos_world = Vector(end_pos) @ target_armature.matrix_world
            offset = [-(end_pos_world[i] - start_pos_world[i]) for i in range(3)]
            
            offset[2] = 0
            
            end_location = location + Vector(offset)
            
            for frame, loc in [(strip.frame_start, location), (strip.frame_end, location), (strip.frame_end + 1, end_location)]:
                self.insert_location_keyframe(target_armature, frame, loc)

            location = end_location 

        self.end_frame_anim = strip.frame_end
        return new_actions_dict



###################################################################

# copy actions

import bpy
from mathutils import Vector
import os
import math

class AnimationHandler:
    def __init__(self, root_path, character_data, actions_dict):
        self.root_path = root_path
        self.character_name = character_data['name']
        self.actions_dict = actions_dict
        self.target_armature = None
        self.box_object = None
        self.end_frame_anim = None

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
    
    def push_action_to_nla(self, armature, action_name):
        """Push down action to NLA"""
        
        # Find the action
        action = bpy.data.actions.get(action_name)
        if action is None:
            raise ValueError(f"Action '{action_name}' not found")
           
        # Set the action to the armature
        if not armature.animation_data:
            armature.animation_data_create()
        armature.animation_data.action = None
         
        # Create or find the NLA track
        nla_tracks = armature.animation_data.nla_tracks
        nla_track = nla_tracks.new()
        nla_track.name = action_name

        nla_strip = nla_track.strips.new(name=action_name , start=0, action=action)

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

    def insert_location_keyframe(self, armature, frame, location):
        """Insert a location keyframe for the armature at the specified frame."""
        armature.location = location
        armature.keyframe_insert(data_path="location", frame=frame)

    def organize_positions(self, armature, action_dict):
        """Organize positions for sequences of animations in the NLA Editor."""
        location = Vector((0, 0, 0))

        # Ensure the armature has animation data
        if not armature.animation_data:
            armature.animation_data_create()

        # Ensure the armature has an action to hold keyframes
        if not armature.animation_data.action:
            armature.animation_data.action = bpy.data.actions.new(name="TempAction")

        action = armature.animation_data.action

        for action_name, frames in action_dict.items():  
            
            offset = self.get_cycle_offset(armature, action_name)
            end_location = location + offset

                
            strip = self.get_strip(armature, action_name)
            
            # Insert keyframes for start and end locations of the strip
            for frame, loc in [(strip.frame_start, location), (strip.frame_end, location), (strip.frame_end + 1, end_location)]:
                self.insert_location_keyframe(armature, frame, loc)

            location = end_location
    
    def duplicate_action(self, original_action_name, new_action_name):
        """Duplicate an action and return the new action"""
        original_action = bpy.data.actions.get(original_action_name)
        if original_action is None:
            raise ValueError(f"Action '{original_action_name}' not found")
        
        # Duplicate the action
        new_action = original_action.copy()
        new_action.name = f"{new_action_name}"
        
        return new_action

    def organize_nla_sequences(self, target_armature, actions_dict):
        """Organize sequences of animations in the NLA Editor for the target armature."""
        
        new_actions_dict = {}
        anim_start = 1

        for action_name, frames in actions_dict.items():
            frame_start = frames[0]
            frame_end = frames[1]
            action_name = action_name.lower().replace(" ", "_") + "_rig_action"
            strip = self.get_strip(target_armature, action_name)
            original_period = int(strip.frame_end - strip.frame_start)
            required_period = frame_end - frame_start
            strip.frame_start = frame_start
            strip.frame_end = strip.frame_start + original_period

            if required_period > original_period:
                num_repeats = math.ceil(required_period / original_period)
                
                # Add original action to the new actions dictionary with original frame range
                original_action_name = action_name
                new_actions_dict[original_action_name] = (strip.frame_start, strip.frame_end)

                # Duplicate the action for the required number of times
                for i in range(num_repeats):
                    new_start_frame = strip.frame_end 
                    new_end_frame = min(new_start_frame + original_period, frame_end)
                    new_action_name = f"{action_name}_{i + 1}"
                    new_actions_dict[new_action_name] = (new_start_frame, new_end_frame)
                    
                    # Duplicate the action
                    duplicated_action = self.duplicate_action(action_name, new_action_name)

                    # Create a new NLA strip for the duplicated action
                    new_strip_name = f"{action_name}_{i + 1}"
                    new_strip = target_armature.animation_data.nla_tracks[0].strips.new(name=new_strip_name, start=int(new_start_frame), action=duplicated_action)
                    
                    # Update the end frame of the original strip
                    new_strip.frame_end = new_end_frame
                    print(f"Frame end: {new_strip.frame_end}")
                    
                    if new_end_frame == frame_end:
                        break
            
            else:
                strip.frame_end = frame_end
                
                # Add the action to the new actions dictionary
                new_actions_dict[action_name] = (frame_start, frame_end)

        self.end_frame_anim = strip.frame_end
        return new_actions_dict

    def run(self):
        self.clear_scene()
        character_path = os.path.join(self.root_path, 'characters')

        # Load the main target armature
        target_fbx_path = os.path.join(character_path, f"{self.character_name}.fbx")
        self.target_armature = self.load_rig(target_fbx_path, 'target_rig')
        
        animation_path = os.path.join(self.root_path, 'animations')

        # Load and process each action
        for action_name, frames in self.actions_dict.items():
            start_frame = frames[0]
            end_frame = frames[1]
            action_fbx_path = os.path.join(animation_path, f"{action_name}.fbx")
            rig_name = action_name.lower().replace(" ", "_") + "_rig"
            action_armature = self.load_rig(action_fbx_path, rig_name)
            action_armature.hide_set(True)
            self.push_action_to_nla(self.target_armature, f"{rig_name}_action")
            self.set_nla_strip_properties(self.target_armature, f"{rig_name}_action")
        
        # Organize the sequences and positions
        new_dict = self.organize_nla_sequences(self.target_armature, self.actions_dict)
        self.organize_positions(self.target_armature, new_dict)
        
        # Adjust scene timeline
        bpy.context.scene.frame_end = int(self.end_frame_anim)
        bpy.context.scene.frame_current = 0

# Example
root_path = r"C:\Users\PMLS\Desktop\blender stuff"
character_data = {'name': 'Boy (age 19 to 25)'}
actions_dict = {
    'Sitting Clap': (10, 90),  
    'Locking Hip Hop Dance': (90, 100), 
    
}

animation_handler = AnimationHandler(root_path, character_data, actions_dict)
animation_handler.run()  




###################################################

import bpy
from mathutils import Vector
import os
import math

class AnimationHandler:
    def __init__(self, root_path, character_data, actions_dict):
        self.root_path = root_path
        self.character_name = character_data['name']
        self.actions_dict = actions_dict
        self.target_armature = None
        self.box_object = None
        self.end_frame_anim = None

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
    
    def push_action_to_nla(self, armature, action_name):
        """Push down action to NLA"""
        
        # Find the action
        action = bpy.data.actions.get(action_name)
        if action is None:
            raise ValueError(f"Action '{action_name}' not found")
           
        # Set the action to the armature
        if not armature.animation_data:
            armature.animation_data_create()
        armature.animation_data.action = None
         
        # Create or find the NLA track
        nla_tracks = armature.animation_data.nla_tracks
        nla_track = nla_tracks.new()
        nla_track.name = action_name

        nla_strip = nla_track.strips.new(name=action_name , start=0, action=action)

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

    def get_cycle_offset(self, rig, action, end_frame):
        """Get the amount that the armature moves with each animation cycle"""
            
        start_pos = [0, 0, 0]
        end_pos = [0, 0, 0]
        for curve in action.fcurves:
            if "mixamorig:Hips" not in curve.data_path: continue
            if "location" not in curve.data_path: continue
            channel = curve.array_index
            
            start_pos[channel] = curve.evaluate(0)
            end_pos[channel] = curve.evaluate(end_frame)
            
        start_pos_world = Vector(start_pos) @ rig.matrix_world
        end_pos_world = Vector(end_pos) @ rig.matrix_world
        offset = [-(end_pos_world[i] - start_pos_world[i]) for i in range(3)]
        
        offset[2] = 0
        return Vector(offset)

    def insert_location_keyframe(self, armature, frame, location):
        """Insert a location keyframe for the armature at the specified frame."""
        armature.location = location
        armature.keyframe_insert(data_path="location", frame=frame)

    def organize_positions(self, armature, action_dict):
        """Organize positions for sequences of animations in the NLA Editor."""
        location = Vector((0, 0, 0))

        # Ensure the armature has animation data
        if not armature.animation_data:
            armature.animation_data_create()

        # Ensure the armature has an action to hold keyframes
        if not armature.animation_data.action:
            armature.animation_data.action = bpy.data.actions.new(name="TempAction")

        action = armature.animation_data.action

        for action_name, frames in action_dict.items():  
            
            offset = self.get_cycle_offset(armature, action_name)
            end_location = location + offset

                
            strip = self.get_strip(armature, action_name)
            
            # Insert keyframes for start and end locations of the strip
            for frame, loc in [(strip.frame_start, location), (strip.frame_end, location), (strip.frame_end + 1, end_location)]:
                self.insert_location_keyframe(armature, frame, loc)

            location = end_location
    
    def duplicate_action(self, original_action_name, new_action_name):
        """Duplicate an action and return the new action"""
        original_action = bpy.data.actions.get(original_action_name)
        if original_action is None:
            raise ValueError(f"Action '{original_action_name}' not found")
        
        # Duplicate the action
        new_action = original_action.copy()
        new_action.name = f"{new_action_name}"
        

        return new_action


    def organize_nla_sequences(self, target_armature, actions_dict):
        """Organize sequences of animations in the NLA Editor for the target armature."""
        
        new_actions_dict = {}
        anim_start = 1
        location = Vector((0, 0, 0))
        
        # Ensure the armature has animation data
        if not target_armature.animation_data:
            target_armature.animation_data_create()

        # Ensure the armature has an action to hold keyframes
        if not target_armature.animation_data.action:
            target_armature.animation_data.action = bpy.data.actions.new(name="TempAction")
        location_action = armature.animation_data.action

        for action_name, frames in actions_dict.items():
            frame_start = frames[0]
            frame_end = frames[1]
            action_name = action_name.lower().replace(" ", "_") + "_rig_action"
            strip = self.get_strip(target_armature, action_name)
            original_period = int(strip.frame_end - strip.frame_start)
            remaining_period = frame_end - frame_start
            
            # Initialize original strip
            strip.frame_start = frame_start
            strip.frame_end = strip.frame_start + min(original_period, remaining_period)
            new_actions_dict[action_name] = (strip.frame_start, strip.frame_end)
            remaining_period -= original_period
            anim_start = strip.frame_end
            
            # Setup Initial position
            offset = self.get_cycle_offset(armature, strip.action, strip.frame_end - strip.frame_start)
            end_location = location + offset
            
            # Insert keyframes for start and end locations of the strip
            for frame, loc in [(strip.frame_start, location), (strip.frame_end, location), (strip.frame_end + 1, end_location)]:
                self.insert_location_keyframe(armature, frame, loc)
            location = end_location
            
            
            while remaining_period > 0:
                new_end_frame = min(new_start_frame + original_period, frame_end)
                new_action_name = f"{action_name}_{i + 1}"
                new_actions_dict[new_action_name] = (new_start_frame, new_end_frame)
                
                # Duplicate the action
                # NOTE: May not be necessary
                duplicated_action = self.duplicate_action(action_name, new_action_name)

                # Create a new NLA strip for the duplicated action
                new_strip_name = f"{action_name}_{i + 1}"
                new_strip = target_armature.animation_data.nla_tracks[0].strips.new(name=new_strip_name, start=int(new_start_frame), action=duplicated_action)
                
                # Update the end frame of the original strip
                new_strip.frame_end = new_end_frame
                anim_start = new_strip.frame_end
                print(f"Frame end: {new_strip.frame_end}")
                remaining_period -= original_period
                
                # Update position
                # Setup Initial position
                offset = self.get_cycle_offset(armature, strip.action, strip.frame_end - strip.frame_start)
                end_location = location + offset
                
                # Insert keyframes for start and end locations of the strip
                for frame, loc in [(strip.frame_start, location), (strip.frame_end, location), (strip.frame_end + 1, end_location)]:
                    self.insert_location_keyframe(armature, frame, loc)
                location = end_location
                    
        self.end_frame_anim = anim_start
        return new_actions_dict
    
    def run(self):
        self.clear_scene()
        character_path = os.path.join(self.root_path, 'characters')

        # Load the main target armature
        target_fbx_path = os.path.join(character_path, f"{self.character_name}.fbx")
        self.target_armature = self.load_rig(target_fbx_path, 'target_rig')
        
        animation_path = os.path.join(self.root_path, 'animations')

        # Load and process each action
        for action_name, frames in self.actions_dict.items():
            start_frame = frames[0]
            end_frame = frames[1]
            action_fbx_path = os.path.join(animation_path, f"{action_name}.fbx")
            rig_name = action_name.lower().replace(" ", "_") + "_rig"
            action_armature = self.load_rig(action_fbx_path, rig_name)
            action_armature.hide_set(True)
            self.push_action_to_nla(self.target_armature, f"{rig_name}_action")
            self.set_nla_strip_properties(self.target_armature, f"{rig_name}_action")
        
        # Organize the sequences and positions
        new_dict = self.organize_nla_sequences(self.target_armature, self.actions_dict)
        self.organize_positions(self.target_armature, new_dict)
        
        # Adjust scene timeline
        bpy.context.scene.frame_end = int(self.end_frame_anim)
        bpy.context.scene.frame_current = 0
        
 

# Example
root_path = r"C:\Users\PMLS\Desktop\blender stuff"
character_data = {'name': 'Boy (age 19 to 25)'}
actions_dict = {
    'Walking': (10, 70),  
    'Locking Hip Hop Dance': (70, 100), 
    
}

animation_handler = AnimationHandler(root_path, character_data, actions_dict)
animation_handler.run()       


#######################################

import bpy
from mathutils import Vector
import os
import math

class AnimationHandler:
    def __init__(self, root_path, character_data, actions_dict):
        self.root_path = root_path
        self.character_name = character_data['name']
        self.actions_dict = actions_dict
        self.target_armature = None
        self.box_object = None
        self.end_frame_anim = None

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
    
    def push_action_to_nla(self, armature, action_name):
        """Push down action to NLA"""
        
        # Find the action
        action = bpy.data.actions.get(action_name)
        if action is None:
            raise ValueError(f"Action '{action_name}' not found")
           
        # Set the action to the armature
        if not armature.animation_data:
            armature.animation_data_create()
        armature.animation_data.action = None
         
        # Create or find the NLA track
        nla_tracks = armature.animation_data.nla_tracks
        nla_track = nla_tracks.new()
        nla_track.name = action_name

        nla_strip = nla_track.strips.new(name=action_name , start=0, action=action)

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

    def get_cycle_offset(self, rig, action, end_frame):
        """Get the amount that the armature moves with each animation cycle"""
            
        start_pos = [0, 0, 0]
        end_pos = [0, 0, 0]
        for curve in action.fcurves:
            if "mixamorig:Hips" not in curve.data_path: continue
            if "location" not in curve.data_path: continue
            channel = curve.array_index
            
            start_pos[channel] = curve.evaluate(0)
            end_pos[channel] = curve.evaluate(end_frame)
            
        start_pos_world = Vector(start_pos) @ rig.matrix_world
        end_pos_world = Vector(end_pos) @ rig.matrix_world
        offset = [-(end_pos_world[i] - start_pos_world[i]) for i in range(3)]
        
        offset[2] = 0
        return Vector(offset)

    def insert_location_keyframe(self, armature, frame, location):
        """Insert a location keyframe for the armature at the specified frame."""
        armature.location = location
        armature.keyframe_insert(data_path="location", frame=frame)

    def organize_positions(self, armature, action_dict):
        """Organize positions for sequences of animations in the NLA Editor."""
        location = Vector((0, 0, 0))

        # Ensure the armature has animation data
        if not armature.animation_data:
            armature.animation_data_create()

        # Ensure the armature has an action to hold keyframes
        if not armature.animation_data.action:
            armature.animation_data.action = bpy.data.actions.new(name="TempAction")

        action = armature.animation_data.action

        for action_name, frames in action_dict.items():  
            
            offset = self.get_cycle_offset(armature, action_name)
            end_location = location + offset

                
            strip = self.get_strip(armature, action_name)
            
            # Insert keyframes for start and end locations of the strip
            for frame, loc in [(strip.frame_start, location), (strip.frame_end, location), (strip.frame_end + 1, end_location)]:
                self.insert_location_keyframe(armature, frame, loc)

            location = end_location
    
    def duplicate_action(self, original_action_name, new_action_name):
        """Duplicate an action and return the new action"""
        original_action = bpy.data.actions.get(original_action_name)
        if original_action is None:
            raise ValueError(f"Action '{original_action_name}' not found")
        
        # Duplicate the action
        new_action = original_action.copy()
        new_action.name = f"{new_action_name}"
        

        return new_action


    def organize_nla_sequences(self, target_armature, actions_dict):
        """Organize sequences of animations in the NLA Editor for the target armature."""
        
        new_actions_dict = {}
        anim_start = 1
        location = Vector((0, 0, 0))
        
        # Ensure the armature has animation data
        if not target_armature.animation_data:
            target_armature.animation_data_create()

        # Ensure the armature has an action to hold keyframes
        if not target_armature.animation_data.action:
            target_armature.animation_data.action = bpy.data.actions.new(name="TempAction")
        location_action = target_armature.animation_data.action

        for action_name, frames in actions_dict.items():
            frame_start = frames[0]
            frame_end = frames[1]
            action_name = action_name.lower().replace(" ", "_") + "_rig_action"
            strip = self.get_strip(target_armature, action_name)
            original_period = int(strip.frame_end - strip.frame_start)
            remaining_period = frame_end - frame_start
            
            # Initialize original strip
            strip.frame_start = frame_start
            strip.frame_end = strip.frame_start + min(original_period, remaining_period)
            new_actions_dict[action_name] = (strip.frame_start, strip.frame_end)
            remaining_period -= original_period
            anim_start = strip.frame_end + 1
            
            # Setup Initial position
            offset = self.get_cycle_offset(target_armature, strip.action, strip.frame_end - strip.frame_start)
            
            end_location = location + offset
            print(f"Starting position: {location}, Offset: {offset}, End location: {end_location}")
            
            # Insert keyframes for start and end locations of the strip
            for frame, loc in [(strip.frame_start, location), (strip.frame_end, location), (strip.frame_end + 1, end_location)]:
                self.insert_location_keyframe(target_armature, frame, loc)
            location = end_location
            
            i = 0
            while remaining_period > 0:
                new_end_frame = min(anim_start + original_period, frame_end)
                new_action_name = f"{action_name}_{i + 1}"
                new_actions_dict[new_action_name] = (anim_start, new_end_frame)
                
                # Duplicate the action
                # NOTE: May not be necessary
                duplicated_action = self.duplicate_action(action_name, new_action_name)

                # Create a new NLA strip for the duplicated action
                new_strip_name = f"{action_name}_{i + 1}"
                new_strip = target_armature.animation_data.nla_tracks[0].strips.new(name=new_strip_name, start=int(anim_start), action=duplicated_action)
                
                # Update the end frame of the original strip
                new_strip.frame_end = new_end_frame
                anim_start = new_strip.frame_end + 1
                print(f"Frame end: {new_strip.frame_end}")
                remaining_period -= original_period
                
                # Update position
                # Setup Initial position
                offset = self.get_cycle_offset(target_armature, strip.action, strip.frame_end - strip.frame_start)
                end_location = location + offset
                print(f"Starting position: {location}, Offset: {offset}, End location: {end_location}")
                
                # Insert keyframes for start and end locations of the strip
                for frame, loc in [(new_strip.frame_start, location), (new_strip.frame_end, location), (new_strip.frame_end + 1, end_location)]:
                    self.insert_location_keyframe(target_armature, frame, loc)
                location = end_location
                i += 1
                    
        self.end_frame_anim = anim_start
        return new_actions_dict
    
    def run(self):
        self.clear_scene()
        character_path = os.path.join(self.root_path, 'characters')

        # Load the main target armature
        target_fbx_path = os.path.join(character_path, f"{self.character_name}.fbx")
        self.target_armature = self.load_rig(target_fbx_path, 'target_rig')
        
        animation_path = os.path.join(self.root_path, 'animations')

        # Load and process each action
        for action_name, frames in self.actions_dict.items():
            start_frame = frames[0]
            end_frame = frames[1]
            action_fbx_path = os.path.join(animation_path, f"{action_name}.fbx")
            rig_name = action_name.lower().replace(" ", "_") + "_rig"
            action_armature = self.load_rig(action_fbx_path, rig_name)
            action_armature.hide_set(True)
            self.push_action_to_nla(self.target_armature, f"{rig_name}_action")
            self.set_nla_strip_properties(self.target_armature, f"{rig_name}_action")
        
        # Organize the sequences and positions
        new_dict = self.organize_nla_sequences(self.target_armature, self.actions_dict)
#        self.organize_positions(self.target_armature, new_dict)
        
        # Adjust scene timeline
        bpy.context.scene.frame_end = int(self.end_frame_anim)
        bpy.context.scene.frame_current = 0
        
 

# Example
root_path = r"C:\Users\PMLS\Desktop\blender stuff"
character_data = {'name': 'Boy (age 19 to 25)'} 
actions_dict = {
    'Walking': (10, 80),  
    'Locking Hip Hop Dance': (81, 100), 
    
}

animation_handler = AnimationHandler(root_path, character_data, actions_dict)
animation_handler.run()       