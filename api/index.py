def handler(request):
    """Root endpoint."""
    return {
        "message": "Slack Conference Deadlines Bot",
        "status": "running",
        "endpoints": ["/slack/command", "/health"],
    }
