# sstate
sstate is a rewrite of a perl-based utility in Python, which will give the current resource state of any Slurm-based HPC cluster.

## Requirements
Uses tabulate python library

## Installation and Usage

### Native
sstate can be run after installing the tabulate python library 

```
pip3 install -r requirements.txt
```

### Bundled
For environments that don't want to have a virtual environment setup nor have python libraries installed:

```
pip3 install -r requirements.txt
pip3 install pipenv pyinstaller
pipenv install
pipenv run pyinstaller sstate.py --onefile
```
