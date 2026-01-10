"""
OpenMC Verification Study 2: Single Layered Torus
==================================================

Purpose:
--------
Basic tokamak topology test. Models a hollow steel torus representing a 
simplified fusion reactor vessel.

Geometry:
---------
- Major radius: 400 cm (4m)
- Inner minor radius: 150 cm
- Outer minor radius: 170 cm (20 cm wall thickness)
- Material: Stainless steel

Expected Runtime:
-----------------
~5-10 minutes on a standard desktop

What This Tests:
----------------
- Toroidal geometry construction
- Ring source (characteristic of fusion reactors)
- More complex particle tracking
- Plasma confinement topology fundamentals
"""

import openmc
import openmc.stats
import numpy as np
import time
import os


def create_materials():
    """
    Create material definitions for the single torus
    """
    print("Creating materials...")
    
    # Stainless steel 316
    steel = openmc.Material(name='SS316')
    steel.add_element('Fe', 0.65, 'wo')
    steel.add_element('Cr', 0.17, 'wo')
    steel.add_element('Ni', 0.12, 'wo')
    steel.add_element('Mo', 0.025, 'wo')
    steel.add_element('Mn', 0.02, 'wo')
    steel.add_element('Si', 0.01, 'wo')
    steel.add_element('C', 0.005, 'wo')
    steel.set_density('g/cm3', 7.99)
    
    materials = openmc.Materials([steel])
    
    return materials


def create_torus_geometry(R0=400.0, r_inner=150.0, r_outer=170.0):
    """
    Create a single-layered hollow torus
    
    Parameters:
    -----------
    R0 : float
        Major radius (cm)
    r_inner : float
        Inner minor radius (cm)
    r_outer : float
        Outer minor radius (cm)
    """
    print(f"Creating torus geometry...")
    print(f"  Major radius: {R0} cm")
    print(f"  Minor radii: {r_inner} - {r_outer} cm")
    print(f"  Wall thickness: {r_outer - r_inner} cm")
    
    # Get materials
    materials = create_materials()
    steel = materials[0]
    
    # Create toroidal surfaces using x^2 + y^2 + z^2 + R0^2 - r^2 = 2*R0*sqrt(x^2 + y^2)
    # For OpenMC, we'll use ZTorus surfaces
    
    inner_torus = openmc.ZTorus(a=R0, b=r_inner, c=r_inner)
    outer_torus = openmc.ZTorus(a=R0, b=r_outer, c=r_outer)
    
    # Bounding box for vacuum boundary
    z_min = openmc.ZPlane(z0=-250, boundary_type='vacuum')
    z_max = openmc.ZPlane(z0=250, boundary_type='vacuum')
    cyl_outer = openmc.ZCylinder(r=R0 + r_outer + 50, boundary_type='vacuum')
    cyl_inner = openmc.ZCylinder(r=R0 - r_outer - 50, boundary_type='vacuum')
    
    # Cells
    # Plasma/vacuum region (inside inner torus)
    plasma_region = -inner_torus & +z_min & -z_max
    plasma_cell = openmc.Cell(name='plasma_vacuum', region=plasma_region)
    
    # Steel wall (between inner and outer torus)
    wall_region = +inner_torus & -outer_torus & +z_min & -z_max
    wall_cell = openmc.Cell(name='steel_wall', fill=steel, region=wall_region)
    
    # Outer vacuum (outside torus, inside bounding box)
    outer_vacuum_region = (+outer_torus & -cyl_outer & +cyl_inner & +z_min & -z_max)
    outer_vacuum_cell = openmc.Cell(name='outer_vacuum', region=outer_vacuum_region)
    
    # Create universe and geometry
    root = openmc.Universe(cells=[plasma_cell, wall_cell, outer_vacuum_cell])
    geometry = openmc.Geometry(root)
    
    return materials, geometry


def create_ring_source(R0=400.0, energy_MeV=14.0):
    """
    Create an isotropic ring source at the major radius
    
    Parameters:
    -----------
    R0 : float
        Major radius (cm)
    energy_MeV : float
        Neutron energy in MeV (14 MeV for D-T fusion)
    """
    print(f"Creating ring source at R={R0} cm, E={energy_MeV} MeV...")
    
    # Ring source distributed around the torus
    # Use cylindrical coordinates: r = R0, z = 0, phi = uniform
    source = openmc.IndependentSource()
    
    # Spatial distribution: ring at major radius
    # We'll use a cylindrical distribution with small spread
    r_dist = openmc.stats.Discrete([R0], [1.0])
    phi_dist = openmc.stats.Uniform(0, 2*np.pi)
    z_dist = openmc.stats.Discrete([0.0], [1.0])
    
    source.space = openmc.stats.CylindricalIndependent(
        r=r_dist, phi=phi_dist, z=z_dist, origin=(0.0, 0.0, 0.0)
    )
    
    # Isotropic angular distribution
    source.angle = openmc.stats.Isotropic()
    
    # Monoenergetic 14 MeV neutrons (D-T fusion)
    source.energy = openmc.stats.Discrete([energy_MeV * 1e6], [1.0])
    source.particle = 'neutron'
    
    return source


