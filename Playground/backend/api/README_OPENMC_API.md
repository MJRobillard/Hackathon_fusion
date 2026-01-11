# OpenMC Backend API

Direct REST API for OpenMC simulation engine on port 8001.

## Quick Start

### Start the API Server

```bash
# Option 1: Using shell script (Linux/Mac)
cd Playground/backend/api
./start_openmc_api.sh

# Option 2: Using PowerShell (Windows)
cd Playground\backend\api
.\start_openmc_api.ps1

# Option 3: Direct Python
python openmc_api.py
```

### Environment Variables

```bash
# Optional - defaults shown
OPENMC_API_HOST=0.0.0.0
OPENMC_API_PORT=8001
OPENMC_RUNS_DIR=runs
MONGO_URI=mongodb://...  # For persistence
```

## API Endpoints

### 🚀 Submit Simulation

```bash
POST /api/v1/simulations
```

**Request:**
```json
{
  "spec": {
    "geometry": "PWR pin cell",
    "materials": ["UO2", "Water"],
    "enrichment_pct": 4.5,
    "temperature_K": 900.0,
    "particles": 10000,
    "batches": 50
  }
}
```

**Response (202 Accepted):**
```json
{
  "run_id": "run_abc123def456",
  "spec_hash": "7a3f9c2e",
  "status": "queued",
  "submitted_at": "2026-01-11T...",
  "estimated_duration_seconds": 30
}
```

### 📊 Get Simulation Status

```bash
GET /api/v1/simulations/{run_id}
```

**Response:**
```json
{
  "run_id": "run_abc123def456",
  "spec_hash": "7a3f9c2e",
  "status": "completed",
  "keff": 1.28734,
  "keff_std": 0.00028,
  "uncertainty_pcm": 28.0,
  "runtime_seconds": 12.34,
  "run_dir": "/path/to/runs/run_abc123def456",
  "submitted_at": "...",
  "completed_at": "..."
}
```

### 📈 Submit Parameter Sweep

```bash
POST /api/v1/sweeps
```

**Request:**
```json
{
  "base_spec": {
    "geometry": "PWR pin cell",
    "materials": ["UO2", "Water"],
    "enrichment_pct": 4.5,
    "temperature_K": 900.0,
    "particles": 5000,
    "batches": 20
  },
  "parameter": "enrichment_pct",
  "values": [3.0, 3.5, 4.0, 4.5, 5.0]
}
```

**Response:**
```json
{
  "sweep_id": "sweep_xyz789abc",
  "run_ids": ["sweep_xyz789abc_p000", "sweep_xyz789abc_p001", ...],
  "total_runs": 5,
  "status": "queued",
  "submitted_at": "..."
}
```

### 🔍 Query Runs

```bash
GET /api/v1/runs?enrichment_min=3.0&enrichment_max=5.0&limit=20
```

**Query Parameters:**
- `geometry`: Filter by geometry type (substring match)
- `enrichment_min`, `enrichment_max`: Enrichment range
- `temperature_min`, `temperature_max`: Temperature range
- `keff_min`, `keff_max`: k-effective range
- `status`: Filter by status (queued, running, completed, failed)
- `limit`: Results per page (default: 20, max: 100)
- `offset`: Pagination offset (default: 0)

### 📊 Compare Runs

```bash
POST /api/v1/runs/compare
```

**Request:**
```json
{
  "run_ids": ["run_abc123", "run_def456", "run_ghi789"]
}
```

**Response:**
```json
{
  "num_runs": 3,
  "keff_values": [1.28734, 1.29021, 1.27891],
  "keff_stds": [0.00028, 0.00031, 0.00026],
  "keff_mean": 1.28549,
  "keff_std_dev": 0.00572,
  "keff_min": 1.27891,
  "keff_max": 1.29021,
  "reactivity_span": 0.01130,
  "runs": [...]
}
```

### 📁 List Run Files

```bash
GET /api/v1/simulations/{run_id}/files
```

