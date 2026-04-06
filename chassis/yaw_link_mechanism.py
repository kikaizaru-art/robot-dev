"""
ヨー軸リンク機構 — ユニバーサルプレート版
===========================================

問題:
  パンチルトブラケット + CoreS3 の全重量が yaw サーボ軸に直接かかっている。
  サーボ軸は回転力を伝えるもので、構造材として荷重を受けるべきではない。

解決:
  ベースプレート上に回転軸（M3ボルト + ナイロンスペーサー）を立て、
  ターンテーブル（上部プレート）をその軸で支持。
  yaw サーボはベースに固定し、リンクアームでターンテーブルを回す。
  → サーボ軸には回転トルクのみ、荷重は中心軸が受ける。

構成:
  1. base_plate    — ベースプレート（ユニバーサルプレート切り出し）
  2. turntable     — ターンテーブル（ユニバーサルプレート切り出し、上に載る）
  3. center_shaft  — 中心回転軸（M3ボルト + ナイロンスペーサー）
  4. yaw_servo     — MG90S、ベースに横付け固定
  5. link_arm      — サーボホーン → ターンテーブル端のプッシュロッド

ユニバーサルプレート仕様:
  - タミヤ 70157: 160 × 60 mm、厚さ 3mm
  - 5mm ピッチの穴（3mm径）、端から 2.5mm オフセット
  - 穴数: 32 × 12 = 384 穴/枚
"""
import cadquery as cq
import os
import sys
import math

# パーツのインポート
sys.path.insert(0, os.path.dirname(__file__))
from parts.mg90s import make_mg90s

# ============================================
#  ユニバーサルプレート仕様
# ============================================
PLATE_FULL_W = 160.0   # 元のプレート幅
PLATE_FULL_D = 60.0    # 元のプレート奥行き
PLATE_H = 3.0          # プレート厚み
HOLE_PITCH = 5.0       # 穴ピッチ
HOLE_D = 3.0           # 穴径
HOLE_OFFSET = 2.5      # 端から最初の穴中心までの距離

# ============================================
#  MG90S 寸法（再掲）
# ============================================
SERVO_BODY_W = 22.8
SERVO_BODY_D = 12.2
SERVO_BODY_H = 22.7
SERVO_FLANGE_W = 32.3
SERVO_FLANGE_Z = 15.9
SERVO_FLANGE_H = 2.5
SERVO_SHAFT_OFFSET_X = 5.9
SERVO_SHAFT_H = 4.0
SERVO_EAR_HOLE_DIST = 27.8

# ============================================
#  設計パラメータ
# ============================================
# ベースプレート切り出しサイズ（穴数ベース）
BASE_HOLES_X = 16       # 16穴 = 77.5mm (2.5 + 15*5 + 2.5)
BASE_HOLES_Y = 12       # 12穴 = 57.5mm (フル幅使用)
BASE_W = HOLE_OFFSET + (BASE_HOLES_X - 1) * HOLE_PITCH + HOLE_OFFSET  # 77.5mm
BASE_D = HOLE_OFFSET + (BASE_HOLES_Y - 1) * HOLE_PITCH + HOLE_OFFSET  # 57.5mm

# ターンテーブル切り出しサイズ
TT_HOLES_X = 10          # 10穴 = 47.5mm
TT_HOLES_Y = 8           # 8穴 = 37.5mm
TT_W = HOLE_OFFSET + (TT_HOLES_X - 1) * HOLE_PITCH + HOLE_OFFSET  # 47.5mm
TT_D = HOLE_OFFSET + (TT_HOLES_Y - 1) * HOLE_PITCH + HOLE_OFFSET  # 37.5mm

# 中心回転軸
CENTER_SHAFT_D = 3.0      # M3ボルト
SPACER_OD = 6.0           # ナイロンスペーサー外径
SPACER_H = 10.0           # スペーサー高さ（ベースとターンテーブル間のクリアランス）
WASHER_D = 7.0            # ナイロンワッシャー外径
WASHER_H = 1.0            # ワッシャー厚

