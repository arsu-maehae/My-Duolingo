#!/usr/bin/env python3
"""
Update/Append Thai synonyms in CSV column 'ความหมาย' using Gemini (Adaptive 429 handling)

Features:
- Appends/merges new synonyms into existing 'ความหมาย' (dedupe, keep order)
- target_total synonyms per row (default 4)
- Robust JSON extraction from model output
- Pre-call pacing (min_interval)
- Adaptive cooldown on repeated 429 (2m -> 5m -> 10m -> 20m -> 30m)
- Auto-fallback model on 429 (flash -> flash-lite)
- Atomic checkpoint writing
- Smoke test mode (1 tiny request)
"""

import argparse
import csv
import json
import logging
import os
import random
import re
import sys
import time
from pathlib import Path

from google import genai

DEFAULT_FILES = [f"n{i}.csv" for i in range(1, 6)]


# -----------------------------
# Utilities
# -----------------------------

def get_gemini_key() -> str:
    key = os.environ.get("GEMINI_API_KEY")
    if not key or not key.strip():
        logging.error("Environment variable GEMINI_API_KEY is missing/empty")
        sys.exit(2)
    return key.strip()


def split_thai_list(thai_value: str) -> list[str]:
    s = (thai_value or "").strip().strip('"')
    if not s:
        return []
    return [p.strip() for p in s.split(",") if p.strip()]


def normalize_token(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").strip())


def merge_synonyms(existing: list[str], new_items: list[str], cap: int) -> list[str]:
    seen = set()
    merged: list[str] = []
    for t in existing:
        nt = normalize_token(t)
        if nt and nt not in seen:
            merged.append(nt)
            seen.add(nt)
    for t in new_items:
        nt = normalize_token(t)
        if nt and nt not in seen:
            merged.append(nt)
            seen.add(nt)
    return merged[:cap]


def extract_json_object(text: str) -> dict:
    raw = (text or "").strip()

    # Strip markdown fences if any
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw).strip()

    # Direct parse
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # Find first {...} block
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        raise ValueError("No JSON object found in model output")

    candidate = m.group(0).strip()
    obj = json.loads(candidate)
    if not isinstance(obj, dict):
        raise ValueError("Extracted JSON is not an object")
    return obj


def is_quota_error(exc: Exception) -> bool:
    msg = str(exc)
    return (
        "429" in msg
        or "RESOURCE_EXHAUSTED" in msg
        or "Too Many Requests" in msg
        or "rate" in msg.lower()
        or "quota" in msg.lower()
    )


def pace(last_call_ts: float, min_interval: float) -> float:
    """Ensure at least min_interval seconds between API calls."""
    now = time.time()
    wait = (last_call_ts + min_interval) - now
    if wait > 0:
        time.sleep(wait)
    return time.time()


def write_csv_atomic(path: Path, fieldnames, rows) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    tmp_path.replace(path)


# -----------------------------
# Gemini calls
# -----------------------------

def generate_additions_batch_once(
    client,
    batch_rows: list[dict],
    model_name: str,
    target_total: int,
) -> dict:
    """
    One attempt only. Caller handles retries/cooldowns.
    Returns dict: { "local_index_in_batch": "new1, new2" }
    Values are ONLY additions.
    """

    items = []
    for i, row in enumerate(batch_rows):
        existing = split_thai_list(row.get("ความหมาย") or "")
        need = max(0, target_total - len(existing))
        if need == 0:
            continue

        meaning_en = (row.get("meaning") or "").strip()
        jp_expr = (row.get("expression") or "").strip()
        jp_read = (row.get("reading") or "").strip()

        items.append((i, need, existing, jp_expr, jp_read, meaning_en))

    if not items:
        return {}

    items_text = "\n".join(
        f'{idx}: need={need} | existing="{", ".join(existing)}" | JP="{jp_expr}" ({jp_read}) | EN="{meaning_en}"'
        for (idx, need, existing, jp_expr, jp_read, meaning_en) in items
    )

    prompt = f"""You add Thai synonyms for a language-learning dataset.

For EACH item:
- Generate EXACTLY the number of NEW Thai synonyms requested by "need"
- NEW synonyms must NOT repeat any word/phrase already in "existing"
- Each synonym should be short (word or short phrase)
- Return STRICT JSON object only:
{{ "ID": "new1, new2", ... }}

Rules:
- Thai only in values
- No extra text, no markdown

Items:
{items_text}
"""

    resp = client.models.generate_content(model=model_name, contents=prompt)
    raw = (resp.text or "").strip()
    return extract_json_object(raw)


