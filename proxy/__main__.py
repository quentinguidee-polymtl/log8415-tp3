import logging
import os
import random

from flask import Flask, request
from ping3 import ping
from mysql.connector import connect

app = Flask(__name__)

MANAGER_HOST = os.environ.get("MANAGER_HOST")
SLAVE_HOSTS = [
    os.environ.get("SLAVE_1_HOST"),
    os.environ.get("SLAVE_2_HOST"),
    os.environ.get("SLAVE_3_HOST")
]


@app.route("/direct", methods=["GET", "POST"])
def handle_direct():
    """
    Directly send the request to the master node
    """
    return send(MANAGER_HOST, request.data.decode())


@app.route("/random", methods=["GET", "POST"])
def handle_random():
    """
    Send the request to a random slave node
    """
    return send(random.choice(SLAVE_HOSTS), request.data.decode())


@app.route("/custom", methods=["GET", "POST"])
def handle_custom():
    """
    Send the request to the slave with the least load
    """
    pings = [ping(host) for host in SLAVE_HOSTS]
    return send(SLAVE_HOSTS[pings.index(min(pings))], request.data.decode())


def send(host: str, sql: str):
    """
    Send the request to the given host and return the response
    """
    app.logger.info(f"Sending SQL command '{sql}' to host '{host}'")

    db = connect(
        host=host,
        user="ubuntu",
        password="ubuntu",
        database="sakila"
    )
    with db.cursor() as cursor:
        cursor.execute(sql)
        res = cursor.fetchall()

    db.close()
    return str(res)


if __name__ == "__main__":
    app.logger.setLevel(logging.DEBUG)
    app.run(host="0.0.0.0", port=8080, debug=True)
