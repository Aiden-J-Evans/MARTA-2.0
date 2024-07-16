# MARTA-2.0
Further research done on the MARTA project.

## Set-up

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
conda create -n momask python=3.8
conda activate momask
conda install pytorch torchvision torchaudio pytorch-cuda=11.8 -c pytorch -c nvidia
```
Navigate to `momask-codes/requirements.txt` and change `matplotlib==3.1.3` to `matplotlib==3.4.0`. This is the a version of matplotlib that covers all aspects of the project.
```
pip install -r momask-codes/requirements.txt
conda install transformers=4.42.2 spacy=3.7.2 diffusers gtts=2.5.1
conda install -c conda-forge cupy
python -m spacy download en_core_web_sm
conda install -c conda-forge ffmpeg=4.3.0
pip install huggingface_hub==0.23.4
```
At this point you need to change some code in the transformer package anaconda3\envs\momask\lib\site-packages\transformers\models\musicgen\modeling_musicgen.py line 2474 & 2476, switching `torch.concatenate()` to `torch.cat()` 

## to do / improvements
- [ ] check transformers=3.1.0 compatibility with project so no manual changes need to be done to the package (this would be for object generation)
- [ ] add logic that (optionally) clears files from previous runs
