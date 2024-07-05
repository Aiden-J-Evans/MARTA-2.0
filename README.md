# MARTA-2.0
Further research done on the MARTA project.

## Set-up
```
git clone https://github.com/EricGuo5513/momask-codes.git
cd momask-codes
conda create -n momask python=3.8
conda activate momask
conda install pytorch torchvision torchaudio pytorch-cuda=11.8 -c pytorch -c nvidia
```
find momask-codes/requirements.txt and change matplotlib==3.1.3 to 3.4.0
```
pip install -r requirements.txt
conda install transformers 
conda install spacy
```

## to do
[] check transformers=3.1.0 compatibility with project so no manual changes need to be done to the package
[] add logic that clears files from previous runs
