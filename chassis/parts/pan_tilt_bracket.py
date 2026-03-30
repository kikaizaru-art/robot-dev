"""
パンチルトロールブラケット (MG90S × 3)
3Dプリント用設計 (Bambu Lab A1 FDM)

構成:
  1. Pan Base    — ヨーサーボを縦置きで保持、胴体上面に固定
  2. Tilt Bracket — ヨー軸に取り付き、ピッチサーボを水平保持
  3. Roll Bracket — ピッチ軸に取り付き、ロールサーボを保持→頭部接続
"""
import cadquery as cq
import os

# ============================================
#  MG90S 寸法 (mg90s.py と同じ値)
# ============================================
BODY_W = 22.8       # 幅 (X)
BODY_D = 12.2       # 奥行き (Y)
BODY_H = 22.7       # ボディ高さ

FLANGE_W = 32.3     # フランジ幅（耳含む）
FLANGE_D = 12.2     # フランジ奥行き
FLANGE_H = 2.5      # フランジ厚み
FLANGE_Z = 15.9     # 底面からフランジ下面まで

SHAFT_OFFSET_X = 5.9  # ボディ中心から軸までのXオフセット
SHAFT_D = 4.8         # 軸直径
SHAFT_H = 4.0         # 軸高さ（フランジ上面から）

EAR_HOLE_D = 2.0      # フランジネジ穴径
EAR_HOLE_DIST = 27.8  # 左右穴間距離

# ============================================
#  3Dプリントパラメータ
# ============================================
WALL = 3.0        # 壁厚
TOL = 0.3         # クリアランス
FILLET_IN = 1.0   # 内角フィレット
FILLET_OUT = 2.0  # 外角フィレット

# ホーンハブ（サーボホーンとの接続）
HORN_HUB_D = 7.5       # サーボホーンのネジ穴用ハブ径
HORN_SCREW_D = 2.2     # ホーンネジ穴径
HORN_BOSS_D = 8.0      # ホーン嵌合ボス外径（サーボ付属ホーンの穴に合わせる）


