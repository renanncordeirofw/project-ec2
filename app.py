import boto3
import json
import pymysql
from flask import Flask, request, jsonify

app = Flask(__name__)

# ===========================
# AWS CONFIG
# ===========================
SECRET_NAME = "rds!db-bcf2dcef-fc12-4675-8142-efdd5287f8ae"
REGION_NAME = "us-east-2"  # altere para sua região

PARAM_DB_HOST = "/myproject/db/host"
PARAM_DB_NAME = "/myproject/db/name"

# ===========================
# AWS HELPERS
# ===========================
def get_secret():
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=REGION_NAME)
    secret_value = client.get_secret_value(SecretId=SECRET_NAME)
    secret = json.loads(secret_value["SecretString"])
    return secret["username"], secret["password"]

def get_parameter(name):
    ssm = boto3.client("ssm", region_name=REGION_NAME)
    response = ssm.get_parameter(Name=name, WithDecryption=True)
    return response["Parameter"]["Value"]

# ===========================
# DATABASE CONNECTION
# ===========================
def get_db_connection():
    username, password = get_secret()
    host = get_parameter(PARAM_DB_HOST)
    db_name = get_parameter(PARAM_DB_NAME)

    connection = pymysql.connect(
        host=host,
        user=username,
        password=password,
        database=db_name,
        cursorclass=pymysql.cursors.DictCursor,
    )
    return connection

# ===========================
# DATABASE INIT
# ===========================
def init_db():
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL
            );
        """)
    conn.commit()
    conn.close()

# ===========================
# ROUTES
# ===========================
@app.route("/")
def index():
    return jsonify({"message": "Servidor Flask rodando com MySQL via RDS!"})

@app.route("/users", methods=["POST"])
def create_user():
    data = request.get_json()
    name = data.get("name")
    email = data.get("email")

    if not name or not email:
        return jsonify({"error": "name e email são obrigatórios"}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO users (name, email) VALUES (%s, %s)", (name, email))
        conn.commit()
        return jsonify({"message": "Usuário cadastrado com sucesso!"}), 201
    except pymysql.err.IntegrityError:
        return jsonify({"error": "Email já cadastrado"}), 409
    finally:
        conn.close()

@app.route("/users", methods=["GET"])
def list_users():
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM users")
        users = cur.fetchall()
    conn.close()
    return jsonify(users)

# ===========================
# MAIN
# ===========================
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=80)
