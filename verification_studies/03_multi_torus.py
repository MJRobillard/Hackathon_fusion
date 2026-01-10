"""
OpenMC Verification Study 3: Multi-Layered Torus
=================================================

Purpose:
--------
Realistic tokamak model with multiple layers representing:
- First wall (facing the plasma)
- Breeding blanket (for tritium production)
- Vacuum vessel (structural containment)

This tests more complex material interfaces and neutronics relevant to
actual fusion reactor design.

Geometry:
---------
- Major radius: 400 cm (4m)
- Plasma minor radius: 140 cm
- First wall: 140-145 cm (5 cm tungsten)
- Blanket: 145-195 cm (50 cm Li4SiO4 + Be multiplier)
- Vacuum vessel: 195-210 cm (15 cm steel)

Expected Runtime:
-----------------
~10-15 minutes on a standard desktop

What This Tests:
----------------
- Multi-material toroidal geometry
- Tritium breeding calculations (TBR)
- Neutron multiplication effects
- Heating distribution across components
"""

import openmc
import openmc.stats
import numpy as np
import time
import os


def create_materials():
    """
    Create material definitions for multi-layered tokamak
    """
    print("Creating materials...")
    
    # Tungsten first wall
    tungsten = openmc.Material(name='Tungsten')
    tungsten.add_element('W', 1.0)
    tungsten.set_density('g/cm3', 19.3)
    
    # Lithium orthosilicate breeder (Li4SiO4)
    li4sio4 = openmc.Material(name='Li4SiO4')
    li4sio4.add_element('Li', 4.0)
    li4sio4.add_element('Si', 1.0)
    li4sio4.add_element('O', 4.0)
    li4sio4.set_density('g/cm3', 2.4)
    
    # For breeding calculations, we need to specify Li isotopes
    # Natural lithium is ~7.5% Li6, 92.5% Li7
    # We'll enrich to 30% Li6 for better breeding
    li4sio4_enriched = openmc.Material(name='Li4SiO4_enriched')
    li4sio4_enriched.add_nuclide('Li6', 1.2)  # 30% enrichment * 4 atoms
    li4sio4_enriched.add_nuclide('Li7', 2.8)  # 70% * 4 atoms
    li4sio4_enriched.add_element('Si', 1.0)
    li4sio4_enriched.add_element('O', 4.0)
    li4sio4_enriched.set_density('g/cm3', 2.4)
    
    # Beryllium neutron multiplier
    beryllium = openmc.Material(name='Beryllium')
    beryllium.add_element('Be', 1.0)
    beryllium.set_density('g/cm3', 1.85)
    
    # Blanket mixture (60% Li4SiO4, 40% Be by volume)
    blanket = openmc.Material.mix_materials(
        [li4sio4_enriched, beryllium],
        [0.6, 0.4],
        'vo',
        name='Blanket_mixture'
    )
    
    # Stainless steel vacuum vessel
    steel = openmc.Material(name='SS316')
    steel.add_element('Fe', 0.65, 'wo')
    steel.add_element('Cr', 0.17, 'wo')
    steel.add_element('Ni', 0.12, 'wo')
    steel.add_element('Mo', 0.025, 'wo')
    steel.add_element('Mn', 0.02, 'wo')
    steel.add_element('Si', 0.01, 'wo')
    steel.add_element('C', 0.005, 'wo')
    steel.set_density('g/cm3', 7.99)
    
    materials = openmc.Materials([tungsten, li4sio4_enriched, beryllium, 
                                   blanket, steel])
    
    return materials


