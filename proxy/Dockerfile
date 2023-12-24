FROM python:3.11-slim

ENV POETRY_VIRTUALENVS_IN_PROJECT=1

ARG MANAGER_HOST
ARG SLAVE_1_HOST
ARG SLAVE_2_HOST
ARG SLAVE_3_HOST

ENV MANAGER_HOST=$MANAGER_HOST
ENV SLAVE_1_HOST=$SLAVE_1_HOST
ENV SLAVE_2_HOST=$SLAVE_2_HOST
ENV SLAVE_3_HOST=$SLAVE_3_HOST

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN pip3 install poetry && \
    poetry install --no-root && \
    rm -rf ~/.cache/

COPY proxy proxy

ENTRYPOINT [ "poetry", "run", "python3" ]
CMD [ "-m", "proxy" ]

EXPOSE 8080
