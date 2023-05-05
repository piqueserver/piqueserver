FROM python:3.7-alpine
VOLUME /config

RUN mkdir -p /usr/src/app && mkdir -p /usr/src/app/enet && mkdir -p /usr/src/app/pyspades
WORKDIR /usr/src/app

# Installing dependencies.
# In order to keep layers lean we instantly remove the build essentials 
COPY requirements.txt /usr/src/app/

# Note: manylinux wheel support isn't enabled by default for alpinelinux
# we temporarly enable it for pyenet since it is compatible
RUN apk add --no-cache --virtual .build-deps-cython gcc musl-dev \
    && apk add --no-cache --virtual .build-deps-pillow zlib-dev jpeg-dev libffi-dev openssl-dev \
    && apk add --no-cache zlib jpeg \
    \
    && echo "manylinux1_compatible = True" > /usr/local/lib/python3.7/_manylinux.py \
    && pip install pyenet \
    && rm /usr/local/lib/python3.7/_manylinux.py \
    && pip install --no-cache-dir -r requirements.txt \
    \
    && apk del .build-deps-cython \
    && apk del .build-deps-pillow

# The fact that we removed gcc beforehand makes us download it again
# This is remedied by building the server core first and leaving all .py scripts 
# to the last. A change in python script won't trigger downloading gcc all over again
# but a change in .pyx or .c file will.
# TODO: while this behaviour suits production envs perfectly, make a dev env option
COPY pyspades/ /usr/src/app/pyspades/
COPY piqueserver/ /usr/src/app/piqueserver/
COPY setup.py COPYING.txt CREDITS.txt LICENSE README.rst /usr/src/app/

RUN apk add --no-cache --virtual .build-deps-server gcc musl-dev g++ \
    && STDCPP_STATIC=1 python ./setup.py install \
    && apk del .build-deps-server \
    && cd / && rm -rf /usr/src/app

# We need ssl support for fetching server's IP
RUN apk add --no-cache openssl

# Copy over the rest and default to launching the server
CMD piqueserver -d /config

EXPOSE 32887/udp 32887 32886 32885
