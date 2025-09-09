import hashlib
import hmac
import json
import logging
import os
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs

import requests
import yaml

LOGGER = logging.getLogger("conf_deadlines_slack")
if not LOGGER.handlers:
    _level = os.getenv("LOG_LEVEL", "INFO").upper()
    LOGGER.setLevel(getattr(logging, _level, logging.INFO))
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    LOGGER.addHandler(_h)

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
                    "timezone": conf.get("timezone") or conf.get("tz"),
                }
                if "deadlines" in conf:
                    for d in conf["deadlines"]:
                        if d.get("type") == "abstract":
                            info["abstract_deadline"] = d.get("date", "")
                            if d.get("timezone") or d.get("tz"):
                                info["timezone"] = d.get("timezone") or d.get("tz")
                        elif d.get("type") == "submission":
                            info["date"] = d.get("date", "")
                            if d.get("timezone") or d.get("tz"):
                                info["timezone"] = d.get("timezone") or d.get("tz")
                results.append(info)
    return results


def format_deadline_response(deadlines, conference_name):
    if not deadlines:
        return {
            "response_type": "ephemeral",
            "text": f"No deadlines found for {conference_name}. Try: iclr, nips, cvpr, icml, aaai, acl, emnlp",
        }

    # Concise code block (no emoji noise)
    sections = []
    for d in deadlines[:3]:
        lines = [f"{d.get('name','')} {d.get('year','')}"]
        if d.get("abstract_deadline"):
            lines.append(f"Abstract: {d['abstract_deadline']}")
        if d.get("date"):
            lines.append(f"Paper:   {d['date']}")
        if d.get("timezone"):
            lines.append(f"TZ:      {d['timezone']}")
        if d.get("location"):
            lines.append(f"Location: {d['location']}")
        if d.get("venue"):
            lines.append(f"Venue:   {d['venue']}")
        if d.get("link"):
            lines.append(f"Link:    {d['link']}")
        sections.append("\n".join(lines))

    code = "\n\n".join(sections)
    return {
        "response_type": "in_channel",
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": f"```{code}```"}}
        ],
    }


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            # Cap body to 10 KB
            if length > 10_000:
                self.send_response(413)
                self.end_headers()
                return
            body = self.rfile.read(length).decode("utf-8")
            # Structured logging of request context
            try:
                LOGGER.info("headers=%s", dict(self.headers))
                LOGGER.info("raw_body=%s", body)
            except Exception:
                pass

            # Slack signature verification (optional but recommended)
            signing_secret = os.getenv("SLACK_SIGNING_SECRET")
            if signing_secret:
                ts = self.headers.get("X-Slack-Request-Timestamp")
                sig = self.headers.get("X-Slack-Signature", "")
                if not ts or not sig:
                    self.send_response(401)
                    self.end_headers()
                    return
                try:
                    ts_int = int(ts)
                except Exception:
                    self.send_response(401)
                    self.end_headers()
                    return
                if abs(int(time.time()) - ts_int) > 300:
                    self.send_response(401)
                    self.end_headers()
                    return
                basestring = f"v0:{ts}:{body}".encode()
                digest = hmac.new(
                    signing_secret.encode(), basestring, hashlib.sha256
                ).hexdigest()
                expected = f"v0={digest}"
                if not hmac.compare_digest(expected, sig):
                    self.send_response(401)
                    self.end_headers()
                    return
            form = parse_qs(body)
            try:
                LOGGER.info("form=%s", {k: v for k, v in form.items()})
            except Exception:
                pass
            command = (form.get("command", [""])[0] or "").strip()
            raw_text = (form.get("text", [""])[0] or "").strip()
            tokens = [t for t in raw_text.split() if t]
            if tokens and tokens[0].lstrip("/").lower() in {"deadline", "deadlines"}:
                tokens = tokens[1:]
            if tokens:
                key = tokens[0].lower()
            else:
                if (
                    command
                    and command.startswith("/")
                    and command.lower() not in {"/deadline", "/deadlines"}
                ):
                    key = command[1:].lower()
                else:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(
                        json.dumps(
                            {
                                "response_type": "ephemeral",
                                "text": "Usage: /deadline <conf>. Try: iclr, neurips, cvpr, icml, aaai, acl, emnlp",
                            }
                        ).encode()
                    )
                    return
            try:
                LOGGER.info(
                    "parsed command=%s raw_text=%s key=%s", command, raw_text, key
                )
            except Exception:
                pass
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
