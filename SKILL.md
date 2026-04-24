---
name: robot-dev
description: M5Stack CoreS3 をベースにした LOVOT 風コンパニオンロボットのプロトタイプ開発プロジェクト。子供たち向けのデスクサイズロボットで、感情表現・顔検知追従・サーボ駆動・音声対話を実装している。次のキーワードや話題が出たときに発動すること： 「ロボット」「コンパニオンロボット」「LOVOT」「CoreS3」「M5Stack」「ESP32-S3」「PCA9685」「MG90S」「FS90R」「サーボ」「パンチルト」「ヨー軸」「筐体」「シャーシ」「CadQuery」「3Dプリント」「Bambu」「ユニバーサルプレート」「表情アニメーション」「顔検知」「Gemini 音声対話」「PlatformIO」「OTA」「ArduinoOTA」。ハード設計・ファームウェア・筐体CAD・機構・購入リスト・商品化方針など、このロボット製作に関する全般の相談相手となる。
---

# CoreS3 コンパニオンロボット (robot-dev)

## プロジェクトの目的
M5Stack CoreS3 をメインコントローラとし、LOVOT のような「そこにいるだけで可愛い」コンパニオンロボットを自作するプロトタイプ。子供たち向けのデスクサイズ玩具として、カメラで人を検知して顔を追い、表情を変え、音で反応し、腕や首を動かし、Gemini API で日本語の音声対話ができる。

最終的には商品化も視野に入れており、USB-C PD 充電、バッテリー駆動、足回り（FS90R 連続回転サーボ + ボールキャスター）への拡張を計画している。まずは動かしてみて手応えを確かめる「過剰設計を避ける」方針で進めている。

## 現在のフェーズ
- **ファームウェア**: 動作確認済み。表情6種（NORMAL / HAPPY / SAD / SURPRISED / SLEEPY / LOVE）、顔検知+肌色+動体による5段階の存在レベル判定、IMU傾き検知、タッチ反応、マイクのスパイク検知、Gemini 音声対話、WiFi OTA まで実装済み。
- **筐体 CAD**: 設計完了・組み立て検証中。`chassis/assembly_v2.py` が軸位置基準（shaft-first）で設計されたメインアセンブリ。
- **機構方針（2026-04-06 決定）**: MG90S ストールトルク 1.8kg·cm に対し負荷 ~150g のため、ヨー軸は**直付けで十分**と判断。ターンテーブル/BBベアリング/リンク機構は検討済みだが現状は不要。実機で動かしてガタつきがあれば補強する。
- **次にやること候補**: 実機組み立て・動作検証、足回り（FS90R 走行）実装、USB-C PD 充電対応、バッテリー搭載検討。

## 技術スタック・使用ツール
- **メインボード**: M5Stack CoreS3 (ESP32-S3, LCD, カメラ, マイク, スピーカー, IMU, タッチ)
- **サーボドライバ**: PCA9685 (I2C, Port A: G2=SDA, G1=SCL, 400kHz)
- **サーボ**: MG90S × 4（首 yaw/tilt + 腕 左右）、FS90R × 2（走行、予定）、ボールキャスター × 1（後輪）
- **電源（プロトタイプ）**: 9V ACアダプタ → DIN BASE (9-24V入力, SY8303AIC, 5V/3A出力)
- **ファームウェア**: PlatformIO CLI, Arduino framework, C++
  - lib: M5CoreS3, M5Unified, ESPAsyncWebServer, AsyncTCP, ESP32Servo, Adafruit PWM Servo Driver, ArduinoJson
- **書き込み**: WiFi OTA（`cores3-robot.local` / espota）。サーボ/PCA9685テストは USB(COM4)
- **シリアルモニタ**: `pio device monitor -b 115200`
- **筐体 CAD**: CadQuery 2.7.0 (Python) → STEP → Fusion 360 で確認
- **3Dプリンタ**: Bambu Lab A1 (FDM)
- **フレーム素材**: タミヤ ユニバーサルプレート 70157（160×60mm, 厚3mm, 5mmピッチ, 3mm穴）
- **音声対話**: Google Gemini API (TTS + 対話)

## リポジトリ構成
- `/README.md` — プロジェクト概要、機能一覧、ビルドコマンド
- `/platformio.ini` — PlatformIO 設定。`m5stack-cores3`（本番、OTA）、`servo-test`（USB）、`pca9685-test`（USB）の 3 環境
- `/.claude/commands/robot.md` — Claude Code 用スラッシュコマンド定義（本プロジェクトの作業手順・判断軸の一次情報源）
- `/src/` — ファームウェア
  - `main.cpp` — メインループ: 検知→存在判定→表情遷移→サーボ制御。WiFi+OTA+WebSocket ログも内包
  - `face.h` — LCD 表情アニメーションエンジン（プロシージャル生成）
  - `camera_detect.h` — ML 顔検知 + 肌色/動体検出 + 存在レベル判定
  - `servo_ctrl.h` — PCA9685 経由のサーボ制御、表情連動アニメ、idle motion
  - `voice_chat.h` — Gemini API による音声対話（IDLE / LISTENING / PROCESSING / SPEAKING の状態機械）
  - `expressions.h` — 表情 enum 共通定義
  - `servo_test.cpp`, `pca9685_test.cpp` — 個別テストファーム
  - （gitignore 済み・secrets）`wifi_config.h`, `gemini_config.h`
