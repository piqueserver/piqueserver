ARG PYTHON_VERSION=3.6
ARG APPDIR=/app

# Build
FROM python:$PYTHON_VERSION

# Set venv
ARG APPDIR
ENV APPDIR ${APPDIR}
RUN python -m venv ${APPDIR}
ENV PATH "${APPDIR}/bin:${PATH}"

CMD pip --no-cache-dir install -e ${APPDIR}/src && \
    piqueserver -d /config
