FROM python:3.12-slim-bookworm

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    clang \
    libffi-dev \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

COPY . .

# Install dependencies and the project in editable mode
# This is necessary to run scripts that depend on the package,
# and ensures that the C-extensions are built.
RUN pip install --no-cache-dir -e .[test,numba,pytz]

# Download and generate timezone data files
# This creates the necessary .fbs and .npy files in timezonefinder/data
RUN ./parse_data.sh