# サーボ配置
SERVO_OFFSET_X = 25.0     # ベース中心からサーボ軸までのXオフセット
SERVO_MOUNT_Z = PLATE_H   # サーボはベースプレート上面に横付け

# リンクアーム
LINK_ARM_LEN = 20.0       # サーボホーンからターンテーブルまでの距離
LINK_ROD_D = 3.0          # M3ボルトをプッシュロッドに流用
LINK_ATTACH_OFFSET = 18.0 # ターンテーブル中心からリンク接続点までの距離


def make_universal_plate(holes_x, holes_y, label="plate"):
    """
    ユニバーサルプレートの切り出し片をモデル化
    holes_x, holes_y: 穴の数
    """
    w = HOLE_OFFSET + (holes_x - 1) * HOLE_PITCH + HOLE_OFFSET
    d = HOLE_OFFSET + (holes_y - 1) * HOLE_PITCH + HOLE_OFFSET

    plate = (
        cq.Workplane("XY")
        .box(w, d, PLATE_H, centered=(True, True, False))
    )

    # 穴を開ける
    hole_points = []
    for ix in range(holes_x):
        for iy in range(holes_y):
            x = -w / 2 + HOLE_OFFSET + ix * HOLE_PITCH
            y = -d / 2 + HOLE_OFFSET + iy * HOLE_PITCH
            hole_points.append((x, y))

    plate = (
        plate
        .faces(">Z")
        .workplane()
        .pushPoints(hole_points)
        .hole(HOLE_D)
    )

    return plate


def make_base_plate():
    """
    ベースプレート
    - ユニバーサルプレートから切り出し (16×12穴)
    - 中央に回転軸用の穴（既存の5mm穴をそのまま利用）
    - サーボ取付エリア
    """
    plate = make_universal_plate(BASE_HOLES_X, BASE_HOLES_Y, "base")
    return plate


def make_turntable():
    """
    ターンテーブル（回転テーブル）
    - ユニバーサルプレートから切り出し (10×8穴)
    - 中央穴＝回転軸（M3ボルト）
    - パンチルトブラケットはこの上に載せる
    - リンクアーム接続穴
    """
    plate = make_universal_plate(TT_HOLES_X, TT_HOLES_Y, "turntable")
    return plate


def make_center_shaft():
    """
    中心回転軸
    - M3ボルト + ナイロンスペーサー + ワッシャー
    - ベースプレート中央穴を貫通→スペーサー→ターンテーブルを支持
    """
    # M3ボルト（軸）
    bolt = (
        cq.Workplane("XY")
        .circle(CENTER_SHAFT_D / 2)
        .extrude(PLATE_H + SPACER_H + PLATE_H + WASHER_H * 2 + 5)
    )

    # ナイロンスペーサー（ベースプレート上面〜ターンテーブル下面）
    spacer = (
        cq.Workplane("XY")
        .workplane(offset=PLATE_H + WASHER_H)
        .circle(SPACER_OD / 2)
        .extrude(SPACER_H)
    )

    # 下ワッシャー（ベース上面）
    washer_bottom = (
        cq.Workplane("XY")
        .workplane(offset=PLATE_H)
        .circle(WASHER_D / 2)
        .extrude(WASHER_H)
    )

    # 上ワッシャー（ターンテーブル上面）
    tt_z = PLATE_H + WASHER_H + SPACER_H
    washer_top = (
        cq.Workplane("XY")
        .workplane(offset=tt_z + PLATE_H)
        .circle(WASHER_D / 2)
        .extrude(WASHER_H)
    )

    result = bolt.union(spacer).union(washer_bottom).union(washer_top)
    return result


def make_link_arm():
    """
    リンクアーム
    - サーボホーンの穴 → ターンテーブル端の穴を結ぶプッシュロッド
    - M3ボルト + スペーサーで構成
    - 両端にピボット（回転自由）
    """
    # プッシュロッド本体（単純な棒で表現）
    rod = (
        cq.Workplane("XY")
        .circle(LINK_ROD_D / 2)
        .extrude(LINK_ARM_LEN)
    )

    # 両端のピボットジョイント（スペーサー表現）
    for z in [0, LINK_ARM_LEN]:
        joint = (
            cq.Workplane("XY")
            .workplane(offset=z - 1.5)
            .circle(3.0)
            .extrude(3.0)
        )
        rod = rod.union(joint)

    return rod


