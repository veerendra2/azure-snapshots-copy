FROM python:3.11-alpine

COPY src/ src/

RUN pip3 install -r /requirements.txt
