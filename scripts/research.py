#!/usr/bin/env python3
"""pinterest-research Skill のメインスクリプト。

入力 JSON（3 方向 x 4 件）を受け取り、各アイテムの og:image を取得して
ローカルに保存し、HTML コンタクトシートと meta.json を出力する。

使い方:
    python3 research.py build --input input.json --out /path/to/pinterest-research

入力 JSON 形式:
    {
      "topic": "<お題>",
      "directions": {
        "A": {
          "title": "...",
          "interpretation": "...",
          "items": [
            {"src_url": "https://www.pinterest.com/pin/.../",
             "rationale": "...",
             "query": "..."}, ... 4 件
          ]
        },
        "B": {...},
        "C": {...}
      }
    }
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import mimetypes
import os
import re
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

SKILL_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = SKILL_DIR / "templates" / "contact_sheet.html"
PLACEHOLDER_PATH = SKILL_DIR / "placeholder.svg"

DIRECTIONS = ("A", "B", "C")
COLUMNS = ("a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l")
# 1 方向あたり 3 行 × 4 列 = 12 枚。バッジは A-a 〜 A-l
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.0 Safari/605.1.15"
)
TIMEOUT = 15


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^\w぀-ヿ一-鿿-]+", "-", text, flags=re.UNICODE)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:48] or "topic"


def http_get(url: str) -> tuple[bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        ctype = resp.headers.get("Content-Type", "")
        return resp.read(), ctype


META_RE = re.compile(
    r'<meta[^>]+(?:property|name)=["\']([^"\']+)["\'][^>]*content=["\']([^"\']*)["\']',
    re.IGNORECASE,
)
META_RE_REV = re.compile(
    r'<meta[^>]+content=["\']([^"\']*)["\'][^>]*(?:property|name)=["\']([^"\']+)["\']',
    re.IGNORECASE,
)


def extract_meta(html_bytes: bytes) -> dict[str, str]:
    try:
        text = html_bytes.decode("utf-8", errors="replace")
    except Exception:
        return {}
    out: dict[str, str] = {}
    for m in META_RE.finditer(text):
        key, val = m.group(1).lower(), m.group(2)
        out.setdefault(key, val)
    for m in META_RE_REV.finditer(text):
        val, key = m.group(1), m.group(2).lower()
        out.setdefault(key, val)
    return out


PINIMG_RE = re.compile(
    r'https?://i\.pinimg\.com/(?:originals|\d+x)/[^\s"\'<>)\\]+\.(?:jpg|jpeg|png|webp|gif)',
    re.IGNORECASE,
)


def find_pinimg_urls(html_bytes: bytes) -> list[str]:
    """HTML 本文から i.pinimg.com の画像 URL を出現順・重複除去で抽出。"""
    try:
        text = html_bytes.decode("utf-8", errors="replace")
    except Exception:
        return []
    seen: set[str] = set()
    urls: list[str] = []
    for m in PINIMG_RE.finditer(text):
        u = m.group(0)
        if u in seen:
            continue
        seen.add(u)
        urls.append(u)
    return urls


def is_pin_detail_url(src_url: str) -> bool:
    """個別 pin ページ（/pin/<digits>/）かどうか。"""
    return bool(re.search(r"pinterest\.[^/]+/pin/\d+/?", src_url))


def looks_like_thumbnail(u: str) -> bool:
    """プロフィールアイコンやファビコンと思しき小さい画像 URL を弾く。"""
    # i.pinimg.com の avatar / 75x75 / 30x30 等を回避
    return bool(re.search(r"/(?:30x30|45x45|60x60|75x75|avatar)/", u))


# Pinterest の全ページに刺さっている既知のグローバル資産（ヒーロー画像・既定 OG など）。
# 実行のたびに同一画像を引いてしまわないようハードスキップする。
PINTEREST_GLOBAL_ASSETS = (
    "default_open_graph",
    "d5/3b/01/d53b014d86a6b6761bf649a0ed813c2b",
)


def is_global_pinterest_asset(u: str) -> bool:
    return any(token in u for token in PINTEREST_GLOBAL_ASSETS)


def prefer_pinterest_high_res(image_url: str) -> str:
    """pinimg.com の 736x や 564x を originals に振り替える試み。
    実体が無い場合は元 URL でフォールバックする呼び出し側の責任。"""
    if "i.pinimg.com" not in image_url:
        return image_url
    m = re.match(r"^(https://i\.pinimg\.com/)([^/]+)(/.*)$", image_url)
    if not m:
        return image_url
    prefix, size, tail = m.group(1), m.group(2), m.group(3)
    if size == "originals":
        return image_url
    return f"{prefix}originals{tail}"


def guess_ext(url: str, ctype: str) -> str:
    path = urllib.parse.urlparse(url).path
    ext = Path(path).suffix.lower()
    if ext in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}:
        return ".jpg" if ext == ".jpeg" else ext
    if ctype:
        guess = mimetypes.guess_extension(ctype.split(";")[0].strip())
        if guess:
            return ".jpg" if guess == ".jpeg" else guess
    return ".jpg"


def download_image(image_url: str, assets_dir: Path) -> Path | None:
    candidates = [image_url]
    upgraded = prefer_pinterest_high_res(image_url)
    if upgraded != image_url:
        candidates.insert(0, upgraded)
    for cand in candidates:
        try:
            data, ctype = http_get(cand)
        except Exception:
            continue
        if not data or len(data) < 512:
            continue
        ext = guess_ext(cand, ctype)
        digest = hashlib.sha1(cand.encode("utf-8")).hexdigest()[:10]
        target = assets_dir / f"{digest}{ext}"
        if not target.exists():
            target.write_bytes(data)
        return target
    return None


def source_label(src_url: str) -> str:
    host = urllib.parse.urlparse(src_url).hostname or ""
    if "pinterest" in host:
        return "Pinterest"
    if "behance" in host:
        return "Behance"
    if "are.na" in host or "arena" in host:
        return "Are.na"
    return host.replace("www.", "") or "リンク"


def process_item(
    item: dict[str, Any],
    assets_dir: Path,
    used_image_urls: set[str] | None = None,
) -> dict[str, Any]:
    if used_image_urls is None:
        used_image_urls = set()
    src_url = item.get("src_url", "").strip()
    result: dict[str, Any] = {
        "src_url": src_url,
        "rationale": item.get("rationale", "").strip(),
        "query": item.get("query", "").strip(),
        "source_label": source_label(src_url),
        "og_title": "",
        "og_description": "",
        "local_path": None,
        "status": "ok",
    }
    if not src_url:
        result["status"] = "no_url"
        return result
    try:
        html_bytes, _ = http_get(src_url)
    except Exception as e:  # noqa: BLE001
        result["status"] = f"fetch_failed:{type(e).__name__}"
        return result
    meta = extract_meta(html_bytes)
    result["og_title"] = meta.get("og:title", "") or meta.get("twitter:title", "")
    result["og_description"] = (
        meta.get("og:description", "") or meta.get("twitter:description", "")
    )
    og_image = meta.get("og:image", "") or meta.get("twitter:image", "")

    # 本文中の pinimg URL（プロフィールアイコン・既知グローバル資産は除外）
    body_pinimg = [
        u
        for u in find_pinimg_urls(html_bytes)
        if not looks_like_thumbnail(u) and not is_global_pinterest_asset(u)
    ]

    # 候補組み立て:
    # 1) 個別 pin ページなら og:image を最優先（ただし既知グローバル資産は除外）
    # 2) ボード／ideas ページなら本文中 pinimg を優先
    candidates: list[str] = []
    is_pin = is_pin_detail_url(src_url)
    if is_pin:
        if og_image and not is_global_pinterest_asset(og_image):
            candidates.append(og_image)
        candidates.extend(u for u in body_pinimg if u not in candidates)
    else:
        candidates.extend(body_pinimg)
        if og_image and not is_global_pinterest_asset(og_image) and og_image not in candidates:
            candidates.append(og_image)

    if not candidates:
        result["status"] = "no_image_candidates"
        return result

    # 同一実行内ですでに引き当てた URL はスキップして fresh な画像を狙う。
    # それでも全候補が used に被るなら最後の手段として被りでも採用する。
    fresh = [u for u in candidates if u not in used_image_urls]
    ordered = fresh if fresh else candidates

    for image_url in ordered:
        local = download_image(image_url, assets_dir)
        if local:
            result["local_path"] = local.name
            result["resolved_image_url"] = image_url
            used_image_urls.add(image_url)
            return result

    result["status"] = "image_download_failed"
    return result


def ensure_placeholder(assets_dir: Path) -> str:
    target = assets_dir / "placeholder.svg"
    if not target.exists():
        shutil.copy2(PLACEHOLDER_PATH, target)
    return target.name


def render_card(direction: str, col_letter: str, item: dict[str, Any], asset_rel: str) -> str:
    badge = f"{direction}-{col_letter}"
    if item.get("local_path"):
        img_src = f"{asset_rel}/{item['local_path']}"
        failed = False
    else:
        img_src = f"{asset_rel}/placeholder.svg"
        failed = True
    src_url = item.get("src_url", "#")
    rationale = item.get("rationale") or item.get("og_title") or ""
    if failed and rationale:
        rationale = f"(原典のみリンク) {rationale}"
    elif failed:
        rationale = "(原典のみリンク)"
    label = item.get("source_label") or "リンク"
    return f"""
      <article class="card" data-badge="{html.escape(badge)}">
        <a class="card__media" href="{html.escape(src_url)}" target="_blank" rel="noopener">
          <img src="{html.escape(img_src)}" alt="{html.escape(rationale)[:80]}" loading="lazy">
        </a>
        <button class="card__badge" data-copy="{html.escape(badge)} を深掘り" type="button" title="クリックで『{html.escape(badge)} を深掘り』をコピー">{html.escape(badge)}</button>
        <div class="card__meta">
          <p class="card__rationale">{html.escape(rationale) if rationale else "&nbsp;"}</p>
          <a class="card__link" href="{html.escape(src_url)}" target="_blank" rel="noopener">↗ {html.escape(label)}</a>
        </div>
      </article>
    """.strip()


def render_section(direction: str, info: dict[str, Any], asset_rel: str) -> str:
    title = html.escape(info.get("title") or f"方向 {direction}")
    interpretation = html.escape(info.get("interpretation") or "")
    cards: list[str] = []
    items = info.get("items") or []
    for idx, col_letter in enumerate(COLUMNS):
        item = items[idx] if idx < len(items) else {"src_url": "", "rationale": "(該当ピン未収集)"}
        cards.append(render_card(direction, col_letter, item, asset_rel))
    return f"""
    <section class="direction" id="dir-{direction}">
      <header class="direction__head">
        <span class="direction__tag">方向 {direction}</span>
        <h2 class="direction__title">{title}</h2>
        <p class="direction__interp">{interpretation}</p>
      </header>
      <div class="direction__grid">
        {''.join(cards)}
      </div>
    </section>
    """.strip()


def build(args: argparse.Namespace) -> int:
    input_path = Path(args.input).expanduser().resolve()
    out_root = Path(args.out).expanduser().resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    topic = payload.get("topic", "untitled")
    directions = payload.get("directions") or {}

    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M")
    if args.drill_from:
        slug = f"{args.drill_from}-drill-{stamp}"
    else:
        slug = f"{slugify(topic)}-{stamp}"
    out_dir = out_root / slug
    assets_dir = out_dir / ".assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    ensure_placeholder(assets_dir)

    processed: dict[str, dict[str, Any]] = {}
    failures: list[str] = []
    used_image_urls: set[str] = set()
    for direction in DIRECTIONS:
        info = directions.get(direction) or {}
        items_out: list[dict[str, Any]] = []
        raw_items = info.get("items") or []
        for idx, col in enumerate(COLUMNS):
            if idx >= len(raw_items):
                items_out.append({
                    "src_url": "",
                    "rationale": "(該当ピン未収集)",
                    "status": "missing",
                    "id": f"{direction}-{col}",
                })
                failures.append(f"{direction}-{col}: missing item in input")
                continue
            print(f"[{direction}-{col}] fetching {raw_items[idx].get('src_url','')}", file=sys.stderr)
            result = process_item(raw_items[idx], assets_dir, used_image_urls)
            result["id"] = f"{direction}-{col}"
            items_out.append(result)
            if result["status"] != "ok":
                failures.append(f"{direction}-{col}: {result['status']}")
        processed[direction] = {
            "title": info.get("title", f"方向 {direction}"),
            "interpretation": info.get("interpretation", ""),
            "items": items_out,
        }

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    asset_rel = ".assets"
    sections_html = "\n".join(
        render_section(d, processed[d], asset_rel) for d in DIRECTIONS
    )
    generated_at = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    drill_from_html = (
        f'<span class="meta__drill">深掘り元: {html.escape(args.drill_from)}</span>'
        if args.drill_from
        else ""
    )
    rendered = (
        template.replace("{{TOPIC}}", html.escape(topic))
        .replace("{{GENERATED_AT}}", html.escape(generated_at))
        .replace("{{SECTIONS_HTML}}", sections_html)
        .replace("{{DRILL_FROM_HTML}}", drill_from_html)
    )
    (out_dir / "index.html").write_text(rendered, encoding="utf-8")

    meta = {
        "topic": topic,
        "generated_at": generated_at,
        "slug": slug,
        "drill_from": args.drill_from or None,
        "directions": processed,
        "failures": failures,
    }
    (out_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(str(out_dir / "index.html"))
    if failures:
        print(f"# warnings: {len(failures)} failures", file=sys.stderr)
        for f in failures:
            print(f"#  - {f}", file=sys.stderr)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="pinterest-research builder")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_build = sub.add_parser("build", help="JSON 入力からコンタクトシートを生成")
    p_build.add_argument("--input", required=True, help="入力 JSON のパス")
    p_build.add_argument("--out", required=True, help="出力ルート（pinterest-research ディレクトリ）")
    p_build.add_argument(
        "--drill-from",
        default="",
        help="深掘り元 slug があれば指定（出力ディレクトリ名と meta に印を付ける）",
    )
    args = parser.parse_args()
    if args.cmd == "build":
        return build(args)
    parser.error(f"unknown command: {args.cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
