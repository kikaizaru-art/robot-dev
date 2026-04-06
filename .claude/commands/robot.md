---
description: CoreS3ロボット制作の続きをする。ハード設計・ファームウェア・筐体CAD・購入リストなど全般。「ロボット」「CoreS3」「サーボ」「筐体」「CadQuery」「パーツ」に関する作業で使用する。
allowed-tools: Bash, Read, Edit, Write, Glob, Grep, Agent, TodoWrite, WebSearch, WebFetch
user-invocable: true
---

# CoreS3 コンパニオンロボット制作スキル

## プロジェクト概要
LOVOTのようなコンパニオンロボットを子供たち向けにプロトタイプ中。
M5Stack CoreS3をベースに、感情表現・センサー融合・サーボ駆動を実装。

## プロジェクト場所
`C:/Users/kikai/projects/cores3-robot/`

## 記憶の参照（必ず最初に読むこと）
このスキル実行時、まず以下のメモリファイルを読んで最新状態を把握する：
1. `~/.claude/projects/C--Users-kikai/memory/project_cores3_robot.md` — プロジェクト全体の状態・パーツ・方針
2. `~/.claude/projects/C--Users-kikai/memory/project_cores3_chassis_cadquery.md` — CadQuery筐体設計の詳細

## ハードウェア構成
- **メインボード:** M5Stack CoreS3 (ESP32-S3)
- **サーボドライバ:** PCA9685 (I2C, Port A: G2=SDA, G1=SCL)
- **サーボ:** MG90S × 4（首パン/チルト + 腕左右）、将来 FS90R × 2（走行）
- **フレーム:** タミヤ ユニバーサルプレート（160×60mm, 5mmピッチ, 3mm穴）
- **3Dプリンタ:** Bambu Lab A1 (FDM)
- **電源（プロトタイプ）:** 9V ACアダプタ → DIN BASE (9-24V入力, SY8303AIC 5V/3A出力)

## 開発環境
- **ファームウェア:** PlatformIO CLI, C++ (Arduino framework)
- **書き込み:** WiFi OTA (`cores3-robot.local` / espota)
- **CAD:** CadQuery 2.7.0 (Python) → STEP → Fusion 360
- **シリアルモニタ:** `pio device monitor -b 115200`（コマンドを毎回表示すること）

## 作業時の注意事項

### ファームウェア
- WiFi初期化はsetup()でノンブロッキング（ブロッキングだとWDTクラッシュ）
- マイク初期化は `cfg.internal_mic = true` で CoreS3.begin(cfg) に渡す（カメラ後に別途beginするとクラッシュ）
- サーボ用タイマーは 2, 3 を使用（0, 1 はディスプレイ/オーディオと競合）
- PCA9685のV+はクローン品だとサーボ端子に繋がっていない → CH0のV+ピンにジャンパーで5V直接給電

### CadQuery筐体設計
- 設計ファイル: `chassis/assembly_v2.py`（メイン）、`chassis/parts/`（パーツモデル）
- `chassis/yaw_link_mechanism.py` — ヨー軸リンク機構の検討モデル（参考用）
- サーボ配置は shaft-first 方式（出力軸位置を先に定義→サーボ本体を逆算配置）
- STEPエクスポート → Fusion 360で確認のワークフロー
- CadQuery実行: `cd chassis && python <file>.py`

### 機構設計の方針（2026-04-06決定）
- **ヨー軸:** MG90Sストールトルク1.8kg·cm に対し負荷~150g → 直付けで耐荷重は余裕
- **まず動かして検証** → ガタつきがあれば固定方法を補強（過剰設計を避ける）
- ターンテーブル/BBベアリング/リンク機構は参考として検討済みだが、現状は不要と判断

### 商品化に向けた方針
- 電源はUSB-C PDで充電できる設計にする（PD トリガーボード → 9-12V → DIN BASE）
- バッテリー搭載は足回り（FS90R）実装後に検討

## ビルド＆書き込みコマンド

```bash
# メインファームウェア（WiFi OTA）
cd C:/Users/kikai/projects/cores3-robot && pio run --target upload

# mDNSが解決しない場合
cd C:/Users/kikai/projects/cores3-robot && pio run --target upload --upload-port 192.168.10.114

# サーボテスト（USB書き込み）
cd C:/Users/kikai/projects/cores3-robot && pio run -e servo-test --target upload

# PCA9685テスト（USB書き込み）
cd C:/Users/kikai/projects/cores3-robot && pio run -e pca9685-test --target upload

# シリアルモニタ
cd C:/Users/kikai/projects/cores3-robot && pio device monitor -b 115200

# CadQueryモデル実行
cd C:/Users/kikai/projects/cores3-robot/chassis && python assembly_v2.py
```

## 買い足しリスト
メモリファイル `project_cores3_robot.md` の「買い足しリスト」セクションを参照・更新すること。

## 作業の進め方
1. メモリファイルを読んで現状把握
2. ユーザーの指示に基づき作業
3. 作業完了後、メモリファイルを更新（パーツ状況・設計方針の変更等）
4. 機能を勝手に削除・簡略化しない（feedback_no_remove_features）
5. シリアルモニタのコマンドは毎回表示する（feedback_serial_monitor）
