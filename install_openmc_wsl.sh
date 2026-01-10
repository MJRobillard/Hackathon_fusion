#!/bin/bash
# OpenMC Installation Script for WSL/Linux
# This script installs OpenMC and its dependencies

set -e  # Exit on error

echo "=========================================="
echo "OpenMC Installation for WSL/Linux"
echo "=========================================="
echo ""

# Check if running in WSL or Linux
if grep -qi microsoft /proc/version; then
    echo "[INFO] Detected WSL environment"
else
    echo "[INFO] Detected Linux environment"
fi

# Update package lists
echo ""
echo "[1/5] Updating package lists..."
sudo apt-get update -qq

# Install Python and pip
echo ""
echo "[2/5] Installing Python dependencies..."
sudo apt-get install -y python3 python3-pip python3-venv

# Create virtual environment (optional but recommended)
echo ""
echo "[3/5] Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "[OK] Virtual environment created"
else
    echo "[OK] Virtual environment already exists"
fi

# Activate virtual environment
source venv/bin/activate

# Install AONP dependencies
echo ""
echo "[4/5] Installing AONP dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Try to install OpenMC
echo ""
echo "[5/5] Installing OpenMC..."
echo ""
echo "Choose installation method:"
echo "  1) pip install (quick, may not work on all systems)"
echo "  2) conda install (recommended, requires conda)"
echo "  3) Skip OpenMC installation (install later)"
echo ""
read -p "Enter choice [1-3]: " choice

case $choice in
    1)
        echo "[INFO] Installing OpenMC via pip..."
        pip install openmc
        ;;
    2)
        echo "[INFO] Installing OpenMC via conda..."
        echo "[INFO] First, install Miniconda if not already installed:"
        echo "       wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
        echo "       bash Miniconda3-latest-Linux-x86_64.sh"
        echo ""
        read -p "Is conda already installed? [y/N]: " has_conda
        if [[ $has_conda =~ ^[Yy]$ ]]; then
            conda install -c conda-forge openmc -y
        else
            echo "[SKIP] Please install conda first, then run:"
            echo "       conda install -c conda-forge openmc"
        fi
        ;;
    3)
        echo "[SKIP] OpenMC installation skipped"
        echo "[INFO] Install later with: pip install openmc"
        ;;
    *)
        echo "[ERROR] Invalid choice"
        exit 1
        ;;
esac

# Test installation
echo ""
echo "=========================================="
echo "Testing Installation"
echo "=========================================="
echo ""

# Test Python imports
python3 -c "import sys; print(f'Python {sys.version}')"
python3 -c "import pydantic; print(f'Pydantic {pydantic.__version__}')"
python3 -c "import yaml; print('PyYAML installed')"
python3 -c "import pandas; print(f'Pandas {pandas.__version__}')"

# Test OpenMC
if python3 -c "import openmc" 2>/dev/null; then
    python3 -c "import openmc; print(f'OpenMC {openmc.__version__}')"
    echo ""
    echo "[OK] OpenMC successfully installed!"
else
    echo ""
    echo "[WARNING] OpenMC not installed"
    echo "[INFO] Core AONP functionality will work without OpenMC"
    echo "[INFO] Only simulation execution requires OpenMC"
fi

# Run core tests
echo ""
echo "=========================================="
echo "Running Core Tests"
echo "=========================================="
echo ""
python3 tests/test_core_only.py

# Summary
echo ""
echo "=========================================="
echo "Installation Complete"
echo "=========================================="
echo ""
echo "To activate the environment in future sessions:"
echo "  source venv/bin/activate"
echo ""
echo "To test OpenMC (if installed):"
echo "  python3 test_openmc_installation.py"
echo ""
echo "To run a quick demo:"
echo "  python3 quick_start.py"
echo ""
echo "Next steps:"
echo "  1. Download nuclear data (see INSTALL.md)"
echo "  2. Set OPENMC_CROSS_SECTIONS environment variable"
echo "  3. Run full acceptance tests"
echo ""

