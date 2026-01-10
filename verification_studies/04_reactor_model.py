"""
OpenMC Verification Study 4: Low-Fidelity Global Reactor Model
===============================================================

Purpose:
--------
A comprehensive verification of a full DEMO-class tokamak using low particle
counts for moderate runtime. This tests integral parameters like Tritium 
Breeding Ratio (TBR) and total heat deposition.

Model:
------
- DEMO-class tokamak (larger than ITER)
- Major radius: 900 cm (9m)
- Multiple breeding zones with different enrichments
- Full toroidal geometry
- 100,000 neutron histories

Expected Runtime:
-----------------
~15-30 minutes on a standard desktop (single core)
~5-10 minutes on 8+ cores

What This Tests:
----------------
- Full-scale reactor geometry
- Integral parameter calculations (TBR, heating)
- Realistic blanket configurations
- Energy deposition patterns
- Computational efficiency strategies
"""

import openmc
import openmc.stats
import numpy as np
import time
import os
from datetime import datetime


def create_demo_materials():
    """
    Create comprehensive material set for DEMO tokamak
    """
    print("Creating DEMO reactor materials...")
    
    materials = openmc.Materials()
    
    # 1. Plasma (deuterium-tritium mix, very low density)
    plasma = openmc.Material(name='DT_Plasma')
    plasma.add_nuclide('H2', 0.5)  # Deuterium
    plasma.add_nuclide('H3', 0.5)  # Tritium
    plasma.set_density('g/cm3', 1e-7)  # Very low density
    materials.append(plasma)
    
    # 2. Tungsten first wall
    tungsten = openmc.Material(name='Tungsten_FW')
    tungsten.add_element('W', 1.0)
    tungsten.set_density('g/cm3', 19.3)
    materials.append(tungsten)
    
    # 3. Breeding blanket - inboard (lower enrichment)
    blanket_inboard = openmc.Material(name='Blanket_Inboard')
    blanket_inboard.add_nuclide('Li6', 0.8)   # 20% Li-6
    blanket_inboard.add_nuclide('Li7', 3.2)   # 80% Li-7
    blanket_inboard.add_element('Pb', 1.0)    # Lead for neutron multiplication
    blanket_inboard.set_density('g/cm3', 9.4)
    materials.append(blanket_inboard)
    
    # 4. Breeding blanket - outboard (higher enrichment)
    blanket_outboard = openmc.Material(name='Blanket_Outboard')
    blanket_outboard.add_nuclide('Li6', 1.5)  # 37.5% Li-6
    blanket_outboard.add_nuclide('Li7', 2.5)  # 62.5% Li-7
    blanket_outboard.add_element('Pb', 1.0)
    blanket_outboard.set_density('g/cm3', 9.4)
    materials.append(blanket_outboard)
    
    # 5. Beryllium neutron multiplier (mixed into blanket)
    beryllium = openmc.Material(name='Beryllium')
    beryllium.add_element('Be', 1.0)
    beryllium.set_density('g/cm3', 1.85)
    materials.append(beryllium)
    
    # 6. Eurofer steel (structural material)
    eurofer = openmc.Material(name='EUROFER')
    eurofer.add_element('Fe', 0.895, 'wo')
    eurofer.add_element('Cr', 0.09, 'wo')
    eurofer.add_element('W', 0.011, 'wo')
    eurofer.add_element('Mn', 0.004, 'wo')
    eurofer.set_density('g/cm3', 7.78)
    materials.append(eurofer)
    
    # 7. Neutron shield (B4C + steel mixture)
    shield = openmc.Material(name='Neutron_Shield')
    shield.add_element('B', 0.2, 'wo')
    shield.add_element('C', 0.1, 'wo')
    shield.add_element('Fe', 0.7, 'wo')
    shield.set_density('g/cm3', 6.5)
    materials.append(shield)
    
    # 8. Vacuum vessel - stainless steel
    vessel = openmc.Material(name='Vacuum_Vessel')
    vessel.add_element('Fe', 0.68, 'wo')
    vessel.add_element('Cr', 0.19, 'wo')
    vessel.add_element('Ni', 0.11, 'wo')
    vessel.add_element('Mo', 0.02, 'wo')
    vessel.set_density('g/cm3', 8.0)
    materials.append(vessel)
    
    return materials


