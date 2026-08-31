#!/usr/bin/env python3
"""
Parse TRACEY sequence update log and generate a statistics report.
Usage: python parse_tracey_log.py <logfile> [--output report.txt]
"""

import re
import sys
import argparse
from collections import defaultdict


def parse_log(filepath):
    """Parse the log file and extract per-sequence update information."""

    # Patterns
    block_pattern = re.compile(r"Similarity block \((\d+)/(\d+)\):")
    entry_pattern = re.compile(r"^(\d+)\t(\S*)\t(\S+)\t(\S+)\t(.+)$")

    sequences = []  # list of dicts with info per sequence entry
    errors = []
    current_block = None
    total_blocks = None

    with open(filepath, "r") as f:
        for line in f:
            line = line.rstrip("\n")

            # Check for similarity block header
            block_match = block_pattern.search(line)
            if block_match:
                current_block = int(block_match.group(1))
                total_blocks = int(block_match.group(2))
                continue

            # Check for sequence entry
            entry_match = entry_pattern.match(line)
            if entry_match:
                tracey_id = entry_match.group(1)
                ncbi_id    = entry_match.group(2).strip()
                shortname  = entry_match.group(3).strip()
                old_name   = entry_match.group(4).strip()
                notes      = entry_match.group(5).strip()

                # Parse status transitions
                status_from = None
                status_to   = None

                status_change = re.search(
                    r"Sequencestatus changed from (\S+) to (\S+)", notes
                )
                if status_change:
                    status_from = status_change.group(1)
                    status_to   = status_change.group(2).rstrip(";")

                # Detect special events
                is_new_entry      = "New sequence entry created" in notes
                is_replaced       = "Sequence updated into NCBI ID" in notes
                is_identical      = "Identical sequence to tracey ID" in notes
                no_ncbi           = "no ncbi_id found" in notes
                dbxref_updated    = "dbxref updated" in notes
                has_error         = "ERROR" in notes

                if has_error:
                    errors.append({"tracey_id": tracey_id, "notes": notes})

                sequences.append({
                    "tracey_id":    tracey_id,
                    "ncbi_id":      ncbi_id,
                    "shortname":    shortname,
                    "old_name":     old_name,
                    "notes":        notes,
                    "status_from":  status_from,
                    "status_to":    status_to,
                    "is_new_entry": is_new_entry,
                    "is_replaced":  is_replaced,
                    "is_identical": is_identical,
                    "no_ncbi":      no_ncbi,
                    "dbxref_updated": dbxref_updated,
                    "has_error":    has_error,
                    "block":        current_block,
                })

    return sequences, errors, total_blocks


