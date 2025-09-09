def handler(request):
    return {
        "message": "Slack Conference Deadlines Bot",
        "status": "running",
        "endpoints": ["/slack/command", "/health"],
    }
