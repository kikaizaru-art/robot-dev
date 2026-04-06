# CoreS3 コンパニオンロボット

M5Stack CoreS3 を使った LOVOT 風コンパニオンロボットのプロトタイプ。
カメラで人を検知し、表情を変え、声で会話し、首や腕を動かす。

## ハードウェア構成

| パーツ | 用途 |
|--------|------|
| M5Stack CoreS3 | メインコントローラ (ESP32-S3, LCD, カメラ, マイク, スピーカー) |
| PCA9685 | I2C サーボドライバ |
| MG90S × 4 | 首ヨー/チルト + 左右腕 |
| FS90R × 2 | 走行用連続回転サーボ (予定) |
| ボールキャスター × 1 | 後輪 |

## 機能

- **表情アニメーション** — 6種類 (NORMAL / HAPPY / SAD / SURPRISED / SLEEPY / LOVE)、プロシージャル生成
- **顔検知 & 追従** — ML顔検知 + 肌色/動体検出、5段階の存在レベル判定
- **サーボ連動** — 検知した顔を首で追従、表情に連動した腕アニメーション
- **音声会話** — Gemini API (TTS) による日本語音声対話
- **タッチ & 音反応** — タッチで表情変化、大きな音で驚く
- **OTA更新** — WiFi経由でファームウェア書き込み

## ディレクトリ構成

```
src/             ファームウェア (PlatformIO, Arduino framework)
  main.cpp       メインループ: 検知→表情→サーボ制御
  face.h         LCD表情アニメーションエンジン
  camera_detect.h  顔検知・存在判定
  servo_ctrl.h   サーボ制御・アニメーション
  voice_chat.h   Gemini API 音声会話
chassis/         筐体 CAD (CadQuery → STEP → Fusion 360)
  assembly_v2.py メインアセンブリ
  parts/         個別パーツモデル (MG90S, FS90R, CoreS3 等)
assets/          表情画像 (PNG + RGB565)
data/            SPIFFS用表情データ
```

## ビルド

```bash
# ファームウェア書き込み (WiFi OTA)
pio run --target upload

# サーボテスト
pio run -e servo-test --target upload

# PCA9685テスト
pio run -e pca9685-test --target upload

# シリアルモニタ
pio device monitor -b 115200
```

## 開発状況

プロトタイプ開発中。ファームウェアは動作確認済み、筐体は CAD 設計完了・組み立て検証中。
