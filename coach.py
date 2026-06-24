import os
import json
import anthropic
from db import get_db

# Canonical failure modes — each has a name, description, and what good looks like
FAILURE_MODES = {
    "wrong_icp": {
        "label": "Wrong ICP",
        "description": "The prospect is not actually a buyer — wrong role, wrong company stage, or wrong pain.",
        "fix": "Tighten your list criteria before outreach. Don't coach your way out of a targeting problem.",
    },
    "wrong_hook": {
        "label": "Wrong Hook",
        "description": "The opening didn't connect with anything the prospect cares about. Led with you, not them.",
        "fix": "Open with a specific observation about *them* (a signal, a result they'd want, a problem they'd recognize).",
    },
    "feature_dump": {
        "label": "Feature Dump",
        "description": "Led with what the product does instead of the pain it solves.",
        "fix": "Start with the pain, prove you understand it, then hint at the mechanism — never feature-list cold.",
    },
    "friction_too_high": {
        "label": "CTA Too Heavy",
        "description": "Asked for too much too soon — 30-min call, demo, or contract on the first touch.",
        "fix": "Ask one small yes/no question instead. Build micro-commitments before asking for time.",
    },
    "timing": {
        "label": "Bad Timing",
        "description": "Reached them at the wrong moment — wrong quarter, wrong project stage, wrong budget cycle.",
        "fix": "Park, set a 60-day reminder, and re-engage with a new signal when timing shifts.",
    },
    "no_pain": {
        "label": "No Felt Pain",
        "description": "The prospect doesn't feel the problem yet — or they've normalized it.",
        "fix": "Quantify the cost of the status quo. Make the invisible pain visible before pitching anything.",
    },
    "social_proof_mismatch": {
        "label": "Proof Mismatch",
        "description": "Referenced customers or results that aren't relevant to this prospect's world.",
        "fix": "Match your proof to their exact context — same industry, same stage, same pain point.",
    },
    "channel_mismatch": {
        "label": "Wrong Channel",
        "description": "They don't use or trust this channel. Email-averse executives, LinkedIn-averse engineers.",
        "fix": "Switch channel or find a warm intro path instead of cold.",
    },
    "too_generic": {
        "label": "Too Generic",
        "description": "The message could have been sent to any of 10,000 people. Zero personalization or specificity.",
        "fix": "Reference something specific: a post they wrote, a job they're hiring for, a product change, a news event.",
    },
    "follow_up_fatigue": {
        "label": "Follow-Up Fatigue",
        "description": "Too many follow-ups with no new value each time — same message restated.",
        "fix": "Each follow-up must add new value: new angle, new proof point, new question. Never just 'bumping this'.",
    },
}


def diagnose_thread(thread_text: str, prospect_name: str, prospect_role: str,
                    prospect_company: str, channel: str,
                    product: str, icp: str) -> dict:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    modes_list = "\n".join(
        f'- "{k}": {v["label"]} — {v["description"]}'
        for k, v in FAILURE_MODES.items()
    )

    prompt = f"""You are a world-class outbound sales coach. A founder is sharing a cold outreach thread that went cold (no response or conversation died). Diagnose exactly why it failed.

SELLER CONTEXT:
Product: {product}
ICP: {icp}

PROSPECT:
Name: {prospect_name or 'Unknown'}
Role: {prospect_role or 'Unknown'}
Company: {prospect_company or 'Unknown'}
Channel: {channel}

THREAD:
{thread_text}

FAILURE MODE OPTIONS:
{modes_list}

Analyze this thread ruthlessly and honestly. Return ONLY valid JSON:
{{
  "primary_failure_mode": "<one key from the list above>",
  "confidence": <integer 60-99>,
  "why_it_failed": "<2-3 sentences being brutally specific about what went wrong in THIS thread — quote the actual lines that killed it>",
  "secondary_issues": ["<other failure mode key if present>"],
  "what_prospect_was_thinking": "<1-2 sentences from the prospect's point of view when they read this and decided not to reply>",
  "pattern_tags": ["<2-4 short tags that capture the failure pattern, e.g. 'led with features', 'no personalization', 'CTA too big'>"]
}}"""

    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = resp.content[0].text.strip()
    return json.loads(raw)


def write_recovery(thread_text: str, diagnosis: dict, prospect_name: str,
                   prospect_role: str, prospect_company: str, channel: str,
                   product: str, icp: str) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    failure_mode = FAILURE_MODES.get(diagnosis["primary_failure_mode"], {})

    prompt = f"""You are a world-class outbound sales coach. Write a recovery message for a cold thread that went dead.

SELLER CONTEXT:
Product: {product}
ICP: {icp}

PROSPECT: {prospect_name or 'them'} — {prospect_role or ''} at {prospect_company or ''}
Channel: {channel}

ORIGINAL THREAD:
{thread_text}

WHY IT FAILED: {diagnosis['why_it_failed']}
PRIMARY FAILURE MODE: {failure_mode.get('label', '')} — {failure_mode.get('description', '')}
WHAT PROSPECT WAS THINKING: {diagnosis['what_prospect_was_thinking']}

Write ONE recovery message that:
1. Directly corrects the failure mode (if it was a bad hook, open completely differently; if CTA was too heavy, shrink it to a single question)
2. Never acknowledges the previous messages awkwardly ("just following up" is banned)
3. Is SHORT — under 75 words for email, under 40 for LinkedIn
4. Ends with a single, low-friction, specific question

Format your response as:

**SUBJECT:** (if email, otherwise skip)

**MESSAGE:**
[the actual message]

**WHY THIS WORKS:**
[1-2 sentences explaining the specific fix you made]"""

    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )

    return resp.content[0].text.strip()


def build_playbook() -> dict:
    """Aggregate all diagnoses into pattern insights."""
    with get_db() as conn:
        threads = conn.execute(
            "SELECT failure_mode, pattern_tags, analyzed_at FROM threads WHERE failure_mode IS NOT NULL"
        ).fetchall()

    if not threads:
        return {}

    # Count failure modes
    mode_counts = {}
    all_tags = []
    for t in threads:
        mode = t["failure_mode"]
        mode_counts[mode] = mode_counts.get(mode, 0) + 1
        if t["pattern_tags"]:
            try:
                tags = json.loads(t["pattern_tags"])
                all_tags.extend(tags)
            except Exception:
                pass

    # Count tags
    tag_counts = {}
    for tag in all_tags:
        tag_counts[tag] = tag_counts.get(tag, 0) + 1

    # Rank failure modes
    ranked_modes = sorted(mode_counts.items(), key=lambda x: x[1], reverse=True)

    # Top tags
    ranked_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:8]

    return {
        "total_analyzed": len(threads),
        "ranked_modes": ranked_modes,
        "top_tags": ranked_tags,
        "mode_details": FAILURE_MODES,
    }
