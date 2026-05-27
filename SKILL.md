---
name: pinterest-research
description: デザイン／撮影／構想のお題に対して 3 方向のリサーチ角度を立て、それぞれ Pinterest を中心に参考画像 12 枚（1 方向 = 3×4 グリッド = 12 枚、× 3 方向 = 計 36 枚 / 1 シート）を集めて 1 枚の HTML コンタクトシートにまとめる Skill。画像はローカル保存・元 pin に別ウィンドウでリンク・セレクト理由のキャプション・方向-列バッジ（A-a〜C-l）付き。「A-c を深掘り」で次の精度に進める。トリガー: 「/pinterest-research」「リファレンス 集めて」「ピンタレスト リサーチ」「ムードボード 作って」「コンタクトシート」「ビジュアル 参考」「<お題> のリファレンス」「<X-y> を深掘り」（X=A/B/C, y=a〜l）。
license: MIT
---

# pinterest-research

3 方向のリサーチ角度 × 4 枚 = 12 枚を 1 枚の HTML コンタクトシートに束ねる Skill。デザイン / 撮影 / 構想（コピー含む）のリファレンス集めで使う。

## 0. ファイル配置

- 本体: `~/.claude/skills/pinterest-research/SKILL.md`（このファイル）
- 生成スクリプト: `~/.claude/skills/pinterest-research/scripts/research.py`
- HTML テンプレ: `~/.claude/skills/pinterest-research/scripts/templates/contact_sheet.html`
- フォールバック画像: `~/.claude/skills/pinterest-research/scripts/placeholder.svg`

成果物は **コマンド実行時の CWD 配下** に書き出す:
```
<CWD>/pinterest-research/<slug>-<YYYYMMDD-HHMM>/
  index.html
  meta.json
  .assets/<sha1>.<ext>
```

## 1. 起動時の判定

ユーザー入力を 2 モードに振り分ける。

| モード | 判定キーワード | やること |
|---|---|---|
| **NEW** | 「リファレンス」「ムードボード」「コンタクトシート」「リサーチ」「ビジュアル 参考」「Pinterest で」+ お題テキスト、または `/pinterest-research <お題>` | Phase A → E を新規実行 |
| **DRILL** | 「`A-c` を深掘り」「`B-a` で詰めて」「`C-b` 方向で」のように **`[A-C]-[a-d]`** を含む | 直近の `meta.json` を読んで深掘り再リサーチ |

判定が曖昧なときはユーザーに 1 行で確認。

## 2. Phase A — 3 方向の構想（Claude が会話で行う）

お題と既知の文脈（業種・トーン・媒体・季節など）から、**互いに距離のある 3 つの角度** を作る。同じ方向の濃淡違いではなく、構成要素や狙いがハッキリ別になるように。

### 被写体モードの判定（プロダクト撮影／人物撮影）

Phase A の **最初に必ず** お題が **プロダクト中心** か **人物・モデル中心** かを判定する。判定結果は Phase A 提示時にユーザーにも明示する（「被写体モード: プロダクト中心」のように 1 行入れる）。

| モード | 判定キーワード | クエリ／URL 選定への含意 |
|---|---|---|
| **プロダクト中心** | 「物撮り」「プロダクト撮影」「商品撮影」「still life」「商品リファレンス」「パッケージ」「ボトル」「容器」「アンプル」 | 検索クエリに **`still life` / `product` / `bottle` / `packaging` / `flat lay` / `tabletop`** を積極的に混ぜる。URL 選定時、ボード／pin のタイトル・パスに **`model` / `portrait` / `face` / `makeup-look` / `skin-close-up` / `lips` / `editorial-beauty`** が含まれるものは除外する |
| **人物・モデル中心** | 「ポートレート」「モデルカット」「メイク撮影」「人物撮影」「キービジュアル」「ビューティ撮影」 | クエリは通常通り。プロダクトのみのボードは選ばない |
| **両方** | 明示無し or 「キャンペーン全体」「カタログ」「LP」 | ミックス。人物と物のバランスを 5:7 / 7:5 程度で取る |

判定が曖昧なときはユーザーに 1 行で確認。**「物撮り」「プロダクト撮影」が明示されていたら、ユーザーに確認せず即プロダクト中心モードに入る**。

