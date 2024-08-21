FROM --platform=linux/amd64 python:3.8.19 as build
WORKDIR /app
COPY etc/apt-sources.list /etc/apt/sources.list
# Fix DNS pollution of local network
COPY etc/resolv.conf /etc/resolv.conf
ARG PYPI_MIRROR="https://mirrors.aliyun.com/pypi/simple/"
ENV PIP_INDEX_URL=$PYPI_MIRROR PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv .venv
ENV PATH=/app/.venv/bin:$PATH
COPY requirements-pip.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements-pip.txt
COPY constraint.txt .
ENV PIP_CONSTRAINT=/app/constraint.txt
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

FROM --platform=linux/amd64 python:3.8.19-slim as runtime
WORKDIR /app
COPY etc/apt-sources.list /etc/apt/sources.list
# Fix DNS pollution of local network
COPY etc/resolv.conf /etc/resolv.conf
ARG PYPI_MIRROR="https://mirrors.aliyun.com/pypi/simple/"
ENV PIP_INDEX_URL=$PYPI_MIRROR PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PATH=/app/.venv/bin:$PATH
COPY --from=build /app/.venv /app/.venv
COPY . /app
ARG EZFAAS_BUILD_ID=''
ARG EZFAAS_COMMIT_ID=''
ENV EZFAAS_BUILD_ID=${EZFAAS_BUILD_ID} EZFAAS_COMMIT_ID=${EZFAAS_COMMIT_ID}
RUN python manage.py collectstatic

FROM --platform=linux/amd64 runtime
CMD [ "/app/runserver.sh" ]
