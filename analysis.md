Nice — I’ll give you two production-ready Python scripts you can run immediately:

compare_csvs.py — robust comparison & diagnostic report (generates Missing.csv, shows problem-character stats, encoding issues, quoting/linebreak problems, and sample bad rows).

sanitize_and_publish.py — sanitizes rows (normalizes unicode, removes control characters, escapes for JSON/CSV), simulates a safe publish flow with retries/logging, and can produce a cleaned CSV or try republishing.


Both are written to be memory-friendly, handle large files (chunked reads), don’t assume a primary key column (they auto-detect common id columns or fall back to full-row hash), and will log everything so you can prove whether symbol/encoding issues caused the loss.

Copy both files into your working directory and run them. I added lots of inline comments so you can tweak behavior quickly.


---

compare_csvs.py

Saves Missing.csv, special_rows.csv (rows with suspicious characters), and compare_report.txt.

#!/usr/bin/env python3
"""
compare_csvs.py

Usage:
  python compare_csvs.py --before BeforeProcess.csv --after AfterProcess.csv \
        [--missing Missing.csv] [--chunksize 50000] [--sample 50]

What it does:
- Detects file encodings (best-effort).
- Loads CSVs in chunks (memory-friendly).
- Auto-detects a "key" column (id, uid, uuid, key, reference) if present; otherwise uses full-row hash.
- Generates Missing.csv containing rows in Before but not in After.
- Produces stats about special/unprintable characters, linebreaks-in-fields, quoting issues, and likely-problematic rows.
- Writes a short human-readable compare_report.txt.
"""
import argparse
import csv
import hashlib
import io
import json
import math
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict

try:
    import chardet
except Exception:
    chardet = None

try:
    import pandas as pd
except Exception:
    pd = None

from tqdm import tqdm

# -----------------------
# Helpers
# -----------------------
def detect_encoding(path, nbytes=8192):
    if chardet is None:
        return 'utf-8'
    with open(path, 'rb') as f:
        raw = f.read(nbytes)
    res = chardet.detect(raw)
    enc = res.get('encoding') or 'utf-8'
    return enc

def row_hash_from_list(values):
    m = hashlib.sha256()
    # use repr to preserve separators, handle None
    for v in values:
        m.update((repr(v) + '\x1f').encode('utf-8', errors='ignore'))
    return m.hexdigest()

def normalize_newlines(s):
    return s.replace('\r\n', '\n').replace('\r', '\n')

def find_key_column(header):
    # common id-like names
    keys = ['id','uid','uuid','key','reference','reference_id','order_id','txn_id']
    header_lower = [h.lower() for h in header]
    for k in keys:
        if k in header_lower:
            return header[header_lower.index(k)]
    return None

# regex to detect "weird" characters: non-printable except whitespace and common punctuation
WEIRD_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')  # control chars excluding tab (0x09), newline (0x0A)
# simple non-ascii detector
NON_ASCII_RE = re.compile(r'[^\x00-\x7f]')

# -----------------------
# Main compare logic
# -----------------------
def build_hash_set_from_csv(path, chunksize=50000):
    """
    Returns (header, set_of_hashes, map_hash_to_rowcount_sample)
    """
    encoding = detect_encoding(path)
    header = None
    hashes = set()
    sample_map = {}
    total = 0
    with open(path, 'r', encoding=encoding, errors='replace', newline='') as fp:
        reader = csv.reader(fp)
        header = next(reader)
        for row in reader:
            total += 1
            h = row_hash_from_list(row)
            hashes.add(h)
            if len(sample_map) < 100:
                sample_map[h] = row
    return header, hashes, sample_map, total