def smoke_test(client, model_name: str) -> None:
    """One tiny request to see if quota is currently allowing calls."""
    prompt = 'Return STRICT JSON only: {"0":"ทดสอบ, ทดลอง, เช็ค"}'
    resp = client.models.generate_content(model=model_name, contents=prompt)
    _ = extract_json_object((resp.text or "").strip())


# -----------------------------
# Adaptive runner
# -----------------------------

def process_file(
    client,
    path: Path,
    batch_size: int,
    model_name: str,
    fallback_model: str,
    checkpoint_every: int,
    target_total: int,
    min_interval: float,
    max_batch_retries: int,
    cooldown_schedule: list[int],
) -> None:
    logging.info(f"📂 เริ่มประมวลผลไฟล์: {path.name}")
    if not path.exists():
        logging.warning(f"หาไฟล์ไม่เจอ: {path}")
        return

    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    if "ความหมาย" not in fieldnames:
        logging.warning("ไม่พบคอลัมน์ 'ความหมาย' ข้ามไฟล์นี้")
        return

    total = len(rows)
    updated_rows = 0
    api_calls = 0
    batches_since_checkpoint = 0
    last_call_ts = 0.0

    # Adaptive state
    current_model = model_name
    cooldown_level = 0
    consecutive_quota_fail_batches = 0

    for start in range(0, total, batch_size):
        batch = rows[start: start + batch_size]

        # Skip if already complete for all rows in this batch
        if all(len(split_thai_list(r.get("ความหมาย") or "")) >= target_total for r in batch):
            continue

        logging.info(f"⏳ เติมคำที่ {start+1} ถึง {min(start+batch_size, total)} / {total}")

        # Try this batch with limited retries; if quota blocks, cooldown and retry later
        success = False
        for attempt in range(1, max_batch_retries + 1):
            # Pre-call pacing
            last_call_ts = pace(last_call_ts, min_interval=min_interval)

            try:
                results = generate_additions_batch_once(
                    client=client,
                    batch_rows=batch,
                    model_name=current_model,
                    target_total=target_total,
                )
                api_calls += 1

                changed_this_batch = 0
                for idx_str, additions_str in (results or {}).items():
                    try:
                        idx = int(idx_str)
                    except Exception:
                        continue
                    if idx < 0 or idx >= len(batch):
                        continue

                    existing_list = split_thai_list(batch[idx].get("ความหมาย") or "")
                    need = max(0, target_total - len(existing_list))
                    if need == 0:
                        continue

                    additions_list = split_thai_list(additions_str or "")
                    additions_list = additions_list[:need]  # keep only needed count

                    merged = merge_synonyms(existing_list, additions_list, cap=target_total)
                    merged_str = ", ".join(merged)

                    old = (batch[idx].get("ความหมาย") or "").strip().strip('"')
                    if merged_str and merged_str != old:
                        batch[idx]["ความหมาย"] = merged_str
                        updated_rows += 1
                        changed_this_batch += 1

                logging.info(f"   ↳ อัปเดต/เติมเพิ่ม {changed_this_batch} แถวใน batch นี้")

                # Reset quota-fail streak on success
                consecutive_quota_fail_batches = 0
                cooldown_level = max(0, cooldown_level - 1)  # slowly relax
                current_model = model_name  # return to main model after success
                success = True
                break

            except Exception as exc:
                if is_quota_error(exc):
                    # Escalate cooldown
                    consecutive_quota_fail_batches += 1
                    cooldown_level = min(cooldown_level + 1, len(cooldown_schedule) - 1)

                    # Switch to fallback model if quota keeps failing
                    if consecutive_quota_fail_batches >= 2 and fallback_model:
                        current_model = fallback_model

                    sleep_s = cooldown_schedule[cooldown_level]
                    # small jitter so you don't align with quota windows badly
                    sleep_s = int(sleep_s * random.uniform(0.9, 1.1))

                    logging.warning(
                        f"⚠️ 429/Quota (batch retry {attempt}/{max_batch_retries}) "
                        f"model={current_model} -> cooldown {sleep_s}s"
                    )
                    time.sleep(sleep_s)

                    # If quota seems totally blocked, stop retrying this batch for now
                    if attempt >= max_batch_retries:
                        logging.warning("⏸️ โควต้ายังตึงมาก: ข้ามไป batch ถัดไปก่อน (resume ได้)")
                else:
                    # Non-quota error: short backoff and retry
                    wait = min(30, 3 * attempt)
                    logging.warning(f"❌ Error (batch retry {attempt}/{max_batch_retries}): {exc} -> sleep {wait}s")
                    time.sleep(wait)

        # checkpoint writing occasionally even if not success (so far progress saved)
        batches_since_checkpoint += 1
        if batches_since_checkpoint >= checkpoint_every:
            write_csv_atomic(path, fieldnames, rows)
            logging.info(f"💾 checkpoint: เขียนไฟล์แล้ว (ทุก {checkpoint_every} batch)")
            batches_since_checkpoint = 0

    write_csv_atomic(path, fieldnames, rows)
    logging.info(f"✅ ไฟล์ {path.name} เสร็จ! เติม/อัปเดตทั้งหมด {updated_rows} แถว")
    logging.info(f"📡 API calls โดยประมาณ: {api_calls}\n")


