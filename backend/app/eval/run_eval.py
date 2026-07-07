"""Evaluation harness for the AI Support Desk agent pipeline.

Runs the routing + specialist pipeline against the labeled set and reports:
- Routing accuracy (per category + overall)
- Average confidence score
- Escalation rate
- Answer quality (keyword overlap with ideal answer)

Usage:
    python -m app.eval.run_eval

Or inside Docker:
    docker-compose exec api python -m app.eval.run_eval
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

LABELED_SET_PATH = Path(__file__).parent / "labeled_set.jsonl"


def load_labeled_set() -> list[dict]:
    items = []
    with open(LABELED_SET_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def keyword_overlap(answer: str, keywords: list[str]) -> float:
    """Fraction of expected keywords found (case-insensitive) in the answer."""
    if not keywords:
        return 1.0  # N/A for unclear tickets
    answer_lower = answer.lower()
    found = sum(1 for kw in keywords if kw.lower() in answer_lower)
    return found / len(keywords)


def print_table(rows: list[dict], columns: list[str]) -> None:
    widths = {col: max(len(col), max(len(str(r.get(col, ""))) for r in rows)) for col in columns}
    header = " | ".join(col.ljust(widths[col]) for col in columns)
    sep = "-+-".join("-" * widths[col] for col in columns)
    print(header)
    print(sep)
    for row in rows:
        print(" | ".join(str(row.get(col, "")).ljust(widths[col]) for col in columns))


async def run_eval() -> None:
    from app.agents.router_agent import run_router
    from app.agents.specialist_agent import run_specialist
    from app.agents.tools.kb_search import make_kb_search_tool
    from app.agents.tools.billing_lookup import billing_lookup
    from app.agents.tools.order_lookup import order_lookup
    from app.db.session import AsyncSessionLocal
    from app.core.config import get_settings

    settings = get_settings()
    labeled = load_labeled_set()

    print(f"\n{'='*60}")
    print(f"AI Support Desk — Evaluation Harness")
    print(f"Model: {settings.openai_chat_model}")
    print(f"Tickets: {len(labeled)}")
    print(f"Confidence threshold: {settings.confidence_threshold}")
    print(f"{'='*60}\n")

    results: list[dict] = []
    correct_routes = 0
    total_confidence = 0.0
    confidence_count = 0
    escalated_count = 0

    async with AsyncSessionLocal() as db:
        for i, item in enumerate(labeled, 1):
            subject = item["subject"]
            body = item["body"]
            expected_category = item["expected_category"]
            ideal_keywords = item.get("ideal_answer_keywords", [])

            print(f"[{i:02d}/{len(labeled)}] {subject[:60]}...")
            t0 = time.monotonic()

            try:
                # Step 1: Route
                route_result = await run_router(subject=subject, body=body)
                predicted_category = route_result.category

                routed_correctly = (predicted_category == expected_category)
                if routed_correctly:
                    correct_routes += 1

                # Step 2: Run specialist (skip if unclear → escalate)
                answer = ""
                confidence = 0.0
                keyword_score = 0.0
                escalated = False

                if predicted_category == "unclear":
                    escalated = True
                    if expected_category == "unclear":
                        keyword_score = 1.0  # correct escalation
                else:
                    tools = [make_kb_search_tool(db, category=predicted_category)]
                    if predicted_category == "billing":
                        tools.append(billing_lookup)
                    elif predicted_category == "technical":
                        tools.append(order_lookup)

                    spec_result = await run_specialist(
                        category=predicted_category,
                        subject=subject,
                        body=body,
                        tools=tools,
                    )
                    answer = spec_result.answer
                    confidence = spec_result.confidence
                    total_confidence += confidence
                    confidence_count += 1

                    if confidence < settings.confidence_threshold:
                        escalated = True
                        escalated_count += 1

                    keyword_score = keyword_overlap(answer, ideal_keywords)

                elapsed = time.monotonic() - t0

                result = {
                    "subject": subject[:45] + "..." if len(subject) > 45 else subject,
                    "expected": expected_category,
                    "predicted": predicted_category,
                    "correct": "✓" if routed_correctly else "✗",
                    "confidence": f"{confidence:.2f}" if confidence else "N/A",
                    "kw_score": f"{keyword_score:.0%}",
                    "escalated": "yes" if escalated else "no",
                    "latency_s": f"{elapsed:.1f}s",
                }
                results.append(result)

                status = "✓" if routed_correctly else "✗"
                print(f"       Route: {predicted_category} (expected: {expected_category}) {status} | conf: {confidence:.2f} | kw: {keyword_score:.0%}")

            except Exception as exc:
                print(f"       ERROR: {exc}")
                results.append({
                    "subject": subject[:45],
                    "expected": expected_category,
                    "predicted": "ERROR",
                    "correct": "✗",
                    "confidence": "N/A",
                    "kw_score": "N/A",
                    "escalated": "N/A",
                    "latency_s": "N/A",
                })

    # ── Summary ────────────────────────────────────────────────────────────────
    total = len(labeled)
    routing_accuracy = correct_routes / total
    avg_confidence = total_confidence / confidence_count if confidence_count else 0.0
    avg_kw = sum(
        float(r["kw_score"].rstrip("%")) / 100
        for r in results
        if r["kw_score"] not in ("N/A",)
    ) / max(len([r for r in results if r["kw_score"] != "N/A"]), 1)

    # Per-category accuracy
    categories = ["billing", "technical", "general", "unclear"]
    cat_stats = {}
    for cat in categories:
        cat_items = [r for r in results if r["expected"] == cat]
        if cat_items:
            cat_correct = sum(1 for r in cat_items if r["correct"] == "✓")
            cat_stats[cat] = f"{cat_correct}/{len(cat_items)} ({cat_correct/len(cat_items):.0%})"
        else:
            cat_stats[cat] = "N/A"

    print(f"\n{'='*60}")
    print("RESULTS TABLE")
    print(f"{'='*60}")
    columns = ["subject", "expected", "predicted", "correct", "confidence", "kw_score", "escalated", "latency_s"]
    print_table(results, columns)

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Overall Routing Accuracy : {routing_accuracy:.1%} ({correct_routes}/{total})")
    print(f"Average Confidence Score : {avg_confidence:.3f}")
    print(f"Average Keyword Overlap  : {avg_kw:.1%}")
    print(f"Escalation Rate          : {escalated_count}/{total} ({escalated_count/total:.1%})")
    print()
    print("Per-Category Accuracy:")
    for cat, stat in cat_stats.items():
        print(f"  {cat:<12}: {stat}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(run_eval())
