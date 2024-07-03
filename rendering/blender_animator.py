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
                offset = self.get_cycle_offset(target_armature, strip.action, new_strip.frame_end - new_strip.frame_start)
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
        
def main():
    # Example
    root_path = r"C:\Users\PMLS\Desktop\blender stuff"
    character_data = {'name': 'Boy (age 19 to 25)'} 
    actions_dict = {
        'Walking': (10, 80),  
        'Locking Hip Hop Dance': (81, 100), 
        
    }

    animation_handler = AnimationHandler(root_path, character_data, actions_dict)
    animation_handler.run()       

main()