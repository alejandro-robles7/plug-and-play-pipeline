# Build an image that can do training and inference in SageMaker
# This is a Python 3.8 image that uses the nginx, gunicorn, flask stack
# for serving inferences in a stable way.

FROM public.ecr.aws/bitnami/python:3.7

RUN apt-get update -y && apt-get install -y libev-dev nginx \
    && apt-get clean \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=TRUE
ENV PYTHONDONTWRITEBYTECODE=TRUE
ENV PATH="/opt/program:${PATH}"

RUN mkdir -p /opt/program
RUN mkdir -p /opt/ml
RUN mkdir -p /opt/ml/model

COPY ml_service/app.py /opt/program
COPY ml_service/server.py /opt/program
COPY ml_service/wsgi.py /opt/program
COPY ml_service/nginx.conf /opt/program
COPY requirements.txt /opt/program

RUN mkdir -p /opt/model_code
COPY model/model.py /opt/model_code
COPY model/model_random.py /opt/model_code

RUN pip install -r /opt/program/requirements.txt

EXPOSE 8080
WORKDIR /opt/program
ENTRYPOINT ["python", "app.py"]
