"""
CoreS3 コンパニオンロボット 全体アセンブリ
実物パーツモデルを使った筐体設計

構成:
  ベース — FS90R×2 + ボールキャスター + 電源
  胴体   — PCA9685 + 腕サーボ(MG90S)×2 + ヨーサーボ(MG90S)×1
  首     — ギア駆動ターンテーブル + ピッチサーボ + ロールサーボ
  ヘッド — CoreS3 マウント
"""
import cadquery as cq
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "parts"))
from mg90s import make_mg90s
from fs90r import make_fs90r
from cores3 import make_cores3

# ============================================
#  設計パラメータ
# ============================================
WALL = 2.5        # 壁厚
TOL = 0.3         # はめあい公差

# ---- パーツインスタンス生成 ----
print("Generating parts...")
mg90s = make_mg90s()
fs90r = make_fs90r()
cores3 = make_cores3()

# PCA9685はSTEPファイルから読み込み
parts_dir = os.path.join(os.path.dirname(__file__), "parts")
pca9685_path = os.path.join(parts_dir, "pca9685.step")
if os.path.exists(pca9685_path):
    print("Loading PCA9685 STEP...")
    pca9685 = cq.importers.importStep(pca9685_path)
else:
    # フォールバック: 簡易ボックス
    print("PCA9685 STEP not found, using placeholder")
    pca9685 = cq.Workplane("XY").box(62, 25.4, 6, centered=(True, True, False))

# ============================================
#  ベースプレート
# ============================================
print("Building base...")
BASE_W = 120
BASE_D = 90
BASE_H = 35  # FS90Rフランジ回転後(32mm) + 余裕

# FS90Rの取付位置（左右）
FS90R_Y = 0       # ベース中央
FS90R_Z = 5       # 底面から少し上

def make_base():
    """ベースプレート: FS90R×2のマウント + ボールキャスター穴"""
    base = (
        cq.Workplane("XY")
        .box(BASE_W, BASE_D, BASE_H, centered=(True, True, False))
        .edges("|Z").fillet(8)
    )

    # 内部空洞（軽量化+配線スペース）
    base = base.cut(
        cq.Workplane("XY")
        .workplane(offset=WALL)
        .box(BASE_W - WALL*2, BASE_D - WALL*2, BASE_H, centered=(True, True, False))
        .edges("|Z").fillet(6)
    )

    # FS90Rマウント穴（左）
    base = base.cut(
        cq.Workplane("YZ")
        .workplane(offset=-BASE_W/2)
        .transformed(offset=(0, FS90R_Z + 11.5, 0))  # サーボ中心高
        .rect(12.5 + TOL*2, 23 + TOL*2)
        .extrude(WALL + 1)
    )
    # FS90Rフランジスロット（左）
    base = base.cut(
        cq.Workplane("YZ")
        .workplane(offset=-BASE_W/2)
        .transformed(offset=(0, FS90R_Z + 18.5 + 1.25, 0))
        .rect(32.5 + TOL, 2.5 + TOL)
        .extrude(WALL * 2)
    )

    # FS90Rマウント穴（右）
    base = base.cut(
        cq.Workplane("YZ")
        .workplane(offset=BASE_W/2 - WALL - 1)
        .transformed(offset=(0, FS90R_Z + 11.5, 0))
        .rect(12.5 + TOL*2, 23 + TOL*2)
        .extrude(WALL + 1)
    )
    # FS90Rフランジスロット（右）
    base = base.cut(
        cq.Workplane("YZ")
        .workplane(offset=BASE_W/2 - WALL*2)
        .transformed(offset=(0, FS90R_Z + 18.5 + 1.25, 0))
        .rect(32.5 + TOL, 2.5 + TOL)
        .extrude(WALL * 2)
    )

    # ボールキャスター穴（前方中央）
    base = base.cut(
        cq.Workplane("XY")
        .transformed(offset=(0, -BASE_D/2 + 18, 0))
        .circle(8)
        .extrude(WALL + 1)
    )

    # 配線穴（上面中央）
    base = base.cut(
        cq.Workplane("XY")
        .workplane(offset=BASE_H - WALL)
        .rect(20, 12)
        .extrude(WALL + 1)
    )

    # 胴体取付ネジ穴（上面4箇所）
    mount_pts = [(35, 25), (-35, 25), (35, -25), (-35, -25)]
    for pt in mount_pts:
        base = base.cut(
            cq.Workplane("XY")
            .workplane(offset=BASE_H - 1)
            .transformed(offset=(pt[0], pt[1], 0))
            .circle(1.25)
            .extrude(2)
        )

    return base


