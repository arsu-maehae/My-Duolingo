#!/usr/bin/env python3
"""
เพิ่มประโยคตัวอย่าง (jp_sentence & th_sentence) ลงใน CSV ด้วย Gemini (Batch Processing, quota-friendly)

- ใช้โมเดล: gemini-2.5-flash-lite (default)
- คุมจำนวน requests/day ด้วย batch_size ที่ใหญ่พอ
- parse JSON แบบ robust
- เขียนไฟล์แบบ atomic + checkpoint
- ถ้าชน daily free-tier quota -> เซฟแล้วหยุดทันที
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

DEFAULT_FILES = ["n5.csv"]


def get_gemini_key() -> str:
    key = os.environ.get("GEMINI_API_KEY")
    if not key or not key.strip():
        logging.error("กรุณาตั้งค่า GEMINI_API_KEY ก่อนรัน (ห้ามเป็นค่าว่าง)")
        sys.exit(2)
    return key.strip()


def extract_json_object(text: str) -> dict:
    raw = (text or "").strip()

    # Strip markdown fences if any
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw).strip()

    # Try direct parse
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # Find a JSON object substring
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        raise ValueError("No JSON object found in model output")

    candidate = m.group(0).strip()
    obj = json.loads(candidate)
    if not isinstance(obj, dict):
        raise ValueError("Extracted JSON is not an object")
    return obj


def is_quota_daily_free_tier(exc: Exception) -> bool:
    msg = str(exc)
    return (
        "generate_content_free_tier_requests" in msg
        and "GenerateRequestsPerDayPerProjectPerModel-FreeTier" in msg
    )


def is_rate_limit(exc: Exception) -> bool:
    msg = str(exc)
    return (
        "429" in msg
        or "RESOURCE_EXHAUSTED" in msg
        or "Too Many Requests" in msg
        or "rate" in msg.lower()
        or "quota" in msg.lower()
    )


def write_csv_atomic(path: Path, fieldnames, rows) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    tmp_path.replace(path)


def generate_sentences_batch(client, batch_rows, model_name: str, max_retries: int = 3) -> dict:
    """
    Return dict:
      { "0": {"jp": "...", "th": "..."}, "5": {"jp": "...", "th": "..."} }
    where keys are local indices inside batch_rows.
    """

    items = []
    for i, row in enumerate(batch_rows):
        # ข้ามถ้ามีแล้วทั้งคู่
        if (row.get("jp_sentence") or "").strip() and (row.get("th_sentence") or "").strip():
            continue

        jp_word = (row.get("expression") or "").strip()
        meaning_th = (row.get("ความหมาย") or "").strip()
        reading = (row.get("reading") or "").strip()

        if not jp_word:
            continue

        items.append((i, jp_word, reading, meaning_th))

    if not items:
        return {}

    # Prompt สั้น ๆ ชัด ๆ (ลดโอกาสหลุด JSON)
    items_text = "\n".join(
        f'{idx}: word="{jp_word}" reading="{reading}" th_hint="{meaning_th}"'
        for (idx, jp_word, reading, meaning_th) in items
    )

    prompt = f"""You are a Japanese teacher.

For EACH item, create ONE short, natural example sentence for JLPT N5 learners:
- Must include the given "word"
- Keep sentence short and simple
- Provide Thai translation
- Avoid rare kanji and long grammar
- Output STRICT JSON only:
{{ "ID": {{"jp":"...","th":"..."}}, ... }}
No extra text.

