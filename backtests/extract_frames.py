"""
Extract still frames from a strategy-teaching video so they can be read as
images (chart markup, drawn FVG zones, sweep arrows, etc.) instead of only
relying on a text transcript, which loses anything shown on screen but not
spoken aloud.

Two extraction modes, combinable:
- interval: one frame every N seconds (default 5s) -- guarantees even
  coverage regardless of how static the screen is.
- scene: ffmpeg scene-change detection -- catches the moment a chart/slide
  actually changes, which interval sampling can straddle and blur past.

Requires ffmpeg/ffprobe on PATH.
"""
import argparse
import os
import subprocess


def probe_duration(video_path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", video_path],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def extract_interval(video_path, out_dir, every_sec):
    os.makedirs(out_dir, exist_ok=True)
    pattern = os.path.join(out_dir, "interval_%05d.jpg")
    subprocess.run(
        ["ffmpeg", "-y", "-i", video_path, "-vf", f"fps=1/{every_sec}",
         "-qscale:v", "3", pattern],
        check=True, capture_output=True,
    )


def extract_scene_changes(video_path, out_dir, threshold):
    os.makedirs(out_dir, exist_ok=True)
    pattern = os.path.join(out_dir, "scene_%05d.jpg")
    subprocess.run(
        ["ffmpeg", "-y", "-i", video_path, "-vf",
         f"select='gt(scene,{threshold})',showinfo",
         "-vsync", "vfr", "-qscale:v", "3", pattern],
        check=True, capture_output=True,
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("video_path")
    ap.add_argument("out_dir")
    ap.add_argument("--mode", choices=["interval", "scene", "both"], default="both")
    ap.add_argument("--every-sec", type=float, default=5.0)
    ap.add_argument("--scene-threshold", type=float, default=0.3)
    args = ap.parse_args()

    duration = probe_duration(args.video_path)
    print(f"Video duration: {duration:.1f}s")

    if args.mode in ("interval", "both"):
        extract_interval(args.video_path, args.out_dir, args.every_sec)
    if args.mode in ("scene", "both"):
        extract_scene_changes(args.video_path, args.out_dir, args.scene_threshold)

    frames = sorted(os.listdir(args.out_dir))
    print(f"Extracted {len(frames)} frames into {args.out_dir}")