def make_pan_base():
    """
    Pan Base（ヨーベース）
    - MG90Sを縦置き(Z+)で保持
    - 段付きキャビティ: 下段=ボディ幅、上段=フランジ幅
    - フランジ耳が段差の棚に載る構造
    - 原点: ブラケット中心底面
    - サーボ底面: Z = base_plate_h (= WALL)
    - サーボ軸先端: Z = base_plate_h + BODY_H + SHAFT_H

    断面図:
        ┌──┐          ┌──┐  ← 上面リップ (ボディ幅)
        │  ├──────────┤  │  ← フランジ耳が棚に載る
        │  │  SERVO   │  │  ← ボディ空間 (狭い)
        │  │  BODY    │  │
        │  │          │  │
        └──┴──────────┴──┘  ← ベースプレート
    """
    # 内寸
    body_cav_w = BODY_W + TOL * 2       # 23.4 (ボディ用キャビティ幅)
    body_cav_d = BODY_D + TOL * 2       # 12.8
    flange_cav_w = FLANGE_W + TOL * 2   # 32.9 (フランジ用キャビティ幅)
    flange_cav_d = FLANGE_D + TOL * 2   # 12.8

    # 外寸: フランジ幅 + 壁
    outer_w = flange_cav_w + WALL * 2   # 38.9
    outer_d = body_cav_d + WALL * 2     # 18.8

    base_plate_h = WALL                 # 3.0

    # 高さ区分（base_plate_h からの相対）
    body_section_h = FLANGE_Z + TOL     # 16.2 (ボディ底面〜フランジ下面)
    flange_section_h = FLANGE_H + TOL   # 2.8  (フランジ厚)
    top_body_h = BODY_H - FLANGE_Z - FLANGE_H  # 4.3 (フランジ上のボディ)
    top_lip_h = top_body_h + 1          # 5.3  (上面リップ)

    wall_h = body_section_h + flange_section_h + top_lip_h
    total_h = base_plate_h + wall_h     # 27.3

    # --- ソリッドブロック ---
    result = (
        cq.Workplane("XY")
        .box(outer_w, outer_d, total_h, centered=(True, True, False))
        .edges("|Z").fillet(FILLET_OUT)
    )

    # --- 1. ボディキャビティ（狭い、底面〜フランジ下面） ---
    result = result.cut(
        cq.Workplane("XY")
        .workplane(offset=base_plate_h)
        .box(body_cav_w, body_cav_d, body_section_h, centered=(True, True, False))
    )

    # --- 2. フランジキャビティ（広い、フランジ位置のみ） ---
    # この段差がフランジ耳の棚になる
    flange_z = base_plate_h + body_section_h
    result = result.cut(
        cq.Workplane("XY")
        .workplane(offset=flange_z)
        .box(flange_cav_w, flange_cav_d, flange_section_h, centered=(True, True, False))
    )

    # --- 3. フランジ上のボディキャビティ（狭い、サーボ上部を保持） ---
    top_body_z = flange_z + flange_section_h
    result = result.cut(
        cq.Workplane("XY")
        .workplane(offset=top_body_z)
        .box(body_cav_w, body_cav_d, top_lip_h + 1, centered=(True, True, False))
    )

    # --- 4. ギアボックス+シャフト逃げ穴（上面） ---
    gear_d = 11.8 + TOL * 2
    result = result.cut(
        cq.Workplane("XY")
        .workplane(offset=top_body_z)
        .transformed(offset=(SHAFT_OFFSET_X, 0, 0))
        .circle(gear_d / 2)
        .extrude(top_lip_h + 1)
    )

    # --- 底面の配線穴 ---
    result = result.cut(
        cq.Workplane("XY")
        .rect(10, 8)
        .extrude(base_plate_h + 1)
    )

    # --- フランジ取付穴（M2、棚を貫通） ---
    for side in [-1, 1]:
        result = result.cut(
            cq.Workplane("XY")
            .workplane(offset=flange_z - 1)
            .transformed(offset=(side * EAR_HOLE_DIST / 2, 0, 0))
            .circle(EAR_HOLE_D / 2 + TOL)
            .extrude(flange_section_h + WALL + 2)
        )

    # --- 底面M3ネジ穴（5mmグリッド、四隅） ---
    m3_hole_d = 3.2
    hole_spacing_x = 15  # 5mmピッチ × 3
    hole_spacing_y = 10  # 5mmピッチ × 2 (奥行きが狭いので)
    for dx in [-1, 1]:
        for dy in [-1, 1]:
            result = result.cut(
                cq.Workplane("XY")
                .transformed(offset=(dx * hole_spacing_x / 2, dy * hole_spacing_y / 2, 0))
                .circle(m3_hole_d / 2)
                .extrude(base_plate_h + 1)
            )

    return result


