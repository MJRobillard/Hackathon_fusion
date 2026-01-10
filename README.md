# AONP - Agent-Orchestrated Neutronics Platform

**Version 0.1.0 - Minimum Reproducible Unit**

A high-integrity neutronics simulation platform with deterministic provenance tracking. AONP ensures that every simulation result can be traced back to its exact input configuration through cryptographic hashing.

## 🎯 Core Concept: Physics-Data Contract

AONP implements a "trust anchor" through deterministic hashing:
- **Same Input → Same Hash** (independent of formatting/comments)
- **Different Input → Different Hash** (sensitive to all physical parameters)
- Every result is linked to its canonical input hash for perfect reproducibility

## 📦 Repository Structure

```
aonp/
├── schemas/          # Pydantic data models
│   ├── study.py      # StudySpec with deterministic hashing
│   └── manifest.py   # RunManifest (provenance record)
├── core/            # Core utilities
│   ├── bundler.py   # Creates canonical run bundles
│   └── extractor.py # Post-processing (H5 → Parquet)
├── runner/          # Execution logic
│   ├── entrypoint.py # OpenMC simulation runner
│   └── Dockerfile    # Container environment
├── api/             # REST API
│   └── main.py      # FastAPI application
└── examples/        # Example studies
    ├── simple_pincell.yaml
    └── pincell_geometry.py
```

## 🚀 Quick Start

### ⚠️ Platform Requirements

**OpenMC requires Linux or macOS**. On Windows, use one of these options:
- **WSL2** (Windows Subsystem for Linux) - Recommended
- **Docker** - Fully isolated environment
- **Conda** - Cross-platform package manager

See **[INSTALL_LINUX.md](INSTALL_LINUX.md)** for detailed Linux/WSL installation.

### Installation (Linux/WSL)

```bash
# Quick setup with provided script
chmod +x setup_linux.sh
./setup_linux.sh

# Or manual installation:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install openmc  # Only works on Linux/macOS
```

### Installation (Windows - WSL)

```bash
# From Windows PowerShell, open WSL
wsl

# Navigate to your project (adjust path)
cd /mnt/c/Users/YOUR_USERNAME/Downloads/fusion

# Run setup
chmod +x setup_linux.sh
./setup_linux.sh
```

### Basic Usage

#### 1. Validate a Study and Get Hash

```python
from pathlib import Path
import yaml
from aonp.schemas.study import StudySpec

# Load study
with open("aonp/examples/simple_pincell.yaml") as f:
    data = yaml.safe_load(f)

study = StudySpec(**data)
print(f"Canonical Hash: {study.get_canonical_hash()}")
```

#### 2. Create a Run Bundle

```python
from aonp.core.bundler import create_run_bundle

run_dir, input_hash = create_run_bundle(study)
print(f"Run directory: {run_dir}")
print(f"Input hash: {input_hash}")
```

#### 3. Run Simulation (requires OpenMC)

```bash
python -m aonp.runner.entrypoint ./runs/run_<hash>
```

#### 4. Start API Server

```bash
uvicorn aonp.api.main:app --reload

# API will be available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

## 🔬 Acceptance Tests

### Hash Stability Test

Verify that comments and whitespace don't affect the hash:

```python
import yaml
from aonp.schemas.study import StudySpec

# Original YAML
with open("aonp/examples/simple_pincell.yaml") as f:
    data1 = yaml.safe_load(f)
    study1 = StudySpec(**data1)
    hash1 = study1.get_canonical_hash()

# Add comments and reformat (same data)
yaml_with_comments = """
# This is a comment
name: "simple_pincell_v1"  # Another comment
# ... rest of YAML with many comments ...
"""

data2 = yaml.safe_load(yaml_with_comments)
study2 = StudySpec(**data2)
hash2 = study2.get_canonical_hash()