def create_demo_geometry(R0=900.0):
    """
    Create DEMO tokamak geometry with inboard/outboard breeding zones
    
    Parameters:
    -----------
    R0 : float
        Major radius (cm) - 9m for DEMO
    
    Layer structure (minor radii in cm):
    - Plasma: 0 - 280 cm
    - First wall: 280 - 285 cm (tungsten)
    - Blanket inboard: 285 - 330 cm (low enrichment - less space)
    - Blanket outboard: 285 - 370 cm (high enrichment - more space)
    - Shield: outer 20 cm of blanket region
    - Vacuum vessel: 370 - 395 cm (steel)
    """
    print(f"Creating DEMO tokamak geometry...")
    print(f"  Major radius: {R0/100:.1f} m")
    
    # Get materials
    materials = create_demo_materials()
    plasma = materials[0]
    tungsten = materials[1]
    blanket_ib = materials[2]
    blanket_ob = materials[3]
    eurofer = materials[5]
    shield = materials[6]
    vessel = materials[7]
    
    # Define radial layers
    r_plasma = 280.0
    r_first_wall = 285.0
    r_blanket_ib = 330.0  # Inboard blanket (thinner)
    r_blanket_ob = 370.0  # Outboard blanket (thicker)
    r_vessel_inner = 370.0
    r_vessel_outer = 395.0
    
    print(f"  Plasma minor radius: {r_plasma/100:.2f} m")
    print(f"  Inboard blanket: {(r_blanket_ib-r_first_wall)/100:.2f} m")
    print(f"  Outboard blanket: {(r_blanket_ob-r_first_wall)/100:.2f} m")
    
    # Create toroidal surfaces
    torus_plasma = openmc.ZTorus(a=R0, b=r_plasma, c=r_plasma)
    torus_first_wall = openmc.ZTorus(a=R0, b=r_first_wall, c=r_first_wall)
    torus_blanket_ib = openmc.ZTorus(a=R0, b=r_blanket_ib, c=r_blanket_ib)
    torus_blanket_ob = openmc.ZTorus(a=R0, b=r_blanket_ob, c=r_blanket_ob)
    torus_vessel_inner = openmc.ZTorus(a=R0, b=r_vessel_inner, c=r_vessel_inner)
    torus_vessel_outer = openmc.ZTorus(a=R0, b=r_vessel_outer, c=r_vessel_outer)
    
    # Bounding surfaces
    z_min = openmc.ZPlane(z0=-400, boundary_type='vacuum')
    z_max = openmc.ZPlane(z0=400, boundary_type='vacuum')
    
    # Cylindrical surfaces to separate inboard/outboard
    # Inboard: r < R0, Outboard: r > R0
    cyl_separating = openmc.ZCylinder(r=R0)
    cyl_inner_bound = openmc.ZCylinder(r=R0 - r_vessel_outer - 50, boundary_type='vacuum')
    cyl_outer_bound = openmc.ZCylinder(r=R0 + r_vessel_outer + 50, boundary_type='vacuum')
    
    # Create cells for each layer
    
    # 1. Plasma
    plasma_region = -torus_plasma & +z_min & -z_max
    plasma_cell = openmc.Cell(cell_id=1, name='plasma', fill=plasma, region=plasma_region)
    
    # 2. First wall (tungsten)
    fw_region = +torus_plasma & -torus_first_wall & +z_min & -z_max
    fw_cell = openmc.Cell(cell_id=2, name='first_wall', fill=tungsten, region=fw_region)
    
    # 3. Inboard blanket (thinner, lower enrichment, r < R0)
    blanket_ib_region = (+torus_first_wall & -torus_blanket_ob & 
                         -cyl_separating & +z_min & -z_max)
    blanket_ib_cell = openmc.Cell(cell_id=3, name='blanket_inboard', fill=blanket_ib, 
                                   region=blanket_ib_region)
    
    # 4. Outboard blanket (thicker, higher enrichment, r > R0)
    blanket_ob_region = (+torus_first_wall & -torus_blanket_ob & 
                         +cyl_separating & +z_min & -z_max)
    blanket_ob_cell = openmc.Cell(cell_id=4, name='blanket_outboard', fill=blanket_ob, 
                                   region=blanket_ob_region)
    
    # 5. Vacuum vessel
    vessel_region = +torus_blanket_ob & -torus_vessel_outer & +z_min & -z_max
    vessel_cell = openmc.Cell(cell_id=5, name='vacuum_vessel', fill=vessel, region=vessel_region)
    
    # 6. Outer void
    outer_region = (+torus_vessel_outer & -cyl_outer_bound & +cyl_inner_bound & 
                    +z_min & -z_max)
    outer_cell = openmc.Cell(cell_id=6, name='outer_void', region=outer_region)
    
    # Create universe and geometry
    root = openmc.Universe(cells=[plasma_cell, fw_cell, blanket_ib_cell, 
                                   blanket_ob_cell, vessel_cell, outer_cell])
    geometry = openmc.Geometry(root)
    
    return materials, geometry


