# skill-pinterest-research

Claude Code 用のリサーチ／ムードボード生成 Skill。デザイン・撮影・構想のお題に対して **3 方向のリサーチ角度** を立て、それぞれ Pinterest を中心に参考画像 12 枚（3 × 4 グリッド）を集めて、合計 36 枚 / 1 シートの HTML コンタクトシートを生成する。

## 何ができる

- お題から **3 つの離れた切り口** を Claude が考案
- 各角度ごとに 4 枚 × 3 列 = 12 枚の参考画像を Pinterest（必要に応じて Behance / Are.na 等）から収集
- 1 枚の HTML コンタクトシートに集約。**画像はローカル保存**、各カードは元 pin に新規ウィンドウでリンク、セレクト理由のキャプション + 方向-列バッジ（A-a 〜 C-l）付き
- 「A-c を深掘り」のような追指示で精度を上げる二段階フローを内蔵

## インストール

```bash
git clone https://github.com/sasaki-ta-instyle/skill-pinterest-research \
  ~/.claude/skills/pinterest-research
```

Claude Code を再起動すれば、自然言語で次のように頼めるようになる。

```
化粧品ブランド ABC の春の販促ビジュアルのリファレンス集めて
```

```
A-c を深掘り
```

## 使い方

詳細仕様は [`SKILL.md`](./SKILL.md) を参照。Claude Code に対する指示の書き方・モード判定・深掘りフローを含む。

## ライセンス

MIT License — [`LICENSE`](./LICENSE) を参照。

このリポジトリで配布しているのはコードと仕様ドキュメントのみ。生成された HTML シートに埋め込まれる Pinterest 画像の著作権は各原著作者に帰属する。社外公開する場合は必ず原著作者の利用条件を確認すること。
