FROM python:3.10.13-alpine3.18

ADD requirements.txt /app/requirements.txt

RUN set -ex \
    && apk add --no-cache --virtual .build-deps postgresql-dev build-base \
    && python -m venv /env \
    && /env/bin/pip install --upgrade pip \
    && /env/bin/pip install --no-cache-dir -r /app/requirements.txt \
    && runDeps="$(scanelf --needed --nobanner --recursive /env \
        | awk '{ gsub(/,/, "\nso:", $2); print "so:" $2 }' \
        | sort -u \
        | xargs -r apk info --installed \
        | sort -u)" \
    && apk add --virtual rundeps $runDeps \
    && apk del .build-deps

WORKDIR /app

RUN mkdir -p /app/minimal
RUN mkdir -p /data/cosi

ADD app.py /app
ADD minimal /app/minimal

# Remove after development
#ADD BucketInfo /data/cosi

ENV VIRTUAL_ENV /env
ENV PATH /env/bin:$PATH

EXPOSE 5000

# The command required to run the Dockerized Python Flask application
ENV FLASK_APP=app.py
CMD ["flask", "run", "--host", "0.0.0.0"]