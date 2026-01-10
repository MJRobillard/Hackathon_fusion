# WSL Quick Start Guide for AONP

## Prerequisites

1. **WSL2 installed** on Windows
2. **Ubuntu** (or another Linux distribution) installed in WSL

## Installation Steps

### From Windows PowerShell

```powershell
# Open WSL
wsl

# Navigate to project (Windows C: drive is at /mnt/c)
cd /mnt/c/Users/YOUR_USERNAME/Downloads/hackathon

# Run installation script
bash install_openmc_wsl.sh
```

### Or Step-by-Step

```bash
# 1. In WSL, navigate to project directory
cd /mnt/c/Users/ratth/Downloads/hackathon

# 2. Update system
sudo apt-get update

# 3. Install Python
sudo apt-get install -y python3 python3-pip python3-venv

# 4. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 5. Install AONP dependencies
pip install -r requirements.txt

# 6. Install OpenMC (choose one method):

# Option A: pip (quick)
pip install openmc

# Option B: conda (recommended)
# First install conda, then:
conda install -c conda-forge openmc

# 7. Test installation
python3 test_openmc_installation.py
```

## Running Tests

### Core Tests (No OpenMC Required)
```bash
# In WSL
python3 tests/test_core_only.py
```

### OpenMC Installation Test
```bash
# In WSL
python3 test_openmc_installation.py
```

### Quick Start Demo
```bash
# In WSL
python3 quick_start.py
```

### Full Acceptance Test (Requires Nuclear Data)
```bash
# In WSL
python3 tests/test_acceptance.py
```

## From Windows (Using Helper Scripts)

You can also run commands from Windows PowerShell:

```powershell
# Test core functionality
run_in_wsl.bat test-core

# Run quick start
run_in_wsl.bat quick-start

# Check OpenMC
run_in_wsl.bat check-openmc

# Open WSL shell in project directory
run_in_wsl.bat shell
```

## Nuclear Data Setup (Required for Simulations)

### Option 1: Quick Download (in WSL)
```bash
# Run the provided script
bash install_openmc_conda.sh
```

### Option 2: Manual Download
```bash
# Create directory
mkdir -p ~/nuclear_data
cd ~/nuclear_data

# Download ENDF/B-VII.1 (~1 GB)
wget https://anl.box.com/shared/static/9igk353zpy8fn9ttvtrqgzvw1vtejoz6.xz \
    -O endfb-vii.1-hdf5.tar.xz

# Extract
tar -xJf endfb-vii.1-hdf5.tar.xz

# Set environment variable (add to ~/.bashrc for persistence)
export OPENMC_CROSS_SECTIONS=~/nuclear_data/endfb-vii.1-hdf5/cross_sections.xml

# Add to ~/.bashrc for future sessions
echo 'export OPENMC_CROSS_SECTIONS=~/nuclear_data/endfb-vii.1-hdf5/cross_sections.xml' >> ~/.bashrc
```

## Verifying Installation

### Check OpenMC
```bash
python3 -c "import openmc; print(f'OpenMC {openmc.__version__}')"
```

### Check Nuclear Data
```bash
python3 -c "import os; print(f'OPENMC_CROSS_SECTIONS={os.environ.get(\"OPENMC_CROSS_SECTIONS\", \"Not set\")}')"
```

### Run Full Test Suite
```bash
python3 test_openmc_installation.py
```

Expected output:
```
============================================================
TEST SUMMARY
============================================================
[OK] OpenMC Import
[OK] Nuclear Data
[OK] Geometry Creation
[OK] Material Creation
[OK] AONP Integration
[OK] Simple Simulation

Passed: 6/6

[SUCCESS] All tests passed!

OpenMC is ready to use with AONP.
```

## Common Issues

### Issue: "ModuleNotFoundError: No module named 'openmc'"
**Solution**: Install OpenMC
```bash
pip install openmc
```

### Issue: "Cross sections XML file not found"
**Solution**: Set the environment variable
```bash
export OPENMC_CROSS_SECTIONS=/path/to/cross_sections.xml
```

### Issue: WSL network/internet not working
**Solution**: Restart WSL from PowerShell
```powershell
wsl --shutdown
# Then restart WSL
wsl
```

### Issue: Permission denied errors
**Solution**: Fix permissions
```bash
chmod +x *.sh
chmod +x *.py
```

## Performance Notes

- **WSL2 Performance**: Nearly native Linux performance (~95%)
- **File Access**: Accessing files on Windows drives (/mnt/c) is slower
- **Best Practice**: For large simulations, copy files to WSL home directory (~/)

## File Paths

- **Windows → WSL**: `C:\Users\ratth\...` becomes `/mnt/c/Users/ratth/...`
- **WSL → Windows**: `~/project` is at `\\wsl$\Ubuntu\home\username\project`

## Next Steps After Installation

1. **Run core tests**: `python3 tests/test_core_only.py`
2. **Test OpenMC**: `python3 test_openmc_installation.py`
3. **Try examples**: `python3 quick_start.py`
4. **Read documentation**: See `README.md` and `openmc_design.md`

## Working with the API

Start the API server in WSL:
```bash
# In WSL
source venv/bin/activate
uvicorn aonp.api.main:app --host 0.0.0.0 --port 8000
```

Access from Windows browser:
```
http://localhost:8000
http://localhost:8000/docs
```

## Development Workflow

Recommended setup for development:

1. **Code editor on Windows** (VSCode with WSL extension)
2. **Run commands in WSL**
3. **Access results from both Windows and WSL**

VSCode WSL Extension:
- Install "Remote - WSL" extension
- Open project in WSL: `code .` (from WSL in project directory)
- Terminal will automatically use WSL

## Troubleshooting

### Get WSL Version
```powershell
wsl --list --verbose
```

### Restart WSL
```powershell
wsl --shutdown
wsl
```

### Check WSL Distribution
```powershell
wsl --list
```

### Update WSL
```powershell
wsl --update
```

## Resources

- [INSTALL.md](INSTALL.md) - Complete installation guide
- [README.md](README.md) - Main documentation
- [openmc_design.md](openmc_design.md) - Design specification
- [tests/README.md](tests/README.md) - Testing guide

