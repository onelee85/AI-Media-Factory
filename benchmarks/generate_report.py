#!/usr/bin/env python3
"""Timing report generator — converts benchmark results into human-readable reports.

Reads timing_results.json from pipeline_benchmark.py and produces:
- timing_report.md (human-readable)
- timing_report.json (structured data)

Usage:
    python benchmarks/generate_report.py
    python benchmarks/generate_report.py --input benchmarks/results/timing_results.json
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

QUAL_TARGET_SECONDS = 300  # 5 minutes


def compute_stats(values: list[float]) -> dict:
    """Compute min, max, avg, median for a list of values."""
    if not values:
        return {"min": 0, "max": 0, "avg": 0, "median": 0, "count": 0}
    return {
        "min": round(min(values), 2),
        "max": round(max(values), 2),
        "avg": round(statistics.mean(values), 2),
        "median": round(statistics.median(values), 2),
        "count": len(values),
    }


def generate_report(input_path: str, output_dir: str) -> None:
    """Generate timing report from benchmark results."""
    results_path = Path(input_path)
    output_path = Path(output_dir)

    if not results_path.exists():
        print(f"Error: {results_path} not found. Run pipeline_benchmark.py first.")
        sys.exit(1)

    with open(results_path) as f:
        results = json.load(f)

    completed = [r for r in results if r.get("status") == "completed"]
    failed = [r for r in results if r.get("status") == "failed"]

    if not completed:
        print("No completed runs to report on.")
        sys.exit(1)

    stages = ["script", "audio", "subtitles", "media", "compose"]

    # Per-stage statistics
    stage_stats = {}
    for stage in stages:
        times = [r["timing"][stage] for r in completed if r.get("timing", {}).get(stage) is not None]
        stage_stats[stage] = compute_stats(times)

    # Total time statistics
    total_times = [r["timing"]["total"] for r in completed if r.get("timing", {}).get("total") is not None]
    total_stats = compute_stats(total_times)

    # Bottleneck analysis
    avg_total = total_stats["avg"] if total_stats["count"] > 0 else 1
    bottleneck_stage = max(stages, key=lambda s: stage_stats[s]["avg"])
    bottleneck_pct = round((stage_stats[bottleneck_stage]["avg"] / avg_total) * 100, 1) if avg_total > 0 else 0

    # Pass/fail against QUAL-01
    qual_pass = total_stats["avg"] < QUAL_TARGET_SECONDS

    # Build structured report
    report_data = {
        "summary": {
            "total_runs": len(results),
            "completed": len(completed),
            "failed": len(failed),
            "qual_01_target_seconds": QUAL_TARGET_SECONDS,
            "qual_01_pass": qual_pass,
        },
        "total_time": total_stats,
        "stage_timings": stage_stats,
        "bottleneck": {
            "stage": bottleneck_stage,
            "avg_seconds": stage_stats[bottleneck_stage]["avg"],
            "percent_of_total": bottleneck_pct,
        },
        "per_run": [
            {
                "run_id": r.get("run_id"),
                "prompt": r.get("prompt", "")[:40],
                "lang": r.get("lang"),
                "status": r.get("status"),
                "timing": r.get("timing", {}),
            }
            for r in results
        ],
    }

    # Write JSON report
    output_path.mkdir(parents=True, exist_ok=True)
    json_path = output_path / "timing_report.json"
    with open(json_path, "w") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)

    # Generate Markdown report
    md_lines = [
        "# Pipeline Timing Report",
        "",
        f"**Generated:** {len(completed)} completed runs, {len(failed)} failed",
        f"**QUAL-01 Target:** < {QUAL_TARGET_SECONDS}s (5 minutes)",
        f"**Result:** {'PASS' if qual_pass else 'FAIL'} — Average total: {total_stats['avg']}s",
        "",
        "## Summary Statistics",
        "",
        "| Stage | Avg (s) | Min (s) | Max (s) | % of Total |",
        "|-------|---------|---------|---------|------------|",
    ]

    for stage in stages:
        stats = stage_stats[stage]
        pct = round((stats["avg"] / avg_total) * 100, 1) if avg_total > 0 else 0
        md_lines.append(f"| {stage} | {stats['avg']} | {stats['min']} | {stats['max']} | {pct}% |")

    md_lines.extend([
        f"| **total** | **{total_stats['avg']}** | **{total_stats['min']}** | **{total_stats['max']}** | 100% |",
        "",
        "## Bottleneck Analysis",
        "",
        f"**Biggest bottleneck:** {bottleneck_stage} stage ({bottleneck_pct}% of total time)",
        f"Average time: {stage_stats[bottleneck_stage]['avg']}s",
        "",
        "## Per-Run Details",
        "",
        "| Run | Prompt | Lang | Status | Total (s) | Script | Audio | Subs | Media | Compose |",
        "|-----|--------|------|--------|-----------|--------|-------|------|-------|---------|",
    ])

    for r in results:
        timing = r.get("timing", {})
        prompt_short = (r.get("prompt", "")[:25] + "...") if len(r.get("prompt", "")) > 25 else r.get("prompt", "")
        md_lines.append(
            f"| {r.get('run_id', '-')} | {prompt_short} | {r.get('lang', '-')} | {r.get('status', '-')} "
            f"| {timing.get('total', '-')} | {timing.get('script', '-')} | {timing.get('audio', '-')} "
            f"| {timing.get('subtitles', '-')} | {timing.get('media', '-')} | {timing.get('compose', '-')} |"
        )

    md_lines.extend(["", "---", ""])

    md_path = output_path / "timing_report.md"
    with open(md_path, "w") as f:
        f.write("\n".join(md_lines))

    print(f"Reports generated:")
    print(f"  Markdown: {md_path}")
    print(f"  JSON:     {json_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate timing report from benchmark results")
    parser.add_argument("--input", default="benchmarks/results/timing_results.json",
                        help="Input timing results JSON")
    parser.add_argument("--output-dir", default="benchmarks/results",
                        help="Output directory for reports")
    args = parser.parse_args()
    generate_report(args.input, args.output_dir)
