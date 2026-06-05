from flask import Flask, request, jsonify, render_template_string, send_file
import json
import os
from datetime import datetime

app = Flask(__name__)

DATA_DIR = "server_data/"
DTC_FILE = DATA_DIR + "dtc_records.json"
HB_FILE  = DATA_DIR + "heartbeat_records.json"

os.makedirs(DATA_DIR, exist_ok=True)

def read_json(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r") as f:
        return json.load(f)

def write_json(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

@app.route("/dtc", methods=["POST"])
def receive_dtc():
    data = request.json
    records = read_json(DTC_FILE)
    records.append(data)
    write_json(DTC_FILE, records)
    print(f"DTC received from {data['device_id']} — {data['total']} codes")
    return jsonify({"status": "received", "total": data["total"]})

@app.route("/heartbeat", methods=["POST"])
def receive_heartbeat():
    data = request.json
    records = read_json(HB_FILE)
    records.append(data)
    records = records[-100:]
    write_json(HB_FILE, records)
    print(f"Heartbeat from {data['device_id']} — {data['timestamp']}")
    return jsonify({"status": "ok"})

@app.route("/upload_csv", methods=["POST"])
def upload_csv():
    if "file" not in request.files:
        return jsonify({"status": "no file"}), 400
    file = request.files["file"]
    file.save(DATA_DIR + "dtc_history.csv")
    print("CSV file received and saved")
    return jsonify({"status": "saved"})

@app.route("/download_csv")
def download_csv():
    csv_path = DATA_DIR + "dtc_history.csv"
    if not os.path.exists(csv_path):
        return "No CSV file available yet", 404
    return send_file(
        csv_path,
        mimetype="text/csv",
        as_attachment=True,
        download_name="dtc_history.csv"
    )

@app.route("/")
def dashboard():
    dtc_records = read_json(DTC_FILE)
    hb_records  = read_json(HB_FILE)
    last_hb     = hb_records[-1] if hb_records else None
    total_dtc   = sum(r["total"] for r in dtc_records)
    all_codes   = []
    for record in dtc_records:
        for code in record["dtc_codes"]:
            code["device_id"] = record["device_id"]
            all_codes.append(code)
    recent_codes = all_codes[-10:][::-1]

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>OTA System Dashboard</title>
        <meta http-equiv="refresh" content="30">
        <style>
            body { font-family: Arial, sans-serif; background:#f4f4f4; padding:20px; }
            h1   { color:#333; }
            .card { background:white; border-radius:8px; padding:20px;
                    margin:10px 0; box-shadow:0 2px 4px rgba(0,0,0,0.1); }
            .online  { color:green; font-weight:bold; }
            .offline { color:red; font-weight:bold; }
            table { width:100%; border-collapse:collapse; }
            th,td { padding:10px; border-bottom:1px solid #ddd; text-align:left; }
            th    { background:#f0f0f0; }
            .badge { padding:4px 10px; border-radius:20px; font-size:12px;
                     background:#ffeded; color:#c00; }
            .download-btn { display:inline-block; padding:10px 20px;
                           background:#0066cc; color:white; border-radius:6px;
                           text-decoration:none; margin-top:10px; }
        </style>
    </head>
    <body>
        <h1>OTA System Dashboard</h1>

        <div class="card">
            <h2>Device Status</h2>
            {% if last_hb %}
                <p>Device ID: <b>{{ last_hb.device_id }}</b></p>
                <p>Status: <span class="online">ONLINE</span></p>
                <p>Last seen: {{ last_hb.timestamp }}</p>
                <p>Uptime: {{ last_hb.uptime }}</p>
            {% else %}
                <p>Status: <span class="offline">NO DATA YET</span></p>
            {% endif %}
        </div>

        <div class="card">
            <h2>DTC Summary</h2>
            <p>Total fault codes received: <b>{{ total_dtc }}</b></p>
            <p>Total upload sessions: <b>{{ dtc_records|length }}</b></p>
            <a href="/download_csv" class="download-btn">Download DTC History CSV</a>
        </div>

        <div class="card">
            <h2>Recent DTC Codes</h2>
            {% if recent_codes %}
            <table>
                <tr>
                    <th>Timestamp</th>
                    <th>Device</th>
                    <th>Code</th>
                    <th>Description</th>
                </tr>
                {% for code in recent_codes %}
                <tr>
                    <td>{{ code.timestamp }}</td>
                    <td>{{ code.device_id }}</td>
                    <td><span class="badge">{{ code.code }}</span></td>
                    <td>{{ code.description }}</td>
                </tr>
                {% endfor %}
            </table>
            {% else %}
                <p>No DTC codes received yet.</p>
            {% endif %}
        </div>
    </body>
    </html>
    """
    return render_template_string(
        html,
        last_hb=last_hb,
        total_dtc=total_dtc,
        dtc_records=dtc_records,
        recent_codes=recent_codes
    )

if __name__ == "__main__":
    app.run(debug=True)