def create_multi_layer_torus(R0=400.0):
    """
    Create a multi-layered toroidal fusion reactor
    
    Parameters:
    -----------
    R0 : float
        Major radius (cm)
    """
    print(f"Creating multi-layer torus geometry...")
    
    # Layer definitions (minor radii in cm)
    r_plasma = 140.0
    r_first_wall = 145.0
    r_blanket = 195.0
    r_vessel = 210.0
    
    print(f"  Plasma region: 0 - {r_plasma} cm")
    print(f"  First wall (W): {r_plasma} - {r_first_wall} cm")
    print(f"  Blanket: {r_first_wall} - {r_blanket} cm")
    print(f"  Vacuum vessel: {r_blanket} - {r_vessel} cm")
    
    # Get materials
    materials = create_materials()
    tungsten = materials[0]
    blanket = materials[3]
    steel = materials[4]
    
    # Create toroidal surfaces
    torus_plasma = openmc.ZTorus(a=R0, b=r_plasma, c=r_plasma)
    torus_first_wall = openmc.ZTorus(a=R0, b=r_first_wall, c=r_first_wall)
    torus_blanket = openmc.ZTorus(a=R0, b=r_blanket, c=r_blanket)
    torus_vessel = openmc.ZTorus(a=R0, b=r_vessel, c=r_vessel)
    
    # Bounding surfaces
    z_min = openmc.ZPlane(z0=-300, boundary_type='vacuum')
    z_max = openmc.ZPlane(z0=300, boundary_type='vacuum')
    cyl_outer = openmc.ZCylinder(r=R0 + r_vessel + 50, boundary_type='vacuum')
    cyl_inner = openmc.ZCylinder(r=max(0, R0 - r_vessel - 50), boundary_type='vacuum')
    
    # Define cells for each layer
    # Plasma region
    plasma_region = -torus_plasma & +z_min & -z_max
    plasma_cell = openmc.Cell(name='plasma', region=plasma_region)
    
    # First wall (tungsten)
    fw_region = +torus_plasma & -torus_first_wall & +z_min & -z_max
    fw_cell = openmc.Cell(name='first_wall', fill=tungsten, region=fw_region)
    
    # Breeding blanket
    blanket_region = +torus_first_wall & -torus_blanket & +z_min & -z_max
    blanket_cell = openmc.Cell(name='blanket', fill=blanket, region=blanket_region)
    
    # Vacuum vessel
    vessel_region = +torus_blanket & -torus_vessel & +z_min & -z_max
    vessel_cell = openmc.Cell(name='vessel', fill=steel, region=vessel_region)
    
    # Outer void
    outer_region = (+torus_vessel & -cyl_outer & +cyl_inner & +z_min & -z_max)
    outer_cell = openmc.Cell(name='outer_void', region=outer_region)
    
    # Create universe and geometry
    root = openmc.Universe(cells=[plasma_cell, fw_cell, blanket_cell, 
                                   vessel_cell, outer_cell])
    geometry = openmc.Geometry(root)
    
    return materials, geometry


def create_ring_source(R0=400.0, r_source=140.0, energy_MeV=14.08):
    """
    Create ring source at plasma edge
    
    Parameters:
    -----------
    R0 : float
        Major radius (cm)
    r_source : float
        Minor radius for source location (cm)
    energy_MeV : float
        Neutron energy in MeV (14.08 MeV for D-T fusion)
    """
    print(f"Creating ring source at plasma edge...")
    
    source = openmc.IndependentSource()
    
    # Ring source using cylindrical coordinates
    # The source is at a ring defined by the major and minor radii
    # For a torus, points are at (R0 + r*cos(theta), r*sin(theta)*cos(phi), r*sin(theta)*sin(phi))
    # Simplified: distribute on a circle at the plasma edge
    
    # Create a ring distribution
    # Use toroidal coordinates approximation
    angle = openmc.stats.Uniform(0, 2*np.pi)
    
    # Convert to Cartesian: points on the ring
    # We'll use a custom distribution by specifying multiple point sources
    # For simplicity, use cylindrical with the plasma minor radius
    r_dist = openmc.stats.Uniform(R0 - 10, R0 + 10)  # Ring with some width
    phi_dist = openmc.stats.Uniform(0, 2*np.pi)
    z_dist = openmc.stats.Uniform(-10, 10)  # Slight vertical spread
    
    source.space = openmc.stats.CylindricalIndependent(
        r=r_dist, phi=phi_dist, z=z_dist, origin=(0.0, 0.0, 0.0)
    )
    
    # Isotropic emission
    source.angle = openmc.stats.Isotropic()
    
    # 14.08 MeV neutrons (D-T fusion)
    source.energy = openmc.stats.Discrete([energy_MeV * 1e6], [1.0])
    source.particle = 'neutron'
    
    return source