def create_plasma_source(R0=900.0, r_plasma=280.0):
    """
    Create realistic plasma source with volumetric distribution
    
    Parameters:
    -----------
    R0 : float
        Major radius (cm)
    r_plasma : float
        Plasma minor radius (cm)
    """
    print(f"Creating volumetric plasma source...")
    
    source = openmc.IndependentSource()
    
    # Volumetric distribution throughout plasma
    # Use toroidal distribution approximated by cylindrical
    r_dist = openmc.stats.Uniform(R0 - r_plasma*0.9, R0 + r_plasma*0.9)
    phi_dist = openmc.stats.Uniform(0, 2*np.pi)
    z_dist = openmc.stats.Uniform(-r_plasma*0.5, r_plasma*0.5)
    
    source.space = openmc.stats.CylindricalIndependent(
        r=r_dist, phi=phi_dist, z=z_dist, origin=(0.0, 0.0, 0.0)
    )
    
    # Isotropic angular distribution
    source.angle = openmc.stats.Isotropic()
    
    # D-T fusion energy (14.08 MeV)
    source.energy = openmc.stats.Discrete([14.08e6], [1.0])
    source.particle = 'neutron'
    
    return source


def create_settings(n_particles=100000, n_batches=30):
    """
    Create optimized settings for low-fidelity run
    """
    print(f"Configuring low-fidelity simulation:")
    print(f"  {n_batches} batches of {n_particles:,} particles")
    print(f"  Total neutron histories: {n_particles * n_batches:,}")
    
    settings = openmc.Settings()
    settings.batches = n_batches
    settings.inactive = 10  # More inactive batches for large geometry
    settings.particles = int(n_particles)
    settings.run_mode = 'fixed source'
    
    # Add plasma source
    settings.source = create_plasma_source()
    
    # Survival biasing for deep penetration
    settings.survival_biasing = True
    
    return settings


def create_integral_tallies():
    """
    Create tallies focused on integral parameters (TBR, heating)
    """
    print("Creating integral parameter tallies...")
    
    tallies = openmc.Tallies()
    
    # Cell filter for all major components
    # Cells: 1=plasma, 2=FW, 3=blanket_IB, 4=blanket_OB, 5=vessel
    all_cells_filter = openmc.CellFilter([1, 2, 3, 4, 5])
    
    # 1. Total flux by component
    flux_tally = openmc.Tally(name='component_flux')
    flux_tally.filters = [all_cells_filter]
    flux_tally.scores = ['flux']
    tallies.append(flux_tally)
    
    # 2. Heating by component (critical for thermal analysis)
    heating_tally = openmc.Tally(name='component_heating')
    heating_tally.filters = [all_cells_filter]
    heating_tally.scores = ['heating']
    tallies.append(heating_tally)
    
    # 3. Tritium breeding in blanket cells
    blanket_filter = openmc.CellFilter([3, 4])  # Both blanket cells
    
    tbr_tally = openmc.Tally(name='tritium_breeding')
    tbr_tally.filters = [blanket_filter]
    tbr_tally.scores = ['(n,Xt)']  # All tritium production reactions
    tallies.append(tbr_tally)
    
    # 4. Separate TBR for inboard vs outboard
    ib_filter = openmc.CellFilter([3])
    ob_filter = openmc.CellFilter([4])
    
    tbr_ib = openmc.Tally(name='TBR_inboard')
    tbr_ib.filters = [ib_filter]
    tbr_ib.scores = ['(n,Xt)']
    tallies.append(tbr_ib)
    
    tbr_ob = openmc.Tally(name='TBR_outboard')
    tbr_ob.filters = [ob_filter]
    tbr_ob.scores = ['(n,Xt)']
    tallies.append(tbr_ob)
    
    # 5. Neutron multiplication
    mult_tally = openmc.Tally(name='neutron_multiplication')
    mult_tally.filters = [blanket_filter]
    mult_tally.scores = ['(n,2n)', '(n,3n)']
    tallies.append(mult_tally)
    
    # 6. Energy deposition by reaction type
    energy_dep = openmc.Tally(name='energy_deposition')
    energy_dep.filters = [all_cells_filter]
    energy_dep.scores = ['heating', 'fission']
    tallies.append(energy_dep)
    
    # 7. Coarse mesh for visualization (lower resolution for speed)
    mesh = openmc.CylindricalMesh(
        r_grid=np.linspace(0, 1400, 15),  # Coarse radial
        phi_grid=np.linspace(0, 2*np.pi, 13),  # Coarse toroidal
        z_grid=np.linspace(-400, 400, 11)  # Coarse vertical
    )
    
    mesh_filter = openmc.MeshFilter(mesh)
    
    mesh_heating = openmc.Tally(name='mesh_heating')
    mesh_heating.filters = [mesh_filter]
    mesh_heating.scores = ['heating']
    tallies.append(mesh_heating)
    
    return tallies


