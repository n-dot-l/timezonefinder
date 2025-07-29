# Use a more recent Debian release (Bookworm, Debian 12) to ensure active repositories
FROM python:3.11-slim-bookworm

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies required for building C extensions (like gcc, make)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy all project files into the container.
# This step is crucial before installation because the project contains C source files
# that need to be compiled as part of the 'pip install .' process.
COPY . /app

# Install the project in editable mode and its 'test' dependencies.
# This command automatically uses pyproject.toml to install required packages
# and builds the C extensions.
RUN pip install --no-cache-dir .[test]

# Define the default command to run when the container starts.
# This will execute the tests using pytest.
CMD ["python", "-m", "pytest"]