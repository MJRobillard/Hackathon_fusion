#!/bin/bash
# AONP Linux/WSL Setup Script
# Run this on Ubuntu/Debian-based systems

set -e  # Exit on error

echo "=========================================="
echo "AONP Setup for Linux/WSL"
echo "=========================================="

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo "Warning: This script is designed for Linux/WSL"
fi

# Install system dependencies
echo ""
echo "[1/5] Installing system dependencies..."
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git cmake g++ libhdf5-dev

# Create virtual environment
echo ""
echo "[2/5] Creating Python virtual environment..."
if [ -d "venv" ]; then
    echo "Virtual environment already exists, skipping..."
else
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install Python dependencies
echo ""
echo "[3/5] Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install OpenMC
echo ""
echo "[4/5] Installing OpenMC..."
echo "Note: OpenMC requires compilation or conda installation"
echo "Attempting pip install (may fail, that's OK for core features)..."
pip install openmc || echo "⚠ OpenMC pip install failed - you'll need conda or compile from source for simulations"

# Verify installation
echo ""
echo "[5/5] Verifying installation..."
python -c "import openmc; print(f'✓ OpenMC {openmc.__version__} installed')"
python -c "from aonp.schemas.study import StudySpec; print('✓ AONP schemas loaded')"
python -c "from aonp.core.bundler import create_run_bundle; print('✓ AONP core loaded')"

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "2. Run acceptance tests:"
echo "   python test_acceptance.py"
echo ""
echo "3. Download nuclear data (required for simulations):"
echo "   mkdir -p ~/nuclear_data && cd ~/nuclear_data"
echo "   python -c 'import openmc; openmc.data.download_endfb71()'"
echo "   export OPENMC_CROSS_SECTIONS=~/nuclear_data/endfb-vii.1-hdf5/cross_sections.xml"
echo ""
echo "4. Start the API server:"
echo "   uvicorn aonp.api.main:app --reload"
echo ""
echo "Note: Nuclear data download is ~2GB and takes time"
echo "      You can skip it if you only want to test hashing/bundling"

