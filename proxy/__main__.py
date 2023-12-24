import os
import random

from flask import Flask, request
from ping3 import ping
from mysql.connector import connect, MySQLConnection

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
    db = database(host)
    cursor = db.cursor()
    app.logger.info(f"Sending SQL command '{sql}' to host '{host}'")
    cursor.execute(sql)
    res = cursor.fetchmany()
    db.commit()
    db.close()
    return str(res)


def database(host: str) -> MySQLConnection:
    """
    Connect to the database on the given host
    """
    return connect(
        host=host,
        user="ubuntu",
        password="ubuntu",
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