def make_tilt_bracket():
    """
    Tilt Bracket（ピッチブラケット）
    - ヨーサーボのシャフトに取り付く回転プラットフォーム
    - フォーク状の両側壁がピッチサーボを水平(X+方向)に保持
    - 原点: ヨーサーボのシャフト位置（回転中心）
    """
    # ピッチサーボを水平(X+)に保持するフォーク
    # サーボは90°回転した状態: 幅方向がZ、高さ方向がX

    # フォークの内寸
    fork_inner_w = BODY_D + TOL * 2    # 12.8 (サーボ奥行きがフォーク間)
    fork_inner_h = BODY_W + TOL * 2    # 23.4 (サーボ幅がフォーク高さ)

    # フォーク壁
    fork_wall = WALL
    fork_outer_w = fork_inner_w + fork_wall * 2  # 18.8

    # ベースプレート（ヨーシャフトに取り付く部分）
    plate_w = fork_outer_w + 6         # フォークより少し広い
    plate_d = BODY_W + 10             # サーボ長さ + 余裕
    plate_h = WALL                     # 3mm厚

    # --- ベースプレート ---
    plate = (
        cq.Workplane("XY")
        .box(plate_w, plate_d, plate_h, centered=(True, True, False))
    )
    plate = plate.edges("|Z").fillet(FILLET_OUT)

    # --- ホーンハブ穴（中央、下面） ---
    # サーボホーンのネジ穴
    plate = plate.cut(
        cq.Workplane("XY")
        .circle(HORN_SCREW_D / 2)
        .extrude(plate_h + 1)
    )
    # ホーン固定用ネジ穴（4箇所、ホーンの穴パターン）
    horn_hole_r = 4.0  # ホーン穴の半径
    for angle in [0, 90, 180, 270]:
        import math
        hx = horn_hole_r * math.cos(math.radians(angle))
        hy = horn_hole_r * math.sin(math.radians(angle))
        plate = plate.cut(
            cq.Workplane("XY")
            .transformed(offset=(hx, hy, 0))
            .circle(1.2)  # M2タッピングネジ用下穴
            .extrude(plate_h + 1)
        )

    # --- フォーク壁（左右） ---
    # フォークはプレート上面から立ち上がり、ピッチサーボを保持
    # サーボのフランジ高さでサーボを支える

    # フォーク高さ: フランジ下面まで + フランジ + 壁
    fork_total_h = FLANGE_Z + FLANGE_H + WALL
    # サーボはX+方向に向く: サーボの高さ方向がX、幅方向がZ
    # フォークの側壁はY方向に立つ

    for side in [-1, 1]:
        wall = (
            cq.Workplane("XY")
            .workplane(offset=plate_h)
            .transformed(offset=(0, side * (fork_inner_w / 2 + fork_wall / 2), 0))
            .box(plate_d - 4, fork_wall, fork_total_h, centered=(True, True, False))
        )
        plate = plate.union(wall)

    # --- フランジ受け棚 ---
    # サーボのフランジが載る内側の棚
    shelf_z = plate_h + FLANGE_Z  # フランジ下面の位置
    for side in [-1, 1]:
        shelf = (
            cq.Workplane("XY")
            .workplane(offset=shelf_z)
            .transformed(offset=(0, side * (fork_inner_w / 2 + TOL), 0))
            .box(FLANGE_W + TOL * 2, WALL + TOL, WALL / 2, centered=(True, True, False))
        )
        plate = plate.union(shelf)

    # --- シャフト通し穴 ---
    # ピッチサーボのシャフトがフォーク壁を貫通する穴
    shaft_local_z = plate_h + FLANGE_Z + FLANGE_H  # シャフト高さ
    shaft_local_x = SHAFT_OFFSET_X  # ボディ中心からのオフセット
    for side in [-1, 1]:
        plate = plate.cut(
            cq.Workplane("XZ")
            .workplane(offset=side * (fork_inner_w / 2 + fork_wall))
            .transformed(offset=(shaft_local_x, shaft_local_z, 0))
            .circle(SHAFT_D / 2 + 2)
            .extrude(fork_wall + 1)
        )

    # --- フランジ取付穴 ---
    for dx in [-1, 1]:
        for side in [-1, 1]:
            plate = plate.cut(
                cq.Workplane("XZ")
                .workplane(offset=side * (fork_inner_w / 2 + fork_wall + 0.5))
                .transformed(offset=(dx * EAR_HOLE_DIST / 2, shelf_z + WALL / 4, 0))
                .circle(EAR_HOLE_D / 2 + TOL)
                .extrude(fork_wall + 2)
            )

    return plate


