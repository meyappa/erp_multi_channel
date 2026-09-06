from app.services.ai import JOB_LABELS, categorize_return_reason, chat_answer, optimize_listing


def test_return_reason_quality():
    r = categorize_return_reason("defective", "screen is broken")
    assert r["category"] == "quality"


def test_listing_optimizer_pads_short_titles():
    out = optimize_listing("Watch", "nice watch", "amazon")
    assert "Fast Ship" in out["title"]
    assert out["bullets"].startswith("- ")


def test_chat_profit_intent():
    reply = chat_answer("what is our profit margin?", {"gross_profit": "1200", "margin_pct": "31", "formula": "x"})
    assert "1200" in reply


def test_automation_job_labels_cover_core_agents():
    for key in ("forecast", "listing_optimize", "anomaly_scan", "chat", "return_categorize", "sync_health"):
        assert key in JOB_LABELS
