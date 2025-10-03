# agents.md — Godot 4.5 粒子ビジュアライザ（砂・花びら・種・水滴）

バージョン: 0.1.0  
対象: Windows (初期) / Android (将来)  
実装想定: Godot 4.5（GDScript メイン、必要なら C# 拡張）

---

## 0. 目的
LLM 駆動で「見た目・物理・演出・エクスポート」を手早く組み替える。各エージェントは**明確な入出力スキーマ**を持ち、Godot 側は JSON/ファイルを介して疎結合に連携する。

---

## 1. 全体アーキテクチャ
```
[UI] ─────────┐
               │  ユーザ操作/プリセット選択
[Timekeeper] ──┼──→ [Simulation Director] ──┬─→ [Particle/CA Core]
               │                              │
[Agents] 〈LLM〉┴→ JSON(プリセット/力場/障害物/演出) ─┘
                         │
                    [Exporter]
```
- **Simulation Director**: Godot ランタイムの司令塔。各 JSON をロードし、シーン/シェーダ/エミッタ/速度場を更新。
- **Agents**: LLM 側の生成・編集・提案を担当。Godot とは JSON/メタファイルでやりとり。

---

## 2. 主要エージェント

### 2.1 PresetAgent（プリセット生成・編集）
- 役割: 砂/花びら/種/水滴などの見た目・挙動と、発生率/積もり方/色調/季節感をまとめたプリセット JSON を生成・編集。
- 入力:
  - ユーザ要望（自然文）
  - 既存 `preset.v1.json`（任意）
  - 制約（最大粒子数、解像度スケール、目標FPS など）
- 出力: `preset.v1.json`
- JSON スキーマ（抜粋）:
```json
{
  "version": "1.0",
  "name": "spring_breeze",
  "emitter": {
    "type": "petal",
    "rate_per_sec": 600,
    "burst": {"interval_sec": 5, "count": 200},
    "spawn_band": {"y": 0.05, "height": 0.02},
    "random_seed": 42
  },
  "appearance": {
    "palette": ["#ffd6e7", "#ffc1dc", "#ffe9f2"],
    "size_px": {"min": 8, "max": 18},
    "sprite": "res://assets/petal_a.png"
  },
  "motion": {
    "drag": 0.12,
    "sway": {"amp": 30.0, "freq": 0.6},
    "spin": {"deg_per_sec": 180},
    "gravity": 240,
    "glide": {"lift": 0.35}
  },
  "accumulation": {
    "enabled": true,
    "mode": "heightmap",
    "max_height_px": 180,
    "diffusion": 0.08
  },
  "obstacle": {
    "collide_mask": "res://runtime/obstacles_mask.png",
    "stickiness": 0.2
  },
  "fx": {
    "bloom": 0.2,
    "background": {
      "gradient": ["#0b1120", "#1e293b"],
      "cycle_by_clock": true
    }
  },
  "targets": {"fps": 60, "internal_scale": 0.75},
  "notes": "桜の花びら・横揺れ強め"
}
```

### 2.2 ForceFieldAgent（風・竜巻・雨/水面）
- 役割: 2D 速度場テクスチャやパラメトリックな風イベントを設計。
- 入力: 要望（例: 「午後3時に強風→竜巻10秒」）、制約（最大風速）
- 出力: `forcefield.v1.json` + 任意でベクトル場テクスチャ（`res://runtime/force_x.png`, `force_y.png`）
- JSON（抜粋）:
```json
{
  "version": "1.0",
  "timeline": [
    {"t": 0,   "type": "wind", "dir_deg": 180, "speed": 120},
    {"t": 30,  "type": "gust", "dir_deg": 150, "speed": 240, "dur": 6},
    {"t": 45,  "type": "tornado", "center": [0.6, 0.7], "radius": 0.2, "vortex": 380, "dur": 10}
  ],
  "texture": {"use_prebaked": false}
}
```

### 2.3 ObstacleAgent（障害物レイアウト）
- 役割: ユーザの自然文や図形指定から、障害物マスク画像/ベクタを生成。
- 入力: 指示（例: 「中央に半月、左右に柱2本」「時刻で地形を掃除」）
- 出力: `obstacles.v1.json` と `obstacles_mask.png`（2048×2048 など）
- JSON（抜粋）:
```json
{
  "version": "1.0",
  "clear_rules": [
    {"trigger": "clock", "at": "03:00", "action": "erase_all"},
    {"trigger": "inactivity_sec", "gte": 180, "action": "soft_clear", "radius_px": 64}
  ],
  "draw_ops": [
    {"op": "circle", "pos": [0.5, 0.6], "radius": 0.1, "mode": "solid"},
    {"op": "rect",   "rect": [0.05,0.2,0.08,0.6], "mode": "solid"}
  ]
}
```

