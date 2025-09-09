# Deadlines Bot

Slash command to fetch conference deadlines from `huggingface/ai-deadlines`.

Endpoint (Vercel Functions): `/api/slack`

Usage in Slack:
```
/deadline <conf>
```

Supported conferences (keys):
```
iclr, nips (neurips), neurips, cvpr, icml, aaai, acl, emnlp,
iccv, eccv, ijcai, kdd, www, recsys, wacv, icassp, interspeech
```

Security:
- Slack signature verification (set `SLACK_SIGNING_SECRET`) is supported.

Notes:
- Results are returned as a concise code block (no emoji), up to 3 entries.