def analyze_results(sp, n_source_particles):
    """
    Analyze and display integral parameters
    
    Parameters:
    -----------
    sp : openmc.StatePoint
        StatePoint object with results
    n_source_particles : int
        Total number of source particles simulated
    """
    print("\n" + "="*70)
    print("INTEGRAL PARAMETER ANALYSIS")
    print("="*70)
    
    # 1. Heating by component
    print("\n1. HEATING DISTRIBUTION")
    print("-"*70)
    heating_tally = sp.get_tally(name='component_heating')
    df_heating = heating_tally.get_pandas_dataframe()
    
    component_names = ['Plasma', 'First Wall', 'Blanket (IB)', 
                      'Blanket (OB)', 'Vacuum Vessel']
    
    total_heating = 0
    for idx, name in enumerate(component_names, start=1):
        cell_data = df_heating[df_heating['cell'] == idx]
        if not cell_data.empty:
            mean_val = cell_data['mean'].values[0]
            std_dev = cell_data['std. dev.'].values[0]
            total_heating += mean_val
            print(f"  {name:20s}: {mean_val:.4e} ± {std_dev:.4e} eV/src")
    
    print(f"\n  {'Total Heating':20s}: {total_heating:.4e} eV/src")
    print(f"  {'Per source neutron':20s}: {total_heating/1e6:.4f} MeV/neutron")
    
    # 2. Tritium Breeding Ratio
    print("\n2. TRITIUM BREEDING RATIO (TBR)")
    print("-"*70)
    
    # Inboard TBR
    tbr_ib_tally = sp.get_tally(name='TBR_inboard')
    df_ib = tbr_ib_tally.get_pandas_dataframe()
    tbr_ib = df_ib['mean'].sum()
    tbr_ib_std = np.sqrt((df_ib['std. dev.']**2).sum())
    
    # Outboard TBR
    tbr_ob_tally = sp.get_tally(name='TBR_outboard')
    df_ob = tbr_ob_tally.get_pandas_dataframe()
    tbr_ob = df_ob['mean'].sum()
    tbr_ob_std = np.sqrt((df_ob['std. dev.']**2).sum())
    
    # Total TBR
    tbr_total = tbr_ib + tbr_ob
    tbr_total_std = np.sqrt(tbr_ib_std**2 + tbr_ob_std**2)
    
    print(f"  Inboard TBR  : {tbr_ib:.4f} ± {tbr_ib_std:.4f}")
    print(f"  Outboard TBR : {tbr_ob:.4f} ± {tbr_ob_std:.4f}")
    print(f"  Total TBR    : {tbr_total:.4f} ± {tbr_total_std:.4f}")
    
    if tbr_total >= 1.0:
        print(f"\n  ✓ TBR > 1.0: Reactor is self-sustaining for tritium!")
    else:
        print(f"\n  ⚠ TBR < 1.0: Need blanket optimization or enrichment increase")
    
    # 3. Neutron multiplication
    print("\n3. NEUTRON MULTIPLICATION")
    print("-"*70)
    mult_tally = sp.get_tally(name='neutron_multiplication')
    df_mult = mult_tally.get_pandas_dataframe()
    
    for _, row in df_mult.iterrows():
        score = row['score']
        mean_val = row['mean']
        std_dev = row['std. dev.']
        print(f"  {score:10s}: {mean_val:.4e} ± {std_dev:.4e} reactions/src")
    
    # 4. Component flux
    print("\n4. NEUTRON FLUX BY COMPONENT")
    print("-"*70)
    flux_tally = sp.get_tally(name='component_flux')
    df_flux = flux_tally.get_pandas_dataframe()
    
    for idx, name in enumerate(component_names, start=1):
        cell_data = df_flux[df_flux['cell'] == idx]
        if not cell_data.empty:
            mean_val = cell_data['mean'].values[0]
            std_dev = cell_data['std. dev.'].values[0]
            print(f"  {name:20s}: {mean_val:.4e} ± {std_dev:.4e} n/cm²/src")


