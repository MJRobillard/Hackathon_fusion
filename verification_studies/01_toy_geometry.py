"""
OpenMC Verification Study 1: Two-Volume Toy Geometry
=====================================================

Purpose:
--------
Fastest possible verification test. Uses a minimal geometry with only two 
non-void volumes to test basic OpenMC functionality and parallel performance.

Expected Runtime:
-----------------
~1-2 minutes on a standard desktop (single core)

What This Tests:
----------------
- Basic OpenMC installation and functionality
- Material definitions
- Simple geometry construction
- Particle transport mechanics
- Tally system
- Basic output generation
"""

import openmc
import numpy as np
import time
import os


def create_toy_geometry():
    """
    Create a minimal two-volume geometry:
    - Inner sphere of water
    - Outer shell of steel
    """
    print("Creating toy geometry with 2 volumes...")
    
    # Materials
    water = openmc.Material(name='Water')
    water.add_nuclide('H1', 2.0)
    water.add_nuclide('O16', 1.0)
    water.set_density('g/cm3', 1.0)
    
    steel = openmc.Material(name='Steel')
    steel.add_element('Fe', 0.98)
    steel.add_element('C', 0.02)
    steel.set_density('g/cm3', 7.85)
    
    materials = openmc.Materials([water, steel])
    
    # Geometry - Simple concentric spheres
    inner_sphere = openmc.Sphere(r=10.0)
    outer_sphere = openmc.Sphere(r=20.0, boundary_type='vacuum')
    
    # Cells
    inner_cell = openmc.Cell(fill=water, region=-inner_sphere)
    outer_cell = openmc.Cell(fill=steel, region=+inner_sphere & -outer_sphere)
    
    # Universe and geometry
    root = openmc.Universe(cells=[inner_cell, outer_cell])
    geometry = openmc.Geometry(root)
    
    return materials, geometry


def create_settings(n_particles=1e5, n_batches=10):
    """
    Create simulation settings with a point source
    """
    print(f"Setting up simulation: {n_batches} batches of {n_particles:.0e} particles")
    
    settings = openmc.Settings()
    settings.batches = n_batches
    settings.inactive = 2
    settings.particles = int(n_particles)
    settings.run_mode = 'fixed source'
    
    # Point source at center with 14 MeV neutrons (fusion energy)
    source = openmc.IndependentSource()
    source.space = openmc.stats.Point((0, 0, 0))
    source.angle = openmc.stats.Isotropic()
    source.energy = openmc.stats.Discrete([14.0e6], [1.0])
    source.particle = 'neutron'
    
    settings.source = source
    
    return settings


def create_tallies():
    """
    Create basic tallies to verify physics calculations
    """
    print("Creating tallies for flux and heating...")
    
    tallies = openmc.Tallies()
    
    # Cell filter for both volumes
    cell_filter = openmc.CellFilter([1, 2])
    
    # Flux tally
    flux_tally = openmc.Tally(name='flux')
    flux_tally.filters = [cell_filter]
    flux_tally.scores = ['flux']
    tallies.append(flux_tally)
    
    # Heating tally
    heating_tally = openmc.Tally(name='heating')
    heating_tally.filters = [cell_filter]
    heating_tally.scores = ['heating']
    tallies.append(heating_tally)
    
    # Absorption tally
    absorption_tally = openmc.Tally(name='absorption')
    absorption_tally.filters = [cell_filter]
    absorption_tally.scores = ['absorption']
    tallies.append(absorption_tally)
    
    return tallies


def run_study(output_dir='toy_geometry_output'):
    """
    Execute the complete toy geometry study
    """
    print("="*60)
    print("OpenMC Verification Study 1: Two-Volume Toy Geometry")
    print("="*60)
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Build model
    materials, geometry = create_toy_geometry()
    settings = create_settings(n_particles=1e5, n_batches=10)
    tallies = create_tallies()
    
    # Export to XML
    materials.export_to_xml(os.path.join(output_dir, 'materials.xml'))
    geometry.export_to_xml(os.path.join(output_dir, 'geometry.xml'))
    settings.export_to_xml(os.path.join(output_dir, 'settings.xml'))
    tallies.export_to_xml(os.path.join(output_dir, 'tallies.xml'))
    
    print(f"\nXML files exported to: {output_dir}/")
    print("\nModel Summary:")
    print(f"  - Volumes: 2 (water sphere + steel shell)")
    print(f"  - Source: Point source at origin, 14 MeV neutrons")
    print(f"  - Particles: 1e5 per batch, 10 batches")
    print(f"  - Tallies: Flux, heating, absorption")
    
    # Run simulation
    print("\n" + "-"*60)
    print("Starting OpenMC simulation...")
    print("-"*60)
    
    start_time = time.time()
    
    try:
        # Change to output directory to run OpenMC there
        original_dir = os.getcwd()
        os.chdir(output_dir)
        
        openmc.run()
        
        elapsed_time = time.time() - start_time
        
        # Read and display results
        sp = openmc.StatePoint('statepoint.10.h5')
        
        print("\n" + "="*60)
        print("SIMULATION COMPLETED SUCCESSFULLY!")
        print("="*60)
        print(f"Runtime: {elapsed_time:.2f} seconds")
        
        # Display tally results
        print("\nTally Results:")
        print("-"*60)
        
        for tally_name in ['flux', 'heating', 'absorption']:
            tally = sp.get_tally(name=tally_name)
            df = tally.get_pandas_dataframe()
            print(f"\n{tally_name.upper()}:")
            print(df.to_string())
        
        # Return to original directory
        os.chdir(original_dir)
        
        return True, elapsed_time
        
    except Exception as e:
        print(f"\n❌ ERROR: Simulation failed!")
        print(f"Error message: {str(e)}")
        os.chdir(original_dir)
        return False, 0


if __name__ == '__main__':
    success, runtime = run_study()
    
    if success:
        print("\n" + "="*60)
        print("✓ VERIFICATION PASSED")
        print("="*60)
        print(f"Your OpenMC installation is working correctly!")
        print(f"Total runtime: {runtime:.2f} seconds")
        print("\nNext steps:")
        print("  - Run Study 2: Single Layered Torus (02_single_torus.py)")
        print("  - Increase particle count for better statistics")
        print("  - Explore visualization with plots.xml")
    else:
        print("\n❌ VERIFICATION FAILED")
        print("Please check your OpenMC installation and nuclear data library.")

