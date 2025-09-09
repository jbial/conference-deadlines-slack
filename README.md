# Deadlines Bot

Slash command to fetch conference deadlines from `huggingface/ai-deadlines`.

Deployed via Vercel.

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