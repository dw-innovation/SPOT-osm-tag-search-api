FROM python:3.11-slim-bookworm

#ENV http_proxy=PROXY
#ENV https_proxy=PROXY

# No apt layer: the official Python image already ships pip, and every
# dependency installs from a prebuilt wheel.
RUN pip install --no-cache-dir --upgrade pip

# CPU-only PyTorch, installed before the requirements so that pip does not
# pull the default Linux wheel: that one bundles the NVIDIA CUDA libraries,
# several gigabytes the service never uses, since it runs on CPU.
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch torchvision

WORKDIR /app

COPY app /app

COPY requirements.txt /app

RUN pip install --no-cache-dir -r /app/requirements.txt

EXPOSE 8080

CMD exec uvicorn main:app --port 8080 --host 0.0.0.0
