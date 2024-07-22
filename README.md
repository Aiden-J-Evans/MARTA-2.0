# MARTA-2.0
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

Install project requirements:

> [!WARNING]
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

</details>

## Running MARTA :running:
<details>

Once you have completed the set-up, ensure your conda environment is still activated.

Assuming you are in the MARTA-2.0 directory, you can now run MARTA.py through your code editor or in your terminal with `python marta.py`.

When you run the script, you will be required to download all models that MARTA utilizes.

Please note that downloading these models requires around ***15 GB of disk space***.

After these models have downloaded, you will be prompted in your terminal to enter your story.


</details>

## Miscellaneous

For further questions about the project, you can contact me at [aiden.evans@mytwu.ca](mailito::aiden.evans@mytwu.ca).

## To Do / Project Improvements :pushpin:
- [ ] check transformers=3.1.0 compatibility with project so no manual changes need to be done to the package
- [ ] add logic that (optionally) clears files from previous runs
- [ ] Begin development of specialized models to lower computational power.
