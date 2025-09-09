import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs

import requests
import yaml

CONFERENCE_MAPPINGS = {
    "iclr": "ICLR",
    "nips": "NeurIPS",
    "neurips": "NeurIPS",
    "cvpr": "CVPR",
    "icml": "ICML",
    "aaai": "AAAI",
    "acl": "ACL",
    "emnlp": "EMNLP",
    "iccv": "ICCV",
    "eccv": "ECCV",
    "ijcai": "IJCAI",
    "kdd": "KDD",
    "www": "WWW",
    "recsys": "RecSys",
    "wacv": "WACV",
    "icassp": "ICASSP",
    "interspeech": "Interspeech",
}


def fetch_conference_data():
    conferences = {}
    conference_files = [
        "iclr",
        "nips",
        "neurips",
        "cvpr",
        "icml",
        "aaai",
        "acl",
        "emnlp",
        "iccv",
        "eccv",
        "ijcai",
        "kdd",
        "www",
        "recsys",
        "wacv",
        "icassp",
        "interspeech",
    ]
    for conf in conference_files:
        url = f"https://raw.githubusercontent.com/huggingface/ai-deadlines/main/src/data/conferences/{conf}.yml"
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                data = yaml.safe_load(r.text)
                if data:
                    conferences[conf] = data
        except Exception:
            pass
    return conferences if conferences else None


def find_conference_deadlines(conference_name, conferences_data):
    if not conferences_data:
        return []
    current_year = datetime.now().year
    results = []
    key = conference_name.lower()
    if key in conferences_data:
        for conf in conferences_data[key]:
            if conf.get("year", 0) >= current_year:
                info = {
                    "name": conf.get("title", ""),
                    "year": conf.get("year", ""),
                    "date": conf.get("deadline", ""),
                    "link": conf.get("link", ""),
                    "location": f"{conf.get('city', '')}, {conf.get('country', '')}".strip(
                        ", "
                    ),
                    "abstract_deadline": conf.get("abstract_deadline", ""),
                    "venue": conf.get("venue", ""),
                }
                if "deadlines" in conf:
                    for d in conf["deadlines"]:
                        if d.get("type") == "abstract":
                            info["abstract_deadline"] = d.get("date", "")
                        elif d.get("type") == "submission":
                            info["date"] = d.get("date", "")
                results.append(info)
    return results


def format_deadline_response(deadlines, conference_name):
    if not deadlines:
        return {
            "response_type": "ephemeral",
            "text": f"No deadlines found for {conference_name}. Try: iclr, nips, cvpr, icml, aaai, acl, emnlp",
        }
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{conference_name.upper()} Conference Deadlines",
            },
        },
        {"type": "divider"},
    ]
    for d in deadlines[:3]:
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*{d['name']} {d['year']}*"},
            }
        )
        details = []
        if d.get("abstract_deadline"):
            details.append(f"📝 *Abstract:* {d['abstract_deadline']}")
        if d.get("date"):
            details.append(f"📄 *Paper:* {d['date']}")
        if details:
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "\n".join(details)},
                }
            )
        info = []
        if d.get("location"):
            info.append(f"📍 {d['location']}")
        if d.get("venue"):
            info.append(f"🏢 {d['venue']}")
        if info:
            blocks.append(
                {"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(info)}}
            )
        if d.get("link"):
            blocks.append(
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "View Conference"},
                            "url": d["link"],
                            "action_id": f"view_{d['year']}",
                        }
                    ],
                }
            )
        blocks.append({"type": "divider"})
    return {"response_type": "in_channel", "blocks": blocks}


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            form = parse_qs(body)
            command = form.get("command", [""])[0]
            text = (form.get("text", [""])[0] or "").strip()
            key = command[1:].lower() if command.startswith("/") else text.lower()
            name = CONFERENCE_MAPPINGS.get(key, key)

            data = fetch_conference_data()
            resp = (
                {
                    "response_type": "ephemeral",
                    "text": "Sorry, I could not fetch conference data at the moment.",
                }
                if not data
                else format_deadline_response(
                    find_conference_deadlines(name, data), name
                )
            )

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(resp).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps(
                    {"response_type": "ephemeral", "text": f"Error: {e}"}
                ).encode()
            )

    def do_GET(self):
        self.send_response(405)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": "Method not allowed"}).encode())
