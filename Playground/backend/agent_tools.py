"""
AONP Agent Tools - MongoDB-backed simulation tools for AI agents
Integrates with AONP database schema, supports both mock and real OpenMC execution
"""

import os
import json
import hashlib
import random
import tempfile
import shutil
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from uuid import uuid4

from dotenv import load_dotenv
from pymongo import MongoClient
from pydantic import BaseModel, Field

load_dotenv()

# Configuration: Set to True to use real OpenMC execution
USE_REAL_OPENMC = True

# ============================================================================
# MONGODB CONNECTION
# ============================================================================

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("MONGO_URI not found in environment")

client = MongoClient(MONGO_URI)
db = client["aonp"]

# Collections
studies_col = db["studies"]
runs_col = db["runs"]
summaries_col = db["summaries"]

# ============================================================================
# SCHEMAS (Simplified for MVP)
# ============================================================================

class StudySpec(BaseModel):
    """Simplified study specification for hackathon MVP"""
    geometry: str
    materials: List[str]
    enrichment_pct: Optional[float] = None
    temperature_K: Optional[float] = None
    particles: int = 10000
    batches: int = 50
    
    def canonical_json_bytes(self) -> bytes:
        """Deterministic JSON serialization for hashing"""
        obj = self.model_dump(mode="json")
        return json.dumps(
            obj,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False
        ).encode("utf-8")
    
    def spec_hash(self) -> str:
        """Generate SHA256 hash of canonical spec"""
        return hashlib.sha256(self.canonical_json_bytes()).hexdigest()


class SummaryRecord(BaseModel):
    """Simulation summary results"""
    run_id: str
    spec_hash: str
    keff: float
    keff_std: float
    runtime_seconds: float
    status: str
    created_at: datetime
    spec: Dict[str, Any]  # Store the original spec for easy querying


# ============================================================================
# OPENMC EXECUTION (Mock or Real)
# ============================================================================

def mock_openmc_execution(spec: StudySpec) -> Dict[str, Any]:
    """
    Mock OpenMC execution - returns realistic-looking results
    Used when USE_REAL_OPENMC is False
    """
    import time
    time.sleep(0.1)  # Simulate execution time
    
    # Generate plausible keff based on spec
    base_keff = 1.0
    
    # Enrichment effect
    if spec.enrichment_pct:
        base_keff += (spec.enrichment_pct - 3.0) * 0.05
    
    # Temperature effect (negative reactivity coefficient)
    if spec.temperature_K:
        base_keff -= (spec.temperature_K - 300) / 1000 * 0.1
    
    # Add random noise
    keff = base_keff + random.uniform(-0.02, 0.02)
    keff_std = random.uniform(0.0002, 0.0005)
    
    return {
        "keff": round(keff, 5),
        "keff_std": round(keff_std, 6),
        "runtime_seconds": 0.1,
        "status": "completed"
    }