Items:
{items_text}
"""

    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            parsed = extract_json_object((resp.text or "").strip())
            return parsed

        except Exception as exc:
            last_err = exc

            # ถ้าชน daily free-tier: ไม่ต้อง retry
            if is_quota_daily_free_tier(exc):
                raise

            if is_rate_limit(exc):
                # backoff สั้น ๆ (แต่ถ้าเป็น daily limit จะถูกจับด้านบนแล้ว)
                sleep_s = min(120.0, 10.0 * (2 ** (attempt - 1)))
                sleep_s *= random.uniform(0.9, 1.2)
                logging.warning(f"⚠️ 429/Quota (attempt {attempt}/{max_retries}) -> sleep {sleep_s:.1f}s")
                time.sleep(sleep_s)
            else:
                sleep_s = min(20.0, 3.0 * attempt)
                logging.warning(f"❌ Error (attempt {attempt}/{max_retries}): {exc} -> sleep {sleep_s:.1f}s")
                time.sleep(sleep_s)

    logging.error(f"❌ Failed after retries. Last error: {last_err}")
    return {}


def process_file(
    client,
    path: Path,
    batch_size: int,
    model_name: str,
    checkpoint_every: int,
    min_interval: float,
) -> None:
    logging.info(f"📂 เริ่มแต่งประโยคให้ไฟล์: {path.name}")
    if not path.exists():
        logging.warning(f"หาไฟล์ไม่เจอ: {path}")
        return

    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    # เพิ่มคอลัมน์ใหม่ถ้ายังไม่มี
    if "jp_sentence" not in fieldnames:
        fieldnames.append("jp_sentence")
    if "th_sentence" not in fieldnames:
        fieldnames.append("th_sentence")

    total = len(rows)
    updated = 0
    api_calls = 0
    batches_since_ckpt = 0
    last_call_ts = 0.0

    def pace():
        nonlocal last_call_ts
        now = time.time()
        wait = (last_call_ts + min_interval) - now
        if wait > 0:
            time.sleep(wait)
        last_call_ts = time.time()

    for start in range(0, total, batch_size):
        batch = rows[start:start + batch_size]

        # ถ้าใน batch นี้ครบแล้วทั้งคู่ทุกแถว -> ข้าม
        if all((r.get("jp_sentence") or "").strip() and (r.get("th_sentence") or "").strip() for r in batch):
            continue

        logging.info(f"⏳ กำลังแต่งประโยคคำที่ {start+1} ถึง {min(start+batch_size, total)} / {total}")

        try:
            pace()
            results = generate_sentences_batch(client, batch, model_name=model_name)
            api_calls += 1
        except Exception as exc:
            if is_quota_daily_free_tier(exc):
                logging.error("🛑 ชนโควต้ารายวันของ Free tier แล้ว (requests/day/model). เซฟแล้วหยุดทันที.")
                write_csv_atomic(path, fieldnames, rows)
                return
            raise

        changed_this_batch = 0
        for idx_str, data in (results or {}).items():
            try:
                idx = int(idx_str)
            except Exception:
                continue
            if idx < 0 or idx >= len(batch):
                continue
            if not isinstance(data, dict):
                continue

            jp = (data.get("jp") or "").strip()
            th = (data.get("th") or "").strip()
            if not jp or not th:
                continue

            if not (batch[idx].get("jp_sentence") or "").strip():
                batch[idx]["jp_sentence"] = jp
            if not (batch[idx].get("th_sentence") or "").strip():
                batch[idx]["th_sentence"] = th

            updated += 1
            changed_this_batch += 1

        logging.info(f"   ↳ เพิ่ม/อัปเดต {changed_this_batch} ประโยคใน batch นี้")

        batches_since_ckpt += 1
        if batches_since_ckpt >= checkpoint_every:
            write_csv_atomic(path, fieldnames, rows)
            logging.info(f"💾 checkpoint: เขียนไฟล์แล้ว (ทุก {checkpoint_every} batch)")
            batches_since_ckpt = 0

    write_csv_atomic(path, fieldnames, rows)
    logging.info(f"✅ ไฟล์ {path.name} อัปเดตสำเร็จ! เพิ่ม/อัปเดต {updated} ประโยค")
    logging.info(f"📡 API calls โดยประมาณ: {api_calls}\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", nargs="*", default=DEFAULT_FILES)

    # quota-friendly defaults (เพราะ free tier จำกัด request/day)
    parser.add_argument("--batch-size", type=int, default=150)
    parser.add_argument("--model", type=str, default="gemini-2.5-flash-lite")

    parser.add_argument("--checkpoint-every", type=int, default=2)
    parser.add_argument("--min-interval", type=float, default=3.0)

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    api_key = get_gemini_key()
    client = genai.Client(api_key=api_key)

    data_dir = Path(__file__).resolve().parent.parent / "jp_datasets"

    for fname in args.files:
        fpath = data_dir / fname
        process_file(
            client=client,
            path=fpath,
            batch_size=args.batch_size,
            model_name=args.model,
            checkpoint_every=args.checkpoint_every,
            min_interval=args.min_interval,
        )


if __name__ == "__main__":
    main()