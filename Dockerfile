FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy SAP NW RFC SDK (you need to download this from SAP)
# Place the extracted SDK in ./sap-nwrfc-sdk/ folder
COPY sap-nwrfc-sdk/ /usr/local/sap/nwrfcsdk/

# Set SAP RFC environment variables
ENV SAPNWRFC_HOME=/usr/local/sap/nwrfcsdk
ENV LD_LIBRARY_PATH=/usr/local/sap/nwrfcsdk/lib:$LD_LIBRARY_PATH

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt || \
    pip install --no-cache-dir fastapi uvicorn sqlalchemy pydantic pyyaml python-dotenv python-jose passlib httpx python-multipart aiohttp structlog networkx pandas numpy scikit-learn

# Copy application code
COPY . .

# Expose port
EXPOSE 9000

# Run the application
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "9000"]
