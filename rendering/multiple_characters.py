import bpy
from mathutils import Vector
import os
import math
import random

class AnimationHandler:
    def __init__(self, root_path, characters_data, actions_list,textures, output_filename,background_characters):
        self.root_path = root_path
        self.characters_data = characters_data
        self.actions_list = actions_list
        self.target_armature = None
        self.box_object = None
        self.end_frame_anim = 100
        self.scene_cameras=[]
        self.char_cameras=[]
        self.smoothing_factor = 0.2
        self.closest_camera=None
        self.textures=textures
        self.max_height=0
        self.output_filename=output_filename
        self.background_characters=background_characters
  

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
        bpy.data.scenes[0].timeline_markers.clear()
        
        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
        bpy.app.handlers.frame_change_pre.clear()
        bpy.app.handlers.frame_change_post.clear()


    def retarget_rokoko(self, source_armature, target_armature):
        def enable_addon(addon_name):
            if addon_name not in bpy.context.preferences.addons:
                bpy.ops.preferences.addon_enable(module=addon_name)

        # Enable the Rokoko Addon
        enable_addon('rokoko-studio-live-blender')

        # Function to build bone list
        def build_bone_list():
            if source_armature:
                bpy.context.scene.rsl_retargeting_armature_source = target_armature
            else:
                print("Source Armature not found")
            if target_armature:
                bpy.context.scene.rsl_retargeting_armature_target = source_armature
            else:
                print("Target Armature not found")
            bpy.ops.rsl.build_bone_list()
        
        build_bone_list()

        # Function to retarget using the Rokoko addon
        def retarget_animation():
            bpy.ops.rsl.retarget_animation()
        
        retarget_animation()



    def load_rig(self, filepath: str, name: str):
        """Load a rig from an FBX file"""
        bpy.ops.import_scene.fbx(filepath=filepath, use_manual_orientation=True, use_anim=False, axis_forward='-Y', axis_up='Z')
        rig = bpy.context.active_object
        rig.name = name
        rig.show_in_front = True
        return rig
    

    def load_animation(self, filepath: str, name: str):
        """Load a rig from an FBX file"""
        bpy.ops.import_anim.bvh(filepath=filepath, axis_forward='Z', axis_up='Y')
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
            
        start_pos_world = Vector(start_pos) @ self.rig_matrix_world
        end_pos_world = Vector(end_pos) @ self.rig_matrix_world
        offset = [-(end_pos_world[i] - start_pos_world[i]) for i in range(3)]
        
        offset[2] = 0
        return Vector(offset)

    def insert_location_keyframe(self, armature, frame, location):
        """Insert a location keyframe for the armature at the specified frame."""
        armature.location = location
        armature.keyframe_insert(data_path="location", frame=frame)
    
    def insert_rotation_keyframe(self, armature, frame, direction):
        """Insert a rotation keyframe for the armature at the specified frame."""
        armature.rotation_euler = direction.to_track_quat('-Y', 'Z').to_euler()
        armature.keyframe_insert(data_path="rotation_euler", frame=frame)

    def place_armature_with_action(self, armature, actions_dict):
        # Set the initial location and keyframe

        previous_direction = Vector((0, 1, 0))
        for action_name, data in actions_dict.items():


            strip = self.get_strip(armature, action_name)
           

            # Get the positional offset of a single cycle with no rotational changes
            cycle_offset = self.get_cycle_offset(armature, strip.action, strip.frame_end - strip.frame_start)
            
            # Determine total desired offset for the cycle
            start_location=data[1]
            end_location=data[2]
            target_offset = end_location - start_location
            target_offset.z = 0

            # Calculate the direction vector from start_location to end_location
            direction = target_offset.normalized()
            
            # Use old direction if direction is 0
            if direction.length == 0: direction = previous_direction
            previous_direction = direction

            # Calculate the cycle offset after the rig has ben rotated
            # Note: Different from normal caclulations because of swapped axes.
            #       (Rig up is Y, blender up is Z)
            rotated_cycle_offset = Vector([
                cycle_offset.x * direction.x - cycle_offset.y * direction.y, 
                - cycle_offset.x * direction.y - cycle_offset.y * direction.x,
                0
            ])
            
            # Add the keyframes
            #   Rotation is constant across the strip
            #   Location:
            #      frame 0: start_location
            #      end_frame: end_location - cycle_offset 
            #                    so that the rig ends up at the target at the end of the cycle
            #                    This is because if end_location was used, the rig motion would move it past
            #                    end_location. By subtracting cycle_offset, the rig ends the cycle at end_location.
            #      end_frame + 1: end_location (so that it doesn't teleport back when rig stops driving animation)
            #                                  (likely overwritten by next strip)
            self.insert_rotation_keyframe(armature, strip.frame_start, direction)
            self.insert_rotation_keyframe(armature, strip.frame_end, direction)
            self.insert_location_keyframe(armature, strip.frame_start, start_location)
            self.insert_location_keyframe(armature, strip.frame_end, end_location - rotated_cycle_offset)
            self.insert_location_keyframe(armature, strip.frame_end + 1, end_location)

            # Update the scene
            bpy.context.view_layer.update()

            action = self.target_armature.animation_data.action
            for curve in action.fcurves:
                for key in curve.keyframe_points:        
                    key.interpolation='LINEAR'


    
    def duplicate_action(self, original_action_name, new_action_name):
        """Duplicate an action and return the new action"""
        original_action = bpy.data.actions.get(original_action_name)
        if original_action is None:
            raise ValueError(f"Action '{original_action_name}' not found")
        
        # Duplicate the action
        new_action = original_action.copy()
        new_action.name = f"{new_action_name}"
        return new_action


    def organize_nla_sequences(self, target_armature, actions_dict, character_name):
        """Organize sequences of animations in the NLA Editor for the target armature."""
        
        new_actions_dict = {}
        anim_start = 1
       
        
        # Ensure the armature has animation data
        if not target_armature.animation_data:
            target_armature.animation_data_create()

        # Ensure the armature has an action to hold keyframes
        if not target_armature.animation_data.action:
            target_armature.animation_data.action = bpy.data.actions.new(name="TempAction")
        location_action = target_armature.animation_data.action

        for action_name, data in actions_dict.items():
            frame_start = data[0][0]
            frame_end = data[0][1]
            action_name = character_name+'_' + action_name.lower().replace(" ", "_") + "_rig_action Retarget"
            strip = self.get_strip(target_armature, action_name)
            original_period = int(strip.frame_end - strip.frame_start)
            remaining_period = frame_end - frame_start
            num_repeats = math.ceil(remaining_period / original_period)

            # Initialize original strip
            strip.frame_start = frame_start
            strip.frame_end = strip.frame_start + min(original_period, remaining_period)
            if remaining_period > original_period:
                start_location=data[1]
                ending_location=data[1]+((data[2]-data[1])/num_repeats)
                new_actions_dict[action_name] = [(strip.frame_start, strip.frame_end),start_location ,ending_location ]
                print(f"action: {action_name}, start location: {start_location}, end location: {ending_location}")
                start_location=ending_location
            else:
                start_location=data[1]
                ending_location=data[2]
                new_actions_dict[action_name] = [(strip.frame_start, strip.frame_end),start_location ,ending_location ]
                print(f"action: {action_name}, start location: {start_location}, end location: {ending_location}")
            
            remaining_period -= original_period
            anim_start = strip.frame_end + 1       
            
            i = 0
            while remaining_period > 0:

                new_end_frame = min(anim_start + original_period, frame_end)
                new_action_name = f"{action_name}_{i + 1}"
                ending_location=start_location+(data[2]-data[1])/num_repeats

                new_actions_dict[new_action_name] = [(anim_start, new_end_frame), start_location, ending_location]
                print(f"action: {new_action_name}, start location: {start_location}, end location: {ending_location}")
                start_location=ending_location
                
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
                
                i += 1
                    
        self.end_frame_anim = anim_start
        return new_actions_dict
    
    def organize_positions(self, armature, action_dict):
        """Organize positions for sequences of animations in the NLA Editor."""
        location = Vector((0, 0, 0))

        for action_name, frames in action_dict.items():  
            # Setup Initial position
            strip = self.get_strip(armature, action_name)
            offset = self.get_cycle_offset(armature, strip.action, strip.frame_end - strip.frame_start)
            
            end_location = location + offset
            print(f"Starting position: {location}, Offset: {offset}, End location: {end_location}")
            
            # Insert keyframes for start and end locations of the strip
            for frame, loc in [(strip.frame_start, location), (strip.frame_end, location), (strip.frame_end + 1, end_location)]:
                self.insert_location_keyframe(armature, frame, loc)
            location = end_location
    
    def create_cameras(self, character_name):
        #setting the position as well 
        """Create a camera for following the character"""
        char_cam_data = bpy.data.cameras.new(name=f'{character_name}_camera')
        char_camera = bpy.data.objects.new(name=f'{character_name}_camera', object_data=char_cam_data)
        bpy.context.collection.objects.link(char_camera)
        camera_dict={'name': f'{character_name}_camera', 'camera': char_camera, 'char_name':character_name, 'previous_loc': Vector((0,0,0)),'smoothed_loc': Vector((0, 0, 0))}
        self.char_cameras.append(camera_dict)

    def smooth_location(self, current_loc, target_loc):
        """Smooth the transition between the current and target locations."""
        return current_loc.lerp(target_loc, self.smoothing_factor)

    def direction_find(self, camera_dict):
        target_bone_names = ['hip', 'pelvis','hips']
        character_name = camera_dict['char_name']
        armature = bpy.data.objects[f'{character_name}_rig']
        
        hips_bone = None
        for bone in armature.pose.bones:
            if any(target_bone_name in bone.name.lower() for target_bone_name in target_bone_names):
                hips_bone = bone
                break
        
        if hips_bone is None:
            raise ValueError(f"No bone named 'hip' or 'pelvis' found in armature {character_name}_rig")
    

        current_location = armature.matrix_world @ hips_bone.head

        previous_loc=camera_dict['previous_loc']
        # Compute the direction
        direction = (current_location-previous_loc).normalized()
        camera_dict['previous_loc']=current_location
        
        return direction
 

    def camera_follow_character(self, scene, dpgraph):
        """Follow hip bone with the camera.""" 

        
        for camera_data in self.char_cameras:
            character_name=camera_data['char_name']
            print(character_name)
            camera_char=camera_data['camera']
            target_armature = scene.objects.get(f'{character_name}_rig')
            target_armature = target_armature.evaluated_get(dpgraph)
            
            target_bone_name = "head"        
            for bone in target_armature.pose.bones:
                if target_bone_name in bone.name.lower():
                    head_bone = target_armature.pose.bones.get(f'{bone.name}')
                    break

            target_bone_name = "foot"        
            for bone in target_armature.pose.bones:
                if target_bone_name in bone.name.lower():
                    foot_bone = target_armature.pose.bones.get(f'{bone.name}')
                    break

            head_bone_world_location =target_armature.matrix_world @ head_bone.head
            
            foot_bone_world_location=target_armature.matrix_world @ foot_bone.head
            height_x = abs(head_bone_world_location.x - foot_bone_world_location.x)
            height_y = abs(head_bone_world_location.y - foot_bone_world_location.y)
            height_z = abs(head_bone_world_location.z - foot_bone_world_location.z)
    
            # Find the maximum height difference
            height = max(height_x, height_y, height_z)
            distance=height*2

            if camera_char and target_armature:
                # Get the location of the hips bone
                target_bone_names = ['hips', 'pelvis','hip']

                hips_bone = None
                for bone in self.target_armature.pose.bones:
                    if any(target_bone_name in bone.name.lower() for target_bone_name in target_bone_names):
                        hips_bone = bone
                        break
    
                if hips_bone:

                    # Calculate the location of the hips bone in world space
                    hips_location = target_armature.matrix_world @ hips_bone.head
                    print(hips_location)
                    camera_char.data.angle = math.radians(110)

                    rotated_offset = self.direction_find(camera_data) * distance
                    print('previous location', camera_data['previous_loc'])
                    rotated_offset.z = 0
                    target_location = hips_location + rotated_offset
                    target_location.z = height + 4       
                    # Smooth the location
                    camera_data['smoothed_loc'] = self.smooth_location(camera_data['smoothed_loc'], target_location)
                    camera_char.location = camera_data['smoothed_loc']
                    
                    # Make the camera look at the hips bone
                    direction = hips_location - camera_char.location
                    rot_quat = direction.to_track_quat('-Z', 'Y')
                    camera_char.rotation_euler = rot_quat.to_euler()
                    camera_char.data.lens = 18 
                    # Adjust camera lens to broaden the view
                    camera_char.data.angle = math.radians(110)  # Adjust angle as needed for wider view
                else:
                    print("Hips bone not found")
            else:
                print("Camera or target armature not found")


    def frame_change_handler(self, scene, dpgraph):
        """Frame change handler to follow the character with the camera"""
        self.camera_follow_character(scene, dpgraph)
        current_frame = bpy.context.scene.frame_current
        active_camera = None
        active_character_count = 0

        for character_data, actions in zip(self.characters_data, self.actions_list):
            character_name = character_data['name']
        
        # Check if any action matches the current frame for the character
    
            for action_name, data in actions.items():
                start_frame = data[0][0]
                end_frame = data[0][1]
                print('action_name in frame change', action_name )
                
                if start_frame <= current_frame and current_frame <= end_frame:
                    if action_name != 'Idle': 
                        active_camera = f"{character_name}"    
                        active_character_count += 1
                    break

        if active_character_count != 1:
            # Use scene camera
            self.update_closest_camera_rotation()
        else:
            char_camera=bpy.data.objects.get(f'{active_camera}_camera')
            marker = bpy.context.scene.timeline_markers.new(name=char_camera.name, frame=current_frame)
            marker.camera = char_camera
        
        print("Updating camera")
                
  

    def create_scene_cameras(self):
        
        avg_hip_bone=Vector((0,0,0))
        n=0

        for character in self.characters_data:
            character_name=character['name']
            armature=bpy.data.objects.get(f'{character_name}_rig')

            target_bone_names = ['hip', 'pelvis', 'hips']
            
            hip_bone = None
            for bone in armature.pose.bones:
                if any(target_bone_name in bone.name.lower() for target_bone_name in target_bone_names):
                    hip_bone = bone
                    break
            

            hip_bone_world_location = armature.matrix_world @ hip_bone.head
            avg_hip_bone+=hip_bone_world_location
            n+=1

        avg_hip_bone=avg_hip_bone/n
        
        vertices_world = [self.box_object.matrix_world @ v.co for v in self.box_object.data.vertices]
    
        j=0
        for i in [0,2,4,6]:
            cam_data = bpy.data.cameras.new(name=f'camera_{j}')
            cam_object = bpy.data.objects.new(name=f'camera_{j}', object_data=cam_data)
            cam_object.location = vertices_world[i]
            cam_object.location.z=self.max_height+10
            bpy.context.collection.objects.link(cam_object)
            direction = avg_hip_bone - cam_object.location
            rot_quat = direction.to_track_quat('-Z', 'Y')
            cam_object.rotation_euler = rot_quat.to_euler()
            j+=1
            self.scene_cameras.append(cam_object)
        print('max height' , self.max_height)
    
            
    def update_closest_camera_rotation(self):
        avg_hip_bone=Vector((0,0,0))
        avg_head_bone_world_location=Vector((0,0,0))
        n=0
        target_bone_names = ['hip', 'pelvis', 'hips']
        for character in self.characters_data:
            character_name=character['name'] 
            armature=bpy.data.objects.get(f'{character_name}_rig')

            target_bone_name = "head"        
            for bone in armature.pose.bones:
                if target_bone_name in bone.name.lower():
                    head_bone = armature.pose.bones.get(f'{bone.name}')
                    break

            head_bone_world_location = armature.matrix_world @ head_bone.head
            
            hip_bone = None
            for bone in armature.pose.bones:
                if any(target_bone_name in bone.name.lower() for target_bone_name in target_bone_names):
                    hip_bone = bone
                    break
            

            hip_bone_world_location = armature.matrix_world @ hip_bone.head
            avg_head_bone_world_location+=head_bone_world_location
            avg_hip_bone+=hip_bone_world_location
            n+=1
        
        avg_hip_bone=avg_hip_bone/n
        avg_head_bone_world_location=avg_head_bone_world_location/n
        # Calculate distances to the hip bone and find the closest camera
        closest_camera = None
        closest_distance = float('inf')  # Initializing to infinity for comparison

        for i, cam in enumerate(self.scene_cameras):
            distance = ((avg_hip_bone) - cam.location).length
            print(f"Camera {i}: {distance}")
            if distance < closest_distance:
                closest_distance = distance
                closest_camera = cam

        if closest_camera:
            current_frame = bpy.context.scene.frame_current
            
            # Define the threshold for switching cameras (e.g., 10 frames)
            frame_threshold = 10
            
            # Check if the closest camera is different and the frame gap is greater than the threshold
            if closest_camera != self.closest_camera and (self.closest_camera is None or abs(current_frame - self.last_camera_switch_frame) > frame_threshold):
                # Create a new marker for the closest camera
                marker = bpy.context.scene.timeline_markers.new(name=closest_camera.name, frame=current_frame)
                marker.camera = closest_camera

                # Rotate the closest camera to face the head bone
                direction = avg_head_bone_world_location - closest_camera.location
                rot_quat = direction.to_track_quat('-Z', 'Y')
                closest_camera.rotation_euler = rot_quat.to_euler()

                # Update the last switch frame and the closest camera
                self.last_camera_switch_frame = current_frame
                self.closest_camera = closest_camera
            elif closest_camera == self.closest_camera:
                # If the closest camera hasn't changed, still update its rotation
                direction = avg_head_bone_world_location - closest_camera.location
                rot_quat = direction.to_track_quat('-Z', 'Y')
                closest_camera.rotation_euler = rot_quat.to_euler()



    # def frame_change_handler(self, scene, dpgraph, character_name):
    #     """Frame change handler to follow the character with the camera"""
        
    #     #self.update_closest_camera_rotation()
    #     self.camera_follow_character(dpgraph, scene, character_name)
        
    #     print("Updating camera")

 
    def render_animation(self, start=10):
        """Render the animation to an MP4 file"""
        output_path = os.path.join(self.root_path, self.output_filename)
        scene = bpy.context.scene
        scene.render.image_settings.file_format = 'FFMPEG'
        scene.render.ffmpeg.format = 'MPEG4'
        scene.render.ffmpeg.codec = 'H264'
        scene.render.ffmpeg.constant_rate_factor = 'HIGH'
        scene.render.ffmpeg.ffmpeg_preset = 'GOOD'
        scene.render.filepath = output_path
        scene.render.engine = 'BLENDER_EEVEE'

        # Set output settings
        scene.render.resolution_x = 720
        scene.render.resolution_y = 460
        scene.render.resolution_percentage = 80
        scene.frame_start = start
        scene.frame_end = int(self.end_frame_anim)

        # Render the animation
        bpy.ops.render.render('INVOKE_DEFAULT', animation=True)

    def create_box(self, Size=100):
        """Create a box around the character to absorb light"""
        
        self.max_height=0

        foot_bone_world_location=Vector((0,0,0))
        n=0

        for character in self.characters_data:
            character_name=character['name']
            armature=bpy.data.objects.get(f'{character_name}_rig')
            
            target_bone_name = "head"        
            for bone in armature.pose.bones:
                if target_bone_name in bone.name.lower():
                    head_bone = armature.pose.bones.get(f'{bone.name}')
                    break

            target_bone_name = "foot"        
            for bone in armature.pose.bones:
                if target_bone_name in bone.name.lower():
                    foot_bone = armature.pose.bones.get(f'{bone.name}')
                    break

            head_bone_world_location =armature.matrix_world @ head_bone.head
            
            foot_bone_world_location=armature.matrix_world @ foot_bone.head
            height_x = abs(head_bone_world_location.x - foot_bone_world_location.x)
            height_y = abs(head_bone_world_location.y - foot_bone_world_location.y)
            height_z = abs(head_bone_world_location.z - foot_bone_world_location.z)
    
            # Find the maximum height difference
            height = max(height_x, height_y, height_z)
    
            
            if height>self.max_height:
                self.max_height=height
                print(self.max_height)


        bpy.ops.mesh.primitive_cube_add()
        bpy.context.object.scale = ((Size, Size, self.max_height+10))
        bpy.context.object.location = ((0, 0, self.max_height+10))
        self.box_object = bpy.context.active_object

    # def set_box_properties(self, walls_color=(0.5, 0.7, 0.5, 1), floor_color=(0.6, 0.4, 0.2, 1), ceiling_color=(1, 1, 1, 1)):
    #     """Set properties of the box with specific materials and colors"""
    #     if not self.box_object:
    #         raise ValueError("Box object not found. Create the box first.")

    #     # Create materials
    #     walls = bpy.data.materials.new(name='walls')
    #     floor = bpy.data.materials.new(name='floor')
    #     ceiling = bpy.data.materials.new(name='ceiling')

    #     # Set the colors for the materials
    #     walls.diffuse_color = walls_color  # Default to soft green color
    #     floor.diffuse_color = floor_color  # Default to sober brown color
    #     ceiling.diffuse_color = ceiling_color  # Default to white color

        
    #     self.box_object.data.materials.append(walls)
    #     self.box_object.data.materials.append(floor)
    #     self.box_object.data.materials.append(ceiling)

    #     self.box_object.data.polygons[0].material_index = self.box_object.material_slots.find('walls')
    #     self.box_object.data.polygons[1].material_index = self.box_object.material_slots.find('walls')
    #     self.box_object.data.polygons[2].material_index = self.box_object.material_slots.find('walls')
    #     self.box_object.data.polygons[3].material_index = self.box_object.material_slots.find('walls')
    #     self.box_object.data.polygons[4].material_index = self.box_object.material_slots.find('floor')
    #     self.box_object.data.polygons[5].material_index = self.box_object.material_slots.find('ceiling')

    #     # Update the mesh to reflect changes
    #     self.box_object.data.update()


    def set_box_properties(self, walls_texture_path, floor_texture_path, ceiling_texture_path,
                        walls_texture_coords='UV', floor_texture_coords='UV', ceiling_texture_coords='UV',
                        walls_mapping_scale=(8,8, 8), floor_mapping_scale=(8, 8, 8), ceiling_mapping_scale=(8, 8, 8),
                        walls_mapping_rotation=(0, 0, 0), floor_mapping_rotation=(0, 0, 0), ceiling_mapping_rotation=(0, 0, 0),
                        walls_mapping_translation=(0, 0, 0), floor_mapping_translation=(0, 0, 0), ceiling_mapping_translation=(0, 0, 0)):
        """Set properties of the box with specific textures and mapping settings"""
        if not self.box_object:
            raise ValueError("Box object not found. Create the box first.")

        # Create materials
        walls = bpy.data.materials.new(name='walls') 
        floor = bpy.data.materials.new(name='floor')
        ceiling = bpy.data.materials.new(name='ceiling')

        # Create textures using the images' paths
        walls.use_nodes = True
        bsdf1 = walls.node_tree.nodes["Principled BSDF"]
        wall_tex = walls.node_tree.nodes.new('ShaderNodeTexImage')
        wall_tex.image = bpy.data.images.load(walls_texture_path)
        walls.shadow_method = 'NONE'


        floor.use_nodes = True
        bsdf2 = floor.node_tree.nodes["Principled BSDF"]
        floor_tex = floor.node_tree.nodes.new('ShaderNodeTexImage')
        floor_tex.image = bpy.data.images.load(floor_texture_path)
        floor.shadow_method='NONE'

        ceiling.use_nodes = True
        bsdf3 = ceiling.node_tree.nodes["Principled BSDF"]
        ceil_tex = ceiling.node_tree.nodes.new('ShaderNodeTexImage')
        ceil_tex.image = bpy.data.images.load(ceiling_texture_path)
        ceiling.shadow_method='NONE'

        # Create texture coordinate and mapping nodes for walls material
        tex_coord1 = walls.node_tree.nodes.new('ShaderNodeTexCoord')
        mapping1 = walls.node_tree.nodes.new('ShaderNodeMapping')
        mapping1.vector_type = 'POINT'
        tex_coord1.location = (-400, 300)
        mapping1.location = (-200, 300)

        # Set mapping properties for walls material
        mapping1.inputs['Scale'].default_value = walls_mapping_scale
        mapping1.inputs['Rotation'].default_value = walls_mapping_rotation
        if 'Translation' in mapping1.inputs:
            mapping1.inputs['Translation'].default_value = walls_mapping_translation

        # Create texture coordinate and mapping nodes for floor material
        tex_coord2 = floor.node_tree.nodes.new('ShaderNodeTexCoord')
        mapping2 = floor.node_tree.nodes.new('ShaderNodeMapping')
        mapping2.vector_type = 'POINT'
        tex_coord2.location = (-400, 0)
        mapping2.location = (-200, 0)

        # Set mapping properties for floor material
        mapping2.inputs['Scale'].default_value = floor_mapping_scale
        mapping2.inputs['Rotation'].default_value = floor_mapping_rotation
        if 'Translation' in mapping2.inputs:
            mapping2.inputs['Translation'].default_value = floor_mapping_translation

        # Create texture coordinate and mapping nodes for ceiling material
        tex_coord3 = ceiling.node_tree.nodes.new('ShaderNodeTexCoord')
        mapping3 = ceiling.node_tree.nodes.new('ShaderNodeMapping')
        mapping3.vector_type = 'POINT'
        tex_coord3.location = (-400, -300)
        mapping3.location = (-200, -300)

        # Set mapping properties for ceiling material
        mapping3.inputs['Scale'].default_value = ceiling_mapping_scale
        mapping3.inputs['Rotation'].default_value = ceiling_mapping_rotation
        if 'Translation' in mapping3.inputs:
            mapping3.inputs['Translation'].default_value = ceiling_mapping_translation

        # Connect nodes in shader editor
        walls.node_tree.links.new(mapping1.inputs['Vector'], tex_coord1.outputs['UV'])
        walls.node_tree.links.new(wall_tex.inputs['Vector'], mapping1.outputs['Vector'])
        walls.node_tree.links.new(bsdf1.inputs['Base Color'], wall_tex.outputs['Color'])

        floor.node_tree.links.new(mapping2.inputs['Vector'], tex_coord2.outputs['UV'])
        floor.node_tree.links.new(floor_tex.inputs['Vector'], mapping2.outputs['Vector'])
        floor.node_tree.links.new(bsdf2.inputs['Base Color'], floor_tex.outputs['Color'])

        ceiling.node_tree.links.new(mapping3.inputs['Vector'], tex_coord3.outputs['UV'])
        ceiling.node_tree.links.new(ceil_tex.inputs['Vector'], mapping3.outputs['Vector'])
        ceiling.node_tree.links.new(bsdf3.inputs['Base Color'], ceil_tex.outputs['Color'])

        # Set roughness and connect to material output
        bsdf1.inputs['Roughness'].default_value = 1.0
        bsdf1.inputs[3].default_value = 1
        bsdf2.inputs['Roughness'].default_value = 1.0
        bsdf2.inputs[3].default_value = 1
        bsdf3.inputs['Roughness'].default_value = 1.0
        bsdf3.inputs[3].default_value = 1

        # Connect bsdf to material output
        mat_out = walls.node_tree.nodes['Material Output']
        walls.node_tree.links.new(mat_out.inputs['Surface'], bsdf1.outputs['BSDF'])
        floor.node_tree.links.new(mat_out.inputs['Surface'], bsdf2.outputs['BSDF'])
        ceiling.node_tree.links.new(mat_out.inputs['Surface'], bsdf3.outputs['BSDF'])

        # Assign materials to the object
        self.box_object.data.materials.append(walls)
        self.box_object.data.materials.append(floor)
        self.box_object.data.materials.append(ceiling)


        # Assign material indices to the object's polygons
        self.box_object.data.polygons[0].material_index = self.box_object.material_slots.find('walls')
        self.box_object.data.polygons[1].material_index = self.box_object.material_slots.find('walls')
        self.box_object.data.polygons[2].material_index = self.box_object.material_slots.find('walls')
        self.box_object.data.polygons[3].material_index = self.box_object.material_slots.find('walls')
        self.box_object.data.polygons[4].material_index = self.box_object.material_slots.find('floor')
        self.box_object.data.polygons[5].material_index = self.box_object.material_slots.find('ceiling')

        # Update the mesh to reflect changes
        self.box_object.data.update()
   



    def create_light(self, light_type='SUN', color=(1, 1, 1), energy=10):
        """Create a light source in the scene"""
        if not self.box_object:
            raise ValueError("Box object not found. Create the box first.")
        
        box_location = self.box_object.location
        
        light_data = bpy.data.lights.new(name="Light_Source", type=light_type)
        light_data.color = color
        light_data.energy = energy
        light_object = bpy.data.objects.new(name="Light_Source", object_data=light_data)
        bpy.context.collection.objects.link(light_object)

        # Position the light inside the upper side of the box like a ceiling light
        light_object.location = (box_location.x, box_location.y, box_location.z - 2)

        # Point the light at the center of the box
        direction = Vector((box_location.x, box_location.y, box_location.z)) - light_object.location
        rot_quat = direction.to_track_quat('-Z', 'Y')
        light_object.rotation_euler = rot_quat.to_euler()
        light_object.rotation_euler = (13.3724, -56.947, 0.923632)
        light_object.data.use_shadow=True

        light_data2 = bpy.data.lights.new(name="Light_Source_1", type=light_type)
        light_data2.color = color
        light_data2.energy = energy
        light_object2 = bpy.data.objects.new(name="Light_Source", object_data=light_data2)
        bpy.context.collection.objects.link(light_object2)

        # Position the light inside the upper side of the box like a ceiling light
        light_object2.location = (box_location.x, box_location.y, box_location.z - 2)

        # Point the light at the center of the box
        direction = Vector((box_location.x, box_location.y, box_location.z)) - light_object2.location
        rot_quat = direction.to_track_quat('-Z', 'Y')
        light_object2.rotation_euler = rot_quat.to_euler()
        light_object2.rotation_euler = (-13.3724, 56.947, -0.923632)
        light_object2.data.use_shadow=False



        return light_object



    def generate_random_locations_within_boundaries(self,vertices, main_scene_divisor, num_points):
        # Calculate main scene vertices by dividing the original vertices by the divisor
        main_scene_vertices = [v / main_scene_divisor for v in vertices]

        # Extract min and max values for x and y from the main scene vertices
        main_scene_min_x = min(v.x for v in main_scene_vertices)
        main_scene_max_x = max(v.x for v in main_scene_vertices)
        main_scene_min_y = min(v.y for v in main_scene_vertices)
        main_scene_max_y = max(v.y for v in main_scene_vertices)

        # Extract min and max values for x and y from the original vertices
        cube_min_x = min(v.x for v in vertices)
        cube_max_x = max(v.x for v in vertices)
        cube_min_y = min(v.y for v in vertices)
        cube_max_y = max(v.y for v in vertices)

        points = []
        for _ in range(num_points):
            while True:
                x = random.uniform(cube_min_x, cube_max_x)
                y = random.uniform(cube_min_y, cube_max_y)
                
                # Check if the point is outside the main scene but within the cube
                if (x < main_scene_min_x or x > main_scene_max_x) or (y < main_scene_min_y or y > main_scene_max_y):
                    points.append((x, y, 0))  # Keep z-coordinate as 0
                    break

        return points

    def place_rigs_randomly(self):
        """Place rigs randomly around the origin inside a cube based on left or right side"""
        # Get the cube object
        cube = self.box_object
        path=self.root_path+'\MARTA-2.0\characters'
        vertices = [cube.matrix_world @ v.co for v in cube.data.vertices]
        main_scene_divisor=1.5
        num_points=len(self.background_characters)

        positions = self.generate_random_locations_within_boundaries(vertices, main_scene_divisor, num_points)

        # Load and place characters on the left side
        for i, char_name  in enumerate(self.background_characters):
            filepath = os.path.join(path, f'{char_name}.fbx')
            rig = self.load_rig(filepath, char_name)
            if rig is None:
                print(f"Failed to load rig from '{filepath}'.")
                continue
            rig.location=positions[i]
            target = Vector((0,0,0))
            delta = target - rig.location
            direction = delta.normalized()
            rotation = direction.to_track_quat('-Y', 'Z')
            rig.rotation_euler = rotation.to_euler()


    def run(self):
        self.clear_scene()
        for character_data, actions_dict in zip(self.characters_data, self.actions_list):
            character_name = character_data['name']
            self.character_name=character_name
            character_path = os.path.join(self.root_path, 'MARTA-2.0\characters')

            # Load the main target armature
            target_fbx_path = os.path.join(character_path, f"{character_name}.fbx")
            self.target_armature = self.load_rig(target_fbx_path, f'{character_name}_rig')
            self.rig_matrix_world = self.target_armature.matrix_world.copy()
        
            animation_path = os.path.join(self.root_path, 'animations')

            # Load and process each action
            for action_name, data in actions_dict.items():
                start_frame = data[0][0]
                end_frame = data[0][1]
                action_path = os.path.join(animation_path, f"{action_name}.bvh")
                rig_name = character_name+'_' + action_name.lower().replace(" ", "_") + "_rig"
                action_armature = self.load_animation(action_path, rig_name)
                self.retarget_rokoko(self.target_armature,action_armature)
                action_armature.hide_set(True)
                self.push_action_to_nla(self.target_armature, f"{rig_name}_action Retarget")
                self.set_nla_strip_properties(self.target_armature, f"{rig_name}_action Retarget")
        
            # Organize the sequences and positions
            new_dict = self.organize_nla_sequences(self.target_armature, actions_dict, character_name)
            self.place_armature_with_action(self.target_armature, new_dict)
            
 
           
            bpy.context.scene.frame_current = 0
            bpy.context.view_layer.update()
            self.create_cameras(character_name)
        
            

        # Register the frame change handler to follow the character during animation
        self.create_box()
        bpy.context.view_layer.update()

        self.create_scene_cameras()
        self.set_box_properties(self.textures[0],self.textures[1], self.textures[2])
        self.create_light(light_type='SUN', color=(1, 1, 1), energy=10)
        bpy.app.handlers.frame_change_pre.clear()
        bpy.app.handlers.frame_change_post.clear()
        bpy.app.handlers.frame_change_post.append(lambda scene, dpgraph: self.frame_change_handler(scene, dpgraph))
        bpy.context.scene.frame_end = int(self.end_frame_anim)
        if len(self.background_characters)>0:
            self.place_rigs_randomly()

        bpy.context.scene.frame_current = 0
        bpy.context.view_layer.update()

        #self.render_animation()
        

            

        