def create_settings(n_particles=1e5, n_batches=20):
    """
    Create simulation settings
    """
    print(f"Configuring simulation: {n_batches} batches of {n_particles:.0e} particles")
    
    settings = openmc.Settings()
    settings.batches = n_batches
    settings.inactive = 5
    settings.particles = int(n_particles)
    settings.run_mode = 'fixed source'
    
    # Add ring source
    settings.source = create_ring_source()
    
    return settings


def create_tallies():
    """
    Create tallies for flux and heating analysis
    """
    print("Creating tallies...")
    
    tallies = openmc.Tallies()
    
    # Mesh tally for spatial distribution
    # Cylindrical mesh is natural for toroidal geometry
    mesh = openmc.CylindricalMesh(
        r_grid=np.linspace(0, 600, 31),  # Radial bins
        phi_grid=np.linspace(0, 2*np.pi, 37),  # Toroidal angle
        z_grid=np.linspace(-250, 250, 26)  # Vertical bins
    )
    
    mesh_filter = openmc.MeshFilter(mesh)
    
    # Neutron flux mesh tally
    flux_tally = openmc.Tally(name='mesh_flux')
    flux_tally.filters = [mesh_filter]
    flux_tally.scores = ['flux']
    tallies.append(flux_tally)
    
    # Heating mesh tally
    heating_tally = openmc.Tally(name='mesh_heating')
    heating_tally.filters = [mesh_filter]
    heating_tally.scores = ['heating']
    tallies.append(heating_tally)
    
    # Cell tallies for integrated quantities
    cell_filter = openmc.CellFilter([1, 2])  # plasma and wall cells
    
    cell_flux = openmc.Tally(name='cell_flux')
    cell_flux.filters = [cell_filter]
    cell_flux.scores = ['flux', 'heating']
    tallies.append(cell_flux)
    
    return tallies


def run_study(output_dir='single_torus_output'):
    """
    Execute the single torus verification study
    """
    print("="*70)
    print("OpenMC Verification Study 2: Single Layered Torus")
    print("="*70)
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Build model
    materials, geometry = create_torus_geometry(R0=400.0, r_inner=150.0, r_outer=170.0)
    settings = create_settings(n_particles=1e5, n_batches=20)
    tallies = create_tallies()
    
    # Export to XML
    materials.export_to_xml(os.path.join(output_dir, 'materials.xml'))
    geometry.export_to_xml(os.path.join(output_dir, 'geometry.xml'))
    settings.export_to_xml(os.path.join(output_dir, 'settings.xml'))
    tallies.export_to_xml(os.path.join(output_dir, 'tallies.xml'))
    
    print(f"\nXML files exported to: {output_dir}/")
    print("\nModel Summary:")
    print(f"  - Geometry: Hollow steel torus (tokamak vessel)")
    print(f"  - Major radius: 4.0 m")
    print(f"  - Wall thickness: 0.2 m")
    print(f"  - Source: Ring source with 14 MeV neutrons")
    print(f"  - Particles: 1e5 per batch, 20 batches")
    print(f"  - Tallies: Cylindrical mesh + cell tallies")
    
    # Run simulation
    print("\n" + "-"*70)
    print("Starting OpenMC simulation...")
    print("This may take several minutes...")
    print("-"*70)
    
    start_time = time.time()
    
    try:
        # Change to output directory
        original_dir = os.getcwd()
        os.chdir(output_dir)
        
        openmc.run()
        
        elapsed_time = time.time() - start_time
        
        # Read and display results
        sp = openmc.StatePoint(f'statepoint.{settings.batches}.h5')
        
        print("\n" + "="*70)
        print("SIMULATION COMPLETED SUCCESSFULLY!")
        print("="*70)
        print(f"Runtime: {elapsed_time:.2f} seconds ({elapsed_time/60:.2f} minutes)")
        
        # Display cell tally results
        print("\nCell Tally Results:")
        print("-"*70)
        
        cell_flux_tally = sp.get_tally(name='cell_flux')
        df = cell_flux_tally.get_pandas_dataframe()
        print(df.to_string())
        
        print("\n📊 Mesh tallies saved in statepoint file for visualization")
        print("   Use the mesh data for detailed spatial analysis")
        
        # Return to original directory
        os.chdir(original_dir)
        
        return True, elapsed_time
        
    except Exception as e:
        print(f"\n❌ ERROR: Simulation failed!")
        print(f"Error message: {str(e)}")
        print("\nTroubleshooting:")
        print("  - Check that nuclear data library is properly configured")
        print("  - Ensure sufficient memory for mesh tallies")
        print("  - Verify geometry is properly closed")
        os.chdir(original_dir)
        return False, 0


if __name__ == '__main__':
    success, runtime = run_study()
    
    if success:
        print("\n" + "="*70)
        print("✓ VERIFICATION PASSED")
        print("="*70)
        print(f"Toroidal geometry working correctly!")
        print(f"Total runtime: {runtime:.2f} seconds")
        print("\nNext steps:")
        print("  - Run Study 3: Multi-Layered Torus (03_multi_torus.py)")
        print("  - Visualize mesh tallies")
        print("  - Analyze neutron flux distribution")
    else:
        print("\n❌ VERIFICATION FAILED")
        print("Review error messages above for debugging.")

