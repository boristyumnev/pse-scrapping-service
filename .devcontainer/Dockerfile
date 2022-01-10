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
RUN python3 -m playwright install

COPY .bashrc /root/.bashrc