### 3 方向の役割分担（固定ルール）

| 方向 | 役割 | 補足 |
|---|---|---|
| **A** | **お題ドメインの最新トレンド寄せ** | お題の業種・媒体・年代における直近 1〜2 年のビジュアルトレンドを引き当てる。Phase B に進む前に、A のためのトレンド下調べを WebSearch で 1 回追加で打つ（後述）。お題に時間軸が無くても A は必ず「いま」の角度で組む |
| **B** | **王道・鉄板** | そのお題で広く成立している中庸の方向。安心して通せる方向 |
| **C** | **対立軸 or ニッチ** | A/B の重心から意図的に外す。逆光⇄順光、暖⇄寒、装飾⇄ミニマム、商品中心⇄環境中心 のいずれかの軸を反転させる |

A の検索クエリには **時間軸キーワードを 1 つ必ず含める**:
- 英語: `2025`, `2026`, `latest`, `current trend`, `this season`, `editorial 2025`
- 日本語: `2025`, `2026`, `最新`, `トレンド`, `今期`

A 案の解釈テキストには、**どのトレンドに寄せたか**（例: 「longevity 系の研究室美学」「pro-aging」「low-fi grain revival」「クワイエットラグジュアリー」など）を 1 行で必ず明示する。

### 提示フォーマット

各方向につき、以下を 1 メッセージにまとめてユーザーに提示する。**ユーザーが OK を出してから Phase B に進む**（早期に外しを止めるため）。

```
お題: <ユーザー入力をそのまま>

方向 A（最新トレンド）: <タイトル 1 行>
  寄せたトレンド: <短く 1 行>
  解釈: <2〜3 行で狙いと拾うべき要素>
  検索クエリ: <時間軸入り英語クエリ>, <英語クエリ>, <日本語クエリ>

方向 B（王道）: ...
方向 C（対立軸）: ...
```

クエリは **英語 1〜2 + 日本語 1** を基本（Pinterest は英語インデックスのほうが収量が多い）。クエリは具体名詞 + 質感語（matte, grainy, overcast, ambient, glassware, neon, paper texture など）で組む。

### A のためのトレンド下調べ（Phase A の前半）

A 案の精度を上げるため、Phase A の構想を出す前に **WebSearch を 1〜2 回** 打って近年（直近 1〜2 年）のビジュアルトレンドを下調べする。クエリ例:
- `<お題ドメイン> visual trend 2025 2026`
- `<お題ドメイン> editorial photography trend`
- `<業種> ビジュアル トレンド 2026`

下調べ結果から拾ったキーワード（例: クワイエットラグジュアリー / longevity / pro-aging / cyber-clinical / grain revival 等）を A 案のタイトル・解釈・クエリに織り込む。下調べを省略しない。

## 3. Phase B — ソース収集（Claude が WebSearch する）

各方向につき以下:

1. `WebSearch` を 2〜3 回。クエリ例:
   - `site:pinterest.com <英語クエリ>`
   - `site:pinterest.com <別軸英語クエリ>`
   - `site:pinterest.com <日本語クエリ>`
2. 返ってきた URL から **12 件** を選ぶ。優先順位:
   - **第一優先**: `https://www.pinterest.com/pin/<数字>/` の個別 pin URL
   - 次点: `pinterest.com/ideas/.../<数字>/` の ideas ページ、ボードページ（research.py 側で本文中の pin 画像を抽出するフォールバックが効く）
   - 重複ビジュアル・人物アイコンのみのものは除外
3. 12 件揃わない方向は補助で `site:behance.net` / `site:are.na` から不足分を混ぜる（必ず 12 件埋める）
4. 各 URL に「**なぜこれを選んだか**」を 1〜2 行で言語化（後で HTML のキャプションに入る）

すべて揃ったら、**1 つの JSON** に組み立てて `research.py build` に渡す。JSON 形式:

```json
{
  "topic": "<お題そのまま>",
  "directions": {
    "A": {
      "title": "マットな深紅 × 雑誌的タイポ",
      "interpretation": "...",
      "items": [
        {"src_url": "https://www.pinterest.com/pin/XXXX/", "rationale": "余白とタイポの抜けが指針", "query": "matte burgundy editorial cosmetics"},
        ... 全 4 件
      ]
    },
    "B": {...},
    "C": {...}
  }
}
```

