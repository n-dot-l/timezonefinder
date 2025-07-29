FROM python:3.12-slim-bookworm

WORKDIR /app

# Install system dependencies needed for building the C extension (cffi)
# clang and libffi-dev are required for building the wheel.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    clang \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire project context.
# This is needed because the build process (pip install .) requires access
# to source files like `timezonefinder/build.py` and the C extension code.
COPY . .

# Install the project with all optional dependencies for testing.
RUN pip install --no-cache-dir .[test,numba,pytz]