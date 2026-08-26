import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "ipam.db")

# SSH defaults
SSH_TIMEOUT = 10
SSH_PORT = 22

# Web server
HOST = "0.0.0.0"
PORT = 5100
DEBUG = False

os.makedirs(DATA_DIR, exist_ok=True)