このまま `research.py` に渡す。

## 4. Phase C/D — 画像取得と HTML 生成（research.py）

実行コマンド:

```bash
python3 "$HOME/.claude/skills/pinterest-research/scripts/research.py" build \
  --input <input.json のパス> \
  --out  "<CWD>/pinterest-research"
```

スクリプトの動き:
- 各 `src_url` を urllib で取得 → `<meta property="og:image">` `og:title` `og:description` を抽出
- Pinterest なら `i.pinimg.com/originals/...` を優先 → 無ければ `/736x/` 系
- 画像を `.assets/<sha1>.<ext>` に保存（既にあればスキップ）
- 取得失敗は `placeholder.svg` を貼ってログに記録、ジョブ全体は止めない
- `index.html`（テンプレ差し込み）と `meta.json`（id / src_url / query / og_title / rationale / local_path）を書き出し
- 完了時に `index.html` の絶対パスを stdout に 1 行で吐く

実行後の Claude のふるまい:
- `index.html` をブラウザで開けるよう、絶対パスをユーザーに **1 行で渡す**
- 取得失敗があった画像は方向と列を明示して「失敗 N 件あり、必要なら同方向で再リサーチします」と通知

## 5. Phase E — 深掘り（DRILL モード）

ユーザー入力例: 「**A-c を深掘り**」「**B-a の方向で、もっと暗くマットに**」

手順:
1. **直近の `meta.json`** を探す（CWD 配下 `pinterest-research/*/meta.json` のうち最新 mtime）
2. 対象 ID（例: `A-c`）の `src_url` / `query` / `rationale` をシードに、**新しい 3 方向** を組み立てる:
   - 新 A: シード画像の最近接（同 query + キーワード強化）
   - 新 B: シードの **質感方向に振る**（ユーザーが追加指示を出していれば最優先で反映）
   - 新 C: シードの **構図方向に振る** か、片軸（光・余白・色温度・素材感）を反対側に振る
3. Phase A のユーザー確認は **省略**（既に深掘り指示が出ているため）、直接 Phase B → research.py へ
4. 出力先は元と区別: `pinterest-research/<元 slug>-drill-Ac-<YYYYMMDD-HHMM>/`

## 6. HTML 仕様（テンプレ）

- ビューポート基準: **iPad Pro 12.9 横 1366×900**
- 3 セクション縦並び（A → B → C）。各セクションに方向タイトル + 解釈テキスト + 3 行 × 4 列のグリッド
- 各セル:
  - 画像（`object-fit: cover`、`aspect-ratio: 4/5`）
  - 右上に **方向-列バッジ**（`A-c` など、白字 / 半透明黒地）。クリックで `navigator.clipboard.writeText("A-c を深掘り")` を実行
  - 画像クリックで **元ソース URL** に `target="_blank" rel="noopener"` で遷移
  - 下に **キャプション**（セレクト理由 1〜2 行 + 小さく `↗ <ソース名>` リンク）
- 配色は instyle.group フラット系のテンプレ内 CSS 変数で完結（Workspace の design-system に依存しない）
- 印刷 CSS: 各セクション改ページ（PDF 化したい時用）

## 7. 著作権・運用上の注意

- 集めた画像は **リサーチ補助のローカル一時利用** のみ。LP / 印刷物 / SNS への直接転用は不可
- 出来上がった HTML は個人作業用。`/html/` 共有ディレクトリ（cpc/app/crhr）には置かない
- 元 pin が削除されてもローカル画像で見返せるが、**元の出典 URL は必ず meta.json と HTML 両方に残す**
- 取得失敗 pin（ログイン必須 / 削除済）は placeholder に差し替え、ジョブは継続する

## 8. 失敗系メモ

- WebSearch が 1 方向で 0 件返した場合: その方向だけ「該当ピンを集められませんでした。角度を変えてください」プレースホルダで描画し、他方向は完成させて出す。ユーザーに角度の振り直しを促す
- og:image が取れない pin: placeholder + キャプションに「(原典のみリンク)」を付記してリンクは生かす
- 出力先 CWD 直下に既に `pinterest-research/` がある場合: 上書きせず timestamp 付き子ディレクトリで並走させる
