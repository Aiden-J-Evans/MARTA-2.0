import bpy
from mathutils import Vector, Matrix
import os, math, json, sys

class AnimationHandler:
    def __init__(self, root_path, characters_data, actions_list,textures, last_frame, audio_frames, background_characters, render_path, render_quality):
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
        self.last_frame = last_frame
        self.audio_frames = audio_frames
        self.output_filename = "render"
        self.background_characters = background_characters
        self.loaded_rigs = {}
        self.render_path = render_path
        self.render_quality = render_quality
        
    def clear_scene(self):
        """Delete all objects from the scene"""
        # turns off edit mode
        if bpy.context.active_object and bpy.context.active_object.mode == 'EDIT':
            bpy.ops.object.editmode_toggle()
            
        # shows all the objects in the scene
        for obj in bpy.data.objects:
            obj.hide_set(False)
            obj.hide_select = False
            obj.hide_viewport = False
            
        # removes any actions from the scene
        for action in bpy.data.actions:
            bpy.data.actions.remove(action)
            
        # delete all objects
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete()
        
        # clears the timeline
        bpy.data.scenes[0].timeline_markers.clear()
        
        # clears data
        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

        bpy.app.handlers.frame_change_pre.clear()
        bpy.app.handlers.frame_change_post.clear()

    def retarget_rokoko(self, source_armature : bpy.types.Object, target_armature: bpy.types.Object):
        """
        Retargets an animation to an armature

        Args:
            source_armature (bpy.types.Object): the animation armature
            target_armature (bpy.types.Object): the character armature
        """
        # Enable the Rokoko Addon
        if 'rokoko-studio-live-blender-master' not in bpy.context.preferences.addons:
            bpy.ops.preferences.addon_enable(module='rokoko-studio-live-blender')

        # locate the source armature
        if source_armature:
            bpy.context.scene.rsl_retargeting_armature_source = target_armature

        # locate the target armature
        if target_armature:
            bpy.context.scene.rsl_retargeting_armature_target = source_armature

        
        # builds the bone list
        bpy.ops.rsl.build_bone_list()
        
        # retargets the animation
        bpy.ops.rsl.retarget_animation()

        print(source_armature.name + " " + str(source_armature.location))

    def load_rig(self, filepath: str, name: str) -> bpy.types.Object:
        """
        Loads an animation rig from an FBX file
        
        Args:
            filepath: the filepath to the fbx
            name: the name of the fbx 
            in_background: whether the rig is being loaded as a main character or a background character
        """
        bpy.ops.import_scene.fbx(filepath=filepath, use_manual_orientation=True, use_anim=False, axis_forward='-Y', axis_up='Z')
        rig = bpy.context.active_object
        rig.name = name
        rig.show_in_front = True
        rig.location.z = -10
        print(f"\nLoaded {name}")
        return rig
    
    def load_animation(self, filepath: str, name: str) -> bpy.types.Object:
        """
        Load a rig from an BVH file
        
        Args:
            filepath (): the filepath to the bvh file 
            name (): the name of the rig
        """
        if filepath == 'idle': 
            filepath = os.path.join(self.root_path, 'rendering', 'animations', 'idle.bvh')
            

        bpy.ops.import_anim.bvh(filepath=filepath, axis_forward='Z', axis_up='Y')
        rig = bpy.context.active_object
        rig.name = name
        rig.show_in_front = True
        rig.animation_data.action.name = f'{name}_action'
        print(f"\nloaded {filepath}")
        return rig

    def push_action_to_nla(self, armature: bpy.types.Object, action_name : str):
        """
        Push down action to NLA
        
        Args:   
            armature (bpy.types.Object): the armature that the action is on
            action_name (str): the name of the action
        
        Returns:
            nla_strip.frame_end (int): the end frame of the animation
        """
        # Find the action
        armature.location = Vector((armature.location.x, armature.location.y, 0))
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

        nla_strip.extrapolation = 'NOTHING'
        nla_strip.use_auto_blend = False
        return nla_strip.frame_end

    def get_strip(self, rig : bpy.types.Object, action_name : str) -> bpy.types.NlaStrip:
        """
        Finds a strip for a specific action on a specific character

        Args:
            rig (bpy.types.Object): the character object that the action would be on
            action_name (str): the name of the searched action

        Returns:
            strip (bpy.types.NlaStrip): The strip that was searched for.
        """
        for track in rig.animation_data.nla_tracks:
            for strip in track.strips:
                if strip.name == action_name:
                    return strip
        raise ValueError(f"No active NLA strip found for action '{action_name}'.")

    def get_cycle_offset(self, rig : bpy.types.Object, action : bpy.types.Action, end_frame : int) -> Vector:
        """
        Get the amount that the armature moves with each animation cycle
        
        Args:
            action (bpy.types.Action): The action/animation that we calculate the distance of
            end_frame (int): the final frame of the animation

        Returns:
            (Vector): The vector offset off the action
        """
        
        start_pos, end_pos = [0, 0, 0], [0, 0, 0]
        for curve in action.fcurves:
            if "mixamorig:Hips" not in curve.data_path: 
                continue
            if "location" not in curve.data_path: 
                continue
            channel = curve.array_index
            start_pos[channel] = curve.evaluate(0)
            end_pos[channel] = curve.evaluate(end_frame)
            
        start_pos_world = Vector(start_pos) @ self.rig_matrix_world
        end_pos_world = Vector(end_pos) @ self.rig_matrix_world
        offset = [-(end_pos_world[i] - start_pos_world[i]) for i in range(3)]
        
        offset[2] = 0
        return Vector(offset)

    # TODO: combine two functions below

    def insert_location_keyframe(self, armature : bpy.types.Object, frame : int, location: Vector):
        """Insert a location keyframe for the armature at the specified frame."""
        armature.location = Vector((location[0], location[1], 0))
        armature.keyframe_insert(data_path="location", frame=frame)
    
    def insert_rotation_keyframe(self, armature: bpy.types.Object, frame : int, direction : Vector):
        """Insert a rotation keyframe for the armature at the specified frame."""
        armature.rotation_euler = direction.to_track_quat('-Y', 'Z').to_euler()
        armature.keyframe_insert(data_path="rotation_euler", frame=frame)

    def place_armature_with_action(self, armature : bpy.types.Object, actions_dict : dict) -> None:
        # Set the initial location and keyframe
        for action_name, data in actions_dict.items():
            strip = self.get_strip(armature, action_name)
            
            # Get the positional offset of a single cycle with no rotational changes
            cycle_offset = self.get_cycle_offset(armature, strip.action, strip.frame_end - strip.frame_start)
            
            # Determine total desired offset for the cycle
            start_location=data[1]
            end_location=data[2]

            displacement = end_location - start_location
            total_frames = strip.frame_end - strip.frame_start
            if displacement != Vector((0, 0, 0)):
                for i, frame in enumerate(range(int(strip.frame_start), int(strip.frame_end))):
                    progress = i / total_frames
                    current_location = start_location + (displacement * progress)
                    self.insert_location_keyframe(armature, frame, current_location)
                self.insert_location_keyframe(armature, strip.frame_end, end_location)
                print(f"Inserted from {start_location} to {end_location} in {total_frames} frames")

            
        
            # Update the scene
            bpy.context.view_layer.update()
            
            strip.action = bpy.data.actions.get(strip.name + " Retarget")
            for curve in strip.action.fcurves:
                for key in curve.keyframe_points:        
                    key.interpolation='LINEAR'

 
    def duplicate_action(self, original_action_name : str, new_action_name : str) -> bpy.types.ID:
        """
        Duplicates an action and returns the new action
        
        Args:
            original_action_name : the name of the original action
            new_action_name : the name for the duplicated action
        
        Returns:
            The duplicated action ID
        """
        original_action = bpy.data.actions.get(original_action_name)
        if original_action is None:
            raise ValueError(f"Action '{original_action_name}' not found")
        
        # Duplicate the action
        new_action = original_action.copy()
        new_action.name = f"{new_action_name}"
        return new_action

    def organize_nla_sequences(self, target_armature : bpy.types.Object, actions_dict : dict, character_name : str) -> dict:
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
            action_name = character_name + '_' + f"({frame_start}, {frame_end})_rig_action"
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
                start_location=ending_location
            else:
                start_location=data[1]
                ending_location=data[2]
                new_actions_dict[action_name] = [(strip.frame_start, strip.frame_end),start_location ,ending_location ]
            
            remaining_period -= original_period
            anim_start = strip.frame_end + 1       
            
        
        self.end_frame_anim = anim_start
        return new_actions_dict
    
    def create_character_cameras(self, character_name):
        """Create a camera for following the character"""
        char_cam_data = bpy.data.cameras.new(name=f'{character_name}_camera')
        char_camera = bpy.data.objects.new(name=f'{character_name}_camera', object_data=char_cam_data)
        bpy.context.collection.objects.link(char_camera)
        camera_dict={'name': f'{character_name}_camera', 'camera': char_camera, 'char_name':character_name, 'previous_loc': Vector((0,0,0)),'smoothed_loc': Vector((0, 0, 0))}
        self.char_cameras.append(camera_dict)
        print("\nCreated cameras for " + character_name)

    def smooth_location(self, current_loc, target_loc):
        """Smooth the transition between the current and target locations."""
        return current_loc.lerp(target_loc, self.smoothing_factor)

    def direction_find(self, camera_dict):
        target_bone_names = ['hip', 'pelvis', 'hips']
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
            camera_char=camera_data['camera']
            target_armature = scene.objects.get(f'{character_name}_rig')

            if not target_armature:
                raise ValueError("No armature found for character")
            
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
                    if camera_char and camera_char.data:
                        camera_char.data.angle = math.radians(110)
                    rotated_offset = self.direction_find(camera_data) * distance
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
        current_frame = scene.frame_current
        active_camera = None
        active_character_count = 0

        for character_name, actions in zip(self.characters_data, self.actions_list):
        # Check if any action matches the current frame for the character
    
            for action_name, data in actions.items():
                start_frame = data[0][0]
                end_frame = data[0][1]
                
                if start_frame <= current_frame and current_frame <= end_frame:
                    if action_name.lower() != 'idle': 
                        active_camera = f"{character_name}"    
                        active_character_count += 1
                    break

        if active_character_count != 1:
            # Use scene camera
            self.update_closest_camera_rotation()
        else:
            char_camera=bpy.data.objects.get(f'{active_camera}_camera')
            marker = scene.timeline_markers.new(name=char_camera.name, frame=current_frame)
            marker.camera = char_camera
           
    def create_scene_cameras(self):
        avg_hip_bone = Vector((0,0,0))
        n = 0

        for character_name in self.characters_data:
            armature=bpy.data.objects.get(f'{character_name}_rig')
            target_bone_names = ['hip', 'pelvis', 'hips']
            hip_bone = None
            for bone in armature.pose.bones:
                if any(target_bone_name in bone.name.lower() for target_bone_name in target_bone_names):
                    hip_bone = bone
                    break
            
            hip_bone_world_location = armature.matrix_world @ hip_bone.head
            avg_hip_bone+=hip_bone_world_location
            n += 1

        avg_hip_bone=avg_hip_bone/n
        
        vertices_world = [self.box_object.matrix_world @ v.co for v in self.box_object.data.vertices]
    
        j = 0
        for i in [0,2,4,6]:
            cam_data = bpy.data.cameras.new(name=f'camera_{j}')
            cam_data.lens = 30
            cam_object = bpy.data.objects.new(name=f'camera_{j}', object_data=cam_data)
            cam_object.location = vertices_world[i]
            cam_object.location.z=self.max_height+10


            bpy.context.collection.objects.link(cam_object)
            direction = avg_hip_bone - cam_object.location
            rot_quat = direction.to_track_quat('-Z', 'Y')
            cam_object.rotation_euler = rot_quat.to_euler()
            j+=1
            self.scene_cameras.append(cam_object)

        print("\nCreated scene cameras")
          
    def update_closest_camera_rotation(self):
        avg_hip_bone=Vector((0,0,0))
        avg_head_bone_world_location=Vector((0,0,0))
        n=0
        target_bone_names = ['hip', 'pelvis', 'hips']
        for character in self.characters_data:
            character_name=character
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

    def render_animation(self, render_quality:str):
        """Render the animation to an MP4 file"""
        if render_quality == "low":
            constant_rate = "HIGH"
            res_x = 720
            res_y = 480
            ffmpeg_preset = "REALTIME"
        elif render_quality == "high":
            constant_rate = 'LOW'
            res_x = 1920
            res_y = 1080
            ffmpeg_preset = "GOOD"
        elif render_quality == "best":
            constant_rate = "LOW"
            res_x = 2560
            res_y = 1440
            ffmpeg_preset = "BEST"
        else:
            constant_rate = "MEDIUM"
            res_x = 1280
            res_y = 720
            ffmpeg_preset = "GOOD"

        scene = bpy.context.scene
        scene.render.image_settings.file_format = 'FFMPEG'
        scene.render.ffmpeg.format = 'MPEG4'
        scene.render.ffmpeg.codec = 'H264'
        scene.render.ffmpeg.constant_rate_factor = constant_rate
        scene.render.ffmpeg.ffmpeg_preset = ffmpeg_preset
        scene.render.filepath = self.render_path
        scene.render.engine = 'BLENDER_EEVEE'

        scene.render.ffmpeg.audio_codec = 'AAC'
        scene.render.ffmpeg.audio_bitrate = 192 
        scene.render.ffmpeg.audio_channels = 'STEREO'
        scene.render.ffmpeg.audio_mixrate = 48000
        # Set output settings
        scene.render.resolution_x = res_x
        scene.render.resolution_y = res_y
        scene.render.resolution_percentage = 100
        scene.frame_start = 1
        scene.frame_end = int(self.last_frame)

        # Render the animation
        bpy.ops.render.render('INVOKE_DEFAULT', animation=True)


    def create_box(self, Size=100):
        """Create a box around the character to absorb light"""
        
        self.max_height=0

        foot_bone_world_location=Vector((0,0,0))
        n=0

        for character in self.characters_data:
            character_name=character
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


        bpy.ops.mesh.primitive_cube_add()
        bpy.context.object.scale = ((Size, Size, self.max_height+10))
        bpy.context.object.location = ((0, 0, self.max_height+10))
        self.box_object = bpy.context.active_object

        print("\nCreated box")

    def set_box_properties(self, walls_texture_path, floor_texture_path, ceiling_texture_path,
                        walls_mapping_scale=(1, 1, 1), floor_mapping_scale=(100, 100, 100), ceiling_mapping_scale=(1, 1, 1),
                        walls_mapping_rotation=(0, 0, 90), floor_mapping_rotation=(0, 0, 0), ceiling_mapping_rotation=(0, 0, 0),
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

        print("\nFinished setting box properties")
   
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

        print("\nCreated lights")

        return light_object

    def add_audio(self):
        """Adds audio strips to the sequencer based on the audio frames."""
        scene = bpy.data.scenes[0]

        # Ensure the scene's sequence editor exists
        if not scene.sequence_editor:
            scene.sequence_editor_create()

        sequence_editor = scene.sequence_editor

        # Add audio strips
        for frame, audio_paths in self.audio_frames:
            if not audio_paths: continue
            for audio_path in audio_paths:
                sequence_editor.sequences.new_sound(name=os.path.basename(audio_path), filepath=audio_path, channel=1, frame_start=frame)

    def face_other_characters(self, character_name, other_name, frame):
        """
        Rotates the main character's armature to face another character's armature.

        Args:
            character_name (str): The name of the main character's armature.
            other_name (str): The name of the other character's armature.
        """
        main_armature = self.loaded_rigs[character_name]
        other_armature = self.loaded_rigs[other_name]

        # Get the locations of both armatures
        main_location = main_armature.location
        other_location = other_armature.location

        # Calculate the direction vector from main to other
        direction = other_location - main_location

        # Debugging: Print the direction vector

        # Normalize the direction vector
        direction.normalize()


        # Calculate the angle to rotate the main armature to face the other armature
        target_angle = math.atan2(direction.x, direction.y)

        # Convert the angle to a rotation matrix
        rotation_matrix = Matrix.Rotation(target_angle, 4, 'Z')

        # Apply the rotation to the main armature
        new_matrix = rotation_matrix @ main_armature.matrix_world
        rotation_euler = new_matrix.to_euler()

    def on_render_complete(scene, depsgraph, context):
        print("\nRender Saved\n")
        print("*" * 14)
        print("\nMARTA COMPLETE\n")
        print("*" * 14)
        #bpy.ops.wm.quit_blender()
    


    def run(self):
        self.clear_scene()
        bpy.app.handlers.render_complete.append(self.on_render_complete)
        self.loaded_rigs = {}
        for character_name, actions_dict in zip(self.characters_data, self.actions_list):
            # set the path for getting characters
            character_path = os.path.join(self.root_path, 'characters')
            
            # Load the main target armature
            target_fbx_path = os.path.join(character_path, f"{character_name}.fbx")
            if character_name not in self.loaded_rigs.keys():
                self.target_armature = self.load_rig(target_fbx_path, f'{character_name}_rig')
                self.loaded_rigs[character_name] = self.target_armature
            else:
                self.target_armature = self.loaded_rigs[character_name]
            self.rig_matrix_world = self.target_armature.matrix_world.copy()
        
            # Load and process each action
            for action_path, data in actions_dict.items():
                # set the name for the rig
                start_frame, end_frame = data[0][0], data[0][1]

                rig_name = character_name + '_' + f"({start_frame}, {end_frame})_rig"
                action_armature = self.load_animation(action_path, rig_name)
                self.retarget_rokoko(self.target_armature, action_armature)
                action_armature.hide_set(True)
                self.push_action_to_nla(self.target_armature, f"{rig_name}_action")
        
            # Organize the sequences and positions
            new_dict = self.organize_nla_sequences(self.target_armature, actions_dict, character_name)
            self.place_armature_with_action(self.target_armature, new_dict)
 
            bpy.context.scene.frame_current = 1
            bpy.context.view_layer.update()
            self.create_character_cameras(character_name)

        # Register the frame change handler to follow the character during animation
        self.create_box()
        bpy.context.view_layer.update()

        self.create_scene_cameras()
        self.set_box_properties(self.textures[0],self.textures[1], self.textures[2])
        self.create_light()
        bpy.app.handlers.frame_change_pre.clear()
        bpy.app.handlers.frame_change_post.clear()

        bpy.app.handlers.frame_change_post.append(lambda scene, dpgraph: self.frame_change_handler(scene, dpgraph))
        bpy.context.scene.frame_end = int(self.end_frame_anim)
       
        bpy.context.scene.frame_current = 0
        bpy.context.view_layer.update()

        self.add_audio()
        self.render_animation(self.render_quality)
        
        
def main():
    # set animation path
    root_path = os.path.join(os.getcwd())
    
    # open the data file
    f = open(sys.argv[-1])
    frame_data = json.load(f)
    audio_frames = []
    characters_data = []
    actions_list = []
    last_frame = 1

    frame_list = [int(key) for key in frame_data if key.isdigit()]
    start_index = 0;
    end_index = 1;
    mult = 10;
    # organize information
    for sequence, data in frame_data.items():
        if sequence.isdigit():
            # add audio
            audio_frames.append([int(sequence), data["audio_paths"]])
            
            for character, ani_data in data['characters'].items():
                characters_data.append(str(character))
                ani_name = ani_data["animation"]
                start_frame = frame_list[start_index]
                end_frame = frame_list[end_index] if end_index < len(frame_list) else frame_data['end_frame'];

                if character in frame_data[str(frame_list[max(start_index - 1, 0)])]['characters']:
                    start_pos = Vector(frame_data[str(frame_list[max(start_index - 1, 0)])]['characters'][character]['sequence_end_position'])
                else:
                    start_pos = Vector(frame_data[str(frame_list[start_index])]['characters'][character]['sequence_end_position'])
                end_pos = Vector(ani_data['sequence_end_position'])
                actions_list.append({ani_name: [(start_frame, end_frame), start_pos * mult, end_pos * mult]}) 
                    
            start_index += 1;
            end_index += 1;

    # Finds the wall, ceiling, and floor textures
    textures = [value for key, value in frame_data.items() if key.endswith('path')]

    # make sure audio knows when to stop
    last_frame = int(frame_data['end_frame'])
    audio_frames.append([last_frame, None])
    background_characters = []
    render_path = frame_data['render_output']
    render_quality = frame_data['render_quality']
    # run the program
    animation_handler = AnimationHandler(root_path, characters_data, actions_list, textures, last_frame, audio_frames, background_characters, render_path, render_quality)
    animation_handler.run()
 
main()





