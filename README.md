# MARTA-2.0
Further research done on the MARTA project.


## Set up

1. download anaconda
2. open anaconda prompt
3. conda init powershell
4. open vscode
5. ensure you have navigated to MARTA-2.0 for your cwd
6. ensure you have git installed

# run the following commands in powershell
``` 
git clone https://github.com/EricGuo5513/momask-codes.git
```
or
```
pip install git+https://github.com/EricGuo5513/momask-codes.git
```
then navigate to the requirements.txt file in momask-codes and change matplotlib=3.1.3 to =3.4.2
```
conda create -n momask python=3.8
conda activate momask
conda install pytorch torchvision torchaudio pytorch-cuda=11.8 -c pytorch -c nvidia
pip install -r momask-codes/requirements.txt
conda install spacy
conda install transformers
```