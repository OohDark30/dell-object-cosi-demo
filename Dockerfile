# using ubuntu LTS version
FROM ubuntu:22.04 AS builder-image

# avoid stuck build due to user prompt
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install --no-install-recommends -y git python3.10 python3.10-dev python3.10-venv python3-pip python3-wheel build-essential && \
	apt-get clean && rm -rf /var/lib/apt/lists/*

# Deploy librdkafka for confluent-kafka-python
ENV LIBRDKAFKA_VERSION v1.4.0 \
RUN cd /tmp && git clone https://github.com/edenhill/librdkafka.git \
  && cd librdkafka \
  && git checkout $LIBRDKAFKA_VERSION \
  && ./configure --install-deps --prefix /usr \
  && make \
  && make install

# create and activate virtual environment
# using final folder name to avoid path issues with packages
RUN python3.10 -m venv /home/delldemo/venv
ENV PATH="/home/delldemo/venv/bin:$PATH"

# install requirements
COPY requirements.txt .
RUN pip3 install --no-cache-dir wheel
RUN pip3 install --no-cache-dir -r requirements.txt

FROM ubuntu:22.04 AS runner-image
RUN apt-get update && apt-get install --no-install-recommends -y python3.10 python3-venv && \
	apt-get clean && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home delldemo
COPY --from=builder-image /home/delldemo/venv /home/delldemo/venv

USER delldemo
RUN mkdir /home/delldemo/app
WORKDIR /home/delldemo/app

RUN mkdir -p /home/delldemo/app/minimal
RUN mkdir -p /home/delldemo/data/cosi

ADD app.py /home/delldemo/app
ADD minimal /home/delldemo/app/minimal
ADD config.py /home/delldemo/app

EXPOSE 5000

# make sure all messages always reach console
ENV PYTHONUNBUFFERED=1

# activate virtual environment
ENV VIRTUAL_ENV=/home/delldemo/venv
ENV PATH="/home/delldemo/venv/bin:$PATH"

# /dev/shm is mapped to shared memory and should be used for gunicorn heartbeat
# this will improve performance and avoid random freezes
ENV FLASK_APP=app.py
CMD ["flask", "run", "--host", "0.0.0.0"]