def make_servo_horn():
    """サーボホーン（シングルアーム、簡易モデル）"""
    horn = (
        cq.Workplane("XY")
        .rect(5, 20)
        .extrude(2)
    )
    # 軸穴
    horn = horn.cut(
        cq.Workplane("XY")
        .circle(2.4)
        .extrude(2)
    )
    # 先端穴（リンク接続）
    horn = horn.cut(
        cq.Workplane("XY")
        .transformed(offset=(0, 8, 0))
        .circle(1.5)
        .extrude(2)
    )
    return horn


def make_assembly():
    """
    全体アセンブリ
    """
    assy = cq.Assembly()

    # --- 1. ベースプレート ---
    base = make_base_plate()
    assy.add(base, name="base_plate", color=cq.Color(0.85, 0.82, 0.75, 1.0))  # タミヤプレート色

    # --- 2. 中心回転軸 ---
    shaft = make_center_shaft()
    assy.add(shaft, name="center_shaft",
             loc=cq.Location((0, 0, 0)),
             color=cq.Color(0.7, 0.7, 0.7, 1.0))  # シルバー

    # --- 3. ターンテーブル ---
    tt_z = PLATE_H + WASHER_H + SPACER_H  # ベース上面 + ワッシャー + スペーサー
    turntable = make_turntable()
    assy.add(turntable, name="turntable",
             loc=cq.Location((0, 0, tt_z)),
             color=cq.Color(0.85, 0.82, 0.75, 0.8))  # 半透明プレート色

    # --- 4. Yawサーボ（ベースに横付け） ---
    # サーボは横倒し（Z軸回りに配置）、軸がZ+を向く
    # ベースプレート上面にフランジで固定
    servo = make_mg90s()
    # サーボを配置: 軸がZ+を向いたまま、ベース上に横付け
    # サーボのシャフトがZ+方向、ベースプレート上に設置
    servo_x = SERVO_OFFSET_X
    servo_y = 0
    servo_z = PLATE_H  # ベース上面
    assy.add(servo, name="yaw_servo",
             loc=cq.Location((servo_x, servo_y, servo_z)),
             color=cq.Color(0.2, 0.3, 0.8, 1.0))  # 青

    # --- 5. リンクアーム ---
    # サーボホーン先端(servo_x + horn_reach, 0) → ターンテーブル端(link_attach_x, 0)
    horn_reach = 8.0  # サーボホーン先端までの距離
    servo_shaft_x = servo_x + SERVO_SHAFT_OFFSET_X
    link_start_x = servo_shaft_x + horn_reach
    link_start_z = servo_z + SERVO_BODY_H + SERVO_SHAFT_H + 2  # シャフト上

    link_end_x = LINK_ATTACH_OFFSET  # ターンテーブル端寄りの穴
    link_end_z = tt_z + PLATE_H / 2

    # リンクの角度と長さを計算
    dx = link_end_x - link_start_x
    dz = link_end_z - link_start_z
    link_len = math.sqrt(dx * dx + dz * dz)
    link_angle = math.degrees(math.atan2(dz, dx))

    link = make_link_arm()
    assy.add(link, name="link_arm",
             loc=cq.Location(
                 (link_start_x, 0, link_start_z),
                 (0, -link_angle, 0)
             ),
             color=cq.Color(0.9, 0.4, 0.1, 1.0))  # オレンジ

    # --- 6. サーボホーン ---
    horn = make_servo_horn()
    horn_z = servo_z + SERVO_BODY_H + SERVO_SHAFT_H
    assy.add(horn, name="servo_horn",
             loc=cq.Location((servo_shaft_x, 0, horn_z)),
             color=cq.Color(1, 1, 1, 1.0))  # 白

    # --- 7. パンチルトブラケット位置の参考マーカー ---
    # ターンテーブル上にパンチルトが載る位置を示す
    pt_marker = (
        cq.Workplane("XY")
        .box(38.9, 18.8, 2, centered=(True, True, False))
    )
    pt_z = tt_z + PLATE_H
    assy.add(pt_marker, name="pantilt_footprint",
             loc=cq.Location((0, 0, pt_z)),
             color=cq.Color(0.3, 0.8, 0.3, 0.4))  # 半透明グリーン

    # --- 8. CoreS3 位置の参考マーカー ---
    cores3_marker = (
        cq.Workplane("XY")
        .box(54, 54, 3, centered=(True, True, False))
    )
    cores3_z = pt_z + 30  # パンチルト高さ概算
    assy.add(cores3_marker, name="cores3_footprint",
             loc=cq.Location((0, 0, cores3_z)),
             color=cq.Color(0.2, 0.2, 0.2, 0.3))  # 半透明ダーク

    return assy


