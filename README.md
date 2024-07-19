# MARTA-2.0
Further research done on the MARTA project.

## Set-up
<Details>

### Pre-reqs
1. download anaconda
2. open anaconda prompt
3. conda init powershell
4. open vscode
5. ensure you have navigated to MARTA-2.0 for your cwd
6. ensure you have git installed

### Environment

Credit to [@makeinufilm](https://medium.com/@makeinufilm) for the super helpful [tutorial](https://medium.com/@makeinufilm/notes-on-how-to-set-up-the-momask-environment-and-how-to-use-blenderaddon-6563f1abdbfa) partly used here.\
We will be using the incredible work done at the University of Alberta to generate animation. All credit for creating animations goes to the contributers of [Momask](https://ericguo5513.github.io/momask/).

> Run the following commands in powershell
``` 
git clone https://github.com/EricGuo5513/momask-codes.git
```
or
```
pip install git+https://github.com/EricGuo5513/momask-codes.git
```
Create and navigate to `momask-codes/checkpoints` then create two folders, `kit` and `t2m`.
- Download [KIT-ML Dataset](https://drive.google.com/file/d/1MNMdUdn5QoO8UW1iwTcZ0QNaLSH4A6G9/view) and extract to `momask-codes/checkpoints/kit`.
- Download [HumanML3D Dataset](https://drive.google.com/file/d/1MNMdUdn5QoO8UW1iwTcZ0QNaLSH4A6G9/view) and extract to `momask-codes/checkpoints/t2m`.

![Folder Organization Structure](readme_assets/Momask%20Example%20Display.png)

```
conda create -n momask python=3.9
conda activate momask
conda install pytorch torchvision torchaudio pytorch-cuda=11.8 -c pytorch -c nvidia
```

At this point you can use `pip install -r requirements.txt` and `conda install ffmpeg=4.3`.\
Install the spaCy model
```
python -m spacy download en_core_web_sm
```

You will also need to install Microsoft Visual C++ 14.0 or greater from [here](https://visualstudio.microsoft.com/visual-cpp-build-tools/). You can use this [tutorial](https://www.youtube.com/watch?v=pDURF7345M8).\

At this point you need to change some code in the transformer package `anaconda3\envs\momask\lib\site-packages\transformers\models\musicgen\modeling_musicgen.py` line 2474 & 2476, switching `torch.concatenate()` to `torch.cat()`.

</details>

## Running MARTA
<details>

Once you have completed the set-up, ensure your conda environment is still activated.\

Assuming you are in the MARTA-2.0 directory, you can now run MARTA.py through your code editor or with `python marta.py`.\

When you run the script, you will be required to download all models that MARTA utilizes.\
Please note that downloading these models requires around ==15 GB of disk space==.\

After these models have downloaded, you will be prompted in your terminal to enter your story.


</details>

## to do / improvements
- [ ] check transformers=3.1.0 compatibility with project so no manual changes need to be done to the package (this would be for object generation)
- [ ] add logic that (optionally) clears files from previous runs
