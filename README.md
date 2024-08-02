# MARTA-2.0 (Modern Automatic Renderings from Text to Animations) Alpha Build
MARTA is a proof of concept for a text-to-3D animation program that utilizes numerous AI models to generate a cohesive video.

## Set-up :wrench:
<Details>

### Pre-reqs:
1. Download [Anaconda](https://www.anaconda.com/download/success)
2. Open the Anaconda prompt
3. Run `conda init powershell`
4. Open your text editor
5. Navigate to MARTA-2.0 in your terminal
6. Ensure you have [Git](https://git-scm.com/downloads) installed
7. Install [Blender](https://www.blender.org/), we used version 4.1
8. Install [Rokoko Blender Addon](https://www.rokoko.com/integrations/blender)

### Environment:

Credit to [@makeinufilm](https://medium.com/@makeinufilm) for the super helpful [tutorial](https://medium.com/@makeinufilm/notes-on-how-to-set-up-the-momask-environment-and-how-to-use-blenderaddon-6563f1abdbfa) partly used here.\
We will be using the incredible work done at the University of Alberta to generate animation. All credit for creating animations goes to the contributers of [Momask](https://ericguo5513.github.io/momask/).

> Run the following commands in powershell
``` 
git clone https://github.com/EricGuo5513/momask-codes.git
```
Create then navigate to `momask-codes/checkpoints` then create two more folders, `kit` and `t2m`.
- Download [KIT-ML Dataset](https://drive.google.com/file/d/1MNMdUdn5QoO8UW1iwTcZ0QNaLSH4A6G9/view) and extract to `momask-codes/checkpoints/kit`.
- Download [HumanML3D Dataset](https://drive.google.com/file/d/1MNMdUdn5QoO8UW1iwTcZ0QNaLSH4A6G9/view) and extract to `momask-codes/checkpoints/t2m`.

Your folder structure should look like this:

![Folder Organization Structure](readme_assets/Momask%20Example%20Display.png)

Create and activate the conda environment:
```
conda create -n momask python=3.9
conda activate momask
```



> Ensure you have selected python 3.9.19 as your python interpreter. Do not install ffmpeg through pip, as the install seems to be broken.

```
pip install -r requirements.txt
conda install ffmpeg=4.3
```

Now install the spaCy model:
```
python -m spacy download en_core_web_sm
```

You will also need to install Microsoft Visual C++ 14.0 or greater from [here](https://visualstudio.microsoft.com/visual-cpp-build-tools/). You can use this YouTube [tutorial](https://www.youtube.com/watch?v=pDURF7345M8).

At this point you need to change some code in the transformer package `anaconda3\envs\momask\lib\site-packages\transformers\models\musicgen\modeling_musicgen.py` line 2474 & 2476, switching `torch.concatenate()` to `torch.cat()`.

Finally, you must install the [Rokoko Blender Addon](https://www.rokoko.com/integrations/blender) as it is essential to the script. Once you have downloaded the `.zip` folder, leave it in a safe directory, and open blender. From the menu bar, navigate to Edit -> Preferences, then click install and navigate to the Rokoko zip folder. Once installed, click on its checkbox to ensure it is activated.

### Characters:
As of right now, MARTA has no way of generating 3D humanoid models suitable for the program. We modeled our own characters with [MakeHuman](http://www.makehumancommunity.org/) and used the [Rokoko Blender Addon](https://www.rokoko.com/integrations/blender) to retarget the characters to match the animations. The Rokoko retargeting is done through the `rendering/renderer.py` script.

For now, it is recommended that you use MakeHuman as it is the only tested character creator, but if you test other applications, please let us know.

You can place your characters in the `characters` folder. These must be in `.fbx` format.

</details>

## Running MARTA :running:
<details>

Once you have completed the set-up, ensure your conda environment is still activated.

Assuming you are in the MARTA-2.0 directory, you can now run MARTA.py through your code editor or in your terminal with `python marta.py`.

When you run the script, you will be required to download all models that MARTA utilizes.

Please note that downloading these models requires around ***15 GB of disk space***.

After these models have downloaded, you will be prompted in your terminal to enter your story.


</details>

## Contributing + Tips

<details>

Contributions and recommendations for the MARTA project are more than welcome. You can contact aiden.evans@mytwu.ca or create your own fork of the repositiory.

If you plan on working with the Blender side of the program, I would recommend using the following command to install the [fake-bpy-module](https://github.com/nutti/fake-bpy-module).

```
pip install fake-bpy-module-4.1
```
Or for different versions of Blender:
```
pip install fake-bpy-module-<version>
```


</details>

## Miscellaneous

For further questions about the project, you can contact me at aiden.evans@mytwu.ca.

## To Do / Project Improvements :pushpin:
- [ ] check transformers=3.1.0 compatibility with project so no manual changes need to be done to the package
- [ ] add logic that (optionally) clears files from previous runs
- [ ] Begin development of specialized models to lower computational power.
- [ ] Find or create a 3D humanoid mesh generator model.
