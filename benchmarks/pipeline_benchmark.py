#!/usr/bin/env python3
"""Pipeline benchmark runner — measures end-to-end video generation timing.

Runs the full pipeline with diverse test prompts and captures per-stage
timing data from Video.render_props.timing (instrumented in Phase 9).

Usage:
    python benchmarks/pipeline_benchmark.py --runs 1
    python benchmarks/pipeline_benchmark.py --runs 3 --prompt-index 0
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import async_session
from app.models.video import Video
from app.services.orchestrator import orchestrator_service
from sqlalchemy import select


TEST_PROMPTS = [
    {"prompt": "人工智能在医疗领域的应用", "voice": "zh-CN-YunxiNeural", "lang": "zh"},
    {"prompt": "The history of space exploration", "voice": "en-US-GuyNeural", "lang": "en"},
    {"prompt": "短视频创作的五个技巧", "voice": "zh-CN-XiaoxiaoNeural", "lang": "zh"},
    {"prompt": "How machine learning is changing education", "voice": "en-US-JennyNeural", "lang": "en"},
    {"prompt": "Python编程入门教程", "voice": "zh-CN-YunxiNeural", "lang": "zh"},
]


async def run_benchmark(prompt_config: dict, run_id: int) -> dict:
    """Run a single pipeline benchmark.

    Args:
        prompt_config: Dict with prompt, voice, lang keys.
        run_id: Run identifier for multi-run benchmarks.

    Returns:
        Dict with timing data and metadata.
    """
    prompt = prompt_config["prompt"]
    voice = prompt_config["voice"]
    lang = prompt_config["lang"]

    print(f"  [Run {run_id}] Starting pipeline: {prompt[:40]}... ({voice})")
    start_time = time.perf_counter()

    # Start pipeline
    result = await orchestrator_service.start_pipeline(
        prompt=prompt,
        title=f"Benchmark Run {run_id}",
        voice=voice,
    )

    video_id = result["video_id"]
    print(f"  [Run {run_id}] Video ID: {video_id}, polling for completion...")

    # Poll until done
    while True:
        await asyncio.sleep(2)
        async with async_session() as session:
            db_result = await session.execute(
                select(Video).where(Video.id == video_id)
            )
            video = db_result.scalar_one_or_none()
            if not video:
                print(f"  [Run {run_id}] ERROR: Video not found")
                return {"run_id": run_id, "prompt": prompt, "error": "Video not found"}

            status = video.status
            stage = (video.render_props or {}).get("stage", "unknown")
            elapsed = round(time.perf_counter() - start_time, 1)

            if status == "completed":
                timing = (video.render_props or {}).get("timing", {})
                print(f"  [Run {run_id}] COMPLETED in {elapsed}s — timing: {timing}")
                return {
                    "run_id": run_id,
                    "prompt": prompt,
                    "voice": voice,
                    "lang": lang,
                    "status": "completed",
                    "timing": timing,
                    "video_id": video_id,
                }
            elif status == "failed":
                error = video.error or "Unknown error"
                print(f"  [Run {run_id}] FAILED after {elapsed}s — {error}")
                return {
                    "run_id": run_id,
                    "prompt": prompt,
                    "voice": voice,
                    "lang": lang,
                    "status": "failed",
                    "error": error,
                    "video_id": video_id,
                }
            else:
                print(f"  [Run {run_id}] Stage: {stage} ({elapsed}s elapsed)")


async def main():
    parser = argparse.ArgumentParser(description="Pipeline benchmark runner")
    parser.add_argument("--runs", type=int, default=1, help="Number of runs per prompt")
    parser.add_argument("--prompt-index", type=int, default=None,
                        help="Run only a specific prompt by index (0-4)")
    parser.add_argument("--output", type=str, default="benchmarks/results/timing_results.json",
                        help="Output JSON file path")
    args = parser.parse_args()

    prompts = TEST_PROMPTS
    if args.prompt_index is not None:
        prompts = [TEST_PROMPTS[args.prompt_index]]

    results = []
    total_runs = len(prompts) * args.runs
    run_counter = 0

    print(f"Pipeline Benchmark: {len(prompts)} prompts × {args.runs} runs = {total_runs} total")
    print("=" * 60)

    for prompt_config in prompts:
        for run_num in range(1, args.runs + 1):
            run_counter += 1
            print(f"\n[{run_counter}/{total_runs}] Running benchmark...")
            result = await run_benchmark(prompt_config, run_num)
            results.append(result)

    # Save results
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n{'=' * 60}")
    print(f"Results saved to {output_path}")

    # Print summary table
    completed = [r for r in results if r.get("status") == "completed"]
    failed = [r for r in results if r.get("status") == "failed"]

    print(f"\nSummary: {len(completed)} completed, {len(failed)} failed, {len(results)} total")

    if completed:
        timings = [r.get("timing", {}).get("total", 0) for r in completed]
        avg_total = sum(timings) / len(timings)
        print(f"Average total time: {avg_total:.1f}s")
        print(f"Target: < 300s (5 minutes) — {'PASS' if avg_total < 300 else 'FAIL'}")

        # Per-stage averages
        stages = ["script", "audio", "subtitles", "media", "compose"]
        print(f"\n{'Stage':<12} {'Avg (s)':<10} {'Min (s)':<10} {'Max (s)':<10}")
        print("-" * 42)
        for stage in stages:
            stage_times = [r.get("timing", {}).get(stage, 0) for r in completed if r.get("timing", {}).get(stage)]
            if stage_times:
                avg = sum(stage_times) / len(stage_times)
                print(f"{stage:<12} {avg:<10.1f} {min(stage_times):<10.1f} {max(stage_times):<10.1f}")


if __name__ == "__main__":
    asyncio.run(main())
