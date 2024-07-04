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
            action_name = action_name.lower().replace(" ", "_") + "_rig_action"
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
    
    def run(self):
        self.clear_scene()
        character_path = os.path.join(self.root_path, 'characters')

        # Load the main target armature
        target_fbx_path = os.path.join(character_path, f"{self.character_name}.fbx")
        self.target_armature = self.load_rig(target_fbx_path, 'target_rig')
        self.rig_matrix_world = self.target_armature.matrix_world.copy()
        
        animation_path = os.path.join(self.root_path, 'animations')

        # Load and process each action
        for action_name, data in self.actions_dict.items():
            start_frame = data[0][0]
            end_frame = data[0][1]
            action_fbx_path = os.path.join(animation_path, f"{action_name}.fbx")
            rig_name = action_name.lower().replace(" ", "_") + "_rig"
            action_armature = self.load_rig(action_fbx_path, rig_name)
            action_armature.hide_set(True)
            self.push_action_to_nla(self.target_armature, f"{rig_name}_action")
            self.set_nla_strip_properties(self.target_armature, f"{rig_name}_action")
        
        # Organize the sequences and positions
        new_dict = self.organize_nla_sequences(self.target_armature, self.actions_dict)
        self.place_armature_with_action(self.target_armature, new_dict)

        #self.organize_positions(self.target_armature, new_dict)
        
        # Adjust scene timeline
        bpy.context.scene.frame_end = int(self.end_frame_anim)
        bpy.context.scene.frame_current = 0
        
def main():
    # Example
    root_path = r"C:\Users\PMLS\Desktop\blender stuff"
    character_data = {'name': 'Boy (age 19 to 25)'} 
    actions_dict = {
        'Walking': [(10, 70), Vector((1,1,0)), Vector((-3,-6,0))] ,
        'Locking Hip Hop Dance':  [(71, 100), Vector((-3,-6,0)), Vector((0,0,0))] 
        
    }

    animation_handler = AnimationHandler(root_path, character_data, actions_dict)
    animation_handler.run()       

main()