# ============================================
#  胴体
# ============================================
print("Building body...")
BODY_W = 80
BODY_D = 70
BODY_H = 55
BODY_Z = BASE_H

def make_body():
    """胴体: PCA9685 + 腕サーボ×2 + ヨーサーボ×1"""
    body = (
        cq.Workplane("XY")
        .workplane(offset=BODY_Z)
        .box(BODY_W, BODY_D, BODY_H, centered=(True, True, False))
        .edges("|Z").fillet(8)
    )

    # 内部空洞
    body = body.cut(
        cq.Workplane("XY")
        .workplane(offset=BODY_Z + WALL)
        .box(BODY_W - WALL*2, BODY_D - WALL*2, BODY_H, centered=(True, True, False))
        .edges("|Z").fillet(6)
    )

    # 腕サーボ穴（左 -X面）
    arm_z = BODY_Z + BODY_H * 0.6
    body = body.cut(
        cq.Workplane("YZ")
        .workplane(offset=-BODY_W/2)
        .transformed(offset=(0, arm_z + 11, 0))
        .rect(12.5 + TOL*2, 23 + TOL*2)
        .extrude(WALL + 1)
    )
    # 軸穴（左）
    body = body.cut(
        cq.Workplane("XY")
        .workplane(offset=arm_z + 22.7 - 3)
        .transformed(offset=(-BODY_W/2, 0, 0))
        .circle(4)
        .extrude(-WALL - 2)
    )

    # 腕サーボ穴（右 +X面）
    body = body.cut(
        cq.Workplane("YZ")
        .workplane(offset=BODY_W/2 - WALL - 1)
        .transformed(offset=(0, arm_z + 11, 0))
        .rect(12.5 + TOL*2, 23 + TOL*2)
        .extrude(WALL + 1)
    )
    # 軸穴（右）
    body = body.cut(
        cq.Workplane("XY")
        .workplane(offset=arm_z + 22.7 - 3)
        .transformed(offset=(BODY_W/2, 0, 0))
        .circle(4)
        .extrude(WALL + 2)
    )

    # 首穴（上面中央）— リングギア用
    body = body.cut(
        cq.Workplane("XY")
        .workplane(offset=BODY_Z + BODY_H - WALL)
        .circle(30)
        .extrude(WALL + 1)
    )

    # 背面メンテナンスハッチ
    body = body.cut(
        cq.Workplane("XZ")
        .workplane(offset=BODY_D/2 - 1)
        .transformed(offset=(0, BODY_Z + BODY_H/2, 0))
        .rect(40, 30)
        .extrude(WALL + 2)
    )

    # 配線穴（底面）
    body = body.cut(
        cq.Workplane("XY")
        .workplane(offset=BODY_Z)
        .rect(20, 12)
        .extrude(WALL + 1)
    )

    return body


# ============================================
#  首 — スペース確保用（内部は実物合わせ）
# ============================================
NECK_Z = BODY_Z + BODY_H
NECK_H = 50
RING_GEAR_D = 55

def make_neck_space():
    """首の可動スペース + 取付プレート"""
    # 下部プレート（胴体に固定）
    bottom = (
        cq.Workplane("XY")
        .workplane(offset=NECK_Z)
        .circle(RING_GEAR_D / 2)
        .circle(RING_GEAR_D / 2 - 5)
        .extrude(3)
    )

    # 上部プレート（ヘッドに接続）
    top = (
        cq.Workplane("XY")
        .workplane(offset=NECK_Z + NECK_H - 3)
        .circle(25)
        .circle(8)
        .extrude(3)
    )

    return bottom.union(top)


# ============================================
#  ヘッド（CoreS3マウント）
# ============================================
HEAD_Z = NECK_Z + NECK_H
# CoreS3は画面を前に向けて立てる: W=54(横), H=22(厚み→奥行き), D=54(高さ)
HEAD_W = 54 + WALL * 2 + TOL * 2   # ~60mm
HEAD_D = 22 + WALL * 2 + TOL * 2 + 8  # ~34mm（配線スペース込み）
HEAD_H = 54 + WALL * 2 + TOL * 2   # ~60mm

