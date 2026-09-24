#!/usr/bin/env python3
"""
Turn the transcript cache into static/data/clips.json.

  ./.venv/bin/python3 scripts/build_clips.py

No network. Reads scripts/cache/transcripts/*.json plus static/data/vocab.json,
merges caption cues into short segments, keeps the ones that use your
vocabulary, and writes a word -> clip index.

Playback is a YouTube embed seeked to the timestamp, so nothing is downloaded
or rehosted — the clip plays from YouTube, with the channel getting the view.

Clips need an English line for the multiple choice, taken from the video's
English caption track (or YouTube's translation of the Chinese one) and
aligned by timestamp. Videos without one are skipped.

One thing to decide before deploying: clips.json contains transcript text, and
that text belongs to the channel. Keeping it to one short line per clip
alongside a link back to the source is the defensible shape, but if you publish
the site you are republishing someone else's words. For a public deploy,
consider gitignoring static/data/clips.json and keeping clips a local feature,
or asking the channels first.
"""

import argparse, collections, json, re, sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

try:
    import jieba
    from opencc import OpenCC
    from pypinyin import pinyin as to_pinyin, Style
except ImportError:
    sys.exit("pip install jieba opencc-python-reimplemented pypinyin")

from build_data import decompose  # same merged-token recovery as the corpus build

HAN = re.compile(r"[\u4e00-\u9fff]")
LATIN_OR_DIGIT = re.compile(r"[A-Za-z0-9]")
NON_WORD = re.compile(r"^[\W_0-9A-Za-z]+$")
PUNCT_END = re.compile(r"[。！？!?；;]$")
PUNCT_SOFT = re.compile(r"[，,、]$")
BRACKETED = re.compile(r"[\[(（【][^\])）】]*[\])）】]")  # [音楽], (laughs) and friends

MIN_CHARS, MAX_CHARS = 5, 26
MAX_GAP = 1.2      # seconds of silence that ends a segment
MAX_DURATION = 9.0
PAD_BEFORE = 0.4   # start slightly early, captions tend to lag the audio
MAX_CLIPS_PER_WORD = 6


def clean(text):
    text = BRACKETED.sub("", text)
    text = text.replace("\n", " ").replace("\u200b", "")
    return re.sub(r"\s+", "", text).strip()


def merge_cues(cues, cc):
    """
    Caption cues are 2-4 seconds each and cut mid-sentence. Glue consecutive
    ones into utterance-sized chunks, breaking on sentence punctuation, a long
    gap, or length. Auto-captions often have no punctuation at all, which is
    why length and gap are the fallbacks.
    """
    segments = []
    buf, start, end = "", None, None

    def flush():
        nonlocal buf, start, end
        if buf and MIN_CHARS <= len(buf) <= MAX_CHARS:
            segments.append({"text": buf, "start": start, "end": end})
        buf, start, end = "", None, None

    for cue in cues:
        text = clean(cc.convert(cue["text"]))
        if not text:
            continue
        cue_start = cue["t"]
        cue_end = cue["t"] + max(cue["d"], 0.4)

        if start is not None and (cue_start - end > MAX_GAP or
                                  cue_end - start > MAX_DURATION or
                                  len(buf) + len(text) > MAX_CHARS):
            flush()

        if start is None:
            start = cue_start
        buf += text
        end = cue_end

        if PUNCT_END.search(buf) or (len(buf) >= MAX_CHARS - 4 and PUNCT_SOFT.search(buf)):
            flush()

    flush()
    return segments


def english_for(en_cues, start, end):
    """
    English covering a Chinese segment's time window.

    Caption tracks in the two languages rarely share cue boundaries, so this
    takes any English cue that overlaps the window by a reasonable margin and
    joins them. Machine-translated tracks lag a little, hence the slack.
    """
    if not en_cues:
        return ""
    slack = 0.6
    parts = []
    for cue in en_cues:
        c_start, c_end = cue["t"], cue["t"] + max(cue["d"], 0.4)
        overlap = min(end, c_end) - max(start, c_start)
        if overlap > 0 or (c_start >= start - slack and c_end <= end + slack):
            text = BRACKETED.sub("", cue["text"]).replace("\n", " ").strip()
            if text:
                parts.append(text)
    joined = re.sub(r"\s+", " ", " ".join(parts)).strip()
    return joined if 3 <= len(joined) <= 160 else ""


