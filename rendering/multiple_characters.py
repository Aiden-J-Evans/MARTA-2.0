import bpy
from mathutils import Vector
import os
import math

class AnimationHandler:
    def __init__(self, root_path, characters_data, actions_list,textures):
        self.root_path = root_path
        self.characters_data = characters_data
        self.actions_list = actions_list
        self.target_armature = None
        self.box_object = None
        self.end_frame_anim = None
        self.scene_cameras=[]
        self.char_cameras=[]
        self.smoothing_factor = 0.2
        self.closest_camera=None
        self.textures=textures
        

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
        armature.rotation_euler = direction.to_track_quat('Z', 'Y').to_euler()
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
                - cycle_offset.x * direction.y - cycle_offset.y * direction.x,
                cycle_offset.x * direction.x - cycle_offset.y * direction.y, 
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
        character_name=camera_dict['char_name']
        armature=bpy.data.objects[f'{character_name}_rig']
        hips_bone = armature.pose.bones.get("mixamorig:Hips")
        current_location = armature.matrix_world @ hips_bone.head

        previous_loc=camera_dict['previous_loc']
        # Compute the direction
        direction = (current_location-previous_loc).normalized()
        camera_dict['previous_loc']=current_location
        
        return direction
 

    def camera_follow_character(self, scene, dpgraph, distance=6):
        """Follow hip bone with the camera.""" 

        for camera_data in self.char_cameras:
            character_name=camera_data['char_name']
            camera_char=camera_data['camera']
            target_armature = scene.objects.get(f'{character_name}_rig')
            target_armature = target_armature.evaluated_get(dpgraph)
            

            if camera_char and target_armature:
                # Get the location of the hips bone
                hips_bone = target_armature.pose.bones.get("mixamorig:Hips")
                if hips_bone:

                    # Calculate the location of the hips bone in world space
                    hips_location = target_armature.matrix_world @ hips_bone.head
                    camera_char.data.angle = math.radians(70)

                    rotated_offset = self.direction_find(camera_data) * distance
                    print('previous location', camera_data['previous_loc'])
                    rotated_offset.z = 0
                    target_location = hips_location + rotated_offset
                                      
                    # Smooth the location
                    camera_data['smoothed_loc'] = self.smooth_location(camera_data['smoothed_loc'], target_location)
                    camera_char.location = camera_data['smoothed_loc']
                    
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
        max_height=0
        avg_hip_bone=Vector((0,0,0))
        avg_head_bone_world_location=Vector((0,0,0))
        n=0

        for character in self.characters_data:
            character_name=character['name']
            armature=bpy.data.objects.get(f'{character_name}_rig')
            head_bone = self.target_armature.pose.bones.get("mixamorig:HeadTop_End")
            head_bone_world_location = self.target_armature.matrix_world @ head_bone.head
            avg_head_bone_world_location+=head_bone_world_location
            head_height = head_bone_world_location.z
            
            if head_height>max_height:
                max_height=head_height

            hip_bone = armature.pose.bones.get("mixamorig:Hips")
            hip_bone_world_location = armature.matrix_world @ hip_bone.head
            avg_hip_bone+=hip_bone_world_location
            n+=1

        avg_hip_bone=avg_hip_bone/n
        avg_head_bone_world_location=avg_head_bone_world_location/n
        vertices_world = [self.box_object.matrix_world @ v.co for v in self.box_object.data.vertices]
    
        j=0
        for i in [0,2,4,6]:
            cam_data = bpy.data.cameras.new(name=f'camera_{j}')
            cam_object = bpy.data.objects.new(name=f'camera_{j}', object_data=cam_data)
            cam_object.location = vertices_world[i]
            cam_object.location.z=max_height+1
            bpy.context.collection.objects.link(cam_object)
            direction = avg_hip_bone - cam_object.location
            rot_quat = direction.to_track_quat('-Z', 'Y')
            cam_object.rotation_euler = rot_quat.to_euler()
            j+=1
            self.scene_cameras.append(cam_object)
    
            
    def update_closest_camera_rotation(self):
        avg_hip_bone=Vector((0,0,0))
        avg_head_bone_world_location=Vector((0,0,0))
        n=0
        for character in self.characters_data:
            character_name=character['name']
            armature=bpy.data.objects.get(f'{character_name}_rig')
            head_bone = armature.pose.bones.get("mixamorig:HeadTop_End")
            head_bone_world_location = armature.matrix_world @ head_bone.head
            hip_bone = self.target_armature.pose.bones.get("mixamorig:Hips")
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
        scene.frame_end = self.update_end_frame(sequence_list) 

        # Set the active camera
        char_camera = bpy.data.objects.get('Character_Camera')
        if char_camera:
            bpy.context.scene.camera = char_camera
        else:
            print("No camera found. Rendering without setting an active camera.")

        # Render the animation
        bpy.ops.render.render(animation=True)

    def create_box(self, Size=40):
        """Create a box around the character to absorb light"""
        bpy.ops.mesh.primitive_cube_add(size=Size, location=(0, 0, Size / 2))
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
                        walls_mapping_scale=(8, 8, 8), floor_mapping_scale=(8, 8, 8), ceiling_mapping_scale=(8, 8, 8),
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

        floor.use_nodes = True
        bsdf2 = floor.node_tree.nodes["Principled BSDF"]
        floor_tex = floor.node_tree.nodes.new('ShaderNodeTexImage')
        floor_tex.image = bpy.data.images.load(floor_texture_path)

        ceiling.use_nodes = True
        bsdf3 = ceiling.node_tree.nodes["Principled BSDF"]
        ceil_tex = ceiling.node_tree.nodes.new('ShaderNodeTexImage')
        ceil_tex.image = bpy.data.images.load(ceiling_texture_path)

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
        bsdf2.inputs['Roughness'].default_value = 1.0
        bsdf3.inputs['Roughness'].default_value = 1.0

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
        for character_data, actions_dict in zip(self.characters_data, self.actions_list):
            character_name = character_data['name']
            self.character_name=character_name
            character_path = os.path.join(self.root_path, 'characters')

            # Load the main target armature
            target_fbx_path = os.path.join(character_path, f"{character_name}.fbx")
            self.target_armature = self.load_rig(target_fbx_path, f'{character_name}_rig')
            self.rig_matrix_world = self.target_armature.matrix_world.copy()
        
            animation_path = os.path.join(self.root_path, 'animations')

            # Load and process each action
            for action_name, data in actions_dict.items():
                start_frame = data[0][0]
                end_frame = data[0][1]
                action_fbx_path = os.path.join(animation_path, f"{action_name}.fbx")
                rig_name = character_name+'_' + action_name.lower().replace(" ", "_") + "_rig"
                action_armature = self.load_rig(action_fbx_path, rig_name)
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
        
            #self.create_light(light_type='SUN', color=(1, 1, 1), energy=1000)

        # Register the frame change handler to follow the character during animation
        self.create_box()
        self.set_box_properties(self.textures[0],self.textures[1], self.textures[2])
        self.create_scene_cameras()
        bpy.app.handlers.frame_change_pre.clear()
        bpy.app.handlers.frame_change_post.clear()
        bpy.app.handlers.frame_change_post.append(lambda scene, dpgraph: self.frame_change_handler(scene, dpgraph))
        bpy.context.scene.frame_end = int(self.end_frame_anim)
       
        bpy.context.scene.frame_current = 0

        

        
def main():

    root_path = r"C:\Users\PMLS\Desktop\blender stuff"
    
    walls_texture_path=r"C:\Users\PMLS\Desktop\blender stuff\textures\forest.jpg"
    floor_texture_path=r"C:\Users\PMLS\Desktop\blender stuff\textures\ground.jpg"
    ceiling_texture_path=r"C:\Users\PMLS\Desktop\blender stuff\textures\sky.jpg"
    textures=[walls_texture_path,floor_texture_path,ceiling_texture_path]
    characters_data = [
        {'name': 'Boy'},
        {'name':'Boy - Copy'}
    ]
    actions_list = [
        {
            'Walking': [(10, 40), Vector((1, 1, 0)), Vector((-3, -6, 0))]
        },
        {
            'Walking': [(10, 40), Vector((0, 0, 0)), Vector((3, -6, 0))]
        }
    ]

    animation_handler = AnimationHandler(root_path, characters_data, actions_list, textures)
    animation_handler.run()
 

main()




