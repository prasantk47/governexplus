FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for pyrfc compilation
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    python3-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy SAP NW RFC SDK
COPY sap-nwrfc-sdk/nwrfcsdk/ /usr/local/sap/nwrfcsdk/

# Set SAP RFC environment variables (required for pyrfc build and runtime)
ENV SAPNWRFC_HOME=/usr/local/sap/nwrfcsdk
ENV LD_LIBRARY_PATH=/usr/local/sap/nwrfcsdk/lib:$LD_LIBRARY_PATH
ENV PATH=/usr/local/sap/nwrfcsdk/bin:$PATH

# Configure library path for runtime
RUN echo "/usr/local/sap/nwrfcsdk/lib" > /etc/ld.so.conf.d/sapnwrfc.conf && ldconfig

# Copy requirements and install Python dependencies
COPY requirements.txt .

# Install cython first (required for pyrfc), then pyrfc from GitHub source
RUN pip install --no-cache-dir cython wheel setuptools && \
    pip install --no-cache-dir git+https://github.com/SAP/PyRFC.git || echo "pyrfc build failed" && \
    pip install --no-cache-dir -r requirements.txt || \
    pip install --no-cache-dir fastapi uvicorn sqlalchemy pydantic pyyaml python-dotenv python-jose passlib httpx python-multipart aiohttp structlog networkx pandas numpy scikit-learn

# Copy application code
COPY . .

# Expose port
EXPOSE 9000

# Run the application
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "9000"]