- `/chassis/` — 筐体設計
  - `assembly_v2.py` — **メインアセンブリ**。軸位置基準（shaft-first）設計
  - `assembly.py` — 旧版（参考）
  - `parts/` — 個別パーツ CadQuery モデル（`mg90s.py` / `fs90r.py` / `cores3.py` / `pan_tilt_bracket.py`）と STEP/STL、PCA9685 の STEP
  - `yaw_link_mechanism.py` — ヨー軸リンク機構の検討モデル（**現状は採用せず、参考用**）
  - `yaw_link_parts/` — リンク機構用のパーツ STEP
  - `robot_chassis.scad` — 初期の OpenSCAD 設計（旧版）
  - `*.step`, `*.stl` — エクスポート済み 3Dデータ（head / body / base / neck / pan_base / tilt_bracket / roll_bracket など）
- `/data/` — SPIFFS(LittleFS) 用の表情 RGB565 バイナリ（each 153600B）
- `/assets/expressions/`, `/assets/rgb565/` — 表情画像ソース
- `/include/`, `/lib/`, `/test/` — PlatformIO 標準（現状ほぼ空）

## Claudeに期待する役割
このプロジェクトの **技術的な議論の相棒**。以下のような相談に付き合ってほしい：

- ファームウェア改修の相談（表情ロジック、センサー融合、サーボモーション、Gemini 連携、OTA、メモリ/タイミング問題）
- 筐体 CAD の設計レビュー・モデル修正（CadQuery スクリプト、軸配置、クリアランス、ブラケット形状）
- 機構設計の判断（直付け vs リンク機構、ベアリング要否、負荷見積もり、3D プリント向け肉厚）
- 実装の優先順位・次のマイルストーンの相談
- 買い足しパーツの選定（型番・価格・入手性）、BOM 更新
- 子供向け玩具としての UX 議論（怖くない・飽きない・壊れない）
- 商品化に向けた電源・充電・バッテリー方式の検討

提案は断定せず選択肢とトレードオフを示し、**過剰設計を避ける**原則に従うこと。既存の設計判断（特にヨー軸直付け方針）を覆す場合は根拠を明示する。

## 注意事項・前提

### ハマりポイント（ファームウェア）
- **WiFi 初期化は setup() でノンブロッキング**。ブロッキングで待つと WDT クラッシュ。
- **マイク初期化は `cfg.internal_mic = true` で `CoreS3.begin(cfg)` に渡す**。カメラ初期化後に別途 `Mic.begin()` を呼ぶとクラッシュする。
- **サーボ用タイマーは 2, 3 を使う**。0, 1 はディスプレイ/オーディオと競合する。
- **PCA9685 クローン品は V+ がサーボ端子に繋がっていないことがある** → CH0 の V+ ピンにジャンパーで 5V 直接給電するワークアラウンドを採用中。
- LCD 表情はプロシージャル生成（PNG ではなく描画）。`data/*.bin` は別系統の RGB565 リソース。
- 表情遷移は `EXPR_SETTLE_MS = 600ms` の安定化時間を設けている。SURPRISED / SAD は即時遷移。

### CadQuery 設計の方針
- **shaft-first**: サーボの出力軸位置を先にワールド座標で決め、`place_servo_by_shaft()` でサーボ本体を逆算配置する。
- サーボ寸法（MG90S / FS90R）はデータシート値をコード先頭にまとめてある。
- 実行は `cd chassis && python <file>.py` → STEP 出力 → Fusion 360 で目視確認。
- タミヤ ユニバーサルプレート（5mm ピッチ 3mm 穴）を前提にした穴配置。

### 過去に検討済み・結論が出ていること
- **ヨー軸の荷重対策**: 直付けで OK（MG90S トルク余裕、負荷 ~150g）。ターンテーブル+中心軸方式は `yaw_link_mechanism.py` にモデル化済みだが採用していない。
- **CAD ツール**: OpenSCAD から CadQuery に移行済み（`robot_chassis.scad` は旧版、参照のみ）。
- **筐体構成**: ベース / ボディ / ヘッド の 3 分割。

### 機能を勝手に削除・簡略化しない
ユーザーの明示指示がない限り、既存機能（表情、顔検知、音声対話、OTA、Web ログ等）を「不要」と判断して削除しない。リファクタ時も挙動は保つ。

### Secrets
`src/wifi_config.h` と `src/gemini_config.h` は gitignore 済み。これらに関する内容を生成するときは、値は伏せてテンプレートのみ示す。

### 未定・未確定事項（2026-04-24 時点）
- 足回り（FS90R 走行）の実装タイミングは**現時点では未定**。
- バッテリー搭載の有無・型番は**現時点では未定**（足回り実装後に検討予定）。
- 商品化のタイムラインや販売形態は**現時点では未定**。
