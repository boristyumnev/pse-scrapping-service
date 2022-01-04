# syntax=docker/dockerfile:1
FROM mcr.microsoft.com/playwright:focal

# adding zsh and ability add alternatives
RUN apt-get update && apt-get install -y zsh software-properties-common
# installing python 3.10
RUN add-apt-repository ppa:deadsnakes/ppa && apt-get update
RUN apt-get install -y python3.10 python3.10-distutils && \
    curl -sS https://bootstrap.pypa.io/get-pip.py | python3.10 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 10

# installing pylint and playwright
RUN python3 -m pip install --upgrade playwright pylint black
RUN python3 -m playwright install firefox

# install missing dependencies
COPY ./requirements.txt /tmp/requirements.txt
RUN python3 -m pip install -r /tmp/requirements.txt && rm /tmp/requirements.txt

# copy all the app stuff
COPY ./app /service/app/
COPY ./main.py /service/
WORKDIR /service

# setup and run
ARG PSE_USERNAME
ARG PSE_PASSWORD
ARG BIND_PORT

ENV PSE_USERNAME="${PSE_USERNAME}"
ENV PSE_PASSWORD="${PSE_PASSWORD}"
ENV DATA_FOLDER="/service/data"
ENV LOGS_FOLDER="/service/logs"
ENV BIND_IP_ADDRESS="0.0.0.0"
ENV BIND_PORT="${BIND_PORT}"

ENTRYPOINT ["python", "main.py"]
