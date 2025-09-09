import json

def handler(request):
    """Root endpoint."""
    if request.method == "GET":
        response = {
            "message": "Slack Conference Deadlines Bot",
            "status": "running",
            "endpoints": ["/slack/command", "/health"],
        }
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(response)
        }
    else:
        return {
            "statusCode": 405,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Method not allowed"})
        }