def export_individual_parts():
    """個別パーツをSTEP/STLエクスポート"""
    out_dir = os.path.join(os.path.dirname(__file__), "yaw_link_parts")
    os.makedirs(out_dir, exist_ok=True)

    print("=== ヨー軸リンク機構 パーツエクスポート ===\n")

    # ベースプレート
    base = make_base_plate()
    cq.exporters.export(base, os.path.join(out_dir, "base_plate.step"))
    print(f"  base_plate.step  ({BASE_W:.1f} × {BASE_D:.1f} × {PLATE_H:.1f} mm)")
    print(f"    穴: {BASE_HOLES_X} × {BASE_HOLES_Y} = {BASE_HOLES_X * BASE_HOLES_Y} 穴")

    # ターンテーブル
    tt = make_turntable()
    cq.exporters.export(tt, os.path.join(out_dir, "turntable.step"))
    print(f"  turntable.step   ({TT_W:.1f} × {TT_D:.1f} × {PLATE_H:.1f} mm)")
    print(f"    穴: {TT_HOLES_X} × {TT_HOLES_Y} = {TT_HOLES_X * TT_HOLES_Y} 穴")

    print(f"\n  中心軸: M3ボルト + Φ{SPACER_OD}スペーサー (h={SPACER_H}mm)")
    print(f"  ベース〜ターンテーブル間隔: {WASHER_H + SPACER_H + WASHER_H:.1f}mm")
    print(f"  サーボ位置: ベース中心から X={SERVO_OFFSET_X}mm")
    print(f"  リンク接続: ターンテーブル中心から {LINK_ATTACH_OFFSET}mm")

    return out_dir


# ============================================
#  メイン
# ============================================
if __name__ == "__main__":
    # 個別パーツ
    out_dir = export_individual_parts()

    # アセンブリ
    print("\nAssembling...")
    assy = make_assembly()

    assy_path = os.path.join(os.path.dirname(__file__), "yaw_link_assembly.step")
    assy.save(assy_path)
    print(f"\n  Assembly: yaw_link_assembly.step")

    print("\n=== 完了 ===")
    print(f"""
重量の流れ:
  CoreS3 (~120g) → パンチルトブラケット → ターンテーブル
    → 中心軸 (M3ボルト+スペーサー) → ベースプレート
  サーボ軸には回転トルクのみ！

組み立て手順:
  1. ベースプレートを切り出す ({BASE_HOLES_X}×{BASE_HOLES_Y}穴 = {BASE_W:.1f}×{BASE_D:.1f}mm)
  2. ターンテーブルを切り出す ({TT_HOLES_X}×{TT_HOLES_Y}穴 = {TT_W:.1f}×{TT_D:.1f}mm)
  3. ベース中央穴にM3ボルト+スペーサーを立てる
  4. ターンテーブルをスペーサー上に載せ、ワッシャー+ナットで軽く締める
  5. MG90Sをベースに横付け固定（フランジ穴→プレート穴にM2ネジ）
  6. サーボホーン先端 → ターンテーブル端の穴にM3プッシュロッドを接続
  7. パンチルトブラケットをターンテーブル上にネジ止め
""")
