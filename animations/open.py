import bpy

def create_animation(motion_frames):
    # Assume 'Armature' is the name of the armature object in Blender
    armature = bpy.data.objects['Armature']
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')
    
    for frame_data in motion_frames:
        frame_number = int(frame_data['timestep'] * 100)  # Assuming timestep is in seconds and Blender runs at 100 FPS
        
        root_bone = armature.pose.bones['root']  # Replace 'root' with your root bone name
        root_bone.location = frame_data['root_position']
        root_bone.rotation_euler = frame_data['root_rotation']
        
        root_bone.keyframe_insert(data_path='location', frame=frame_number)
        root_bone.keyframe_insert(data_path='rotation_euler', frame=frame_number)

        # Additional bones and joint positions can be handled here similarly
        
    bpy.ops.object.mode_set(mode='OBJECT')

def main():
  file_path = 'path_to_your_motion.xml'
  motion_frames = parse_xml_file(file_path)
  create_animation(motion_frames)
  bpy.ops.export_scene.fbx(filepath='output_animation.fbx')

if __name__ == '__main__':
  main()