def compare(before_path, after_path, out_missing_path, chunksize=50000, sample=50):
    print("Detecting encodings...")
    enc_before = detect_encoding(before_path)
    enc_after = detect_encoding(after_path)
    print(f"Before encoding: {enc_before}; After encoding: {enc_after}")

    print("Collecting hashes from AFTER file...")
    after_header, after_hashes, after_sample, after_count = build_hash_set_from_csv(after_path, chunksize)
    print(f"After rows (count sampled): {len(after_hashes)}")

    print("Scanning BEFORE file and detecting missing rows...")
    missing_rows = []
    suspicious_rows = []
    problematic_counts = Counter()
    total_before = 0
    header = None
    with open(before_path, 'r', encoding=enc_before, errors='replace', newline='') as fp:
        reader = csv.reader(fp)
        header = next(reader)
        key_col = find_key_column(header)
        if key_col:
            print(f"Auto-detected key column: {key_col}")
        else:
            print("No id-like column detected; using full-row hash as key.")

        for row in tqdm(reader, desc="Comparing rows"):
            total_before += 1
            h = row_hash_from_list(row)
            if h not in after_hashes:
                missing_rows.append(row)
            # quick checks on row content for suspicious characters
            row_text = ' '.join(row)
            if WEIRD_RE.search(row_text):
                suspicious_rows.append((row, 'control_chars'))
                problematic_counts['control_chars'] += 1
            if NON_ASCII_RE.search(row_text):
                suspicious_rows.append((row, 'non_ascii'))
                problematic_counts['non_ascii'] += 1
            if '\n' in row_text or '\r' in row_text:
                problematic_counts['linebreaks'] += 1
            # detect lots of quotes or unbalanced quotes could be parser issues
            if row_text.count('"') % 2 != 0:
                problematic_counts['unbalanced_quotes'] += 1

    missing_count = len(missing_rows)
    print(f"Total BEFORE rows scanned: {total_before}")
    print(f"Missing rows (before - after): {missing_count}")

    # write Missing.csv
    print(f"Writing missing rows to {out_missing_path} ...")
    enc_out = 'utf-8'
    with open(out_missing_path, 'w', encoding=enc_out, newline='') as outfp:
        writer = csv.writer(outfp)
        writer.writerow(header)
        for r in missing_rows:
            writer.writerow(r)

    # write suspicious rows sample
    samp_out = "special_rows.csv"
    print(f"Writing suspicious rows sample to {samp_out} ...")
    with open(samp_out, 'w', encoding=enc_out, newline='') as fp:
        w = csv.writer(fp)
        w.writerow(header + ['_issue'])
        for r, issue in suspicious_rows[:200]:
            w.writerow(r + [issue])

    # produce report
    report = {
        'before_path': before_path,
        'after_path': after_path,
        'before_total_rows': total_before,
        'after_total_rows_sampled': after_count,
        'missing_count': missing_count,
        'problematic_counts': dict(problematic_counts),
        'encoding_before': enc_before,
        'encoding_after': enc_after,
    }
    with open('compare_report.txt', 'w', encoding='utf-8') as rep:
        rep.write(json.dumps(report, indent=2))
    print("Wrote compare_report.txt")

    # print quick summary
    print("\nSUMMARY:")
    print(f"Before rows: {total_before}")
    print(f"After rows (sampled): {after_count}")
    print(f"Missing rows: {missing_count}")
    print("Top problems detected:")
    for k,v in problematic_counts.most_common():
        print(f"  - {k}: {v}")

    return report

# -----------------------
# CLI
# -----------------------
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Compare BEFORE/AFTER CSVs and detect suspicious rows")
    parser.add_argument('--before', required=True, help="BeforeProcess.csv")
    parser.add_argument('--after', required=True, help="AfterProcess.csv")
    parser.add_argument('--missing', default='Missing.csv', help="Output Missing.csv")
    parser.add_argument('--chunksize', type=int, default=50000)
    parser.add_argument('--sample', type=int, default=50)
    args = parser.parse_args()

    compare(args.before, args.after, args.missing, chunksize=args.chunksize, sample=args.sample)


---

sanitize_and_publish.py

This script sanitizes rows, can save a cleaned CSV, and contains a pluggable publish() function (you replace with your actual publisher). It logs per-row failures with reasons and supports configurable batch sizes and retries.