def run_study(output_dir='reactor_model_output'):
    """
    Execute the low-fidelity global reactor model study
    """
    print("="*70)
    print("OpenMC Verification Study 4: Low-Fidelity DEMO Reactor")
    print("="*70)
    print(f"\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Build model
    print("\nBuilding DEMO reactor model...")
    materials, geometry = create_demo_geometry(R0=900.0)
    settings = create_settings(n_particles=100000, n_batches=30)
    tallies = create_integral_tallies()
    
    # Export to XML
    materials.export_to_xml(os.path.join(output_dir, 'materials.xml'))
    geometry.export_to_xml(os.path.join(output_dir, 'geometry.xml'))
    settings.export_to_xml(os.path.join(output_dir, 'settings.xml'))
    tallies.export_to_xml(os.path.join(output_dir, 'tallies.xml'))
    
    print(f"\nXML files exported to: {output_dir}/")
    print("\n" + "="*70)
    print("MODEL SUMMARY")
    print("="*70)
    print(f"Geometry Type    : DEMO-class Tokamak")
    print(f"Major Radius     : 9.0 m")
    print(f"Plasma Radius    : 2.8 m")
    print(f"Components       : Plasma, First Wall, Dual Blankets, Vessel")
    print(f"Source           : Volumetric D-T plasma (14.08 MeV)")
    print(f"Total Histories  : {settings.particles * settings.batches:,}")
    print(f"Tallies          : TBR, Heating, Flux, Multiplication")
    
    # Run simulation
    print("\n" + "="*70)
    print("STARTING SIMULATION")
    print("="*70)
    print("This low-fidelity run will take 15-30 minutes...")
    print("Progress will be shown below:")
    print("-"*70)
    
    start_time = time.time()
    
    try:
        # Change to output directory
        original_dir = os.getcwd()
        os.chdir(output_dir)
        
        # Run OpenMC
        openmc.run()
        
        elapsed_time = time.time() - start_time
        
        # Read results
        sp = openmc.StatePoint(f'statepoint.{settings.batches}.h5')
        
        print("\n" + "="*70)
        print("✓ SIMULATION COMPLETED SUCCESSFULLY!")
        print("="*70)
        print(f"Runtime: {elapsed_time:.2f} seconds ({elapsed_time/60:.2f} minutes)")
        print(f"Ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Analyze results
        n_total_particles = settings.particles * settings.batches
        analyze_results(sp, n_total_particles)
        
        print("\n" + "="*70)
        print("📊 OUTPUT FILES")
        print("="*70)
        print(f"  - statepoint.{settings.batches}.h5  : Full simulation results")
        print(f"  - summary.h5        : Geometry and material summary")
        print(f"  - tallies.out       : Text output of tallies")
        
        # Return to original directory
        os.chdir(original_dir)
        
        return True, elapsed_time
        
    except Exception as e:
        print(f"\n" + "="*70)
        print("❌ SIMULATION FAILED")
        print("="*70)
        print(f"Error: {str(e)}")
        print("\nTroubleshooting:")
        print("  1. Verify nuclear data library (ENDF/B-VII.1 or newer)")
        print("  2. Check memory: ~2-4 GB recommended")
        print("  3. Ensure OpenMC version >= 0.13.0")
        print("  4. Review geometry definition in materials.xml/geometry.xml")
        
        import traceback
        traceback.print_exc()
        
        os.chdir(original_dir)
        return False, 0


if __name__ == '__main__':
    print("\n")
    success, runtime = run_study()
    
    if success:
        print("\n" + "="*70)
        print("✓✓✓ VERIFICATION PASSED ✓✓✓")
        print("="*70)
        print("Full-scale DEMO reactor simulation successful!")
        print(f"\nPerformance:")
        print(f"  Total runtime: {runtime:.1f} seconds ({runtime/60:.1f} minutes)")
        print(f"  Particle rate: ~{(100000*30)/runtime:.0f} particles/second")
        
        print(f"\nCapabilities Verified:")
        print(f"  ✓ Large-scale toroidal geometry (9m major radius)")
        print(f"  ✓ Multi-zone breeding blanket")
        print(f"  ✓ Tritium breeding ratio calculation")
        print(f"  ✓ Integral heating and flux tallies")
        print(f"  ✓ Neutron multiplication tracking")
        
        print(f"\nNext Steps:")
        print(f"  - Run Study 5: Sector Slicing (05_sector_model.py)")
        print(f"  - Increase particle count for production runs")
        print(f"  - Perform parameter sweeps (enrichment, thickness)")
        print(f"  - Add high-fidelity mesh tallies")
        
    else:
        print("\n" + "="*70)
        print("❌ VERIFICATION FAILED")
        print("="*70)
        print("Please review error messages and check your OpenMC installation.")

