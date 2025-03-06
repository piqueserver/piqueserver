ARG PYTHON_VERSION=3.12
ARG APPDIR=/app

# Build
FROM python:${PYTHON_VERSION}-alpine

# Set venv
ARG APPDIR
ENV APPDIR=${APPDIR}
RUN python -m venv ${APPDIR}
ENV PATH="${APPDIR}/bin:${PATH}"

# Install the dependencies
RUN apk add --no-cache g++ git

CMD [ \
    "sh", "-c", \
    "pip --no-cache-dir install -e ${APPDIR}/src && \
    piqueserver -d /config" \
]
