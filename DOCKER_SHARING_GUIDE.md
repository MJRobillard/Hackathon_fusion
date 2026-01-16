# Docker Sharing Guide

This guide explains how to share your Docker setup with others or download it for deployment.

## Option 1: Share the Repository (Recommended - Easiest)

The simplest way is to share the entire project repository. The recipient can then build everything from source.

### Steps:

1. **Share the repository:**
   ```bash
   # If using Git, push to a repository
   git push origin main
   
   # Or create a zip/tarball
   # On Windows (PowerShell):
   Compress-Archive -Path . -DestinationPath hackathon-fusion.zip -Exclude @('node_modules', '.git', '__pycache__', '*.pyc', '.next')
   
   # On Linux/WSL:
   tar -czf hackathon-fusion.tar.gz --exclude='node_modules' --exclude='.git' --exclude='__pycache__' --exclude='.next' .
   ```

2. **Recipient setup:**
   ```bash
   # Clone or extract the project
   git clone <your-repo-url>
   # OR extract the zip/tar file
   
   # Navigate to project root
   cd Hackathon_fusion
   
   # Build and run
   docker compose up --build
   ```

**Note:** The recipient will need:
- Docker and Docker Compose installed
- The `nuclear_data` directory (if you want to include it, it's large - ~GB)
- Optional: `.env` file with API keys

---

## Option 2: Export Docker Images (Pre-built Images)

If you want to share pre-built Docker images (faster for recipient, but larger files):

### Export Images:

```bash
# First, build your images
docker compose build

# Export backend image
docker save hackathon_fusion-backend:latest -o backend-image.tar

# Export frontend image  
docker save hackathon_fusion-frontend:latest -o frontend-image.tar

# Note: mongo and ollama use public images, so recipient can pull them
```

### Share the Files:

```bash
# Compress the images (they're large)
# On Windows:
Compress-Archive -Path backend-image.tar,frontend-image.tar -DestinationPath docker-images.zip

# On Linux/WSL:
tar -czf docker-images.tar.gz backend-image.tar frontend-image.tar
```

### Recipient Setup:

```bash
# Extract images
# On Windows:
Expand-Archive docker-images.zip
# On Linux:
tar -xzf docker-images.tar.gz

# Load images
docker load -i backend-image.tar
docker load -i frontend-image.tar

# Update docker-compose.yml to use loaded images instead of building
# Change from:
#   build:
#     context: .
#     dockerfile: Playground/backend/Dockerfile
# To:
#   image: hackathon_fusion-backend:latest

# Then run
docker compose up
```

---

## Option 3: Push to Docker Hub (Cloud Registry)

Share images via Docker Hub (requires free account):

### Push Images:

```bash
# Tag your images
docker tag hackathon_fusion-backend:latest yourusername/hackathon-fusion-backend:latest
docker tag hackathon_fusion-frontend:latest yourusername/hackathon-fusion-frontend:latest

# Login to Docker Hub
docker login

# Push images
docker push yourusername/hackathon-fusion-backend:latest
docker push yourusername/hackathon-fusion-frontend:latest
```

### Update docker-compose.yml for Recipient:

Create a `docker-compose.public.yml` file:

```yaml
services:
  mongo:
    image: mongo:7
    # ... same as before

  ollama:
    image: ollama/ollama:latest
    # ... same as before

  backend:
    image: yourusername/hackathon-fusion-backend:latest  # Changed from build
    # ... rest same

  frontend:
    image: yourusername/hackathon-fusion-frontend:latest  # Changed from build
    # ... rest same
```

### Recipient Setup:

```bash
# Pull and run
docker compose -f docker-compose.public.yml pull
docker compose -f docker-compose.public.yml up
```

---

## Option 4: Create Deployment Package

Bundle everything needed for deployment:

### Create Package Script:

```bash
# create-deployment-package.sh
#!/bin/bash

PACKAGE_NAME="hackathon-fusion-deployment"
mkdir -p $PACKAGE_NAME

# Copy essential files
cp docker-compose.yml $PACKAGE_NAME/
cp -r Playground/backend/Dockerfile $PACKAGE_NAME/backend.Dockerfile
cp -r frontend/Dockerfile $PACKAGE_NAME/frontend.Dockerfile
cp -r Playground/backend $PACKAGE_NAME/
cp -r frontend $PACKAGE_NAME/
cp requirements.txt $PACKAGE_NAME/ 2>/dev/null || true
cp pyproject.toml $PACKAGE_NAME/ 2>/dev/null || true

# Create README for recipient
cat > $PACKAGE_NAME/README.md << 'EOF'
# Hackathon Fusion - Deployment Package

## Quick Start

1. Install Docker and Docker Compose
2. Run: `docker compose up --build`
3. Access:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - MongoDB: localhost:27017

## Optional: Environment Variables

Create `.env` file:
```
FIREWORKS=your_key_here
VOYAGE_API_KEY=your_key_here
```

## Note on Nuclear Data

The `nuclear_data` directory is large (~GB). If not included:
- Download from: [OpenMC Nuclear Data](https://openmc.org/official-data-libraries/)
- Extract to `nuclear_data/endfb-vii.1-hdf5/`
EOF

# Create archive
tar -czf ${PACKAGE_NAME}.tar.gz $PACKAGE_NAME/
echo "Created ${PACKAGE_NAME}.tar.gz"
```

---

## Recommended Approach

**For most cases, use Option 1 (Share Repository):**
- ✅ Simplest for recipient
- ✅ Always up-to-date with code
- ✅ Standard practice
- ✅ Works with version control

**Use Option 2 (Export Images) if:**
- Recipient has slow internet (pre-built images)
- You want to share exact build state
- Recipient doesn't have build tools

**Use Option 3 (Docker Hub) if:**
- You want to share publicly or with many people
- You want version control for images
- Recipient has good internet connection

---

## Important Notes

1. **Nuclear Data**: The `nuclear_data` directory is very large (several GB). Consider:
   - Excluding it from the package
   - Sharing via cloud storage (Google Drive, Dropbox, etc.)
   - Or letting recipient download from OpenMC official sources

2. **Environment Variables**: Don't commit `.env` files with real API keys. Share a `.env.example` instead.

3. **Image Sizes**: Docker images can be 1-5GB each. Compress them before sharing.

4. **Docker Compose Version**: Make sure recipient has compatible Docker Compose version (v2+ uses `docker compose`, v1 uses `docker-compose`).