def make_head():
    """ヘッド: CoreS3を立てて収納"""
    head = (
        cq.Workplane("XY")
        .workplane(offset=HEAD_Z)
        .box(HEAD_W, HEAD_D, HEAD_H, centered=(True, True, False))
        .edges("|Z").fillet(5)
        .edges(">Z").fillet(3)
    )

    # 内部空洞
    head = head.cut(
        cq.Workplane("XY")
        .workplane(offset=HEAD_Z + WALL)
        .box(HEAD_W - WALL*2, HEAD_D - WALL*2, HEAD_H - WALL, centered=(True, True, False))
    )

    # 画面開口（前面）— CoreS3の画面エリア
    head = head.cut(
        cq.Workplane("XZ")
        .workplane(offset=-HEAD_D/2)
        .transformed(offset=(0, HEAD_Z + HEAD_H/2, 0))
        .rect(42, 32)
        .extrude(WALL + 1)
    )

    # カメラ穴（前面上部）
    head = head.cut(
        cq.Workplane("XZ")
        .workplane(offset=-HEAD_D/2)
        .transformed(offset=(20, HEAD_Z + HEAD_H - 10, 0))
        .circle(4)
        .extrude(WALL + 1)
    )

    # マイク穴
    for x_off in [-6, 0, 6]:
        head = head.cut(
            cq.Workplane("XZ")
            .workplane(offset=-HEAD_D/2)
            .transformed(offset=(x_off, HEAD_Z + 8, 0))
            .circle(1)
            .extrude(WALL + 1)
        )

    # 底面取付穴+配線穴
    head = head.cut(
        cq.Workplane("XY")
        .workplane(offset=HEAD_Z)
        .rect(12, 10)
        .extrude(WALL + 1)
    )

    return head


# ============================================
#  アセンブリ
# ============================================
print("Assembling...")

# 筐体パーツ
base = make_base()
body = make_body()
neck_space = make_neck_space()
head = make_head()

# ============================================
#  実物パーツの配置（バウンディングボックス検証済み）
# ============================================
# パーツ座標系:
#   MG90S/FS90R: XY中心、Z=0が底、軸は+Z上面（+Xオフセット）
#   CoreS3: XY中心、Z=0が底、画面は+Z上面
#   PCA9685: 原点が角にある → 中心に補正が必要

# ---- PCA9685を中心原点に補正 ----
pca9685_centered = pca9685.translate((-29.2, -6.2, 2.0))

# ---- FS90R左: 軸が-X方向（左壁を貫通）、ベース内 ----
# rotate 90° around Y: shaft(+Z) → (-X), height(Z 0..23) → X(-23..0)
# フランジ(32mm)がZ方向になるので BASE_H=35 に合わせて中央配置
fs90r_left = (
    fs90r
    .rotate((0, 0, 0), (0, 1, 0), 90)
    .translate((-BASE_W/2 + WALL + 12, 0, BASE_H/2 + 1))
)

# ---- FS90R右: 軸が+X方向（右壁を貫通）----
fs90r_right = (
    fs90r
    .rotate((0, 0, 0), (0, 1, 0), -90)
    .translate((BASE_W/2 - WALL - 12, 0, BASE_H/2 + 1))
)

# ---- PCA9685: 胴体底面中央に水平配置 ----
pca_placed = pca9685_centered.translate((0, 0, BODY_Z + WALL + 1))

# ---- 腕サーボ左: 軸が-X方向（左壁を貫通）----
# rotate 90° Y: Z→-X. ボディの左壁(X=-40)の内側にフランジが来るように配置
arm_z = BODY_Z + BODY_H * 0.65
mg90s_arm_left = (
    mg90s
    .rotate((0, 0, 0), (0, 1, 0), 90)
    .translate((-BODY_W/2 + WALL + 1, 0, arm_z))
)

# ---- 腕サーボ右: 軸が+X方向（右壁を貫通）----
mg90s_arm_right = (
    mg90s
    .rotate((0, 0, 0), (0, 1, 0), -90)
    .translate((BODY_W/2 - WALL - 1, 0, arm_z))
)

