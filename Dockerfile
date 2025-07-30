# Use a specific Python 3.12 version for reproducibility, based on CI config
FROM python:3.12-slim

# Set environment variables to prevent generating .pyc files, for unbuffered output,
# and to force the use of the clang compiler for the C extension.
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV CC=clang

# Install system dependencies required for building the CFFI extension.
# build-essential: Provides make, etc.
# libffi-dev: Required by CFFI.
# clang: A test requires the extension to be built with this compiler.
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential libffi-dev clang && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the project files (respecting .dockerignore for a clean context)
COPY . .

# Install the project and its testing dependencies. We install them manually
# because the project uses [dependency-groups] which is not a standard for pip extras.
# 'setuptools' and 'wheel' are needed for tests that build packages.
# 'pytest', 'pytz', and 'numba' are needed to run the full test suite.
RUN pip install --no-cache-dir . \
    pytest \
    "pytz>=2022.7.1" \
    "setuptools>=61" \
    "wheel" \
    "numba>=0.59,<1"

# Set the default command to run the test suite.
CMD ["pytest", "tests"]