assert hash1 == hash2, "Hash must be stable across formatting changes!"
print("✓ Hash stability test passed")
```

### Sensitivity Test

Verify that physical changes affect the hash:

```python
# Change density slightly
data3 = data1.copy()
data3["materials"]["fuel"]["density"] = 10.401  # Changed from 10.4
study3 = StudySpec(**data3)
hash3 = study3.get_canonical_hash()

assert hash1 != hash3, "Hash must be sensitive to physical changes!"
print("✓ Hash sensitivity test passed")
```

### Extraction Test

Requires a completed OpenMC simulation:

```python
from aonp.core.extractor import create_summary, load_summary

# Extract from statepoint
summary_path = create_summary("./runs/run_<hash>/statepoint.100.h5")

# Load and verify
df = load_summary(summary_path)
print(df)
# Expected columns: metric, value, std_dev, n_batches, n_inactive, n_particles
```

## 🌐 API Endpoints

### `POST /validate`

Upload a YAML file and receive its canonical hash.

```bash
curl -X POST "http://localhost:8000/validate" \
  -F "file=@aonp/examples/simple_pincell.yaml"
```

Response:
```json
{
  "validation_status": "valid",
  "canonical_hash": "a1b2c3d4...",
  "study_name": "simple_pincell_v1",
  "nuclear_data_id": "endfb71"
}
```

### `POST /run`

Trigger a simulation run.

```bash
curl -X POST "http://localhost:8000/run" \
  -F "file=@aonp/examples/simple_pincell.yaml"
```

### `GET /runs/{run_id}`

Get status and results of a specific run.

## 🐳 Docker Usage

```bash
# Build image
docker build -t aonp:v0.1 -f aonp/runner/Dockerfile .

# Run API server
docker run -p 8000:8000 aonp:v0.1

# Run simulation
docker run -v $(pwd)/runs:/app/runs aonp:v0.1 \
  python3 -m aonp.runner.entrypoint /app/runs/run_<hash>
```

## 🧪 Testing

```bash
# Install test dependencies
pip install pytest httpx

# Run tests (when test suite is added)
pytest tests/
```

## 📋 Key Features

### ✅ Implemented (v0.1)

- **Deterministic Hashing**: SHA256 of canonical JSON (sorted keys)
- **Pydantic Validation**: Type-safe schemas with automatic validation
- **Run Bundles**: Self-contained execution directories with provenance
- **Result Extraction**: HDF5 → Parquet for efficient storage
- **REST API**: Validate and trigger simulations
- **Docker Support**: Reproducible execution environment

### 🚧 Roadmap

- [ ] SQLite/PostgreSQL result database
- [ ] Tally specification in YAML
- [ ] Distributed execution (Celery/Ray)
- [ ] Web UI for study management
- [ ] Automated test suite
- [ ] Nuclear data management
- [ ] Geometry DSL (alternative to script-based)

## 🔐 Provenance Model

Every run produces a `run_manifest.json`:

```json
{
  "input_hash": "a1b2c3d4e5f6...",
  "timestamp": "2026-01-09T12:34:56Z",
  "seed": 42,
  "schema_version": "0.1.0",
  "openmc_version": "0.14.0",
  "run_id": "run_a1b2c3d4e5f6"
}
```

This manifest links all results to their exact input, enabling:
- **Reproducibility**: Re-run with identical inputs
- **Traceability**: Verify results against inputs
- **Version Control**: Track changes across studies

## 📚 Documentation

- **Schemas**: See `aonp/schemas/` for data models
- **API Docs**: Visit `/docs` when server is running
- **Examples**: Check `aonp/examples/` for sample studies

## 🤝 Contributing

This is the v0 vertical slice. Future contributions should maintain:
1. Deterministic behavior (no hidden randomness)
2. Schema-first design (Pydantic validation)
3. Provenance tracking (every result traceable)
4. High-integrity computing principles

## 📄 License

[Add your license here]

## 🙏 Acknowledgments

- Built on [OpenMC](https://openmc.org) - MIT's Monte Carlo particle transport code
- Inspired by high-integrity scientific computing principles

---

**Next Steps**: Test the hash acceptance criteria with the simple pincell example!

