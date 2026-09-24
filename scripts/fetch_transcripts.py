#!/usr/bin/env python3
"""
Pull Chinese (and English) subtitles for the channels in channels.csv.

  ./.venv/bin/python3 scripts/fetch_transcripts.py
  ./.venv/bin/python3 scripts/fetch_transcripts.py --only VIDEO_ID --verbose
  ./.venv/bin/python3 scripts/fetch_transcripts.py --probe VIDEO_ID

Needs:  uv pip install yt-dlp curl_cffi        (plus Deno, see preflight)

Everything goes through yt-dlp. youtube-transcript-api hits a separate
timedtext endpoint that YouTube fingerprints hard, and corporate or datacenter
IPs get blocked within a handful of requests.

Manual and auto-generated captions are requested together in one pass; yt-dlp
prefers a real subtitle track when the video has one. Most channels only have
auto-generated captions, so looking for manual tracks separately just doubled
the requests.

Caches, so re-running only costs new uploads:
  scripts/cache/videos/<channel>.json   video IDs per channel
  scripts/cache/subs/<id>.<lang>.<ext>  raw subtitle files
  scripts/cache/transcripts/<id>.json   parsed, what build_clips.py reads
"""

import argparse, csv, json, os, re, shutil, subprocess, sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
CACHE = HERE / "cache"
VIDEO_CACHE, SUB_CACHE, TRANSCRIPT_CACHE = (
    CACHE / "videos", CACHE / "subs", CACHE / "transcripts")

ZH_LANGS = ["zh-Hans", "zh-CN", "zh", "zh-Hant", "zh-TW", "zh-HK"]
EN_LANGS = ["en", "en-US", "en-GB", "en-orig"]
SUB_LANGS = ",".join(ZH_LANGS + EN_LANGS)
SUB_EXTS = ("json3", "srv3", "vtt", "srt")

YTDLP = None
VERBOSE = False


# ---------------------------------------------------------------- yt-dlp

def find_ytdlp():
    """
    Resolve yt-dlp explicitly. A system apt copy and a venv copy can both
    exist, and PATH order decides which runs — which is how you upgrade one
    and keep running the other. Override with YTDLP=/path/to/yt-dlp.
    """
    if os.environ.get("YTDLP"):
        return os.environ["YTDLP"]
    beside = Path(sys.executable).parent / "yt-dlp"
    return str(beside) if beside.exists() else (
        shutil.which("yt-dlp") or sys.exit("yt-dlp not found: uv pip install yt-dlp"))


