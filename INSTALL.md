# Installation Guide - AONP

Complete installation instructions for all supported platforms.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Linux Installation](#linux-installation)
3. [macOS Installation](#macos-installation)
4. [Windows (WSL) Installation](#windows-wsl-installation)
5. [Docker Installation](#docker-installation)
6. [Nuclear Data Setup](#nuclear-data-setup)
7. [Verification](#verification)
8. [Troubleshooting](#troubleshooting)

---

## System Requirements

**Minimum**:
- Python 3.8+
- 4 GB RAM
- 2 GB disk space (for nuclear data)

**Recommended**:
- Python 3.11+
- 16 GB RAM (for large simulations)
- 10 GB disk space
- Multi-core CPU

**Platform Support**:
- ✅ Linux (native, fully supported)
- ✅ macOS (native, fully supported)
- ✅ Windows via WSL2 (recommended)
- ✅ Docker (all platforms)

---

## Linux Installation

### Quick Setup (Recommended)

```bash
# Run automated setup script
chmod +x setup_linux.sh
./setup_linux.sh
```

### Manual Installation

#### 1. Install System Dependencies

**Ubuntu/Debian**:
```bash
sudo apt-get update
sudo apt-get install -y \
    python3 python3-pip python3-venv \
    git wget curl
```

**Fedora/RHEL**:
```bash
sudo dnf install -y \
    python3 python3-pip \
    git wget curl
```

#### 2. Create Virtual Environment

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate
```

#### 3. Install AONP

**Option A: From source**:
```bash
# Install core dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

**Option B: With OpenMC**:
```bash
# Install AONP with OpenMC support
pip install -e ".[openmc]"
```

**Option C: Full installation**:
```bash
# Install everything (API, OpenMC, dev tools)
pip install -e ".[openmc,api,dev]"
```

#### 4. Install OpenMC

**Using Conda (easiest)**:
```bash
conda install -c conda-forge openmc
```

**From source**:
```bash
# Install build dependencies
sudo apt-get install -y \
    cmake build-essential \
    libhdf5-dev libpng-dev

# Clone and build
git clone https://github.com/openmc-dev/openmc.git
cd openmc
mkdir build && cd build
cmake ..
make
sudo make install

# Install Python API
cd ..
pip install .
```

---

## macOS Installation

### Using Homebrew + Conda

```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python@3.11

# Install Conda (for OpenMC)
brew install --cask miniconda

# Create environment
conda create -n openmc python=3.11
conda activate openmc

# Install OpenMC
conda install -c conda-forge openmc

# Install AONP
pip install -r requirements.txt
pip install -e .
```

---

## Windows (WSL) Installation

### Step 1: Install WSL2

**From PowerShell (as Administrator)**:
```powershell
# Enable WSL
wsl --install

# Or use the provided batch script
.\install_wsl.bat

# Restart computer when prompted
```

### Step 2: Launch WSL

```powershell
# Open Ubuntu (or your preferred distro)
wsl
```

### Step 3: Follow Linux Instructions

Once in WSL, follow the [Linux Installation](#linux-installation) steps above.

**Important**: Your Windows files are accessible at `/mnt/c/`:
```bash
cd /mnt/c/Users/YOUR_USERNAME/Downloads/hackathon
```

---

## Docker Installation

### Build Docker Image

```bash
# Build with OpenMC included
docker build -t aonp:v0.1 -f Dockerfile .
```

### Run Container

**Interactive mode**:
```bash
docker run -it --rm \
    -v $(pwd)/runs:/app/runs \
    aonp:v0.1 /bin/bash
```

**Run simulation**:
```bash
docker run --rm \
    -v $(pwd)/runs:/app/runs \
    aonp:v0.1 \
    python -m aonp.runner.entrypoint /app/runs/run_<hash>
```

**API server**:
```bash
docker run -d -p 8000:8000 \
    -v $(pwd)/runs:/app/runs \
    aonp:v0.1 \
    uvicorn aonp.api.main:app --host 0.0.0.0
```

### Docker Compose (Future)

```yaml
# docker-compose.yml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./runs:/app/runs
    environment:
      - OPENMC_CROSS_SECTIONS=/data/cross_sections.xml
```

---

## Nuclear Data Setup

OpenMC requires nuclear cross-section data. Several options available:

### Option 1: Conda (Automatic)

```bash
conda install -c conda-forge openmc
# Nuclear data is automatically downloaded to:
# $CONDA_PREFIX/share/openmc/cross_sections/
```

### Option 2: Manual Download (ENDF/B-VII.1)

```bash
# Run provided script
bash install_openmc_conda.sh

# Or download manually
mkdir -p ~/nuclear_data
cd ~/nuclear_data

# Download ENDF/B-VII.1 (~1 GB)
wget https://anl.box.com/shared/static/9igk353zpy8fn9ttvtrqgzvw1vtejoz6.xz \
    -O endfb-vii.1-hdf5.tar.xz

# Extract
tar -xJf endfb-vii.1-hdf5.tar.xz

# Set environment variable (add to ~/.bashrc for persistence)
export OPENMC_CROSS_SECTIONS=~/nuclear_data/endfb-vii.1-hdf5/cross_sections.xml
```

### Option 3: ENDF/B-VIII.0 (Latest)

```bash
# Download from OpenMC website
wget https://openmc.org/downloads/endfb-viii.0-hdf5.tar.xz

# Extract and set path
tar -xJf endfb-viii.0-hdf5.tar.xz
export OPENMC_CROSS_SECTIONS=$PWD/endfb-viii.0-hdf5/cross_sections.xml
```

### Verify Nuclear Data

```python
python -c "
import openmc
config = openmc.config
print(f'Cross sections: {config[\"cross_sections\"]}')
"
```

---

## Verification

### Test 1: Core Functionality (No OpenMC Required)

```bash
python tests/test_core_only.py
```

**Expected output**:
```
✓ Study validation passed
✓ Hash computation passed
✓ Hash stability passed
✓ Hash sensitivity passed
✓ Validation errors caught

✅ All core tests passed!
```

### Test 2: Quick Start

```bash
python quick_start.py
```

Follow the interactive prompts to:
1. Validate example study
2. Create run bundle
3. (Optional) Run simulation

### Test 3: Full Acceptance Test

```bash
# Requires OpenMC + nuclear data
python tests/test_acceptance.py
```

### Test 4: API Server

```bash
# Start server
uvicorn aonp.api.main:app --reload

# Test in another terminal
curl http://localhost:8000/
curl http://localhost:8000/health
```

---

## Troubleshooting

### Python Version Issues

**Problem**: Wrong Python version

**Solution**:
```bash
# Check version
python3 --version

# Use specific version
python3.11 -m venv venv
```

### OpenMC Import Error

**Problem**: `ImportError: No module named 'openmc'`

**Solution**:
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Install OpenMC
pip install openmc
# OR
conda install -c conda-forge openmc
```

### Nuclear Data Not Found

**Problem**: `RuntimeError: Cross sections XML file not found`

**Solution**:
```bash
# Set environment variable
export OPENMC_CROSS_SECTIONS=/path/to/cross_sections.xml

# Or add to ~/.bashrc
echo 'export OPENMC_CROSS_SECTIONS=/path/to/cross_sections.xml' >> ~/.bashrc
source ~/.bashrc
```

### WSL Network Issues

**Problem**: Cannot access internet from WSL

**Solution**:
```bash
# Reset WSL networking
# From PowerShell (as Administrator)
wsl --shutdown
# Then restart WSL
```

### HDF5 Errors

**Problem**: `ImportError: HDFStore requires PyTables`

**Solution**:
```bash
pip install tables
# OR
conda install pytables
```

### Permission Denied

**Problem**: Permission errors when creating files

**Solution**:
```bash
# Fix permissions on runs directory
chmod -R 755 runs/

# Or run with proper permissions
sudo chown -R $USER:$USER .
```

### Conda Environment Issues

**Problem**: Packages not found after conda install

**Solution**:
```bash
# Update conda
conda update -n base -c defaults conda

# Create fresh environment
conda create -n openmc-fresh python=3.11
conda activate openmc-fresh
conda install -c conda-forge openmc
```

---

## Platform-Specific Notes

### Linux

- **Best performance**: Native installation recommended
- **GPU support**: Available with NVIDIA GPUs (advanced)
- **HPC clusters**: Use module system or Conda

### macOS

- **M1/M2 Macs**: Use Conda (native ARM support)
- **Intel Macs**: All methods work
- **Xcode**: May need Command Line Tools: `xcode-select --install`

### Windows + WSL

- **File access**: Use `/mnt/c/` to access Windows files
- **Performance**: Nearly native (within 5% of Linux)
- **GUI**: Can use VSCode with WSL extension

### Docker

- **Pros**: Fully isolated, reproducible
- **Cons**: Slower I/O, larger image size
- **Best for**: CI/CD, deployment

---

## Getting Help

**Documentation**:
- `README.md` - Quick start guide
- `openmc_design.md` - Complete design document
- `tests/README.md` - Testing guide

**Community**:
- [OpenMC Discourse](https://openmc.discourse.group/)
- [OpenMC GitHub](https://github.com/openmc-dev/openmc)

**Issues**:
If you encounter problems:
1. Check this troubleshooting guide
2. Search existing issues
3. Create new issue with full error trace

---

## Next Steps

After successful installation:

1. **Run examples**: `python quick_start.py`
2. **Read documentation**: See `aonp/examples/README.md`
3. **Write your study**: Copy and modify `simple_pincell.yaml`
4. **Explore API**: Visit `http://localhost:8000/docs`

**Happy simulating!** 🚀

