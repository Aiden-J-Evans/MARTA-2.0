import bpy
from mathutils import Vector
import os
import json

class AnimationHandler:
    def __init__(self, root_path, character_data, actions_list):
        self.root_path = root_path
        self.character_name = character_data['name']
        self.actions_list = actions_list
        self.target_armature = None

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

    def push_action_to_nla(self, armature, action_name, start_frame):
        """Push down action to NLA"""
        
        # Ensure the armature is in OBJECT mode
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Find the action
        action = bpy.data.actions.get(action_name)
        if action is None:
            raise ValueError(f"Action '{action_name}' not found")
        
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
        
        # Clear the current action
        armature.animation_data.action = None

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
        
        anim_start = 1 
        for index, action_name in enumerate(sequence_list):  
            anim_start = self.push_action_to_nla(self.target_armature, action_name, audio_frames[index][0])
        
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

        for action_name in sequence_list:  
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
            sequence_editor.sequences.new_sound(name=os.path.basename(audio_path), filepath=audio_path, channel=1, frame_start=frame)
            

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
            
        
        # Organize the sequences and positions
        sequence_list = [f"{action.lower().replace(' ', '_')}_rig_action" for action in self.actions_list]
        self.organize_nla_sequences(sequence_list)
        self.organize_positions(self.target_armature, sequence_list)
        self.add_audio()

# path to animation/character folder
root_path = os.getcwd() + "\\animations"

f = open(os.getcwd() + "\\frame_data.json")
frame_data = json.load(f)
audio_frames = []

for sequence, data in frame_data.items():
    audio_frames.append((int(sequence), data["audio_path"]))

    for character, char_data in data['characters'].items():
        print(f'Loading: {character}')
        print(f'Playing: {char_data["animation"]}')

character_data = {'name': 'Remy'}
actions_list = ["Walking", "Locking Hip Hop Dance"]

animation_handler = AnimationHandler(root_path, character_data, actions_list)
animation_handler.run()