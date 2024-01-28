#!/bin/bash

# Download Miniconda installer
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh

# Install Miniconda
bash miniconda.sh -b -p $HOME/miniconda

# Initialize Conda
echo 'source $HOME/miniconda/bin/activate' >> ~/.bashrc
source ~/.bashrc

# Clean up the installer
rm miniconda.sh

# Verify the installation
conda list

# Create a new environment (optional)
conda create -n aistudio python=3.11

# make this script executable with "chmod +x install_miniconda.sh"
# run script with "./install_miniconda.sh".