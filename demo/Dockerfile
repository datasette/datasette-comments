FROM python:3.11-slim-bullseye

RUN pip install datasette==1.0a6
ADD https://congress-legislators.datasettes.com/legislators.db /legislators.db

COPY . /datasette-comments
WORKDIR /datasette-comments
RUN pip install -e .[test]

COPY tests/basic_plugin /plugin

CMD datasette --host 0.0.0.0 --port 8080 --plugins-dir=/plugin /legislators.db
