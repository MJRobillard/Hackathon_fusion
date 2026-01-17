FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        ca-certificates \
        bzip2 \
        cmake \
        libhdf5-dev \
        pkg-config \
        gfortran \
    && rm -rf /var/lib/apt/lists/*

# Install OpenMC via conda-forge (pip doesn't reliably provide OpenMC wheels)
ENV MAMBA_ROOT_PREFIX=/opt/micromamba
RUN curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest \
    | tar -xj -C /usr/local/bin/ --strip-components=1 bin/micromamba
RUN micromamba create -y -n app -c conda-forge python=3.11 openmc pip \
    && micromamba clean -a -y
ENV PATH=/opt/micromamba/envs/app/bin:$PATH

# Install dependencies first
COPY Playground/backend/api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt && \
    pip install --no-cache-dir openmc_data_downloader

# Verify uvicorn installation with both python and python3
RUN python -c "import uvicorn; print(f'✓ uvicorn {uvicorn.__version__} installed (python)')" && \
    python3 -c "import uvicorn; print(f'✓ uvicorn {uvicorn.__version__} installed (python3)')" || \
    (echo "❌ uvicorn installation failed" && pip install --no-cache-dir uvicorn[standard]==0.27.0 && \
     python -c "import uvicorn; print(f'✓ uvicorn {uvicorn.__version__} installed (fallback)')" && \
     python3 -c "import uvicorn; print(f'✓ uvicorn {uvicorn.__version__} installed (python3 fallback)')")

# Copy application code
COPY . /app

# Final verification that uvicorn is accessible with python3 (what we'll use in CMD)
RUN python3 -c "import sys; import uvicorn; print(f'✓ uvicorn {uvicorn.__version__} verified in {sys.executable}')" || \
    (echo "❌ uvicorn verification failed after COPY" && pip install --no-cache-dir uvicorn[standard]==0.27.0 && \
     python3 -c "import uvicorn; print(f'✓ uvicorn {uvicorn.__version__} reinstalled')")

# Verify OpenMC installation
RUN python -c "import openmc; print(f'✓ openmc {openmc.__version__} verified')"

EXPOSE 8000

ENV API_HOST=0.0.0.0 \
    API_PORT=8000

# Use python3 (matches final verification and script shebang)
CMD ["python", "Playground/backend/start_server.py"]
