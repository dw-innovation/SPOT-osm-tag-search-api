FROM python:3.11-slim-bookworm

#ENV http_proxy=PROXY
#ENV https_proxy=PROXY

# No apt layer: the official Python image already ships pip, and every
# dependency installs from a prebuilt wheel.
RUN pip install --upgrade pip

WORKDIR /app

COPY app /app

COPY requirements.txt /app

RUN pip install -r /app/requirements.txt

EXPOSE 8080

CMD exec uvicorn main:app --port 8080 --host 0.0.0.0
