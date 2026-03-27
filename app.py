from flask import Flask, jsonify, Response
import requests
from datetime import datetime
import threading
import time
import re
import os

app = Flask(__name__, static_url_path="", static_folder=".")

# TRON block API
BASE_URL = "https://apilist.tronscanapi.com/api/block"

# Store processed blocks
results = []
seen = set()
lock = threading.Lock()
MAX_RESULTS = 1000

# 🔢 IssueNumber (manual start)
current_seq = 779 # 👉 start from 0123

def next_issue():
    global current_seq

    current_seq += 1
    if current_seq > 1440:
        current_seq = 1

    date_str = datetime.now().strftime("%Y%m%d")
    base = "10301"
    seq_str = str(current_seq).zfill(4)

    return f"{date_str}{base}{seq_str}"

# Last digit color logic
def get_color(digit):
    if digit in [1, 3, 7, 9]:
        return "GREEN"
    elif digit in [2, 4, 6, 8]:
        return "RED"
    else:
        return "VIOLET"
    
def get_BS(digit):
    if digit<4:
        return "S"    
    else:
        return "B"

# Background thread
def loop():
    while True:
        try:
            res = requests.get(BASE_URL, params={"limit": 10}, timeout=10)
            data = res.json()

            for block in data.get("data", []):
                number = block["number"]
                ts = block["timestamp"]
                hsh = block["hash"]

                if number in seen:
                    continue

                dt = datetime.fromtimestamp(ts / 1000)

                # only 54 second block
                if dt.second == 54:
                    seen.add(number)

                    digits_only = re.sub(r"\D", "", hsh)
                    last_digit = int(digits_only[-1]) if digits_only else 0

                    row = {
                        "issue": next_issue(),  # ✅ IssueNumber
                        "block": number,
                        "time": dt.strftime("%H:%M:%S"),
                        "hash": hsh,
                        "last_digit": last_digit,
                        "B/S" :get_BS(last_digit),
                        "color": get_color(last_digit)
                    }

                    # thread-safe insert
                    with lock:
                        results.insert(0, row)

                        if len(results) > MAX_RESULTS:
                            results.pop()

                    # console output (row format)
                    print(f"{row},")

        except Exception as e:
            print("ERROR:", e)

        time.sleep(2)

# Start thread
threading.Thread(target=loop, daemon=True).start()

# API (row format text)
@app.route("/api/live")
def live():
    lines = []
    for r in results:
        line = f"{r},"
        lines.append(line)

    return Response("\n".join(lines), mimetype="text/plain")

# JSON API (optional)
@app.route("/api/json")
def json_api():
    return jsonify(results)

# HTML
@app.route("/")
def home():
    return app.send_static_file("index.html")




if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