# ---- ヨーサーボ: 胴体内上部、軸が上(+Z)を向く ----
# ピニオンギアでリングギアを駆動する想定
mg90s_yaw = mg90s.translate((20, 0, BODY_Z + BODY_H - 24))

# ---- ピッチサーボ: 首空間内、軸がX方向（うなずき）----
# rotate 90° Y後のZ範囲は±16.1mm。NECK_Z+17でギリギリ収まる
mg90s_pitch = (
    mg90s
    .rotate((0, 0, 0), (0, 1, 0), 90)
    .translate((0, 0, NECK_Z + 17))
)

# ---- ロールサーボ: 首空間上部、軸がY方向（首かしげ）----
mg90s_roll = (
    mg90s
    .rotate((0, 0, 0), (1, 0, 0), 90)
    .translate((0, 0, NECK_Z + NECK_H - 12))
)

# ---- CoreS3: ヘッド内、画面を前(-Y)に向けて立てる ----
# rotate -90° X: 画面(+Z)→前(-Y)、元Z[0..22]→Y[0..22]
# Y中心補正: -11でY[-11..11]に（HEAD内Y[-16..16]に収まる）
cores3_placed = (
    cores3
    .rotate((0, 0, 0), (1, 0, 0), -90)
    .translate((0, -11, HEAD_Z + HEAD_H/2))
)

# ============================================
#  軸マーカー + 回転アーク（機構の可視化）
# ============================================
# MG90Sの軸オフセット: ボディ中心から+X方向に5.9mm、高さは上面(22.7mm)
# 回転後の軸位置を計算して赤い棒(軸)と黄色い弧(回転範囲)を配置
print("Adding axis markers...")

def make_shaft_arrow(length=20):
    """赤い軸棒（回転軸方向を示す）"""
    return (
        cq.Workplane("XY")
        .circle(1.5).extrude(length)
        .faces(">Z").workplane().circle(3).extrude(2)  # 矢印の頭
    )

def make_rotation_arc(radius=15, angle=120):
    """黄色い回転範囲アーク"""
    import math
    pts = []
    for i in range(int(angle/5) + 1):
        a = math.radians(-angle/2 + i * 5)
        pts.append((radius * math.cos(a), radius * math.sin(a)))
    # アークを太い線として作成
    arc = cq.Workplane("XY")
    for i in range(len(pts) - 1):
        seg = (
            cq.Workplane("XY")
            .transformed(offset=(pts[i][0], pts[i][1], 0))
            .circle(0.8).extrude(1)
        )
        arc = arc.union(seg)
    return arc

shaft = make_shaft_arrow(25)

# ---- 各サーボの軸マーカー ----

# FS90R左: 軸は-X方向（左壁を貫通→タイヤへ）
# 元の軸位置: (+5.9, 0, 22.7+shaft) → rotate 90°Y → Z方向がX方向に
shaft_fs90r_l = (
    shaft
    .rotate((0, 0, 0), (0, 1, 0), 90)  # 軸を-X方向に
    .translate((-BASE_W/2 + 3, 0, BASE_H/2 + 1))
)

# FS90R右: 軸は+X方向
shaft_fs90r_r = (
    shaft
    .rotate((0, 0, 0), (0, 1, 0), -90)
    .translate((BASE_W/2 - 3, 0, BASE_H/2 + 1))
)

# 腕サーボ左: 軸は-X方向（左壁を貫通→フリッパーへ）
shaft_arm_l = (
    shaft
    .rotate((0, 0, 0), (0, 1, 0), 90)
    .translate((-BODY_W/2 + 1, 0, arm_z + 18))
)

# 腕サーボ右: 軸は+X方向
shaft_arm_r = (
    shaft
    .rotate((0, 0, 0), (0, 1, 0), -90)
    .translate((BODY_W/2 - 1, 0, arm_z + 18))
)

# ヨーサーボ: 軸は+Z方向（上向き→リングギア/ターンテーブル）
shaft_yaw = (
    shaft
    .translate((20 + 5.9, 0, BODY_Z + BODY_H - 24 + 22.7))
)

# ピッチサーボ: 軸はX方向（横向き→うなずき回転）
shaft_pitch = (
    shaft
    .rotate((0, 0, 0), (0, 1, 0), -90)
    .translate((0, 0, NECK_Z + 17 + 6))
)

