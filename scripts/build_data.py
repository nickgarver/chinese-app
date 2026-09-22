#!/usr/bin/env python3
"""
Turn the raw HSK CSVs + Tatoeba sentence pairs into static JSON the app ships.

Run:  python3 scripts/build_data.py --src "path/to/hsk data" --out static/data

Steps:
  1. Load HSK word lists (levels 1-5 by default).
  2. Load class word lists from scripts/class/year_*.txt and merge them in.
     A word in both keeps its HSK level and gains a class reference; a word
     only taught in class gets level 0.
  3. Load sentence pairs, convert Traditional -> Simplified, dedupe.
  4. Segment with jieba (all known words injected into the dict).
  5. Recover merged tokens (一百 -> 一 + 百) and substring matches.
  6. Score each sentence: highest level used, count of out-of-list words.
  7. Tag every word with categories from categories.json.
  8. Emit vocab.json, sentences.json, meta.json + a coverage report.
"""

import argparse, csv, json, re, sys, collections
from pathlib import Path

try:
    import jieba
    from opencc import OpenCC
    from pypinyin import pinyin as to_pinyin, Style
except ImportError:
    sys.exit("pip install jieba opencc-python-reimplemented pypinyin")

HAN = re.compile(r'[\u4e00-\u9fff]')
# pypinyin passes punctuation through untouched; drop those tokens
HAN_ONLY = re.compile(r'^[^\w]+$', re.UNICODE)
LATIN_OR_DIGIT = re.compile(r'[A-Za-z0-9]')
NON_WORD = re.compile(r'^[\W_0-9A-Za-z]+$')
MAX_SENTENCES_PER_WORD = 8
MIN_LEN, MAX_LEN = 4, 24


def load_hsk(src: Path, max_level: int):
    """word -> {level, pinyin, definition, refs}. First level a word appears in wins."""
    words = {}
    for lv in range(1, max_level + 1):
        path = src / f"hsk{lv}.csv"
        if not path.exists():
            sys.exit(f"missing {path}")
        with open(path, encoding="utf-8-sig") as f:
            for row in csv.reader(f):
                if len(row) < 3 or not row[0].strip():
                    continue
                w = row[0].strip()
                if w not in words:
                    words[w] = {
                        "level": lv,
                        "pinyin": row[1].strip(),
                        "definition": row[2].strip(),
                        "refs": [],
                    }
    return words


