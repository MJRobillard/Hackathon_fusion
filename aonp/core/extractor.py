"""
Result extraction from OpenMC HDF5 outputs to structured data formats.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional


def extract_results(statepoint_path: Path) -> Dict[str, Any]:
    """
    Extract key results from OpenMC statepoint file.
    
    Args:
        statepoint_path: Path to statepoint.*.h5 file
    
    Returns:
        Dictionary with k-effective, uncertainties, and batch stats
    """
    try:
        import openmc
    except ImportError:
        raise ImportError(
            "OpenMC is required for result extraction. "
            "Install with: pip install openmc"
        )
    
    sp = openmc.StatePoint(str(statepoint_path))
    
    # Extract k-effective
    keff = sp.keff.nominal_value
    keff_std = sp.keff.std_dev
    
    # Extract batch statistics
    results = {
        'keff': keff,
        'keff_std': keff_std,
        'keff_uncertainty_pcm': keff_std * 1e5,  # Convert to pcm
        'n_batches': sp.n_batches,
        'n_inactive': sp.n_inactive,
        'n_particles': sp.n_particles,
        'n_realizations': sp.n_realizations,
    }
    
    # Extract batch k-effective values
    results['batch_keff'] = sp.k_generation.tolist()
    
    # Extract entropy (if available)
    if hasattr(sp, 'entropy'):
        results['entropy'] = sp.entropy.tolist()
    
    return results


def create_summary(statepoint_path: Path, output_path: Optional[Path] = None) -> Path:
    """
    Create summary Parquet file from statepoint.
    
    Args:
        statepoint_path: Path to statepoint file
        output_path: Optional output path (default: same dir as statepoint)
    
    Returns:
        Path to created summary.parquet file
    """
    results = extract_results(statepoint_path)
    
    # Create DataFrame with scalar metrics
    summary_data = {
        'metric': ['keff', 'keff_std', 'keff_uncertainty_pcm', 
                   'n_batches', 'n_inactive', 'n_particles'],
        'value': [results['keff'], results['keff_std'], 
                  results['keff_uncertainty_pcm'],
                  results['n_batches'], results['n_inactive'], 
                  results['n_particles']]
    }
    
    df = pd.DataFrame(summary_data)
    
    # Determine output path
    if output_path is None:
        output_path = statepoint_path.parent / "summary.parquet"
    
    # Write Parquet (efficient for queries)
    df.to_parquet(output_path, index=False)
    
    print(f"[OK] Extracted results to: {output_path}")
    print(f"  k-eff: {results['keff']:.6f} +/- {results['keff_std']:.6f}")
    print(f"  Uncertainty: {results['keff_uncertainty_pcm']:.1f} pcm")
    print(f"  Batches: {results['n_batches']} ({results['n_inactive']} inactive)")
    
    return output_path


def export_batch_statistics(statepoint_path: Path, output_path: Optional[Path] = None) -> Path:
    """
    Export per-batch statistics for detailed analysis.
    
    Args:
        statepoint_path: Path to statepoint file
        output_path: Optional output path (default: batch_statistics.parquet)
    
    Returns:
        Path to created batch_statistics.parquet file
    """
    try:
        import openmc
    except ImportError:
        raise ImportError("OpenMC is required for result extraction")
    
    sp = openmc.StatePoint(str(statepoint_path))
    
    # Create per-batch DataFrame
    df = pd.DataFrame({
        'batch': range(1, sp.n_batches + 1),
        'keff': sp.k_generation,
        'active': [i >= sp.n_inactive for i in range(sp.n_batches)]
    })
    
    # Add entropy if available
    if hasattr(sp, 'entropy'):
        df['entropy'] = sp.entropy
    
    # Determine output path
    if output_path is None:
        output_path = statepoint_path.parent / "batch_statistics.parquet"
    
    df.to_parquet(output_path, index=False)
    print(f"[OK] Exported batch statistics to: {output_path}")
    
    return output_path


def load_summary(parquet_path: Path) -> pd.DataFrame:
    """
    Load summary DataFrame from Parquet file.
    
    Args:
        parquet_path: Path to summary.parquet file
    
    Returns:
        DataFrame with summary metrics
    """
    return pd.read_parquet(parquet_path)

