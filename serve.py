import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
import yaml
from flask import Flask, jsonify, request

app = Flask(__name__)

CONFERENCE_MAPPINGS: Dict[str, str] = {
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


def fetch_conference_data() -> Optional[Dict[str, List[Dict[str, Any]]]]:
    """Fetch conference data from ai-deadlines repository."""
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
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = yaml.safe_load(response.text)
                if data:
                    conferences[conf] = data
        except Exception as e:
            print(f"Error fetching {conf} data: {e}")

    return conferences if conferences else None


def find_conference_deadlines(
    conference_name: str, conferences_data: Dict[str, List[Dict[str, Any]]]
) -> List[Dict[str, Any]]:
    """Find deadlines for a specific conference."""
    if not conferences_data:
        return []

    current_year = datetime.now().year
    results = []

    # Try to find the conference by key first
    conference_key = conference_name.lower()
    if conference_key in conferences_data:
        for conf in conferences_data[conference_key]:
            # Check if it's current or next year
            conf_year = conf.get("year", 0)
            if conf_year >= current_year:
                # Extract deadline information
                deadline_info = {
                    "name": conf.get("title", ""),
                    "year": conf.get("year", ""),
                    "date": conf.get("deadline", ""),
                    "type": "Paper Submission",
                    "link": conf.get("link", ""),
                    "location": f"{conf.get('city', '')}, {conf.get('country', '')}".strip(
                        ", "
                    ),
                    "abstract_deadline": conf.get("abstract_deadline", ""),
                    "venue": conf.get("venue", ""),
                }

                # Add additional deadlines if available
                if "deadlines" in conf:
                    for deadline in conf["deadlines"]:
                        if deadline.get("type") == "abstract":
                            deadline_info["abstract_deadline"] = deadline.get(
                                "date", ""
                            )
                        elif deadline.get("type") == "submission":
                            deadline_info["date"] = deadline.get("date", "")

                results.append(deadline_info)

    return results


def format_deadline_response(
    deadlines: List[Dict[str, Any]], conference_name: str
) -> Dict[str, Any]:
    """Format deadlines into Slack Block Kit format."""
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

    for deadline in deadlines[:3]:  # Show up to 3 most recent deadlines
        # Conference title and year
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{deadline['name']} {deadline['year']}*",
                },
            }
        )

        # Deadlines section
        deadline_text = ""
        if deadline.get("abstract_deadline"):
            deadline_text += f"📝 *Abstract:* {deadline['abstract_deadline']}\n"
        if deadline.get("date"):
            deadline_text += f"📄 *Paper:* {deadline['date']}\n"

        if deadline_text:
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": deadline_text.strip()},
                }
            )

        # Location and venue info
        info_text = ""
        if deadline.get("location"):
            info_text += f"📍 {deadline['location']}\n"
        if deadline.get("venue"):
            info_text += f"🏢 {deadline['venue']}\n"

        if info_text:
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": info_text.strip()},
                }
            )

        # Link button if available
        if deadline.get("link"):
            blocks.append(
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "View Conference"},
                            "url": deadline["link"],
                            "action_id": f"view_conference_{deadline['year']}",
                        }
                    ],
                }
            )

        # Add divider between conferences (except for the last one)
        if deadline != deadlines[-1]:
            blocks.append({"type": "divider"})

    return {"response_type": "in_channel", "blocks": blocks}


@app.route("/slack/command", methods=["POST"])
def handle_slash_command():
    """Handle Slack slash commands."""
    command = request.form.get("command", "")
    text = request.form.get("text", "").strip()

    # Extract conference name from command or text
    if command.startswith("/"):
        conference_key = command[1:].lower()
    else:
        conference_key = text.lower() if text else ""

    # Map to full conference name
    conference_name = CONFERENCE_MAPPINGS.get(conference_key, conference_key)

    # Fetch conference data
    conferences_data = fetch_conference_data()
    if not conferences_data:
        return jsonify(
            {
                "response_type": "ephemeral",
                "text": "Sorry, I could not fetch conference data at the moment.",
            }
        )

    # Find deadlines
    deadlines = find_conference_deadlines(conference_name, conferences_data)

    # Format response
    response = format_deadline_response(deadlines, conference_name)

    return jsonify(response)


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy"})


@app.route("/", methods=["GET"])
def root():
    """Root endpoint."""
    return jsonify(
        {
            "message": "Slack Conference Deadlines Bot",
            "status": "running",
            "endpoints": ["/slack/command", "/health"],
        }
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
