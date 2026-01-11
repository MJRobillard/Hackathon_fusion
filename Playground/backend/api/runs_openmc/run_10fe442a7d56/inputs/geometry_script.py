"""
Example geometry script: Simple PWR-style fuel pin cell.

This script demonstrates how to create OpenMC geometry for AONP studies.
The geometry script must define a create_geometry() function that accepts
a materials dictionary and returns an openmc.Geometry object.
"""

import openmc


def create_geometry(materials_dict):
    """
    Create a simple pin cell geometry.
    
    Args:
        materials_dict: Dictionary of OpenMC materials keyed by name
        
    Returns:
        openmc.Geometry object
    
    Geometry:
        - Fuel pellet (UO2) in center
        - Moderator (water) surrounding fuel
        - Reflective boundary conditions (infinite lattice)
    """
    
    # Extract materials (assumes 'fuel' and 'moderator' are defined)
    fuel = materials_dict.get('fuel')
    moderator = materials_dict.get('moderator')
    
    if fuel is None or moderator is None:
        raise ValueError("Geometry requires 'fuel' and 'moderator' materials")
    
    # Define surfaces
    # Fuel pellet outer radius (cm)
    fuel_or = openmc.ZCylinder(r=0.39, name='fuel_outer')
    
    # Pin outer radius with reflective boundary (infinite lattice)
    pin_or = openmc.ZCylinder(r=0.63, name='pin_outer', boundary_type='reflective')
    
    # Define cells
    fuel_cell = openmc.Cell(name='fuel')
    fuel_cell.fill = fuel
    fuel_cell.region = -fuel_or
    
    moderator_cell = openmc.Cell(name='moderator')
    moderator_cell.fill = moderator
    moderator_cell.region = +fuel_or & -pin_or
    
    # Create universe and geometry
    root_universe = openmc.Universe(cells=[fuel_cell, moderator_cell])
    geometry = openmc.Geometry(root_universe)
    
    return geometry


def create_geometry_with_gap(materials_dict):
    """
    Alternative geometry with fuel-cladding gap.
    
    This is a more detailed pin cell with:
        - Fuel pellet
        - Gap (typically helium)
        - Cladding (typically Zircaloy)
        - Moderator
    """
    fuel = materials_dict['fuel']
    moderator = materials_dict['moderator']
    
    # Optional: get gap and cladding if defined
    gap = materials_dict.get('gap', moderator)  # Default to moderator if not defined
    cladding = materials_dict.get('cladding', moderator)
    
    # Define surfaces (typical PWR dimensions in cm)
    fuel_or = openmc.ZCylinder(r=0.3975)
    gap_or = openmc.ZCylinder(r=0.4095)
    clad_or = openmc.ZCylinder(r=0.4750, boundary_type='reflective')
    
    # Define cells
    fuel_cell = openmc.Cell(fill=fuel, region=-fuel_or)
    gap_cell = openmc.Cell(fill=gap, region=+fuel_or & -gap_or)
    clad_cell = openmc.Cell(fill=cladding, region=+gap_or & -clad_or)
    
    # Create geometry
    root = openmc.Universe(cells=[fuel_cell, gap_cell, clad_cell])
    geometry = openmc.Geometry(root)
    
    return geometry

