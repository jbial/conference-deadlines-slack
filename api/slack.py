import json
import requests
import yaml
from datetime import datetime
from urllib.parse import parse_qs

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
    """Fetch conference data from ai-deadlines repository."""
    conferences = {}
    conference_files = [
        "iclr", "nips", "neurips", "cvpr", "icml", "aaai", "acl", "emnlp",
        "iccv", "eccv", "ijcai", "kdd", "www", "recsys", "wacv", "icassp", "interspeech"
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

def find_conference_deadlines(conference_name, conferences_data):
    """Find deadlines for a specific conference."""
    if not conferences_data:
        return []

    current_year = datetime.now().year
    results = []
    
    conference_key = conference_name.lower()
    if conference_key in conferences_data:
        for conf in conferences_data[conference_key]:
            conf_year = conf.get("year", 0)
            if conf_year >= current_year:
                deadline_info = {
                    "name": conf.get("title", ""),
                    "year": conf.get("year", ""),
                    "date": conf.get("deadline", ""),
                    "type": "Paper Submission",
                    "link": conf.get("link", ""),
                    "location": f"{conf.get('city', '')}, {conf.get('country', '')}".strip(", "),
                    "abstract_deadline": conf.get("abstract_deadline", ""),
                    "venue": conf.get("venue", ""),
                }
                
                if "deadlines" in conf:
                    for deadline in conf["deadlines"]:
                        if deadline.get("type") == "abstract":
                            deadline_info["abstract_deadline"] = deadline.get("date", "")
                        elif deadline.get("type") == "submission":
                            deadline_info["date"] = deadline.get("date", "")
                
                results.append(deadline_info)
    
    return results

def format_deadline_response(deadlines, conference_name):
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

    for deadline in deadlines[:3]:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{deadline['name']} {deadline['year']}*",
            },
        })

        deadline_text = ""
        if deadline.get("abstract_deadline"):
            deadline_text += f"📝 *Abstract:* {deadline['abstract_deadline']}\n"
        if deadline.get("date"):
            deadline_text += f"📄 *Paper:* {deadline['date']}\n"

        if deadline_text:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": deadline_text.strip()},
            })

        info_text = ""
        if deadline.get("location"):
            info_text += f"📍 {deadline['location']}\n"
        if deadline.get("venue"):
            info_text += f"🏢 {deadline['venue']}\n"

        if info_text:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": info_text.strip()},
            })

        if deadline.get("link"):
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View Conference"},
                        "url": deadline["link"],
                        "action_id": f"view_conference_{deadline['year']}",
                    }
                ],
            })

        if deadline != deadlines[-1]:
            blocks.append({"type": "divider"})

    return {"response_type": "in_channel", "blocks": blocks}

def handler(request):
    """Vercel serverless function handler for Slack commands."""
    try:
        # Parse form data
        content_length = int(request.headers.get("Content-Length", 0))
        post_data = request.rfile.read(content_length)
        form_data = parse_qs(post_data.decode("utf-8"))

        command = form_data.get("command", [""])[0]
        text = form_data.get("text", [""])[0].strip()

        # Extract conference name
        if command.startswith("/"):
            conference_key = command[1:].lower()
        else:
            conference_key = text.lower() if text else ""

        conference_name = CONFERENCE_MAPPINGS.get(conference_key, conference_key)

        # Fetch and process data
        conferences_data = fetch_conference_data()
        if not conferences_data:
            response = {
                "response_type": "ephemeral",
                "text": "Sorry, I could not fetch conference data at the moment.",
            }
        else:
            deadlines = find_conference_deadlines(conference_name, conferences_data)
            response = format_deadline_response(deadlines, conference_name)

        return response

    except Exception as e:
        return {"response_type": "ephemeral", "text": f"An error occurred: {str(e)}"}