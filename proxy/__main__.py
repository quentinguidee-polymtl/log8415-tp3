from flask import Flask

app = Flask(__name__)


@app.route("/direct")
def handle_direct():
    """
    Directly send the request to the master node
    """
    pass


@app.route("/random")
def handle_random():
    """
    Send the request to a random slave node
    """
    pass


@app.route("/custom")
def handle_custom():
    """
    Send the request to the slave with the least load
    """
    pass


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
