ARG PYTHON=python3
ARG PYTHON_VERSION=3.8.13

# PyTorch Binaries
ARG PT_TORCHVISION_URL=https://download.pytorch.org/whl/cpu/torchvision-0.13.1%2Bcpu-cp38-cp38-linux_x86_64.whl
ARG PT_TORCHAUDIO_URL=https://download.pytorch.org/whl/cpu/torchaudio-0.12.1%2Bcpu-cp38-cp38-linux_x86_64.whl
ARG PT_TORCHDATA_URL=https://download.pytorch.org/whl/test/torchdata-0.4.1-cp38-cp38-manylinux_2_17_x86_64.manylinux2014_x86_64.whl

FROM ubuntu:20.04

#ENV http_proxy=PROXY
#ENV https_proxy=PROXY

# No apt-get upgrade: focal is out of standard support, so its security
# pocket can stop serving a package while still advertising it, and the
# upgrade then fails with a 404. The same line broke the NLP API's build on a
# clean runner. Installing only what is needed keeps that surface small.
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3-pip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

WORKDIR /app

COPY app /app

COPY requirements.txt /app

RUN pip install -r /app/requirements.txt

EXPOSE 8080

CMD exec uvicorn main:app --port 8080 --host 0.0.0.0
