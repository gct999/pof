# pof



# PoF
Title (A Title Image too if possible…Edit them on canva.com if you are not a graphic designer.)
## Description

## Demo

## Technical

### Installation

'''
pip install pof
'''
Description(Describe by words and images alike)
Demo(Images, Video links, Live Demo links)
Technologies Used
Special Gotchas of your projects (Problems you faced, unique elements of your project)
Technical Description of your project like- Installation, Setup, How to contribute.

### Get the source code up and running


#### Clone Repo


### Select Interpreter
ctrl + shift + p
https://code.visualstudio.com/docs/python/environments 
#### Setup a virtual environment
Create a new virtual environment so that previous python installations work
>>> virtualenv .venv -p python3.9

Activate the venv or launch a new terminal. You will know this has worked if you have (.venv) in front of your path in the terminal
>>> ./venv/bin/activate

Upgrade pip to make sure everything installs correctly

>>> python -m pip install --upgrade pip

Install the packages for this module

>>> pip install -r requirements.txt

Install some dev 

>>> pip install black pylint

If using notebooks you may need to link the ipykernel

[instructions from Mel K]

### Check the unit tests are running correctly

ctrl + shift + p
Configure Test Framework

#### Open 

# Gotchas
Problem: Errors using virtual enrironment
Solution: https://stackoverflow.com/questions/45954528/pip-is-configured-with-locations-that-require-tls-ssl-however-the-ssl-module-in/61429593#61429593
Specifically, I copied the following files from C:\Users\MyUser\Miniconda3\Library\bin to C:\Users\MyUser\Miniconda3\DLLs:

libcrypto-1_1-x64.dll
libcrypto-1_1-x64.pdb
libssl-1_1-x64.dll
libssl-1_1-x64.pdb

https://stackoverflow.com/questions/58612306/how-to-fix-importerror-dll-load-failed-while-importing-win32api
Reinstall Pywin32
copy dlls across from other working pacakge. error apparent when running pywin32_postinstall.py -install



https://pipenv-fork.readthedocs.io/en/latest/ 

How to get the virtual environment working - https://medium.com/@vladbezden/new-python-project-configuration-with-vs-code-b41b77f7aed8

Structure - https://docs.python-guide.org/writing/structure/ 

https://opensource.com/article/18/2/why-python-devs-should-use-pipenv 


## Ipykernel issue