def analyse(text, words):
    """-> (vocab_words_used, out_of_list_count) or None if unusable."""
    if LATIN_OR_DIGIT.search(text) or not HAN.search(text):
        return None
    tokens = [t for t in jieba.cut(text) if not NON_WORD.match(t)]
    used, unknown = set(), 0
    for t in tokens:
        if t in words:
            used.add(t)
            continue
        pieces = decompose(t, words)
        if pieces:
            used.update(pieces)
        else:
            unknown += 1
    return used, unknown


# pypinyin passes punctuation through untouched; those tokens are the ones to drop
PUNCT_TOKEN = re.compile(r"^[^\w]+$", re.UNICODE)


def sentence_pinyin(zh):
    syllables = to_pinyin(zh, style=Style.TONE, errors="ignore")
    return " ".join(s[0] for s in syllables if not PUNCT_TOKEN.match(s[0]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE.parent / "static" / "data"))
    ap.add_argument("--max-unknown", type=int, default=2,
                    help="out-of-list words tolerated per clip (default 2)")
    args = ap.parse_args()

    out = Path(args.out)
    vocab_path = out / "vocab.json"
    if not vocab_path.exists():
        sys.exit(f"missing {vocab_path} - run build_data.py first")

    vocab = json.loads(vocab_path.read_text(encoding="utf-8"))
    words = {v["w"]: v["l"] for v in vocab}
    for w in words:
        jieba.add_word(w)

    cache = HERE / "cache" / "transcripts"
    files = sorted(cache.glob("*.json")) if cache.exists() else []
    if not files:
        sys.exit(f"no cached transcripts in {cache} - run fetch_transcripts.py first")

    cc = OpenCC("t2s")
    clips, by_word = [], collections.defaultdict(list)
    stats = collections.Counter()

    for path in files:
        record = json.loads(path.read_text(encoding="utf-8"))
        stats[record.get("status", "?")] += 1
        if record.get("status") != "ok":
            continue
        video_id = record["video_id"]
        en_cues = record.get("en_cues") or []
        if not en_cues:
            stats["skipped_no_english"] += 1
            continue

        kept = 0
        for seg in merge_cues(record["cues"], cc):
            result = analyse(seg["text"], words)
            if result is None:
                continue
            used, unknown = result
            if not used or unknown > args.max_unknown:
                continue

            english = english_for(en_cues, seg["start"], seg["end"])
            if not english:
                stats["no_english_line"] += 1
                continue

            levels = [words[w] for w in used if words[w]]
            idx = len(clips)
            clips.append([
                video_id,
                round(max(seg["start"] - PAD_BEFORE, 0), 2),
                round(seg["end"], 2),
                seg["text"],
                sentence_pinyin(seg["text"]),
                max(levels) if levels else 0,
                english,
            ])
            for w in used:
                by_word[w].append(idx)
            kept += 1
        stats["clips"] += kept

    # cap per word, then drop anything left unreferenced
    for w, ids in by_word.items():
        ids.sort(key=lambda i: len(clips[i][3]))
        by_word[w] = ids[:MAX_CLIPS_PER_WORD]

    keep = sorted({i for ids in by_word.values() for i in ids})
    remap = {old: new for new, old in enumerate(keep)}
    clips = [clips[i] for i in keep]
    by_word = {w: [remap[i] for i in ids] for w, ids in by_word.items() if ids}

    (out / "clips.json").write_text(
        json.dumps({"c": clips, "byWord": by_word}, ensure_ascii=False,
                   separators=(",", ":")), encoding="utf-8")

    covered = len(by_word)
    print(f"transcripts: " + "  ".join(f"{k}={v}" for k, v in sorted(stats.items())))
    print(f"wrote {len(clips)} clips covering {covered} words "
          f"({covered / len(vocab) * 100:.0f}% of the vocabulary)")
    if clips:
        print("\nsample:")
        for row in clips[:3]:
            print(f"  {row[3]}")
            print(f"    {row[6]}")
            print(f"    [{row[0]} @ {row[1]}s]")


if __name__ == "__main__":
    main()