# -----------------------------
# Main
# -----------------------------

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", nargs="*", default=DEFAULT_FILES)

    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--target-total", type=int, default=4)

    parser.add_argument("--model", type=str, default="gemini-2.5-flash")
    parser.add_argument("--fallback-model", type=str, default="gemini-2.5-flash-lite")

    parser.add_argument("--min-interval", type=float, default=90.0)
    parser.add_argument("--checkpoint-every", type=int, default=4)

    parser.add_argument("--max-batch-retries", type=int, default=3)

    parser.add_argument("--smoke-test", action="store_true")
    parser.add_argument("--force-disable-afc", action="store_true",
                        help="Best-effort: set env vars to reduce AFC/auto-remote behavior (SDK-dependent).")

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.force_disable_afc:
        # SDK-dependent best-effort toggles (won't crash if ineffective)
        os.environ.setdefault("GOOGLE_GENAI_DISABLE_AFC", "1")
        os.environ.setdefault("GENAI_DISABLE_AFC", "1")

    api_key = get_gemini_key()
    client = genai.Client(api_key=api_key)

    if args.smoke_test:
        logging.info("🧪 Smoke test (1 tiny request)...")
        smoke_test(client, args.model)
        logging.info("✅ Smoke test passed")
        return

    data_dir = Path(__file__).resolve().parent.parent / "jp_datasets"

    # Cooldown ladder for quota pressure (seconds)
    # escalates when 429 repeats; relaxes slowly after success
    cooldown_schedule = [30, 120, 300, 600, 1200, 1800]  # 30s, 2m, 5m, 10m, 20m, 30m

    for fname in args.files:
        fpath = data_dir / fname
        process_file(
            client=client,
            path=fpath,
            batch_size=args.batch_size,
            model_name=args.model,
            fallback_model=args.fallback_model,
            checkpoint_every=args.checkpoint_every,
            target_total=args.target_total,
            min_interval=args.min_interval,
            max_batch_retries=args.max_batch_retries,
            cooldown_schedule=cooldown_schedule,
        )

    logging.info("🎉 ปิดจ๊อบ! เติม synonym ครบตาม target แล้ว!")


if __name__ == "__main__":
    main()