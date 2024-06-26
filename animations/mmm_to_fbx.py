import os
import json
import xml.etree.cElementTree as ET
import logging
import numpy as np
import argparse
import pyfbx

def parse_motions(path):
    xml_tree = ET.parse(path)
    xml_root = xml_tree.getroot()
    xml_motions = xml_root.findall('Motion')
    motions = []

    if len(xml_motions) > 1:
        logging.warn('more than one <Motion> tag in file "%s", only parsing the first one', path)
    motions.append(_parse_motion(xml_motions[0], path))
    return motions

def _parse_motion(xml_motion, path):
    xml_joint_order = xml_motion.find('JointOrder')
    if xml_joint_order is None:
        raise RuntimeError('<JointOrder> not found')

    joint_names = []
    joint_indexes = []
    for idx, xml_joint in enumerate(xml_joint_order.findall('Joint')):
        name = xml_joint.get('name')
        if name is None:
            raise RuntimeError('<Joint> has no name')
        joint_indexes.append(idx)
        joint_names.append(name)

    frames = []
    xml_frames = xml_motion.find('MotionFrames')
    if xml_frames is None:
        raise RuntimeError('<MotionFrames> not found')
    for xml_frame in xml_frames.findall('MotionFrame'):
        frames.append(_parse_frame(xml_frame, joint_indexes))

    return joint_names, frames

def _parse_frame(xml_frame, joint_indexes):
    n_joints = len(joint_indexes)
    xml_joint_pos = xml_frame.find('JointPosition')
    if xml_joint_pos is None:
        raise RuntimeError('<JointPosition> not found')
    joint_pos = _parse_list(xml_joint_pos, n_joints, joint_indexes)

    return joint_pos

def _parse_list(xml_elem, length, indexes=None):
    if indexes is None:
        indexes = range(length)
    elems = [float(x) for idx, x in enumerate(xml_elem.text.rstrip().split(' ')) if idx in indexes]
    if len(elems) != length:
        raise RuntimeError('invalid number of elements')
    return elems

def create_fbx(joint_names, frames, output_path):
    scene = pyfbx.FbxScene()
    skeleton = pyfbx.FbxSkeleton()
    scene.root_node.add_child(skeleton)
    
    # Create joints
    joint_nodes = {}
    for joint_name in joint_names:
        joint_node = pyfbx.FbxNode(joint_name)
        skeleton.add_child(joint_node)
        joint_nodes[joint_name] = joint_node
    
    # Set keyframe animations
    for frame_idx, frame in enumerate(frames):
        for joint_idx, joint_pos in enumerate(frame):
            joint_name = joint_names[joint_idx]
            joint_node = joint_nodes[joint_name]
            joint_node.set_translation(frame_idx, joint_pos, 0.0, 0.0)

    # Export scene to FBX file
    scene.save(output_path)

def main(args):
    input_path = args.input
    
    print('Scanning files ...')
    files = [f for f in os.listdir(input_path) if os.path.isfile(os.path.join(input_path, f)) and f[0] != '.']
    basenames = list(set([os.path.splitext(f)[0].split('_')[0] for f in files]))
    print('done, {} potential motions and their annotations found'.format(len(basenames)))
    print('')

    # Parse all files.
    print('Processing data in "{}" ...'.format(input_path))
    all_ids = []
    all_motions = []
    all_annotations = []
    all_metadata = []
    reference_joint_names = None
    for idx, basename in enumerate(basenames):
        print('  {}/{} ...'.format(idx + 1, len(basenames))),

        # Load motion.
        mmm_path = os.path.join(input_path, basename + '_mmm.xml')
        assert os.path.exists(mmm_path)
        joint_names, frames = parse_motions(mmm_path)[0]
        if reference_joint_names is None:
            reference_joint_names = joint_names[:]
        elif reference_joint_names != joint_names:
            print('skipping, invalid joint_names {}'.format(joint_names))
            continue
        
        # Load annotation.
        annotations_path = os.path.join(input_path, basename + '_annotations.json')
        assert os.path.exists(annotations_path)
        with open(annotations_path, 'r') as f:
            annotations = json.load(f)

        # Load metadata.
        meta_path = os.path.join(input_path, basename + '_meta.json')
        assert os.path.exists(meta_path)
        with open(meta_path, 'r') as f:
            meta = json.load(f)

        assert len(annotations) == meta['nb_annotations']
        all_ids.append(int(basename))
        all_motions.append(np.array(frames, dtype='float32'))
        all_annotations.append(annotations)
        all_metadata.append(meta)
        print('done')
    assert len(all_motions) == len(all_annotations)
    assert len(all_motions) == len(all_ids)
    print('done, successfully processed {} motions and their annotations'.format(len(all_motions)))
    print('')

    # Create FBX files
    output_path = os.path.join(input_path, "output.fbx")
    for joint_names, frames in zip(reference_joint_names, all_motions):
        create_fbx(joint_names, frames, output_path)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('input', type=str)
    main(parser.parse_args("C:\\Users\\aiden\\Downloads\\KIT-ML-Motions\\00531_mmm.xml"))