def run_ytdlp(args, timeout=900):
    global YTDLP
    if YTDLP is None:
        YTDLP = find_ytdlp()
    try:
        return subprocess.run([YTDLP, *args], capture_output=True,
                              text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None


def preflight():
    """
    Three things whose absence shows up as vague warnings and empty downloads
    rather than a clear error, so check them up front.
    """
    global YTDLP
    YTDLP = find_ytdlp()
    out = run_ytdlp(["--version"], timeout=60)
    version = out.stdout.strip().splitlines()[0] if out and out.stdout.strip() else "?"
    print(f"yt-dlp {version}  ({YTDLP})")

    problems = []
    try:
        age = (datetime.now() - datetime.strptime(version[:10], "%Y.%m.%d")).days
        if age > 60:
            problems.append(
                f"yt-dlp is {age} days old. YouTube changes how captions are\n"
                "  exposed often, and a stale extractor returns nothing while\n"
                "  everything else still looks fine.\n"
                "      uv pip install --upgrade yt-dlp")
    except ValueError:
        pass

    try:
        import curl_cffi  # noqa: F401
    except ImportError:
        problems.append(
            "curl_cffi is missing. YouTube requires TLS impersonation for\n"
            "  caption downloads; without it yt-dlp warns about 'no impersonate\n"
            "  target' and writes empty files.\n"
            "      uv pip install curl_cffi")

    if not (shutil.which("deno") or (Path.home() / ".deno/bin/deno").exists()):
        problems.append(
            "No JavaScript runtime. YouTube needs one to resolve caption URLs.\n"
            '      curl -fsSL https://deno.land/install.sh | sh\n'
            '      export PATH="$HOME/.deno/bin:$PATH"')

    if problems:
        print("=" * 66)
        for i, text in enumerate(problems, 1):
            print(f"  {i}. {text}")
        print("  Downloads will keep failing until these are resolved.")
        print("=" * 66)


# ---------------------------------------------------------------- listing

def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "channel"


def normalise_channel(url):
    """
    A bare channel URL expands to several tabs — Videos, Shorts, Live — and
    --playlist-end applies to each, so asking for 3 gets you 6 to 9.
    """
    clean = url.rstrip("/")
    if any(x in clean for x in ("/playlist", "/watch", "list=")):
        return clean
    if re.search(r"/(videos|shorts|streams)$", clean):
        return clean
    if clean.endswith("/featured"):
        return clean[: -len("/featured")] + "/videos"
    if any(x in clean for x in ("/@", "/channel/", "/c/", "/user/")):
        return clean + "/videos"
    return clean


def list_videos(url, limit):
    out = run_ytdlp(["--flat-playlist", "--print", "%(id)s",
                     "--playlist-end", str(limit), "--ignore-errors",
                     normalise_channel(url)], timeout=300)
    if out is None:
        print("    timed out")
        return []
    ids = [l.strip() for l in out.stdout.splitlines() if len(l.strip()) == 11]
    if not ids and out.stderr.strip():
        print(f"    {out.stderr.strip().splitlines()[-1][:140]}")
    return list(dict.fromkeys(ids))[:limit]


# ---------------------------------------------------------------- download

def solver_args(args):
    """
    Recent yt-dlp needs an external challenge-solver script to answer
    YouTube's JS challenge; having Deno installed is no longer enough, and
    without it you get "n challenge solving failed" followed by "The page
    needs to be reloaded".

    yt-dlp can fetch that script from its GitHub releases or from the npm
    registry. They are interchangeable, which matters on networks that filter
    one host but not the other — plenty of corporate networks allow the npm
    registry while github.com times out. "both" lets yt-dlp fall back.
    """
    if args.solver == "off":
        return []
    if args.solver == "both":
        return ["--remote-components", "ejs:github",
                "--remote-components", "ejs:npm"]
    return ["--remote-components", f"ejs:{args.solver}"]


def cookie_args(args):
    """
    Anonymous caption requests hit HTTP 429 quickly. A logged-in session gets
    a far higher allowance, so this is the difference between a fetch that
    works and one that stalls after a handful of videos.
    """
    if args.cookies:
        return ["--cookies", args.cookies]
    if args.cookies_from_browser:
        return ["--cookies-from-browser", args.cookies_from_browser]
    return []


def download_subs(video_ids, args):
    """
    One batched yt-dlp run. Asks for manual and auto captions together —
    yt-dlp prefers a real track when one exists. Returns {id: spoken_language}
    from the same extraction, so the language check costs no extra requests.
    """
    SUB_CACHE.mkdir(parents=True, exist_ok=True)
    out = run_ytdlp([
        *solver_args(args),
        *cookie_args(args),
        # --print implies --simulate, and simulate writes nothing to disk.
        # Without --no-simulate yt-dlp picks the track, logs the format it
        # chose, then silently skips the write. Do not remove this.
        "--no-simulate",
        "--skip-download", "--ignore-errors",
        "--write-subs", "--write-auto-subs",
        "--sub-langs", SUB_LANGS, "--sub-format", "json3/srv3/vtt/srt/best",
        "--sleep-requests", str(args.sleep),
        # separate from --sleep-requests; this one throttles caption fetches,
        # which is exactly what YouTube rate-limits
        "--sleep-subtitles", str(int(args.sleep)),
        "--retries", "3", "--retry-sleep", "exp=5:120",
        "-o", str(SUB_CACHE / "%(id)s.%(ext)s"),
        "--print", "%(id)s\t%(language)s",
        *[f"https://www.youtube.com/watch?v={v}" for v in video_ids],
    ])
    if out is None:
        print("    yt-dlp timed out")
        return {}

    langs = {}
    for line in out.stdout.splitlines():
        parts = line.strip().split("\t")
        if len(parts) == 2 and len(parts[0]) == 11:
            langs[parts[0]] = None if parts[1].strip() in ("NA", "None", "") \
                else parts[1].strip()

    if VERBOSE:
        for line in out.stderr.splitlines():
            if line.strip():
                print(f"    | {line.rstrip()}")
    else:
        for line in out.stderr.splitlines():
            if "ERROR" in line or "429" in line:
                print(f"    {line.strip()[:150]}")

    if "challenge solving failed" in out.stderr or "needs to be reloaded" in out.stderr:
        blocked = "github.com" if "host='github.com'" in out.stderr else None
        print("""
    YouTube's JS challenge could not be solved. yt-dlp needs Deno, curl_cffi,
    and its challenge-solver script all present together.""")
        if blocked:
            print(f"""
    github.com timed out from this machine, so the script could not be
    downloaded. Try the npm registry instead, which many filtered networks
    still allow:
        npm run clips:fetch -- --solver npm ...
    If both hosts are blocked, run the fetch from another network. The cache
    is just files — copy scripts/cache/ back afterwards.""")
        else:
            print("    If it persists, upgrade:  uv pip install --upgrade yt-dlp")

    if "429" in out.stderr:
        print("""
    HTTP 429: YouTube is rate-limiting caption downloads from this IP.
    Everything else is working — the request got through and was refused.

      1. Wait. These clear on their own, often within an hour.
      2. Then use a logged-in session, which raises the limit a lot:
           npm run clips:fetch -- --cookies-from-browser firefox
         On a headless box, export cookies.txt from a browser elsewhere:
           npm run clips:fetch -- --cookies ~/youtube-cookies.txt
      3. Go slower:  --batch 3 --sleep 6
""")
    return langs


# ---------------------------------------------------------------- parsing

TIMING = re.compile(r"(\d{2}):(\d{2}):(\d{2})[.,](\d{3})\s*-->\s*"
                    r"(\d{2}):(\d{2}):(\d{2})[.,](\d{3})")
VTT_TAG = re.compile(r"<[^>]+>")


def find_sub(video_id, langs):
    """First matching subtitle file, in the caller's language preference order."""
    for lang in langs:
        for ext in SUB_EXTS:
            hit = SUB_CACHE / f"{video_id}.{lang}.{ext}"
            if hit.exists():
                return hit
    # regional variants not named exactly (zh-Hans-en, en-orig, ...)
    for path in sorted(SUB_CACHE.glob(f"{video_id}.*")):
        if path.suffix.lstrip(".") not in SUB_EXTS:
            continue
        base = path.name[len(video_id) + 1 : -len(path.suffix)].split("-")[0].lower()
        if any(base == l.split("-")[0].lower() for l in langs):
            return path
    return None


def parse_subs(path):
    if path is None:
        return []
    ext = path.suffix.lstrip(".").lower()
    return parse_json3(path) if ext in ("json3", "srv3") else parse_vtt(path)


def parse_json3(path):
    """Auto tracks emit rolling partial events flagged aAppend; drop those."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    cues = []
    for ev in data.get("events", []):
        if ev.get("aAppend"):
            continue
        text = "".join(s.get("utf8", "") for s in ev.get("segs") or []).strip()
        if text:
            cues.append({"t": round(ev.get("tStartMs", 0) / 1000, 2),
                         "d": round(ev.get("dDurationMs", 0) / 1000, 2) or 1.0,
                         "text": text})
    return cues


def parse_vtt(path):
    """
    WebVTT and SRT. Auto-caption VTT repeats each line across consecutive cues
    as words appear, and carries inline <c> timing tags, so both are stripped
    and consecutive duplicates collapsed.
    """
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return []

    cues, start, end, buf = [], None, None, []

    def flush():
        nonlocal start, end, buf
        text = re.sub(r"\s+", " ", VTT_TAG.sub("", " ".join(buf))).strip()
        if text and start is not None and (not cues or cues[-1]["text"] != text):
            cues.append({"t": round(start, 2),
                         "d": round(max(end - start, 0.4), 2), "text": text})
        start, end, buf = None, None, []

    def seconds(h, m, s, ms):
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000

    for raw in lines:
        line = raw.strip()
        match = TIMING.search(line)
        if match:
            flush()
            g = match.groups()
            start, end = seconds(*g[:4]), seconds(*g[4:])
        elif not line:
            flush()
        elif line.upper().startswith(("WEBVTT", "NOTE", "STYLE")):
            continue
        elif start is not None and not (line.isdigit() and not buf):
            buf.append(line)
    flush()
    return cues


# ---------------------------------------------------------------- main

def is_chinese_audio(lang):
    """None means unknown; the caller decides whether to keep those."""
    if lang is None:
        return None
    return lang.lower().startswith("zh") or lang.lower() in ("cmn", "yue")


def fetch(wanted, args):
    todo = [v for v in wanted if not (TRANSCRIPT_CACHE / f"{v}.json").exists()]
    if args.limit:
        todo = todo[: args.limit]
    print(f"\n{len(wanted)} videos total, {len(todo)} to fetch")
    if not todo:
        print("nothing to do (delete scripts/cache/transcripts to redo)")
        return

    langs = {}
    for i in range(0, len(todo), args.batch):
        chunk = todo[i : i + args.batch]
        print(f"\nbatch {i // args.batch + 1} ({len(chunk)} videos)...")
        langs.update(download_subs(chunk, args))

    on_disk = [p.suffix.lstrip(".") for p in SUB_CACHE.glob("*")
               if p.suffix.lstrip(".") in SUB_EXTS]
    if on_disk:
        tally = {e: on_disk.count(e) for e in dict.fromkeys(on_disk)}
        print("\nsubtitle files: " + ", ".join(f"{v} .{k}" for k, v in tally.items()))
    else:
        print(f"\nno subtitle files were written to {SUB_CACHE}")

    counts = {}
    for video_id in todo:
        zh_path = find_sub(video_id, ZH_LANGS)
        lang = langs.get(video_id)
        chinese = is_chinese_audio(lang)

        if not zh_path:
            record = {"status": "none"}
        elif not args.any_language and chinese is False:
            record = {"status": "wrong_language", "language": lang}
        elif not args.any_language and args.skip_unknown and chinese is None:
            record = {"status": "unknown_language"}
        else:
            cues = parse_subs(zh_path)
            record = {"status": "ok", "language": lang, "cues": cues,
                      "en_cues": parse_subs(find_sub(video_id, EN_LANGS))} \
                if cues else {"status": "none"}

        record["video_id"] = video_id
        (TRANSCRIPT_CACHE / f"{video_id}.json").write_text(
            json.dumps(record, ensure_ascii=False), encoding="utf-8")

        counts[record["status"]] = counts.get(record["status"], 0) + 1
        if record["status"] == "ok":
            en = len(record["en_cues"])
            print(f"  {video_id}  ok ({len(record['cues'])} cues, "
                  f"{'en:' + str(en) if en else 'NO ENGLISH'})")
        else:
            print(f"  {video_id}  {record['status']}" + (f" ({lang})" if lang else ""))

    print("\n" + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    if counts.get("none"):
        print("'none' means no Chinese captions were found or parsed.")
        print("Inspect one with:  npm run clips:fetch -- --probe VIDEO_ID")
    print("now run: npm run clips:build")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh-lists", action="store_true")
    ap.add_argument("--batch", type=int, default=15, help="videos per yt-dlp call")
    ap.add_argument("--sleep", type=float, default=1.0, help="seconds between requests")
    ap.add_argument("--limit", type=int, default=0, help="stop after N new videos")
    ap.add_argument("--probe", metavar="VIDEO_ID",
                    help="list every caption track YouTube has for one video, then exit")
    ap.add_argument("--only", metavar="VIDEO_ID", action="append",
                    help="fetch just this video, ignoring channels.csv. Repeatable.")
    ap.add_argument("--verbose", action="store_true", help="show yt-dlp's full output")
    ap.add_argument("--solver", choices=("github", "npm", "both", "off"),
                    default="both",
                    help="where yt-dlp gets YouTube's JS challenge solver "
                         "(default: both, so a blocked host falls back)")
    ap.add_argument("--cookies", metavar="FILE",
                    help="Netscape cookies.txt for a logged-in YouTube session")
    ap.add_argument("--cookies-from-browser", metavar="BROWSER",
                    help="read cookies straight from a local browser "
                         "(firefox, chrome, chromium, edge, safari)")
    ap.add_argument("--any-language", action="store_true",
                    help="keep videos that aren't spoken in Chinese")
    ap.add_argument("--skip-unknown", action="store_true",
                    help="also drop videos whose language YouTube never reported")
    args = ap.parse_args()

    global VERBOSE
    VERBOSE = args.verbose
    preflight()

    if args.probe:
        out = run_ytdlp([*solver_args(args), *cookie_args(args),
                         "--list-subs", "--skip-download",
                         f"https://www.youtube.com/watch?v={args.probe}"], timeout=120)
        print(out.stdout if out else "timed out")
        return

    for d in (VIDEO_CACHE, SUB_CACHE, TRANSCRIPT_CACHE):
        d.mkdir(parents=True, exist_ok=True)

    if args.only:
        print(f"\ntesting {len(args.only)} video(s), ignoring channels.csv")
        return fetch([v.strip() for v in args.only], args)

    channels_path = HERE / "channels.csv"
    if not channels_path.exists():
        sys.exit(f"missing {channels_path}")
    with open(channels_path, encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(l for l in f if not l.startswith("#"))
                if (r.get("url") or "").strip()]
    if not rows:
        sys.exit("no channels in channels.csv")

    wanted = []
    for row in rows:
        name = (row.get("name") or row["url"]).strip()
        limit = int((row.get("max_videos") or "30").strip() or 30)
        cache_file = VIDEO_CACHE / f"{slug(name)}.json"
        if cache_file.exists() and not args.refresh_lists:
            ids = json.loads(cache_file.read_text())["ids"][:limit]
            print(f"{name}: {len(ids)} videos (cached)")
        else:
            print(f"{name}: asking yt-dlp...")
            ids = list_videos(row["url"].strip(), limit)
            cache_file.write_text(json.dumps({"url": row["url"], "ids": ids}, indent=1))
            print(f"    {len(ids)} videos")
        wanted.extend(ids)

    fetch(list(dict.fromkeys(wanted)), args)


if __name__ == "__main__":
    main()