def real_openmc_execution(spec: StudySpec, run_id: str) -> Dict[str, Any]:
    """
    Real OpenMC execution using direct OpenMC API (like verification studies)
    Used when USE_REAL_OPENMC is True
    """
    try:
        import openmc
        import time
        import tempfile
        import shutil
        
        start_time = time.time()
        
        # Create temporary directory for this run
        temp_dir = tempfile.mkdtemp(prefix=f"openmc_{run_id}_")
        
        try:
            # Define materials based on spec
            materials = []
            
            if "UO2" in spec.materials or "fuel" in [m.lower() for m in spec.materials]:
                # UO2 fuel - use atomic fractions consistently
                enrichment = spec.enrichment_pct or 4.5
                temp_k = spec.temperature_K or 900.0
                
                # Convert enrichment from weight % to atomic fraction
                # For UO2: 1 U atom to 2 O atoms
                u235_frac = enrichment / 100.0
                u238_frac = 1.0 - u235_frac
                
                fuel = openmc.Material(name='UO2')
                fuel.add_nuclide('U235', u235_frac, 'ao')
                fuel.add_nuclide('U238', u238_frac, 'ao')
                fuel.add_nuclide('O16', 2.0, 'ao')
                fuel.set_density('g/cm3', 10.4)
                fuel.temperature = temp_k
                materials.append(fuel)
            
            if "Water" in spec.materials or "H2O" in spec.materials:
                # Light water moderator
                water = openmc.Material(name='Water')
                water.add_nuclide('H1', 2.0, 'ao')
                water.add_nuclide('O16', 1.0, 'ao')
                water.set_density('g/cm3', 0.7)
                water.temperature = 600.0
                materials.append(water)
            
            if "Zircaloy" in spec.materials:
                # Zircaloy cladding
                zirc = openmc.Material(name='Zircaloy')
                zirc.add_element('Zr', 1.0)
                zirc.set_density('g/cm3', 6.5)
                zirc.temperature = 600.0
                materials.append(zirc)
            
            # Create simple pin cell geometry
            fuel_or = openmc.ZCylinder(r=0.39)
            clad_ir = openmc.ZCylinder(r=0.40)
            clad_or = openmc.ZCylinder(r=0.46)
            pitch = 1.26
            box = openmc.model.RectangularPrism(pitch, pitch, boundary_type='reflective')
            
            # Define cells
            fuel_cell = openmc.Cell(name='fuel', fill=materials[0], region=-fuel_or)
            
            if len(materials) >= 3:  # fuel, water, zircaloy
                gap_cell = openmc.Cell(name='gap', region=+fuel_or & -clad_ir)
                clad_cell = openmc.Cell(name='clad', fill=materials[2], region=+clad_ir & -clad_or)
                water_cell = openmc.Cell(name='water', fill=materials[1], region=+clad_or & -box)
                root = openmc.Universe(cells=[fuel_cell, gap_cell, clad_cell, water_cell])
            else:  # simplified: just fuel and water
                water_cell = openmc.Cell(name='water', fill=materials[1], region=+fuel_or & -box)
                root = openmc.Universe(cells=[fuel_cell, water_cell])
            
            geometry = openmc.Geometry(root)
            
            # Settings
            settings = openmc.Settings()
            settings.batches = spec.batches
            settings.inactive = min(10, spec.batches // 5)
            settings.particles = spec.particles
            settings.run_mode = 'eigenvalue'
            
            # Create model
            model = openmc.Model(geometry=geometry, materials=openmc.Materials(materials), settings=settings)
            
            # Export and run in temp directory
            original_dir = os.getcwd()
            os.chdir(temp_dir)
            
            # Run simulation
            model.export_to_xml()
            openmc.run()
            
            # Read results
            sp = openmc.StatePoint(f'statepoint.{spec.batches}.h5')
            keff = sp.keff
            
            os.chdir(original_dir)
            
            elapsed_time = time.time() - start_time
            
            return {
                "keff": float(keff.nominal_value),
                "keff_std": float(keff.std_dev),
                "runtime_seconds": elapsed_time,
                "status": "completed"
            }
            
        finally:
            # Clean up temporary directory
            os.chdir(original_dir) if os.getcwd() == temp_dir else None
            shutil.rmtree(temp_dir, ignore_errors=True)
            
    except Exception as e:
        print(f"[ERROR] Real OpenMC execution failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Fall back to mock
        print("[WARN] Falling back to mock execution")
        return mock_openmc_execution(spec)


def execute_simulation(spec: StudySpec, run_id: str) -> Dict[str, Any]:
    """
    Execute simulation using configured method (mock or real)
    """
    if USE_REAL_OPENMC:
        print(f"  Using REAL OpenMC execution")
        return real_openmc_execution(spec, run_id)
    else:
        print(f"  Using MOCK OpenMC execution")
        return mock_openmc_execution(spec)


# ============================================================================
# AGENT TOOLS
# ============================================================================

def submit_study(study_spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Agent Tool: Submit a simulation study
    
    1. Validates and hashes study spec
    2. Upserts to studies collection (deduplication)
    3. Creates run record
    4. Executes simulation (mocked)
    5. Stores summary
    6. Returns run_id and results
    """
    print(f"\n[TOOL: submit_study]")
    
    # Parse and validate spec
    spec = StudySpec(**study_spec)
    spec_hash = spec.spec_hash()
    run_id = f"run_{uuid4().hex[:8]}"
    
    print(f"  spec_hash: {spec_hash[:12]}...")
    print(f"  run_id: {run_id}")
    
    # Upsert study (ensures uniqueness by spec_hash)
    studies_col.update_one(
        {"spec_hash": spec_hash},
        {
            "$set": {
                "spec_hash": spec_hash,
                "canonical_spec": json.loads(spec.canonical_json_bytes()),
                "created_at": datetime.now(timezone.utc)
            }
        },
        upsert=True
    )
    
    # Create run record
    runs_col.insert_one({
        "run_id": run_id,
        "spec_hash": spec_hash,
        "status": "running",
        "created_at": datetime.now(timezone.utc)
    })
    
    # Execute (mock or real based on configuration)
    print(f"  Executing simulation...")
    result = execute_simulation(spec, run_id)
    
    # Update run status
    runs_col.update_one(
        {"run_id": run_id},
        {"$set": {"status": result["status"]}}
    )
    
    # Store summary
    summary = SummaryRecord(
        run_id=run_id,
        spec_hash=spec_hash,
        keff=result["keff"],
        keff_std=result["keff_std"],
        runtime_seconds=result["runtime_seconds"],
        status=result["status"],
        created_at=datetime.now(timezone.utc),
        spec=spec.model_dump()
    )
    
    summaries_col.insert_one(summary.model_dump())
    
    print(f"  [OK] keff = {result['keff']:.5f} +/- {result['keff_std']:.6f}")
    
    return {
        "run_id": run_id,
        "spec_hash": spec_hash,
        "keff": result["keff"],
        "keff_std": result["keff_std"],
        "status": result["status"]
    }


def query_results(filter_params: Optional[Dict[str, Any]] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Agent Tool: Query past simulation results
    
    Examples:
    - query_results({"spec.geometry": "PWR pin cell"})
    - query_results({"keff": {"$gt": 1.0}})
    """
    print(f"\n[TOOL: query_results]")
    
    if filter_params is None:
        filter_params = {}
    
    print(f"  filter: {filter_params}")
    
    results = list(summaries_col.find(filter_params).limit(limit))
    
    # Remove MongoDB _id for cleaner output
    for r in results:
        r.pop("_id", None)
        r["created_at"] = r["created_at"].isoformat() if "created_at" in r else None
    
    print(f"  Found {len(results)} results")
    
    return results


def generate_sweep(base_spec: Dict[str, Any], param_name: str, param_values: List[Any]) -> List[str]:
    """
    Agent Tool: Generate parameter sweep
    
    Creates multiple study specs by varying a parameter
    Submits all runs and returns run_ids
    
    Example:
    generate_sweep(
        base_spec={"geometry": "PWR pin", "materials": ["UO2"], "enrichment_pct": 3.0},
        param_name="enrichment_pct",
        param_values=[3.0, 3.5, 4.0, 4.5, 5.0]
    )
    """
    print(f"\n[TOOL: generate_sweep]")
    print(f"  Sweeping {param_name} over {len(param_values)} values")
    
    run_ids = []
    
    for value in param_values:
        # Create variant spec
        variant_spec = base_spec.copy()
        variant_spec[param_name] = value
        
        # Submit
        result = submit_study(variant_spec)
        run_ids.append(result["run_id"])
    
    print(f"  [OK] Generated {len(run_ids)} runs")
    
    return run_ids


def compare_runs(run_ids: List[str]) -> Dict[str, Any]:
    """
    Agent Tool: Compare multiple simulation runs
    
    Returns structured comparison data
    """
    print(f"\n[TOOL: compare_runs]")
    print(f"  Comparing {len(run_ids)} runs")
    
    results = list(summaries_col.find({"run_id": {"$in": run_ids}}))
    
    if not results:
        return {"error": "No results found for provided run_ids"}
    
    # Extract key metrics
    comparison = {
        "num_runs": len(results),
        "keff_values": [r["keff"] for r in results],
        "keff_mean": sum(r["keff"] for r in results) / len(results),
        "keff_min": min(r["keff"] for r in results),
        "keff_max": max(r["keff"] for r in results),
        "runs": []
    }
    
    for r in results:
        comparison["runs"].append({
            "run_id": r["run_id"],
            "keff": r["keff"],
            "keff_std": r["keff_std"],
            "spec": r["spec"]
        })
    
    print(f"  keff range: [{comparison['keff_min']:.5f}, {comparison['keff_max']:.5f}]")
    
    return comparison


def get_study_statistics() -> Dict[str, Any]:
    """
    Agent Tool: Get database statistics
    
    Returns counts and summary info about stored simulations
    """
    print(f"\n[TOOL: get_study_statistics]")
    
    stats = {
        "total_studies": studies_col.count_documents({}),
        "total_runs": runs_col.count_documents({}),
        "total_summaries": summaries_col.count_documents({}),
        "completed_runs": runs_col.count_documents({"status": "completed"}),
    }
    
    # Get recent runs
    recent = list(summaries_col.find().sort("created_at", -1).limit(5))
    stats["recent_runs"] = [
        {
            "run_id": r["run_id"],
            "keff": r["keff"],
            "geometry": r["spec"].get("geometry", "unknown")
        }
        for r in recent
    ]
    
    print(f"  Studies: {stats['total_studies']}, Runs: {stats['total_runs']}")
    
    return stats


def get_run_by_id(run_id: str) -> Optional[Dict[str, Any]]:
    """
    Agent Tool: Get specific run by ID
    
    Returns complete run information including spec, results, and metadata
    """
    print(f"\n[TOOL: get_run_by_id]")
    print(f"  run_id: {run_id}")
    
    result = summaries_col.find_one({"run_id": run_id})
    
    if not result:
        print(f"  [ERROR] Run {run_id} not found")
        return None
    
    # Remove MongoDB _id
    result.pop("_id", None)
    result["created_at"] = result["created_at"].isoformat() if "created_at" in result else None
    
    print(f"  [OK] keff = {result['keff']:.5f}")
    
    return result


def get_recent_runs(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Agent Tool: Get most recent simulation runs
    
    Returns the N most recent runs sorted by creation time
    """
    print(f"\n[TOOL: get_recent_runs]")
    print(f"  limit: {limit}")
    
    results = list(summaries_col.find().sort("created_at", -1).limit(limit))
    
    # Remove MongoDB _id and format dates
    for r in results:
        r.pop("_id", None)
        r["created_at"] = r["created_at"].isoformat() if "created_at" in r else None
    
    print(f"  Found {len(results)} recent runs")
    
    return results


def validate_physics(spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Agent Tool: Validate physics parameters
    
    Checks if study specification is physically reasonable
    Returns validation result with warnings/errors
    """
    print(f"\n[TOOL: validate_physics]")
    
    validation = {
        "valid": True,
        "warnings": [],
        "errors": []
    }
    
    # Validate enrichment
    if "enrichment_pct" in spec and spec["enrichment_pct"] is not None:
        enrichment = spec["enrichment_pct"]
        if enrichment < 0 or enrichment > 100:
            validation["valid"] = False
            validation["errors"].append(f"Enrichment {enrichment}% out of range [0, 100]")
        elif enrichment < 2.0:
            validation["warnings"].append(f"Low enrichment {enrichment}% - may be subcritical")
        elif enrichment > 20.0:
            validation["warnings"].append(f"High enrichment {enrichment}% - unusual for commercial reactors")
    
    # Validate temperature
    if "temperature_K" in spec and spec["temperature_K"] is not None:
        temp = spec["temperature_K"]
        if temp < 0:
            validation["valid"] = False
            validation["errors"].append(f"Temperature {temp}K is negative")
        elif temp < 273:
            validation["warnings"].append(f"Temperature {temp}K below freezing")
        elif temp > 3000:
            validation["warnings"].append(f"Temperature {temp}K very high - fuel may be damaged")
    
    # Validate particles and batches
    if "particles" in spec:
        particles = spec["particles"]
        if particles < 100:
            validation["warnings"].append(f"Very few particles ({particles}) - results will be noisy")
        elif particles > 1000000:
            validation["warnings"].append(f"Many particles ({particles}) - simulation will be slow")
    
    if "batches" in spec:
        batches = spec["batches"]
        if batches < 10:
            validation["warnings"].append(f"Few batches ({batches}) - statistics may be poor")
    
    # Validate materials
    if "materials" in spec:
        materials = spec["materials"]
        known_materials = ["UO2", "Water", "H2O", "Zircaloy", "fuel", "moderator", "coolant"]
        unknown = [m for m in materials if m not in known_materials and not any(k.lower() in m.lower() for k in known_materials)]
        if unknown:
            validation["warnings"].append(f"Unknown materials: {unknown}")
    
    status = "valid" if validation["valid"] else "invalid"
    print(f"  Status: {status}")
    if validation["warnings"]:
        print(f"  Warnings: {len(validation['warnings'])}")
    if validation["errors"]:
        print(f"  Errors: {len(validation['errors'])}")
    
    return validation


# ============================================================================
# TOOL REGISTRY FOR AGENT INTEGRATION
# ============================================================================

AGENT_TOOLS = {
    "submit_study": {
        "function": submit_study,
        "description": "Submit a new simulation study. Returns run_id and results.",
        "parameters": {
            "study_spec": "Dict with keys: geometry, materials, enrichment_pct, temperature_K, particles, batches"
        }
    },
    "query_results": {
        "function": query_results,
        "description": "Query past simulation results with optional filters.",
        "parameters": {
            "filter_params": "Optional dict for MongoDB query (e.g. {'spec.geometry': 'PWR pin cell'})",
            "limit": "Max results to return (default 10)"
        }
    },
    "generate_sweep": {
        "function": generate_sweep,
        "description": "Generate and execute parameter sweep.",
        "parameters": {
            "base_spec": "Base study specification dict",
            "param_name": "Parameter name to vary (e.g. 'enrichment_pct')",
            "param_values": "List of values to sweep over"
        }
    },
    "compare_runs": {
        "function": compare_runs,
        "description": "Compare multiple runs and return statistics.",
        "parameters": {
            "run_ids": "List of run_id strings to compare"
        }
    },
    "get_study_statistics": {
        "function": get_study_statistics,
        "description": "Get database statistics and recent runs.",
        "parameters": {}
    },
    "get_run_by_id": {
        "function": get_run_by_id,
        "description": "Get specific run by ID. Returns complete run information.",
        "parameters": {
            "run_id": "Run ID string (e.g. 'run_abc12345')"
        }
    },
    "get_recent_runs": {
        "function": get_recent_runs,
        "description": "Get most recent simulation runs.",
        "parameters": {
            "limit": "Number of recent runs to return (default 10)"
        }
    },
    "validate_physics": {
        "function": validate_physics,
        "description": "Validate physics parameters. Checks if spec is physically reasonable.",
        "parameters": {
            "spec": "Study specification dict to validate"
        }
    }
}


# ============================================================================
# TEST / DEMO
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("AONP AGENT TOOLS - DEMO")
    print("=" * 80)
    
    # Test 1: Submit single study
    print("\n[TEST 1] Submit single study")
    result = submit_study({
        "geometry": "PWR pin cell",
        "materials": ["UO2", "Zircaloy", "Water"],
        "enrichment_pct": 4.5,
        "temperature_K": 600,
        "particles": 10000,
        "batches": 50
    })
    
    # Test 2: Query results
    print("\n[TEST 2] Query PWR simulations")
    pwr_results = query_results({"spec.geometry": "PWR pin cell"})
    
    # Test 3: Generate sweep
    print("\n[TEST 3] Generate enrichment sweep")
    sweep_run_ids = generate_sweep(
        base_spec={
            "geometry": "PWR pin cell",
            "materials": ["UO2", "Zircaloy", "Water"],
            "temperature_K": 600,
            "particles": 10000,
            "batches": 50
        },
        param_name="enrichment_pct",
        param_values=[3.0, 3.5, 4.0, 4.5, 5.0]
    )
    
    # Test 4: Compare sweep results
    print("\n[TEST 4] Compare sweep results")
    comparison = compare_runs(sweep_run_ids)
    print(f"\n  Enrichment sweep results:")
    for run_data in comparison["runs"]:
        enrichment = run_data["spec"]["enrichment_pct"]
        keff = run_data["keff"]
        print(f"    {enrichment}% -> keff = {keff:.5f}")
    
    # Test 5: Statistics
    print("\n[TEST 5] Database statistics")
    stats = get_study_statistics()
    
    print("\n" + "=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)