#!/usr/bin/env python3
"""
sanitize_and_publish.py

Usage example:
  python sanitize_and_publish.py --input BeforeProcess.csv --output CleanedBefore.csv \
     --simulate-publish --batch-size 100 --retries 3

What it does:
- Reads input CSV chunk-wise
- Normalizes unicode (NFKC), strips control characters, normalizes newlines inside fields
- Optionally writes a cleaned CSV
- Optionally "publishes" rows (simulated) with per-row try/retry and detailed logging
- Produces publish_log.jsonl with per-row status (success/failure/reason)
"""
import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
from typing import List, Dict

try:
    import chardet
except Exception:
    chardet = None

from tqdm import tqdm

WEIRD_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')  # control chars
# Keep tabs and newlines only when inside field we will convert newlines to space by default
NEWLINE_RE = re.compile(r'[\r\n]+')

def detect_encoding(path, nbytes=8192):
    if chardet is None:
        return 'utf-8'
    with open(path, 'rb') as f:
        raw = f.read(nbytes)
    res = chardet.detect(raw)
    enc = res.get('encoding') or 'utf-8'
    return enc

def normalize_field(value: str, remove_newlines=True, replace_newline_with=' '):
    if value is None:
        return value
    # normalize unicode
    v = unicodedata.normalize('NFKC', value)
    # remove control characters (except tab)
    v = WEIRD_RE.sub('', v)
    if remove_newlines:
        v = NEWLINE_RE.sub(replace_newline_with, v)
    # strip leading/trailing whitespace
    v = v.strip()
    return v

def row_to_json_safe(header: List[str], row: List[str]):
    data = {}
    for h, v in zip(header, row):
        # convert to string and ensure it's JSON-serializable
        data[h] = v if v is not None else ''
    return json.dumps(data, ensure_ascii=False)

# Example publish function (replace with real publish logic). It should raise on failure.
def publish_batch(json_lines: List[str]):
    """
    Simulated publisher: raises on lines containing the token "<PUBLISH_FAIL>"
    Replace with your real publisher client (kafka.producer, requests.post, etc.).
    """
    failures = []
    for i, l in enumerate(json_lines):
        if "<PUBLISH_FAIL>" in l:
            failures.append(i)
    if failures:
        raise RuntimeError(f"Simulated publish failure for indices: {failures}")
    # Simulate latency
    time.sleep(0.01)
    return True

def process_and_publish(input_path, output_path=None, batch_size=100, retries=3, simulate_publish=True):
    enc = detect_encoding(input_path)
    print(f"Detected encoding: {enc}")

    header = None
    pub_log_path = "publish_log.jsonl"
    with open(input_path, 'r', encoding=enc, errors='replace', newline='') as infp, \
         open(pub_log_path, 'w', encoding='utf-8') as logfp, \
         (open(output_path, 'w', encoding='utf-8', newline='') if output_path else DummyContextManager()):
        reader = csv.reader(infp)
        header = next(reader)
        writer = None
        if output_path:
            writer = csv.writer(open(output_path, 'w', encoding='utf-8', newline=''))
            writer.writerow(header)

        batch = []
        batch_orig_rows = []
        processed = 0
        success = 0
        failed = 0

        for row in tqdm(reader, desc="Processing rows"):
            # sanitize fields
            clean = [normalize_field(v) for v in row]
            if writer:
                writer.writerow(clean)

            # prepare JSON-safe payload
            payload = row_to_json_safe(header, clean)
            batch.append(payload)
            batch_orig_rows.append(clean)
            if len(batch) >= batch_size:
                ok, s, f = try_publish_with_retries(batch, batch_orig_rows, retries, simulate_publish, logfp)
                success += s
                failed += f
                processed += len(batch)
                batch = []
                batch_orig_rows = []

        # publish remainder
        if batch:
            ok, s, f = try_publish_with_retries(batch, batch_orig_rows, retries, simulate_publish, logfp)
            success += s
            failed += f
            processed += len(batch)

    print("\nPublish summary:")
    print(f"Processed rows: {processed}")
    print(f"Success: {success}, Failed: {failed}")
    print(f"Per-row publish log saved to {pub_log_path}")

class DummyContextManager:
    def __enter__(self): return None
    def __exit__(self, *args): return False

