FROM ubuntu:24.04

# Do not ask for user inputs
ARG DEBIAN_FRONTEND=noninteractive

# Configure UTF-8 (Useful for tty spinners)
# Install Python + venv
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        locales \
        libffi-dev \
        python3-venv \
        build-essential \
        clang zip unzip \
        sudo wget curl git vim \
        gcc-multilib libc6-dev-i386 && \
    locale-gen en_US.UTF-8 && \
    rm -rf /var/lib/apt/lists/*

ENV LANG=en_US.UTF-8
ENV PYTHONIOENCODING=utf-8

# Create virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy SumSynth files
COPY . /root/summboundverify
WORKDIR /root/summboundverify

# Install Python modules
RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install -r scripts/installers/requirements.txt

# Make summbv availabe globally
RUN ln -sf /root/summboundverify/src/main.py /usr/local/bin/summbv

# Configure bash prompt
RUN echo 'export PS1="\u@\h:\w# "' >> /root/.bashrc

# Set the working directory to start from
WORKDIR /root/dev

# Start bash
CMD ["/bin/bash"]