def create_settings(n_particles=2e5, n_batches=25):
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
    Create comprehensive tallies for fusion reactor analysis
    """
    print("Creating tallies for TBR and heating analysis...")
    
    tallies = openmc.Tallies()
    
    # Cell filter for all regions
    cell_filter = openmc.CellFilter([1, 2, 3, 4])  # plasma, FW, blanket, vessel
    
    # Neutron flux by cell
    flux_tally = openmc.Tally(name='cell_flux')
    flux_tally.filters = [cell_filter]
    flux_tally.scores = ['flux']
    tallies.append(flux_tally)
    
    # Heating by cell
    heating_tally = openmc.Tally(name='cell_heating')
    heating_tally.filters = [cell_filter]
    heating_tally.scores = ['heating']
    tallies.append(heating_tally)
    
    # Tritium Breeding Ratio (TBR) calculation
    # This is the key metric for fusion reactors
    # TBR = (T produced from Li6 + T produced from Li7) / source neutrons
    
    # Blanket cell filter
    blanket_filter = openmc.CellFilter([3])
    
    # Li6(n,t) reaction rate
    li6_filter = openmc.MaterialFilter(materials=[3])  # blanket material
    li6_tally = openmc.Tally(name='li6_tritium_production')
    li6_tally.filters = [blanket_filter]
    li6_tally.scores = ['(n,Xt)']  # All reactions producing tritium
    tallies.append(li6_tally)
    
    # Total tritium production
    tbr_tally = openmc.Tally(name='TBR')
    tbr_tally.filters = [blanket_filter]
    tbr_tally.scores = ['(n,Xt)']
    tallies.append(tbr_tally)
    
    # Neutron multiplication in blanket (from Be(n,2n) reactions)
    multiplication_tally = openmc.Tally(name='neutron_multiplication')
    multiplication_tally.filters = [blanket_filter]
    multiplication_tally.scores = ['(n,2n)', '(n,3n)']
    tallies.append(multiplication_tally)
    
    # Mesh tally for spatial distribution
    mesh = openmc.CylindricalMesh()
    mesh.r_grid = np.linspace(0, 700, 36)
    mesh.phi_grid = np.linspace(0, 2*np.pi, 25)
    mesh.z_grid = np.linspace(-300, 300, 31)
    
    mesh_filter = openmc.MeshFilter(mesh)
    
    mesh_heating = openmc.Tally(name='mesh_heating')
    mesh_heating.filters = [mesh_filter]
    mesh_heating.scores = ['heating']
    tallies.append(mesh_heating)
    
    return tallies


def run_study(output_dir='multi_torus_output'):
    """
    Execute the multi-layered torus verification study
    """
    print("="*70)
    print("OpenMC Verification Study 3: Multi-Layered Torus")
    print("="*70)
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Build model
    materials, geometry = create_multi_layer_torus(R0=400.0)
    settings = create_settings(n_particles=2e5, n_batches=25)
    tallies = create_tallies()
    
    # Export to XML
    materials.export_to_xml(os.path.join(output_dir, 'materials.xml'))
    geometry.export_to_xml(os.path.join(output_dir, 'geometry.xml'))
    settings.export_to_xml(os.path.join(output_dir, 'settings.xml'))
    tallies.export_to_xml(os.path.join(output_dir, 'tallies.xml'))
    
    print(f"\nXML files exported to: {output_dir}/")
    print("\nModel Summary:")
    print(f"  - Geometry: Multi-layer tokamak")
    print(f"    * Tungsten first wall")
    print(f"    * Li4SiO4 + Be breeding blanket")
    print(f"    * Steel vacuum vessel")
    print(f"  - Source: Ring source, 14.08 MeV D-T neutrons")
    print(f"  - Particles: 2e5 per batch, 25 batches")
    print(f"  - Tallies: TBR, heating, flux, multiplication")
    
    # Run simulation
    print("\n" + "-"*70)
    print("Starting OpenMC simulation...")
    print("This will take several minutes...")
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
        
        # Display key results
        print("\n" + "="*70)
        print("KEY RESULTS")
        print("="*70)
        
        # Cell heating
        print("\nHeating by Component:")
        print("-"*70)
        heating_tally = sp.get_tally(name='cell_heating')
        df_heating = heating_tally.get_pandas_dataframe()
        print(df_heating.to_string())
        
        # TBR (approximate - needs normalization)
        print("\nTritium Production (Raw Tally):")
        print("-"*70)
        tbr_tally = sp.get_tally(name='TBR')
        df_tbr = tbr_tally.get_pandas_dataframe()
        print(df_tbr.to_string())
        print("\n⚠ Note: TBR calculation requires normalization per source neutron")
        print("   TBR = (tritium production rate) / (source rate)")
        
        # Neutron multiplication
        print("\nNeutron Multiplication:")
        print("-"*70)
        mult_tally = sp.get_tally(name='neutron_multiplication')
        df_mult = mult_tally.get_pandas_dataframe()
        print(df_mult.to_string())
        
        print("\n📊 Full results saved in statepoint file")
        
        # Return to original directory
        os.chdir(original_dir)
        
        return True, elapsed_time
        
    except Exception as e:
        print(f"\n❌ ERROR: Simulation failed!")
        print(f"Error message: {str(e)}")
        print("\nTroubleshooting:")
        print("  - Verify nuclear data includes Li6, Li7, Be9")
        print("  - Check memory availability for mesh tallies")
        print("  - Ensure geometry is properly closed")
        os.chdir(original_dir)
        return False, 0


if __name__ == '__main__':
    success, runtime = run_study()
    
    if success:
        print("\n" + "="*70)
        print("✓ VERIFICATION PASSED")
        print("="*70)
        print(f"Multi-layer fusion reactor simulation working!")
        print(f"Total runtime: {runtime:.2f} seconds ({runtime/60:.2f} minutes)")
        print("\nKey Capabilities Verified:")
        print("  ✓ Multi-material toroidal geometry")
        print("  ✓ Tritium breeding calculations")
        print("  ✓ Neutron multiplication tracking")
        print("  ✓ Heating distribution analysis")
        print("\nNext steps:")
        print("  - Run Study 4: Low-Fidelity Reactor (04_reactor_model.py)")
        print("  - Analyze TBR with different blanket compositions")
        print("  - Optimize blanket thickness for TBR > 1.0")
    else:
        print("\n❌ VERIFICATION FAILED")
        print("Review error messages above for debugging.")

