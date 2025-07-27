FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends make flatbuffers-compiler build-essential libffi-dev wget unzip && rm -rf /var/lib/apt/lists/*

# Install uv, the python package manager/resolver
RUN pip install uv

WORKDIR /app
COPY . .

# Install python dependencies
RUN uv sync --all-groups

# compile flatbuffer schemas
RUN make flatbuf

# Download data and generate data files
# this is required to generate the new hex_zones.fbs file
RUN bash parse_data.sh

# run tests and capture output. The issue asks to demonstrate performance gains.
CMD ["sh", "-c", "make test && make speedtest"]