**Response:**
```json
{
  "run_id": "run_abc123",
  "files": [
    {
      "path": "outputs/statepoint.50.h5",
      "size": 1048576,
      "modified": "2026-01-11T..."
    },
    ...
  ]
}
```

### 📥 Download File

```bash
GET /api/v1/simulations/{run_id}/files/{file_path}
```

Returns the file for download.

### 📊 Get Statistics

```bash
GET /api/v1/statistics
```

**Response:**
```json
{
  "total_runs": 142,
  "completed_runs": 128,
  "failed_runs": 3,
  "running_runs": 2,
  "total_sweeps": 12,
  "average_runtime_seconds": 15.2,
  "recent_runs": [...]
}
```

### 🏥 Health Check

```bash
GET /api/v1/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-01-11T...",
  "services": {
    "mongodb": "connected",
    "openmc": "available",
    "openmc_version": "0.14.0",
    "nuclear_data": "configured"
  },
  "runs_directory": "/path/to/runs",
  "available_runs": 142
}
```

### ❌ Cancel Simulation

```bash
DELETE /api/v1/simulations/{run_id}
```

## Frontend Integration

The frontend automatically connects to the OpenMC API when you click **⚛️ OpenMC Engine** in the terminal switcher.

### Features:
- **Submit**: Create new simulations with custom parameters
- **Monitor**: Real-time status updates for running simulations
- **Query**: Search and filter run history
- **Sweep**: Run parameter sweeps across multiple values

## Testing

Run the test suite:

```bash
cd Playground/backend/api
python test_openmc_api.py
```

This tests all major endpoints with sample data.

## Architecture

```
Frontend (localhost:3000)
    ↓
OpenMC API (localhost:8001)
    ↓
OpenMC Adapter
    ↓
AONP Core → OpenMC Engine
    ↓
MongoDB (shared storage)
```

## Differences from Agent API

| Feature | Agent API (8000) | OpenMC API (8001) |
|---------|------------------|-------------------|
| Purpose | Natural language interface | Direct simulation control |
| Input | English queries | Structured specs |
| Routing | Yes (multi-agent) | No (direct execution) |
| Overhead | Higher (LLM calls) | Lower (direct) |
| Use Case | User interface | Programmatic access |

## Example Workflow

1. **Submit a simulation:**
   ```bash
   curl -X POST http://localhost:8001/api/v1/simulations \
     -H "Content-Type: application/json" \
     -d '{
       "spec": {
         "geometry": "PWR pin cell",
         "materials": ["UO2", "Water"],
         "enrichment_pct": 4.5,
         "temperature_K": 900.0,
         "particles": 10000,
         "batches": 50
       }
     }'
   ```

2. **Get run ID from response and monitor:**
   ```bash
   curl http://localhost:8001/api/v1/simulations/run_abc123def456
   ```

3. **Query all completed runs:**
   ```bash
   curl http://localhost:8001/api/v1/runs?status=completed&limit=10
   ```

4. **Compare multiple runs:**
   ```bash
   curl -X POST http://localhost:8001/api/v1/runs/compare \
     -H "Content-Type: application/json" \
     -d '{"run_ids": ["run_abc123", "run_def456"]}'
   ```

## Error Handling

All endpoints return standard HTTP status codes:

- `200` - Success
- `202` - Accepted (async operation)
- `400` - Bad Request (invalid input)
- `404` - Not Found
- `500` - Internal Server Error
- `503` - Service Unavailable (database down)

Error responses:
```json
{
  "detail": "Error message here"
}
```

## Performance

- **Async execution**: Simulations run in background
- **Concurrent runs**: Multiple simulations can run simultaneously
- **Caching**: Results stored in MongoDB for quick retrieval
- **Polling**: Frontend polls every 2-3 seconds for updates

## Next Steps

1. **Try the frontend**: Open http://localhost:3000 and click ⚛️ OpenMC Engine
2. **Submit test run**: Use the Submit tab to create a simulation
3. **Monitor progress**: Watch real-time status updates
4. **Query history**: Browse completed runs
5. **Run sweeps**: Create parameter sweeps for analysis

## API Documentation

Full interactive API docs available at:
- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