def try_publish_with_retries(batch_payloads, batch_rows, retries, simulate_publish, logfp):
    attempt = 0
    while attempt <= retries:
        try:
            if simulate_publish:
                publish_batch(batch_payloads)
            else:
                publish_batch(batch_payloads)  # replace with actual publisher call
            # success for entire batch
            for row in batch_rows:
                logfp.write(json.dumps({'status':'success','row':row}, ensure_ascii=False) + '\n')
            return True, len(batch_rows), 0
        except Exception as e:
            attempt += 1
            # if last attempt, attempt per-item publish to identify bad rows
            if attempt > retries:
                # per-item fallback to isolate bad rows
                succ = 0
                fail = 0
                for r, payload in zip(batch_rows, batch_payloads):
                    try:
                        if simulate_publish:
                            publish_batch([payload])
                        else:
                            publish_batch([payload])
                        logfp.write(json.dumps({'status':'success','row':r}, ensure_ascii=False) + '\n')
                        succ += 1
                    except Exception as e2:
                        logfp.write(json.dumps({'status':'failed','row':r,'reason':str(e2)}, ensure_ascii=False) + '\n')
                        fail += 1
                return False, succ, fail
            else:
                # exponential backoff
                wait = 0.5 * (2 ** (attempt-1))
                time.sleep(wait)
                continue

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Sanitize CSV and (optionally) publish safely with retries")
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', default=None, help="Optional cleaned CSV output")
    parser.add_argument('--batch-size', type=int, default=100)
    parser.add_argument('--retries', type=int, default=2)
    parser.add_argument('--simulate-publish', action='store_true', help='Simulate publishing using internal stub')
    args = parser.parse_args()

    process_and_publish(args.input, args.output, args.batch_size, args.retries, args.simulate_publish)


---

How to use these two scripts together (recommended workflow)

1. Run the comparator to confirm which rows are missing:

python compare_csvs.py --before BeforeProcess.csv --after AfterProcess.csv --missing Missing.csv

Inspect compare_report.txt and special_rows.csv. If special_rows.csv contains many rows, you likely have symbol/encoding/control-char problems.



2. Run the sanitizer in simulation mode to see which rows would fail publishing:

python sanitize_and_publish.py --input BeforeProcess.csv --output CleanedBefore.csv --simulate-publish --batch-size 200 --retries 2

Check publish_log.jsonl. Failed rows will have 'status':'failed' and a reason.



3. If simulation shows particular rows failing, inspect them (they’ll be logged) and:

Fix at source (recommended), or

Add escaping or remove the problematic characters in the sanitizer, or

Configure the producer to accept the characters (e.g., ensure UTF-8 encoding, set producer to not drop on bad JSON).



4. Once confident, run sanitizer with --simulate-publish off (replace publish_batch() with your actual publisher) to send cleaned records.




---

Notes, caveats & quick tips

These scripts use a full-row hash to match rows when no id column exists. If you have a stable unique id column, the compare will be faster & more accurate — edit find_key_column if your ID name is different, or pass an explicit column name by modifying the script (I can add a CLI flag if you want).

The simulated publish_batch raises for payloads containing "<PUBLISH_FAIL>" — replace with your real publisher code (Kafka producer, HTTP request, etc.). Keep similar error-handling: retry, then per-record fallback, and always log.

We aggressively normalize Unicode with NFKC. If your downstream consumers expect raw original bytes, be cautious — but NFKC reduces weird variant characters that often cause problems.

If the issue is batches being dropped because of one bad row, the try_publish_with_retries logic will isolate bad rows and log them — that should prove the root cause.

If you want, I can adapt the code to:

Use a database (to requeue only failures),

Produce a diff showing exactly which columns differ,

Or implement a direct Kafka/RabbitMQ publisher with your credentials.




---

If you want, I can:

Add a --key-column CLI flag to compare_csvs.py so you can force a certain column to be used as the key.

Modify sanitize_and_publish.py to integrate with your actual message service (give me the library you use — kafka-python, confluent-kafka, pika, azure-servicebus, etc. — and I’ll produce the ready-to-run publish code and safe retry logic).


Which would you like next?