def make_roll_bracket():
    """
    Roll Bracket（ロールブラケット）
    - ピッチサーボのシャフトに取り付くL字ブラケット
    - ロールサーボを前向き(Y-)に保持
    - 頭部接続用プレート付き
    - 原点: ピッチサーボのシャフト位置
    """
    # L字ブラケット: 垂直面 + 水平面

    # 垂直プレート（ピッチ軸に取り付く面）
    vert_w = BODY_W + 8   # サーボ幅 + 余裕
    vert_h = 20            # 高さ
    vert_t = WALL          # 厚み

    # 水平プレート（ロールサーボを保持する面）
    horiz_w = vert_w
    horiz_d = BODY_H + 8  # サーボの高さ方向 + 余裕
    horiz_t = WALL

    # --- 垂直プレート ---
    vert_plate = (
        cq.Workplane("XZ")
        .box(vert_w, vert_h, vert_t, centered=(True, True, False))
    )

    # --- ホーンハブ穴（垂直面中央） ---
    vert_plate = vert_plate.cut(
        cq.Workplane("XZ")
        .transformed(offset=(0, vert_h / 2, 0))
        .circle(HORN_SCREW_D / 2)
        .extrude(vert_t + 1)
    )
    # ホーン固定穴
    import math
    for angle in [0, 90, 180, 270]:
        hx = 4.0 * math.cos(math.radians(angle))
        hz = 4.0 * math.sin(math.radians(angle))
        vert_plate = vert_plate.cut(
            cq.Workplane("XZ")
            .transformed(offset=(hx, vert_h / 2 + hz, 0))
            .circle(1.2)
            .extrude(vert_t + 1)
        )

    # --- 水平プレート ---
    horiz_plate = (
        cq.Workplane("XY")
        .workplane(offset=vert_h)
        .transformed(offset=(0, -(horiz_d / 2 - vert_t / 2), 0))
        .box(horiz_w, horiz_d, horiz_t, centered=(True, True, False))
    )

    result = vert_plate.union(horiz_plate)

    # --- ロールサーボ取付穴 ---
    # ロールサーボはY-方向にシャフトが向く
    # サーボフランジ固定用のスロット
    servo_mount_z = vert_h + horiz_t  # 水平プレート上面
    # フランジ取付穴（M2）
    for dx in [-1, 1]:
        result = result.cut(
            cq.Workplane("XY")
            .workplane(offset=vert_h)
            .transformed(offset=(dx * EAR_HOLE_DIST / 2, -(horiz_d / 2 - vert_t / 2), 0))
            .circle(EAR_HOLE_D / 2 + TOL)
            .extrude(horiz_t + 1)
        )

    # サーボボディ用の穴（水平プレート中央）
    result = result.cut(
        cq.Workplane("XY")
        .workplane(offset=vert_h)
        .transformed(offset=(SHAFT_OFFSET_X, -(horiz_d / 2 - vert_t / 2), 0))
        .rect(BODY_W + TOL * 2, BODY_D + TOL * 2)
        .extrude(horiz_t + 1)
    )

    # --- 補強リブ（L字の内角） ---
    rib_size = 10
    rib = (
        cq.Workplane("YZ")
        .moveTo(0, vert_h)
        .lineTo(0, vert_h - rib_size)
        .lineTo(-rib_size, vert_h)
        .close()
        .extrude(WALL)
        .translate((-WALL / 2, 0, 0))
    )
    result = result.union(rib)

    # 右側リブ
    rib_r = (
        cq.Workplane("YZ")
        .moveTo(0, vert_h)
        .lineTo(0, vert_h - rib_size)
        .lineTo(-rib_size, vert_h)
        .close()
        .extrude(WALL)
        .translate((vert_w / 2 - WALL - WALL / 2, 0, 0))
    )
    result = result.union(rib_r)

    return result


# ============================================
#  メイン: 個別エクスポート
# ============================================
if __name__ == "__main__":
    out_dir = os.path.dirname(__file__)

    print("Generating Pan Base...")
    pan_base = make_pan_base()
    cq.exporters.export(pan_base, os.path.join(out_dir, "pan_base.step"))
    cq.exporters.export(pan_base, os.path.join(out_dir, "pan_base.stl"))

    print("Generating Tilt Bracket...")
    tilt_bracket = make_tilt_bracket()
    cq.exporters.export(tilt_bracket, os.path.join(out_dir, "tilt_bracket.step"))
    cq.exporters.export(tilt_bracket, os.path.join(out_dir, "tilt_bracket.stl"))

    print("Generating Roll Bracket...")
    roll_bracket = make_roll_bracket()
    cq.exporters.export(roll_bracket, os.path.join(out_dir, "roll_bracket.step"))
    cq.exporters.export(roll_bracket, os.path.join(out_dir, "roll_bracket.stl"))

    print("\nAll bracket parts exported!")
    print(f"  pan_base.step/stl")
    print(f"  tilt_bracket.step/stl")
    print(f"  roll_bracket.step/stl")
