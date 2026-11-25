"""yt-comment: triage first, then DRAFT replies. Nothing is ever posted automatically."""
import json, re

BAIT = re.compile(r"\b(suck\w*|trash|garbage|stupid|idiot|dumb|hate|kys|scam|fake|shit\w*)\b", re.I)
CORR = re.compile(r"\b(actually|wrong|incorrect|mistake|typo|pronounced|spelled|misspell\w*)\b", re.I)
PRAISE = re.compile(r"\b(love\w*|great|amazing|scary|scared|best|awesome|good|creepy|chills)\b", re.I)


def triage(cs):
    piles = {"questions": [], "corrections": [], "praise": [], "bait": [], "skip": []}
    for c in cs:
        t = c["text"]
        if BAIT.search(t): piles["bait"].append(c)
        elif "?" in t: piles["questions"].append(c)
        elif CORR.search(t): piles["corrections"].append(c)
        elif PRAISE.search(t): piles["praise"].append(c)
        else: piles["skip"].append(c)
    return piles


def draft_prompt(cs, channel):
    return f"""[task:replies]
You write replies for the channel "{channel.get('name') or 'this channel'}", an original horror and mystery story channel. Sound like one person, warm and brief.
RULES: each reply under 30 words. Answer the question in the first sentence. Thank corrections plainly and say what you will check. Never argue, never defend.
Never promise future videos, dates or giveaways. Never reply to bait. Do not use emoji more than once per reply.
COMMENTS: {json.dumps(cs)}
Return ONLY JSON: {{"replies": [{{"id": "comment id", "reply": "text"}}]}}"""
