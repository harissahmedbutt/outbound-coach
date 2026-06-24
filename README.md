# Outbound Coach

A brutally honest AI coach for sales founders. Paste a dead outreach thread, get an exact diagnosis of why it went cold, a recovery draft, and a personal playbook built from your own failure patterns.

## What it does

- **Diagnoses** dead threads against 10 canonical failure modes (wrong ICP, feature dump, no pain, follow-up fatigue, etc.)
- **Explains** why *that specific thread* died — not generic advice
- **Writes** a recovery message you can send today
- **Builds a playbook** as you analyze more threads — ranked by your actual failure patterns

## Setup

**1. Clone and install dependencies**
```bash
git clone https://github.com/harissahmedbutt/outbound-coach.git
cd outbound-coach
pip3 install -r requirements.txt
```

**2. Add your Anthropic API key**
```bash
cp .env.example .env
# Edit .env and paste your key from console.anthropic.com
```

**3. Run**
```bash
./run.sh
# or
python3 app.py
```

App runs at **http://localhost:5051**

## Stack

- Python / Flask
- Claude (`claude-sonnet-4-6`) via Anthropic SDK
- SQLite
- Vanilla HTML/CSS (dark theme, no framework)

## The 10 failure modes

| Mode | What it means |
|------|--------------|
| Wrong ICP | This prospect was never going to buy |
| Wrong hook | The opening didn't connect to their actual world |
| Feature dump | Led with features, not outcomes |
| Friction too high | Too much effort required to respond |
| Timing | Right message, wrong moment |
| No pain | Didn't establish why they need to change |
| Social proof mismatch | Wrong logos/references for this buyer |
| Channel mismatch | Wrong channel for this persona |
| Too generic | Could have been sent to anyone |
| Follow-up fatigue | Over-messaged, now ignored |
