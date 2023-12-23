from flask import Flask

app = Flask(__name__)


@app.route("/<method>")
def handle(method: str):
    """
    Handle /direct, /random, and /custom requests
    """
    pass


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
