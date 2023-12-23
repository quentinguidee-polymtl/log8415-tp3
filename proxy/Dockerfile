FROM python:3.11-slim

ENV POETRY_VIRTUALENVS_IN_PROJECT=1

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN pip3 install poetry && \
    poetry install --only proxy --no-root && \
    rm -rf ~/.cache/

COPY proxy proxy

ENTRYPOINT [ "poetry", "run", "python3" ]
CMD [ "-m", "proxy" ]

EXPOSE 8080
