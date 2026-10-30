"""
youtube_loader.py
Fetches and downloads YouTube videos at user-specified resolutions (720p, 1080p, etc.)
using yt-dlp, providing a local video path or stream for real-time computer learning.
"""

import os
import re
from typing import Optional, Tuple
import yt_dlp


class YouTubeStreamLoader:
    def __init__(self, download_dir: str = "downloads"):
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)

    def resolve_video(
        self,
        url_or_path: str,
        quality: str = "720p",
        progress_hook=None
    ) -> Tuple[str, str, int, int]:
        """
        Resolves a YouTube URL or local file path.
        Downloads YouTube video with yt-dlp to download_dir at requested resolution.
        Returns: (local_video_path, title, width, height)
        """
        # If it's already a local file
        if os.path.exists(url_or_path):
            return url_or_path, os.path.basename(url_or_path), 1280, 720

        # Check if already downloaded in download_dir by video ID
        video_id_match = re.search(r"(?:v=|youtu\.be\/|embed\/)([0-9A-Za-z_-]{11})", url_or_path)
        if video_id_match:
            vid_id = video_id_match.group(1)
            if os.path.exists(self.download_dir):
                for f in os.listdir(self.download_dir):
                    if vid_id in f and f.endswith((".mp4", ".mkv", ".webm")):
                        existing_path = os.path.join(self.download_dir, f)
                        if os.path.getsize(existing_path) > 10000:
                            print(f"[YouTubeLoader] Found existing stored video on disk: {existing_path}")
                            return existing_path, f, 1280, 720

        # Quality format selector
        height_match = re.search(r"(\d+)", quality)
        max_h = int(height_match.group(1)) if height_match else 720

        # Locate ffmpeg from imageio_ffmpeg if available
        ffmpeg_exe = None
        try:
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            pass

        format_str = (
            f"bestvideo[height<={max_h}][ext=mp4]+bestaudio[ext=m4a]/"
            f"best[height<={max_h}][ext=mp4]/"
            f"bestvideo[height<={max_h}]/best[height<={max_h}]/best"
        )

        output_template = os.path.join(self.download_dir, "%(title).50s [%(id)s] [%(height)sp].%(ext)s")

        ydl_opts = {
            "format": format_str,
            "outtmpl": output_template,
            "noplaylist": True,
            "quiet": False,
            "no_warnings": True,
            "merge_output_format": "mp4",
        }

        if ffmpeg_exe:
            ydl_opts["ffmpeg_location"] = ffmpeg_exe
            print(f"[YouTubeLoader] Using bundled ffmpeg: {ffmpeg_exe}")

        if progress_hook:
            ydl_opts["progress_hooks"] = [progress_hook]

        print(f"[YouTubeLoader] Fetching video from: {url_or_path} (Target: {quality})")

        # First probe the URL without downloading to catch "unavailable" early
        probe_opts = {"quiet": True, "no_warnings": True, "noplaylist": True, "skip_download": True}
        if ffmpeg_exe:
            probe_opts["ffmpeg_location"] = ffmpeg_exe
        try:
            with yt_dlp.YoutubeDL(probe_opts) as ydl_probe:
                probe_info = ydl_probe.extract_info(url_or_path, download=False)
            video_title_check = probe_info.get("title", "?")
            print(f"[YouTubeLoader] Video accessible: '{video_title_check}' — proceeding to download.")
        except Exception as probe_err:
            err_msg = str(probe_err)
            if "unavailable" in err_msg.lower() or "private" in err_msg.lower() or "removed" in err_msg.lower():
                raise ValueError(
                    f"Video is unavailable or private. Please paste a different YouTube URL.\n"
                    f"Details: {err_msg}"
                )
            # Not a fatal probe error — try downloading anyway (geo-block, age-gate, etc.)
            print(f"[YouTubeLoader] Probe warning (will still try download): {probe_err}")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url_or_path, download=True)
        except Exception as e:
            err_msg = str(e)
            if "unavailable" in err_msg.lower() or "private" in err_msg.lower():
                raise ValueError(
                    f"Video is unavailable or private. Please paste a different YouTube URL.\n"
                    f"Details: {err_msg}"
                )
            print(f"[YouTubeLoader] Note: Falling back to single-stream video without audio merge: {e}")
            ydl_opts["format"] = f"bestvideo[height<={max_h}]/best"
            ydl_opts.pop("merge_output_format", None)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url_or_path, download=True)

        video_id = info.get("id", "video")
        title = info.get("title", "YouTube Video")
        actual_w = info.get("width") or 1280
        actual_h = info.get("height") or max_h

        filename = ydl.prepare_filename(info)
        base, _ = os.path.splitext(filename)
        final_mp4 = f"{base}.mp4"
        if not os.path.exists(final_mp4):
            for candidate in [filename, f"{base}.mkv", f"{base}.webm"]:
                if os.path.exists(candidate):
                    final_mp4 = candidate
                    break

        print(f"[YouTubeLoader] Successfully stored on disk: {final_mp4} ({actual_w}x{actual_h})")
        return final_mp4, title, actual_w, actual_h


if __name__ == "__main__":
    loader = YouTubeStreamLoader()
    # Demo test
    print("YouTubeStreamLoader initialized ready for URL input.")
