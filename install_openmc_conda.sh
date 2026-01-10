#!/bin/bash
# Install OpenMC via Conda (recommended for WSL/Linux)
# This is more reliable than pip for OpenMC

set -e

echo "=========================================="
echo "OpenMC Installation via Conda"
echo "=========================================="

# Check if conda is installed
if ! command -v conda &> /dev/null; then
    echo "Conda not found. Installing Miniconda..."
    
    # Download and install Miniconda
    cd ~
    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh
    bash miniconda.sh -b -p $HOME/miniconda3
    
    # Initialize conda
    eval "$($HOME/miniconda3/bin/conda shell.bash hook)"
    conda init bash
    
    echo "Miniconda installed. Please restart your terminal and run this script again."
    echo "Or run: source ~/.bashrc"
    exit 0
fi

# Ensure conda is available
eval "$(conda shell.bash hook)"

# Check if aonp environment exists
if conda env list | grep -q "^aonp "; then
    echo "aonp conda environment already exists"
    conda activate aonp
else
    echo "Creating new conda environment 'aonp'..."
    conda create -n aonp python=3.10 -y
    conda activate aonp
fi

# Install OpenMC from conda-forge
echo ""
echo "Installing OpenMC from conda-forge..."
conda install -c conda-forge openmc -y

# Install other dependencies with pip
echo ""
echo "Installing other dependencies..."
cd ~/projects/fusion
pip install -r requirements.txt

# Verify installation
echo ""
echo "Verifying installation..."
python -c "import openmc; print(f'✓ OpenMC {openmc.__version__} installed')"
python -c "from aonp.schemas.study import StudySpec; print('✓ AONP schemas loaded')"

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "To use this environment in the future:"
echo "  conda activate aonp"
echo ""
echo "Next: Download nuclear data (~2GB):"
echo "  mkdir -p ~/nuclear_data && cd ~/nuclear_data"
echo "  python -c 'import openmc; openmc.data.download_endfb71()'"
echo "  echo 'export OPENMC_CROSS_SECTIONS=~/nuclear_data/endfb-vii.1-hdf5/cross_sections.xml' >> ~/.bashrc"
echo ""