# ロールサーボ: 軸はY方向（前後→首かしげ回転）
shaft_roll = (
    shaft
    .rotate((0, 0, 0), (1, 0, 0), -90)
    .translate((0, 0, NECK_Z + NECK_H - 12 + 6))
)

# ============================================
#  エクスポート
# ============================================
out_dir = os.path.dirname(__file__)

# 筐体パーツ（印刷用STL）
print("Exporting chassis STLs...")
cq.exporters.export(base, os.path.join(out_dir, "base.stl"))
cq.exporters.export(body, os.path.join(out_dir, "body.stl"))
cq.exporters.export(head, os.path.join(out_dir, "head.stl"))

# 筐体パーツ（STEP — Fusion 360で確認用）
print("Exporting chassis STEPs...")
cq.exporters.export(base, os.path.join(out_dir, "base.step"))
cq.exporters.export(body, os.path.join(out_dir, "body.step"))
cq.exporters.export(head, os.path.join(out_dir, "head.step"))
cq.exporters.export(neck_space, os.path.join(out_dir, "neck.step"))

# 全体アセンブリ（STEP — 実物パーツ配置確認用）
print("Exporting full assembly STEP...")
assy = cq.Assembly()
assy.add(base, name="base", color=cq.Color(0.3, 0.3, 0.3, 0.8))
assy.add(body, name="body", color=cq.Color(0.4, 0.4, 0.5, 0.8))
assy.add(neck_space, name="neck", color=cq.Color(0.7, 0.7, 0.8, 0.5))
assy.add(head, name="head", color=cq.Color(0.2, 0.3, 0.3, 0.8))
assy.add(fs90r_left, name="fs90r_left", color=cq.Color(0, 0.5, 1, 0.6))
assy.add(fs90r_right, name="fs90r_right", color=cq.Color(0, 0.5, 1, 0.6))
assy.add(pca_placed, name="pca9685", color=cq.Color(0, 0.8, 0, 0.6))
assy.add(mg90s_arm_left, name="mg90s_arm_left", color=cq.Color(0, 0.5, 1, 0.6))
assy.add(mg90s_arm_right, name="mg90s_arm_right", color=cq.Color(0, 0.5, 1, 0.6))
assy.add(mg90s_yaw, name="mg90s_yaw", color=cq.Color(0, 0.5, 1, 0.6))
assy.add(mg90s_pitch, name="mg90s_pitch", color=cq.Color(0, 0.5, 1, 0.6))
assy.add(mg90s_roll, name="mg90s_roll", color=cq.Color(1, 0.5, 0, 0.6))
assy.add(cores3_placed, name="cores3", color=cq.Color(0.1, 0.1, 0.1, 0.7))

# 軸マーカー（赤=回転軸、見やすくするため）
assy.add(shaft_fs90r_l, name="axis_wheel_L", color=cq.Color(1, 0, 0, 0.9))
assy.add(shaft_fs90r_r, name="axis_wheel_R", color=cq.Color(1, 0, 0, 0.9))
assy.add(shaft_arm_l, name="axis_arm_L", color=cq.Color(1, 0, 0, 0.9))
assy.add(shaft_arm_r, name="axis_arm_R", color=cq.Color(1, 0, 0, 0.9))
assy.add(shaft_yaw, name="axis_yaw", color=cq.Color(1, 0, 0, 0.9))
assy.add(shaft_pitch, name="axis_pitch", color=cq.Color(1, 0, 0, 0.9))
assy.add(shaft_roll, name="axis_roll", color=cq.Color(1, 0, 0, 0.9))

assy.save(os.path.join(out_dir, "assembly.step"))

print("\n=== Export complete ===")
print(f"Chassis STLs: base.stl, body.stl, head.stl")
print(f"Chassis STEPs: base.step, body.step, head.step, neck.step")
print(f"Full assembly: assembly.step (open in Fusion 360 to verify)")
print(f"\nTotal height: {HEAD_Z + HEAD_H}mm")
print(f"Base: {BASE_W}x{BASE_D}x{BASE_H}mm")
print(f"Body: {BODY_W}x{BODY_D}x{BODY_H}mm")
print(f"Head: {HEAD_W:.0f}x{HEAD_D:.0f}x{HEAD_H:.0f}mm")