### 2.4 SimulationDirectorAgent（シーケンス脚本）
- 役割: プリセット/力場/障害物/FX の切替や演出キューを脚本化。
- 入力: シーン意図（自然文）、開催時間/季節/時刻
- 出力: `sequence.v1.json`
- JSON（抜粋）:
```json
{
  "version": "1.0",
  "tracks": [
    {"t": 0, "apply": {"preset": "spring_breeze.json", "force": "calm.json"}},
    {"t": 20, "apply": {"force": "gust_short.json"}},
    {"t": 40, "apply": {"preset": "maple_seed_glide.json"}},
    {"t": 60, "apply": {"force": "tornado_teaser.json"}}
  ],
  "loop": true
}
```

### 2.5 ExporterAgent（出力系）
- 役割: 高解像度スクショ、短尺動画（mp4/webm）、プリセット/ランダムシード付きの再現パッケージを生成。
- 入力: 出力指定、演出長、解像度/フレームレート
- 出力: 画像/動画/zip（`preset.json`, `sequence.json`, `forcefield.json`, `seed.txt`）
- JSON（抜粋）:
```json
{
  "version": "1.0",
  "capture": {"type": "video", "w": 1920, "h": 1080, "fps": 60, "dur_sec": 10},
  "watermark": {"text": "@sandviz", "pos": "tr"},
  "seed": 123456
}
```

### 2.6 TimekeeperAgent（時刻/季節ロジック）
- 役割: 実時刻/擬似時刻で色相・重力・風などを季節連動させる設定を生成。
- 入力: 地域/カレンダー設定
- 出力: `timefx.v1.json`

### 2.7 UIHintsAgent（UI ヒント/チュートリアル）
- 役割: 初回ユーザ向け操作説明、オススメプリセット提案。
- 入力: 使用ログの要約
- 出力: `uihints.v1.json`

### 2.8 AssetPackAgent（素材バンドル整備）
- 役割: 必要なテクスチャ/スプライト/シェーダ定義の参照リストを構築し、欠品を警告。
- 入力: 既存 JSON 群
- 出力: `assets.v1.json`

---

## 3. Godot 側 API（ファイルベース・最小セット）
- `res://runtime/preset.json` … 読み込み時/ホットリロード可能
- `res://runtime/forcefield.json` … 速度場/イベントを反映
- `res://runtime/sequence.json` … シーン進行
- `res://runtime/obstacles_mask.png` … 衝突と積層対象
- `res://runtime/capture.json` … エクスポート指示

Godot からは `user://out/` に実ファイルを書き出し（スクショ/動画/zip）。ホットリロードはファイル監視で実装。

---

## 4. プロンプト設計（例）

### PresetAgent 用（指示テンプレ）
```
あなたはビジュアル粒子のプリセット設計者です。下記制約を満たし、JSON preset.v1 を生成します。
- 表現: 桜の花びら、横揺れを強め、夜明け色の背景
- 目標: 60fps, FHD, 上限10万粒
- 積層: 高さマップ方式、最大 180px
出力は JSON のみ。説明文は "notes" フィールド内に 80 文字以内で。
```

### ForceFieldAgent 用（例）
```
午後 3:00 に 6 秒の突風、その後 10 秒間の小さな竜巻を右下で。最大風速は 400。
forcefield.v1 の JSON を生成。timeline の t は秒。テクスチャは使わない。
```

---

## 5. スキーマ仕様（ドラフト）
- すべて UTF-8 / LF。数値は px か正規化(0..1)を明記。
- 互換性: `version` を必須。後方互換破壊はメジャーアップ。
- 相対パスは `res://` 基点。動的生成物は `res://runtime/`。

---

## 6. 運用フロー
1. ユーザ操作 → Godot が現在の JSON 群を書き出し（編集点も含む）
2. LLM 側エージェントが読み込み、変更案を生成
3. Godot が差分適用（プレビュー）
4. OK なら保存/エクスポート

---

## 7. セキュリティ/安全
- ファイル書き込み先を `user://out/` に限定。
- 外部 URL 参照はホワイトリスト。
- JSON の数値にクランプ（NaN/Inf 防止、最大粒子数/速度の上限）

---

## 8. テレメトリ/評価（任意）
- FPS、ドロップ率、粒子数、シェーダ時間をログ（ローカル）。
- ユーザ許諾がある場合のみ匿名集計。

---

## 9. 既知のリスク
- 低スペック端末では CA + 粒子の同時実行でフレーム落ち
- Android のサーフェス解像度差による見え方の不一致

---

## 10. 付録: Godot 連携の最小 I/O 例
- 起動時: `preset.json` をロードして `ParticleProcess2D`/シェーダに橋渡し
- 入力描画: `obstacles_mask.png` にペイント（ViewportTexture + Shader）
- 風: `forcefield.json` の timeline を `Process` で進行
- クリア: マスク書き換え + 高さマップクリア

---

## 変更履歴
- 0.1.0: 初版。主要エージェント・スキーマの雛形を定義

