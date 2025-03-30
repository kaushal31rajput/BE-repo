from flask import Flask, request, jsonify
from flask_cors import CORS
from google.cloud import storage
import os
import psycopg2
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Google Cloud Storage bucket name
GCS_BUCKET = "file-test-gke-frontend-001"  # Replace with your GCS bucket name

# Database configuration (replace with your database details)
DB_HOST = "postgresql.default.svc.cluster.local"  # Kubernetes DNS for database pod
DB_PORT = 5432  # Default PostgreSQL port
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASSWORD = "wAe5mk3Wb0"

def get_db_connection():
    """Create and return a database connection."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )

@app.route("/upload", methods=["POST"])
def upload_file():
    """Endpoint to handle file uploads."""
    try:
        # Check if file and file name are provided
        if "file" not in request.files or "fileName" not in request.form:
            return jsonify({"error": "File or file name not provided"}), 400

        file = request.files["file"]
        file_name = request.form["fileName"]

        # Debugging logs for input
        print(f"Received file: {file.filename}, Name: {file_name}")

        # Upload file to GCS
        storage_client = storage.Client()
        bucket = storage_client.bucket(GCS_BUCKET)
        blob = bucket.blob(file_name)
        blob.upload_from_file(file)

        # Store metadata in the database
        upload_time = datetime.utcnow()
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO file_uploads (file_name, upload_time) VALUES (%s, %s)",
            (file_name, upload_time),
        )
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"message": f"File '{file_name}' uploaded successfully to GCS and metadata stored!"}), 200
    except Exception as e:
        print(f"Error during file upload: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/files', methods=["GET"])
def list_files():
    """Endpoint to retrieve all file uploads from the database."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT file_name, upload_time FROM file_uploads ORDER BY upload_time DESC")
        rows = cur.fetchall()
        files = []
        for row in rows:
            files.append({
                "file_name": row[0],
                "upload_time": row[1].isoformat()  # Convert datetime to ISO string for JSON
            })
        cur.close()
        conn.close()
        return jsonify(files), 200
    except Exception as e:
        print(f"Error retrieving file list: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))  # Cloud Run default PORT
    app.run(host="0.0.0.0", port=port)
