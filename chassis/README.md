# CoreS3 コンパニオンロボット 筐体設計

## 構成

3分割構造:
1. **ベースプレート** — FS90R駆動輪×2 + ボールキャスター
2. **ボディシェル** — 腕サーボ×2 + PCA9685 + 配線
3. **ヘッドマウント** — CoreS3をスライドイン固定、パンチルト接続

## ファイル

- `robot_chassis.scad` — OpenSCAD設計ファイル（全パーツ統合）

## OpenSCADで開く

```bash
openscad chassis/robot_chassis.scad
```

## STLエクスポート（印刷用）

```bash
cd chassis
openscad -D "show_base=true;show_body=false;show_head=false;show_components=false" -o base.stl robot_chassis.scad
openscad -D "show_body=true;show_base=false;show_head=false;show_components=false" -o body.stl robot_chassis.scad
openscad -D "show_head=true;show_base=false;show_body=false;show_components=false" -o head.stl robot_chassis.scad
```

## サイズ

| パーツ | サイズ(mm) |
|--------|-----------|
| ベース | 105 x 90 x 25 |
| ボディ | 90 x 75 x 55 |
| ヘッド | ~63 x ~47 x 50 |
| 全高 | ~160mm |

## 買い足しパーツ

| パーツ | 数量 | 価格目安 |
|--------|------|----------|
| PCA9685互換品 | 1 | 500-1,000 |
| MG90Sサーボ | 3 | 1,500 |
| FS90R連続回転サーボ | 2 | 800-1,200 |
| FS90R用タイヤ | 2 | 300-500 |
| ボールキャスター(小) | 1 | 100-300 |
| パンチルトブラケット | 1 | 300-600 |
| 5V 3A電源 | 1 | 500-1,000 |
| **合計** | | **4,000-6,100** |
