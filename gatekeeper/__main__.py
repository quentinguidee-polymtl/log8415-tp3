import os

import requests
from flask import Flask, request

app = Flask(__name__)

PROXY_HOST = os.environ.get("PROXY_HOST")


@app.route("/<method>", methods=["GET", "POST"])
def handle(method: str):
    """
    Handle /direct, /random, and /custom requests
    """
    url = f"http://{PROXY_HOST}/{method}"

    match request.method:
        case "GET":
            res = requests.get(url)
        case "POST":
            res = requests.post(url)
        case _:
            return "Method not allowed", 405

    return res.content


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
