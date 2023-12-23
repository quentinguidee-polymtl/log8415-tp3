import os
import random

from flask import Flask
from ping3 import ping

app = Flask(__name__)

MASTER_HOST = os.environ.get("MASTER_HOST")
SLAVE_HOSTS = [
    os.environ.get("SLAVE_1_HOST"),
    os.environ.get("SLAVE_2_HOST"),
    os.environ.get("SLAVE_3_HOST")
]


@app.route("/direct")
def handle_direct():
    """
    Directly send the request to the master node
    """
    return send(MASTER_HOST)


@app.route("/random")
def handle_random():
    """
    Send the request to a random slave node
    """
    return send(random.choice(SLAVE_HOSTS))


@app.route("/custom")
def handle_custom():
    """
    Send the request to the slave with the least load
    """
    pings = []
    for slave in SLAVE_HOSTS:
        pings.append(ping(slave))

    return send(SLAVE_HOSTS[pings.index(min(pings))])


def send(host: str):
    """
    Send the request to the given host
    """
    pass


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
