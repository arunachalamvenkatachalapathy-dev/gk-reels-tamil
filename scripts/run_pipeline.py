"""Fail-closed placeholder. Tamil editorial material is not ready."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = ROOT / "data" / "questions_ta.json"
REVIEWED = ROOT / "data" / "reviewed_ta.json"


def main():
    if os.environ.get("PUBLISHING_ENABLED", "").lower() != "true":
        print("PAUSED: publishing remains disabled until owner verification and approval.")
        return
    questions = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    reviewed = json.loads(REVIEWED.read_text(encoding="utf-8"))
    if not questions or not reviewed:
        raise RuntimeError("Tamil source-checked question bank is empty; refusing to render or publish.")
    raise RuntimeError("Pipeline rendering is not installed yet; no content was uploaded.")


if __name__ == "__main__":
    main()
