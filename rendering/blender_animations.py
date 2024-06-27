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
        
        bpy.context.area.ui_type = 'DOPESHEET'

        bpy.ops.object.select_all(action='DESELECT')
        armature.select_set(True)
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode='OBJECT')
        action = bpy.data.actions.get(action_name)
        if action is None:
            raise ValueError(f"Action '{action_name}' not found")
        armature.animation_data.action = action

        dope_sheet_found = False
        for area in bpy.context.screen.areas:
            if area.type == 'DOPESHEET_EDITOR':
                dope_sheet_found = True
                override_context = bpy.context.copy()
                override_context['area'] = area
                override_context['region'] = area.regions[-1]
                override_context['space_data'] = area.spaces.active
                override_context['space_data'].mode = 'ACTION'
                override_context['object'] = armature
                with bpy.context.temp_override(**override_context):
                    bpy.ops.action.push_down()
                break

        if not dope_sheet_found:
            print("No Dope Sheet editor found in current screen layout") 


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
        
        for action_name, frames in new_dict.items():
            print(action_name, f'{frames[0]} to {frames[1]}')



# Example usage:
root_path = r"C:\Users\PMLS\Desktop\blender stuff"
character_data = {'name': 'Boy (age 19 to 25)'}
actions_dict = {
    'Walking': (10, 60),  
    'Idle': (60, 90),  
}

animation_handler = AnimationHandler(root_path, character_data, actions_dict)
animation_handler.run()