def generate_report(sequences, errors, total_blocks, logfile):
    """Generate a human-readable statistics report."""

    lines = []
    lines.append("=" * 60)
    lines.append("TRACEY DATABASE UPDATE REPORT")
    lines.append("=" * 60)
    lines.append(f"Log file      : {logfile}")
    lines.append(f"Total similarity blocks processed: {total_blocks}")
    lines.append(f"Total sequence entries parsed    : {len(sequences)}")
    lines.append("")

    # ── 1. Status transitions ────────────────────────────────────
    lines.append("-" * 60)
    lines.append("STATUS TRANSITIONS")
    lines.append("-" * 60)

    transitions = defaultdict(list)
    for s in sequences:
        if s["status_from"] and s["status_to"]:
            key = f"{s['status_from']} → {s['status_to']}"
            transitions[key].append(s["shortname"])

    if transitions:
        for transition, names in sorted(transitions.items(), key=lambda x: -len(x[1])):
            lines.append(f"  {transition:40s}: {len(names):4d} sequences")
    else:
        lines.append("  No status transitions found.")
    lines.append("")

    # ── 2. No change needed ──────────────────────────────────────
    no_change = [s for s in sequences if "No changes needed" in s["notes"]]
    lines.append(f"  No changes needed (already correct status): {len(no_change):4d} sequences")
    lines.append("")

    # ── 3. New entries created ───────────────────────────────────
    lines.append("-" * 60)
    lines.append("NEW SEQUENCE ENTRIES CREATED")
    lines.append("-" * 60)
    new_entries = [s for s in sequences if s["is_new_entry"]]
    lines.append(f"  Total new entries created: {len(new_entries)}")
    for s in new_entries:
        lines.append(f"    TRACEY ID {s['tracey_id']:>8s}  {s['shortname']}  ({s['ncbi_id']})")
    lines.append("")

    # ── 4. Sequences replaced by newer NCBI version ──────────────
    lines.append("-" * 60)
    lines.append("SEQUENCES REPLACED BY A NEW NCBI VERSION")
    lines.append("-" * 60)
    replaced = [s for s in sequences if s["is_replaced"]]
    lines.append(f"  Total replaced sequences: {len(replaced)}")
    for s in replaced:
        new_ncbi = re.search(r"Sequence updated into NCBI ID (\S+)", s["notes"])
        new_ncbi = new_ncbi.group(1).rstrip(";") if new_ncbi else "?"
        lines.append(
            f"    TRACEY ID {s['tracey_id']:>8s}  {s['shortname']:30s}  "
            f"{s['ncbi_id']} → {new_ncbi}"
        )
    lines.append("")

    # ── 5. Identical/duplicate sequences ─────────────────────────
    lines.append("-" * 60)
    lines.append("IDENTICAL / DUPLICATE SEQUENCES (no NCBI ID, not updated)")
    lines.append("-" * 60)
    identical = [s for s in sequences if s["is_identical"]]
    lines.append(f"  Total identical sequences skipped: {len(identical)}")
    for s in identical:
        ref_id = re.search(r"Identical sequence to tracey ID (\d+)", s["notes"])
        ref_id = ref_id.group(1) if ref_id else "?"
        lines.append(
            f"    TRACEY ID {s['tracey_id']:>8s}  {s['shortname']:30s}  "
            f"(duplicate of TRACEY ID {ref_id})"
        )
    lines.append("")

    # ── 6. dbxref updates ────────────────────────────────────────
    dbxref_updated = [s for s in sequences if s["dbxref_updated"]]
    lines.append("-" * 60)
    lines.append(f"DBXREF UPDATED: {len(dbxref_updated)} sequences")
    lines.append("")

    # ── 7. Errors ────────────────────────────────────────────────
    lines.append("-" * 60)
    lines.append("ERRORS")
    lines.append("-" * 60)
    lines.append(f"  Total errors encountered: {len(errors)}")
    for e in errors:
        lines.append(f"    TRACEY ID {e['tracey_id']:>8s}: {e['notes'][:120]}...")
    lines.append("")

    # ── 8. Summary table ─────────────────────────────────────────
    lines.append("=" * 60)
    lines.append("SUMMARY")
    lines.append("=" * 60)
    lines.append(f"  {'Total entries parsed':<45}: {len(sequences)}")
    lines.append(f"  {'Status transitions':<45}: {sum(len(v) for v in transitions.values())}")
    for t, names in sorted(transitions.items(), key=lambda x: -len(x[1])):
        lines.append(f"    {'- ' + t:<43}: {len(names)}")
    became_live = [s for s in sequences if s["status_to"] == "live"]
    left_live   = [s for s in sequences if s["status_from"] == "live"]
    lines.append(f"  {'Sequences that became live (any → live)':<45}: {len(became_live)}")
    lines.append(f"  {'Sequences that left live (live → any)':<45}: {len(left_live)}")
    lines.append(f"  {'No changes needed':<45}: {len(no_change)}")
    lines.append(f"  {'New entries created (live)':<45}: {len(new_entries)}")
    lines.append(f"  {'Replaced by newer NCBI version':<45}: {len(replaced)}")
    lines.append(f"  {'Identical/duplicate sequences skipped':<45}: {len(identical)}")
    lines.append(f"  {'Dbxref updated':<45}: {len(dbxref_updated)}")
    lines.append(f"  {'Errors':<45}: {len(errors)}")
    lines.append("=" * 60)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Parse TRACEY update log and generate a statistics report."
    )
    parser.add_argument("logfile", help="Path to the log file")
    parser.add_argument(
        "--output", "-o", default=None,
        help="Optional output file for the report (default: print to stdout)"
    )
    args = parser.parse_args()

    sequences, errors, total_blocks = parse_log(args.logfile)
    report = generate_report(sequences, errors, total_blocks, args.logfile)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Report written to {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()