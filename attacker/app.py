from flask import Flask, request, render_template_string
from datetime import datetime

app = Flask(__name__)

# 수집된 데이터를 저장할 리스트 (메모리 저장 방식)
collected_data = []

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Attacker Dashboard</title>
    <style>
        body { font-family: sans-serif; margin: 40px; background: #1a1a1a; color: #eee; }
        h1 { color: #ff4d4d; border-bottom: 2px solid #333; padding-bottom: 10px; }
        .entry { background: #2a2a2a; padding: 15px; margin-bottom: 15px; border-left: 5px solid #ff4d4d; border-radius: 4px; }
        .timestamp { font-size: 0.8em; color: #888; margin-bottom: 5px; }
        .data { font-family: monospace; word-break: break-all; color: #40ff00; }
        .no-data { color: #888; font-style: italic; }
    </style>
</head>
<body>
    <h1>Attacker Dashboard - Collected Data</h1>
    {% if data %}
        {% for item in data %}
            <div class="entry">
                <div class="timestamp">[{{ item.time }}] From: {{ item.ip }}</div>
                <div class="data">{{ item.content }}</div>
            </div>
        {% endfor %}
    {% else %}
        <p class="no-data">수집된 데이터가 아직 없습니다...</p>
    {% endif %}
    <p><small>* 이 페이지는 실습용 공격자 서버입니다.</small></p>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE, data=collected_data)

@app.route("/collect", methods=["GET", "POST"])
def collect():
    content = ""
    if request.method == "POST":
        content = request.get_data(as_text=True)
    else:
        # GET 파라미터 모두 수집
        content = str(request.args.to_dict())
    
    if content:
        collected_data.insert(0, {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ip": request.remote_addr,
            "content": content
        })
    return "OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9000)