def main():

    root_path = r"C:\Users\PMLS\Desktop\blender stuff"
    output_filename='final'
    walls_texture_path=r"C:\Users\PMLS\Desktop\blender stuff\textures\walls_texture.webp"
    floor_texture_path=r"C:\Users\PMLS\Desktop\blender stuff\textures\floor.jpg"
    ceiling_texture_path=r"C:\Users\PMLS\Desktop\blender stuff\textures\walls_texture.webp"
    textures=[walls_texture_path,floor_texture_path,ceiling_texture_path]
    characters_data = [
        {'name': 'Boy'}, {'name': 'Girl'}
        
    ]
    actions_list = [
        {   # Boy's Actions
           
            'walking': [(0, 40), Vector((-5, -10, 0.5)), Vector((-5, 0, 0.5))],
            'dancing girl': [(40, 80), Vector((1, -4, 0)), Vector((1, -4, 0))] 
        }, 

        {   # Girl's Actions
            
            'walking': [(0, 40), Vector((6,-10, 0.5)), Vector((6, 0, 0.5))],
            'dancing girl': [(40, 80), Vector((5,0, 0.5)), Vector((5, 0, 0.5))]
        }

    ]
    background_characters = ['D_Army_1']
    animation_handler = AnimationHandler(root_path, characters_data, actions_list, textures, output_filename, background_characters)
    animation_handler.run()
 

main()





