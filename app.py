import os
import json
from flask import Flask, render_template, request, redirect, url_for, jsonify
from dotenv import load_dotenv
from db import init_db, get_db
from coach import diagnose_thread, write_recovery, build_playbook, FAILURE_MODES

load_dotenv()

app = Flask(__name__)


@app.before_request
def setup():
    init_db()


# ── Home / recent diagnoses ────────────────────────────────────────────────────

@app.route("/")
def index():
    with get_db() as conn:
        ctx = conn.execute("SELECT * FROM seller_context LIMIT 1").fetchone()
        threads = conn.execute(
            "SELECT * FROM threads ORDER BY analyzed_at DESC LIMIT 20"
        ).fetchall()
    return render_template("index.html", ctx=ctx, threads=threads, failure_modes=FAILURE_MODES)


# ── Seller context ─────────────────────────────────────────────────────────────

@app.route("/context", methods=["GET", "POST"])
def context():
    if request.method == "POST":
        product = request.form["product"].strip()
        icp = request.form["icp"].strip()
        with get_db() as conn:
            conn.execute("DELETE FROM seller_context")
            conn.execute("INSERT INTO seller_context (product, icp) VALUES (?, ?)", (product, icp))
        return redirect(url_for("index"))

    with get_db() as conn:
        ctx = conn.execute("SELECT * FROM seller_context LIMIT 1").fetchone()
    return render_template("context.html", ctx=ctx)


# ── Analyze a thread ───────────────────────────────────────────────────────────

@app.route("/analyze", methods=["GET", "POST"])
def analyze():
    with get_db() as conn:
        ctx = conn.execute("SELECT * FROM seller_context LIMIT 1").fetchone()

    if request.method == "POST":
        data = {
            "prospect_name": request.form.get("prospect_name", "").strip(),
            "prospect_role": request.form.get("prospect_role", "").strip(),
            "prospect_company": request.form.get("prospect_company", "").strip(),
            "channel": request.form.get("channel", "email"),
            "thread_text": request.form.get("thread_text", "").strip(),
        }

        diagnosis = diagnose_thread(
            data["thread_text"], data["prospect_name"], data["prospect_role"],
            data["prospect_company"], data["channel"],
            ctx["product"], ctx["icp"],
        )

        recovery = write_recovery(
            data["thread_text"], diagnosis, data["prospect_name"],
            data["prospect_role"], data["prospect_company"], data["channel"],
            ctx["product"], ctx["icp"],
        )

        with get_db() as conn:
            cur = conn.execute(
                """INSERT INTO threads
                   (prospect_name, prospect_role, prospect_company, channel, thread_text,
                    failure_mode, failure_confidence, failure_explanation,
                    recovery_draft, pattern_tags)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    data["prospect_name"], data["prospect_role"],
                    data["prospect_company"], data["channel"], data["thread_text"],
                    diagnosis.get("primary_failure_mode"),
                    diagnosis.get("confidence"),
                    json.dumps({
                        "why": diagnosis.get("why_it_failed"),
                        "prospect_pov": diagnosis.get("what_prospect_was_thinking"),
                        "secondary": diagnosis.get("secondary_issues", []),
                    }),
                    recovery,
                    json.dumps(diagnosis.get("pattern_tags", [])),
                ),
            )
            thread_id = cur.lastrowid

        return redirect(url_for("diagnosis", thread_id=thread_id))

    return render_template("analyze.html", ctx=ctx)


# ── Diagnosis result ───────────────────────────────────────────────────────────

@app.route("/diagnosis/<int:thread_id>")
def diagnosis(thread_id):
    with get_db() as conn:
        thread = conn.execute("SELECT * FROM threads WHERE id = ?", (thread_id,)).fetchone()

    if not thread:
        return "Not found", 404

    failure_detail = FAILURE_MODES.get(thread["failure_mode"], {})
    try:
        explanation = json.loads(thread["failure_explanation"] or "{}")
    except Exception:
        explanation = {}
    try:
        pattern_tags = json.loads(thread["pattern_tags"] or "[]")
    except Exception:
        pattern_tags = []

    return render_template(
        "diagnosis.html",
        thread=thread,
        failure_detail=failure_detail,
        explanation=explanation,
        pattern_tags=pattern_tags,
    )


# ── Delete a thread ────────────────────────────────────────────────────────────

@app.route("/threads/<int:thread_id>/delete", methods=["POST"])
def delete_thread(thread_id):
    with get_db() as conn:
        conn.execute("DELETE FROM threads WHERE id = ?", (thread_id,))
    return redirect(url_for("index"))


# ── Playbook ───────────────────────────────────────────────────────────────────

@app.route("/playbook")
def playbook():
    data = build_playbook()
    return render_template("playbook.html", data=data, failure_modes=FAILURE_MODES)


if __name__ == "__main__":
    app.run(debug=True, port=5051)
