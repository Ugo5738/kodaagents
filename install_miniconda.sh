#!/bin/bash

# Download Miniconda installer
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh

# Install Miniconda
bash miniconda.sh -b -p $HOME/miniconda

# Remove the installer to save space
rm -f miniconda.sh

# Initialize Miniconda environment
# This step makes conda command available from the terminal
source "$HOME/miniconda/bin/activate"

# Optionally, you can initialize your shell to automatically activate conda in any new terminals
# Not necessary in CI/CD environments, but useful for local setups
# conda init

# Verify the installation
conda list

# Create a new environment (optional)
conda create -n aistudio python=3.11

# Activate the new environment (if created)
conda activate aistudio

# Display conda version to verify installation
conda --version

# Provide a message to indicate successful installation
echo "Miniconda installation and setup completed."

# make this script executable with "chmod +x install_miniconda.sh"
# run script with "./install_miniconda.sh".