def load_class(folder: Path):
    """
    Parse scripts/class/year_N.txt (Lesson,Chinese,Pinyin,English).
    Returns word -> {"refs": ["1-5"], "pinyin": ..., "definition": ...}
    where a ref is "<year>-<chapter>".
    """
    entries = {}
    if not folder.exists():
        return entries
    for path in sorted(folder.glob("year_*.txt")):
        try:
            year = int(path.stem.split("_")[1])
        except (IndexError, ValueError):
            print(f"  skipping {path.name}: expected year_<n>.txt")
            continue
        with open(path, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                word = (row.get("Chinese") or "").strip()
                chapter = (row.get("Lesson") or "").strip()
                if not word or not chapter.isdigit():
                    continue
                rec = entries.setdefault(word, {
                    "refs": [],
                    "pinyin": (row.get("Pinyin") or "").strip(),
                    "definition": (row.get("English") or "").strip(),
                })
                ref = f"{year}-{int(chapter)}"
                if ref not in rec["refs"]:
                    rec["refs"].append(ref)
    return entries


def load_sentences(src: Path):
    """Traditional -> Simplified, dedupe, keep the shortest English gloss."""
    cc = OpenCC("t2s")
    pairs = {}
    path = src / "sentence pairs.tsv"
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            parts = line.rstrip("\r\n").split("\t")
            if len(parts) < 4:
                continue
            zh = cc.convert(parts[1].strip())
            en = parts[3].strip()
            if not zh or not en:
                continue
            prev = pairs.get(zh)
            # shortest translation is usually the cleanest
            if prev is None or len(en) < len(prev):
                pairs[zh] = en
    return pairs


def sentence_pinyin(zh):
    """
    Space-separated pinyin with tone marks, punctuation dropped.

    pypinyin is good but not perfect: it does not apply tone sandhi (不 stays
    bù before a fourth tone) and it sometimes gives a full tone where a native
    speaker uses the neutral one (yī fú rather than yī fu). Good enough as a
    reading aid, not authoritative.
    """
    syllables = to_pinyin(zh, style=Style.TONE, errors="ignore")
    return " ".join(s[0] for s in syllables if HAN_ONLY.match(s[0]) is None)


def decompose(token, words):
    """Split a token jieba merged (不是, 一百) back into HSK words. None if it won't split."""
    out, i = [], 0
    while i < len(token):
        for size in (4, 3, 2, 1):
            piece = token[i:i + size]
            if piece in words:
                out.append(piece)
                i += size
                break
        else:
            return None
    return out


def analyse(zh, words):
    """-> (hsk_words_used, out_of_list_count) or None if the sentence is unusable."""
    # Latin letters or digits anywhere means the pinyin line would have holes
    # in it, so drop the sentence rather than show a truncated reading.
    if LATIN_OR_DIGIT.search(zh):
        return None
    tokens = [t for t in jieba.cut(zh) if not NON_WORD.match(t)]
    if any(not HAN.search(t) for t in tokens):
        return None  # latin letters or digits in the sentence
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


def tag_words(words, categories):
    """word -> [category keys]. Seeds always match; regex matches the English gloss."""
    compiled = {
        key: [re.compile(p, re.I) for p in spec.get("en", [])]
        for key, spec in categories.items() if not key.startswith("_")
    }
    seeds = {
        key: set(spec.get("seeds", []))
        for key, spec in categories.items() if not key.startswith("_")
    }
    tags = {}
    for w, rec in words.items():
        definition = rec["definition"]
        hits = []
        for key in compiled:
            if w in seeds[key] or any(rx.search(definition) for rx in compiled[key]):
                hits.append(key)
        if hits:
            tags[w] = hits
    return tags


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="folder holding hsk1.csv ... and sentence pairs.tsv")
    ap.add_argument("--out", default="static/data")
    ap.add_argument("--max-level", type=int, default=5)
    ap.add_argument("--max-unknown", type=int, default=1,
                    help="out-of-list words tolerated per sentence")
    args = ap.parse_args()

    src, out = Path(args.src), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    here = Path(__file__).parent

    print("loading HSK lists...")
    words = load_hsk(src, args.max_level)
    print(f"  {len(words)} words through HSK{args.max_level}")

    print("loading class lists...")
    class_words = load_class(here / "class")
    overlap = new = 0
    for w, rec in class_words.items():
        if w in words:
            # already an HSK word: keep the HSK pinyin and gloss so the app stays
            # internally consistent, and just record where class taught it
            words[w]["refs"] = rec["refs"]
            overlap += 1
        else:
            words[w] = {
                "level": 0,  # taught in class, not in HSK 1-5
                "pinyin": rec["pinyin"],
                "definition": rec["definition"],
                "refs": rec["refs"],
            }
            new += 1
    print(f"  {len(class_words)} class words: {overlap} already in HSK, {new} new")

    for w in words:
        jieba.add_word(w)

    print("loading sentences (converting traditional -> simplified)...")
    pairs = load_sentences(src)
    print(f"  {len(pairs)} unique sentences")

    print("segmenting and indexing...")
    sentences = []          # [zh, en, level, unknown_count]
    by_word = collections.defaultdict(list)
    for zh, en in pairs.items():
        if not (MIN_LEN <= len(zh) <= MAX_LEN):
            continue
        result = analyse(zh, words)
        if result is None:
            continue
        used, unknown = result
        if not used or unknown > args.max_unknown:
            continue
        levels_used = [words[w]["level"] for w in used if words[w]["level"]]
        level = max(levels_used) if levels_used else 0
        idx = len(sentences)
        sentences.append([zh, en, level, unknown, sentence_pinyin(zh)])
        for w in used:
            by_word[w].append(idx)

    # substring rescue for words the segmenter never surfaced
    missing = [w for w in words if not by_word[w]]
    if missing:
        print(f"  substring pass for {len(missing)} unmatched words...")
        for i, row in enumerate(sentences):
            zh = row[0]
            for w in missing:
                if w in zh:
                    by_word[w].append(i)

    # keep the shortest sentences per word, then drop anything now unreferenced
    for w, ids in by_word.items():
        ids.sort(key=lambda i: len(sentences[i][0]))
        by_word[w] = ids[:MAX_SENTENCES_PER_WORD]

    keep = sorted({i for ids in by_word.values() for i in ids})
    remap = {old: new for new, old in enumerate(keep)}
    sentences = [sentences[i] for i in keep]
    by_word = {w: [remap[i] for i in ids] for w, ids in by_word.items() if ids}

    print("tagging categories...")
    categories = json.loads((here / "categories.json").read_text(encoding="utf-8"))
    tags = tag_words(words, categories)
    cat_counts = collections.Counter(k for v in tags.values() for k in v)

    # ---- emit ----
    vocab = [
        {
            "w": w,
            "p": rec["pinyin"],
            "d": rec["definition"],
            "l": rec["level"],
            "t": tags.get(w, []),
            "c": rec["refs"],
        }
        for w, rec in sorted(words.items(), key=lambda kv: (kv[1]["level"], kv[0]))
    ]
    (out / "vocab.json").write_text(
        json.dumps(vocab, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (out / "sentences.json").write_text(
        json.dumps({"s": sentences, "byWord": by_word}, ensure_ascii=False,
                   separators=(",", ":")), encoding="utf-8")

    # class chapters, in year then chapter order, with live counts
    chapter_counts = collections.Counter(r for v in vocab for r in v["c"])
    years = collections.defaultdict(list)
    for ref, n in chapter_counts.items():
        y, ch = ref.split("-")
        years[int(y)].append({"ref": ref, "chapter": int(ch), "count": n})
    class_meta = [
        {
            "year": y,
            "chapters": sorted(years[y], key=lambda c: c["chapter"]),
            "count": sum(1 for v in vocab if any(r.startswith(f"{y}-") for r in v["c"])),
        }
        for y in sorted(years)
    ]

    meta = {
        "maxLevel": args.max_level,
        "wordCount": len(vocab),
        "sentenceCount": len(sentences),
        "levels": {str(lv): sum(1 for v in vocab if v["l"] == lv)
                   for lv in range(1, args.max_level + 1)},
        "classOnlyCount": sum(1 for v in vocab if v["l"] == 0),
        "categories": [
            {
                "key": k,
                "label": spec["label"],
                "emoji": spec.get("emoji", ""),
                "count": cat_counts.get(k, 0),
            }
            for k, spec in categories.items()
            if not k.startswith("_") and cat_counts.get(k, 0) > 0
        ],
        "class": class_meta,
    }
    (out / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---- report ----
    print(f"\nwrote {len(vocab)} words, {len(sentences)} sentences to {out}/")
    def cover(pool, label):
        if not pool:
            return
        c1 = sum(1 for w in pool if len(by_word.get(w, [])) >= 1)
        c3 = sum(1 for w in pool if len(by_word.get(w, [])) >= 3)
        print(f"  {label:12s} {len(pool):5d} words | >=1 sent {c1/len(pool)*100:5.1f}%"
              f" | >=3 sent {c3/len(pool)*100:5.1f}%")

    print("\ncoverage by level:")
    for lv in range(1, args.max_level + 1):
        cover([v["w"] for v in vocab if v["l"] == lv], f"HSK{lv}")
    cover([v["w"] for v in vocab if v["l"] == 0], "class-only")

    print("\ncoverage by class year:")
    for entry in class_meta:
        y = entry["year"]
        cover([v["w"] for v in vocab if any(r.startswith(f"{y}-") for r in v["c"])],
              f"Year {y}")
    thin = [c for e in class_meta for c in e["chapters"] if c["count"] < 8]
    if thin:
        print("  chapters under 8 words: " +
              ", ".join(f"{c['ref']} ({c['count']})" for c in thin))

    untagged = len(vocab) - len(tags)
    print(f"\ncategories: {len(meta['categories'])} active, "
          f"{untagged} words untagged ({untagged/len(vocab)*100:.0f}%)")
    for c in sorted(meta["categories"], key=lambda c: -c["count"]):
        print(f"  {c['label']:26s} {c['count']:4d}")

    gaps = [v["w"] for v in vocab if not by_word.get(v["w"])]
    if gaps:
        (out / "gaps.json").write_text(
            json.dumps(gaps, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n{len(gaps)} words have no sentence -> {out}/gaps.json")


if __name__ == "__main__":
    main()
