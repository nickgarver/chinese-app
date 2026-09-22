#!/usr/bin/env python3
"""
Re-apply scripts/class/year_*.txt to the data already in static/data.

Use this when you have only edited the class lists (or categories.json). It
rewrites vocab.json and meta.json in place and needs no raw HSK CSVs and no
Tatoeba corpus, so it finishes instantly.

  ./.venv/bin/python3 scripts/refresh_class.py

What it does:
  - updates every word's class chapter refs to match the files
  - drops class-only words you removed from the lists
  - adds class-only words you added (they start with no example sentences)
  - re-runs category tagging from categories.json
  - rebuilds the chapter structure in meta.json

What it cannot do: index sentences for brand new words, because that needs the
sentence corpus. Those words are listed at the end so you know to run the full
build_data.py when you want their examples.
"""

import json, sys
from pathlib import Path

from build_data import load_class, tag_words

HERE = Path(__file__).parent


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent / "static" / "data"
    vocab_path, meta_path = out / "vocab.json", out / "meta.json"
    sent_path = out / "sentences.json"

    for p in (vocab_path, meta_path, sent_path):
        if not p.exists():
            sys.exit(f"missing {p} - run build_data.py once first")

    vocab = json.loads(vocab_path.read_text(encoding="utf-8"))
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    by_word = json.loads(sent_path.read_text(encoding="utf-8"))["byWord"]

    print("loading class lists...")
    class_words = load_class(HERE / "class")
    if not class_words:
        sys.exit("no class words found - nothing to do")

    index = {v["w"]: v for v in vocab}
    added, dropped, retagged = [], [], 0

    # refresh refs on everything already present
    for v in vocab:
        v["c"] = class_words[v["w"]]["refs"] if v["w"] in class_words else []

    # words newly added to the class lists
    for word, rec in class_words.items():
        if word in index:
            continue
        index[word] = {
            "w": word,
            "p": rec["pinyin"],
            "d": rec["definition"],
            "l": 0,
            "t": [],
            "c": rec["refs"],
        }
        added.append(word)

    # class-only words you removed have nothing left to justify them
    keep = [v for v in index.values() if v["l"] > 0 or v["c"]]
    dropped = [v["w"] for v in index.values() if v["l"] == 0 and not v["c"]]

    # re-tag categories (cheap, and picks up categories.json edits too)
    categories = json.loads((HERE / "categories.json").read_text(encoding="utf-8"))
    tags = tag_words({v["w"]: {"definition": v["d"]} for v in keep}, categories)
    for v in keep:
        new = tags.get(v["w"], [])
        if new != v["t"]:
            retagged += 1
        v["t"] = new

    keep.sort(key=lambda v: (v["l"], v["w"]))

    # rebuild the chapter structure meta.json exposes to the UI
    import collections
    chapter_counts = collections.Counter(r for v in keep for r in v["c"])
    years = collections.defaultdict(list)
    for ref, n in chapter_counts.items():
        y, ch = ref.split("-")
        years[int(y)].append({"ref": ref, "chapter": int(ch), "count": n})

    cat_counts = collections.Counter(k for v in keep for k in v["t"])
    meta["class"] = [
        {
            "year": y,
            "chapters": sorted(years[y], key=lambda c: c["chapter"]),
            "count": sum(1 for v in keep if any(r.startswith(f"{y}-") for r in v["c"])),
        }
        for y in sorted(years)
    ]
    meta["wordCount"] = len(keep)
    meta["classOnlyCount"] = sum(1 for v in keep if v["l"] == 0)
    meta["categories"] = [
        {
            "key": k,
            "label": spec["label"],
            "emoji": spec.get("emoji", ""),
            "count": cat_counts.get(k, 0),
        }
        for k, spec in categories.items()
        if not k.startswith("_") and cat_counts.get(k, 0) > 0
    ]

    vocab_path.write_text(
        json.dumps(keep, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    meta_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{len(keep)} words written ({meta['classOnlyCount']} class-only)")
    if dropped:
        print(f"removed {len(dropped)}: {' '.join(dropped[:20])}"
              + (" ..." if len(dropped) > 20 else ""))
    if retagged:
        print(f"re-tagged {retagged} words")
    for entry in meta["class"]:
        print(f"Year {entry['year']} ({entry['count']}): " +
              " ".join(f"C{c['chapter']}={c['count']}" for c in entry["chapters"]))

    no_sentences = [w for w in added if not by_word.get(w)]
    if added:
        print(f"\nadded {len(added)}: {' '.join(added)}")
    if no_sentences:
        print(f"{len(no_sentences)} of them have no example sentences yet.")
        print("Run build_data.py with the raw corpus when you want those indexed.")


if __name__ == "__main__":
    main()
