# Quick fix script
cat > fix_material_ids.py << 'EOF'
with open('aonp/core/bundler.py', 'r') as f:
    content = f.read()

# Fix 1: Add ID counter for materials.xml generation
old1 = '''    materials = openmc.Materials()

    for mat_name, mat_spec in study.materials.items():
        mat = openmc.Material(name=mat_name)'''

new1 = '''    materials = openmc.Materials()

    mat_id = 1
    for mat_name, mat_spec in study.materials.items():
        mat = openmc.Material(material_id=mat_id, name=mat_name)
        mat_id += 1'''

# Fix 2: Add ID counter for geometry materials
old2 = '''    # Create OpenMC materials for geometry script
    materials_dict = {}
    for mat_name, mat_spec in study.materials.items():
        mat = openmc.Material(name=mat_name)'''

new2 = '''    # Create OpenMC materials for geometry script
    materials_dict = {}
    mat_id = 1
    for mat_name, mat_spec in study.materials.items():
        mat = openmc.Material(material_id=mat_id, name=mat_name)
        mat_id += 1'''

content = content.replace(old1, new1).replace(old2, new2)

with open('aonp/core/bundler.py', 'w') as f:
    f.write(content)
    
print("Fixed material ID assignments!")
