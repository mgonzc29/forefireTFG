FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Habilitar universe para algunos paquetes (opcional)
RUN apt-get update && apt-get install -y software-properties-common \
    && add-apt-repository universe \
    && apt-get update

# Instalar dependencias del sistema
RUN apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    build-essential \
    cmake \
    git \
    libnetcdf-dev \
    libnetcdf-c++4-dev \
    netcdf-bin \
    # libgdal-dev \
    # gdal-bin \
    && rm -rf /var/lib/apt/lists/*

# Dependencias Python
RUN pip3 install --upgrade pip \
    && pip3 install pybind11 numpy matplotlib setuptools wheel

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt 

# Variable de entorno para NetCDF
ENV NETCDF_HOME=/usr
