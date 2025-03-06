FROM python:3.12-alpine AS stage-setup

# Create the virtualenv
WORKDIR /app
RUN python3 -m venv venv

# Install the dependencies
RUN apk add --no-cache g++ git

# Install piqueserver
COPY .git ./.git
COPY pyspades/ ./pyspades
COPY piqueserver/ ./piqueserver
COPY pyproject.toml setup.py ./
RUN STDCPP_STATIC=1 /app/venv/bin/pip install .

FROM python:3.12-alpine AS stage-runtime
COPY --from=stage-setup /app /app

# Expose the server port
EXPOSE 32887/udp

# Run the command to start the server
WORKDIR /app/config
RUN /app/venv/bin/piqueserver --copy-config -d .
CMD ["/app/venv/bin/piqueserver", "-d", "."]
