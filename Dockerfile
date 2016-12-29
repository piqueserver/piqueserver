FROM python:2.7-alpine

RUN mkdir -p /usr/src/app
RUN mkdir -p /usr/src/app/enet
RUN mkdir -p /usr/src/app/pyspades
WORKDIR /usr/src/app

# Installing dependencies.
# In order to keep layers lean we instantly remove the build essentials 
COPY requirements.txt /usr/src/app/

RUN apk add --no-cache --virtual .build-deps-cython gcc musl-dev \
    && apk add --no-cache --virtual .build-deps-pillow zlib-dev jpeg-dev \
    \
    && pip install --no-cache-dir -r requirements.txt \
    && apk del .build-deps-cython \
    && apk del .build-deps-pillow

# The fact that we removed gcc beforehand makes us download it again
# This is remedied by building the server core first and leaving all .py scripts 
# to the last. A change in python script won't trigger downloading gcc all over again
# but a change in .pyx or .c file will.
# TODO: while this behaviour suits production envs perfectly, make a dev env option
COPY pyspades/ /usr/src/app/pyspades/
COPY enet/ /usr/src/app/enet/
COPY build.py build.sh COPYING.txt CREDITS.txt LICENSE /usr/src/app/

RUN apk add --no-cache --virtual .build-deps-server gcc musl-dev g++ \
    && STDCPP_STATIC=1 ./build.sh \
    && apk del .build-deps-server 

# Copy over the rest and default to launching the server
COPY . /usr/src/app
CMD ./run_server.sh

EXPOSE 32887/udp 32887 32886 32885
