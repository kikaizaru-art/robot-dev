"""
CoreS3 コンパニオンロボット アセンブリ v2
軸位置基準設計: 各サーボの出力軸位置を先に定義し、サーボ本体を逆算配置
"""
import cadquery as cq
import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "parts"))
from mg90s import make_mg90s
from fs90r import make_fs90r
from cores3 import make_cores3
from pan_tilt_bracket import make_pan_base, make_tilt_bracket, make_roll_bracket

# ============================================
#  パーツ生成
# ============================================
print("Generating parts...")
mg90s_part = make_mg90s()
fs90r_part = make_fs90r()
cores3_part = make_cores3()

parts_dir = os.path.join(os.path.dirname(__file__), "parts")
pca9685_path = os.path.join(parts_dir, "pca9685.step")
pca9685_raw = cq.importers.importStep(pca9685_path)
# PCA9685の原点を中心に補正
pca9685_part = pca9685_raw.translate((-29.2, -6.2, 2.0))

# ============================================
#  サーボの軸情報（データシートから）
# ============================================
# MG90S: 軸はボディ中心から X=+5.9mm, 高さ Z=22.7mm（フランジ上面+shaft）
MG90S_SHAFT_X = 5.9     # ボディ中心からのXオフセット
MG90S_SHAFT_Z = 22.7    # ボディ底面からの軸高さ（shaft根元）
MG90S_SHAFT_LEN = 4.0   # shaft長さ

# FS90R: 軸はボディ中心から X=+5.5mm, 高さ Z=23mm
FS90R_SHAFT_X = 5.5
FS90R_SHAFT_Z = 23.0
FS90R_SHAFT_LEN = 3.5

# ============================================
#  筐体パラメータ
# ============================================
WALL = 2.5
TOL = 0.3

BASE_W = 80
BASE_D = 90
BASE_H = 35

BODY_W = 80
BODY_D = 70
BODY_H = 55
BODY_Z = BASE_H

NECK_Z = BODY_Z + BODY_H   # = 90
NECK_H = 50
RING_GEAR_D = 55

HEAD_Z = NECK_Z + NECK_H   # = 140
HEAD_W = 60
HEAD_D = 36
HEAD_H = 60

# ============================================
#  サーボ配置ヘルパー
# ============================================
def place_servo_by_shaft(servo_part, shaft_pos, shaft_dir, shaft_x_offset, shaft_z_height):
    """
    サーボの出力軸が指定位置・方向に来るように配置する

    shaft_pos: (x, y, z) 軸の根元位置（ワールド座標）
    shaft_dir: "X+" / "X-" / "Y+" / "Y-" / "Z+" / "Z-" 軸の向き
    shaft_x_offset: サーボ中心から軸までのXオフセット
    shaft_z_height: サーボ底面から軸までのZ高さ
    """
    # まずサーボ原点(中心,底面)から軸位置へのオフセット
    # サーボのローカル座標で軸は (shaft_x_offset, 0, shaft_z_height)

    # 回転を決定
    if shaft_dir == "Z+":
        # デフォルト向き（軸が上）
        rotated = servo_part
        axis_local = (shaft_x_offset, 0, shaft_z_height)
    elif shaft_dir == "Z-":
        rotated = servo_part.rotate((0, 0, 0), (1, 0, 0), 180)
        axis_local = (shaft_x_offset, 0, -shaft_z_height)
    elif shaft_dir == "X-":
        # 軸を-X方向に向ける（左壁貫通、本体は+X側=内側）
        rotated = servo_part.rotate((0, 0, 0), (0, 1, 0), -90)
        # rotate -90° Y: (x,y,z) → (-z, y, x)
        axis_local = (-shaft_z_height, 0, shaft_x_offset)
    elif shaft_dir == "X+":
        # 軸を+X方向に向ける（右壁貫通、本体は-X側=内側）
        rotated = servo_part.rotate((0, 0, 0), (0, 1, 0), 90)
        # rotate 90° Y: (x,y,z) → (z, y, -x)
        axis_local = (shaft_z_height, 0, -shaft_x_offset)
    elif shaft_dir == "Y-":
        # 軸を-Y方向（前方）: +90°X回転でZ→-Y
        rotated = servo_part.rotate((0, 0, 0), (1, 0, 0), 90)
        # rotate +90° X: (x,y,z) → (x, -z, y)
        axis_local = (shaft_x_offset, -shaft_z_height, 0)
    elif shaft_dir == "Y+":
        # 軸を+Y方向（後方）: -90°X回転でZ→+Y
        rotated = servo_part.rotate((0, 0, 0), (1, 0, 0), -90)
        # rotate -90° X: (x,y,z) → (x, z, -y)
        axis_local = (shaft_x_offset, shaft_z_height, 0)
    else:
        raise ValueError(f"Unknown shaft_dir: {shaft_dir}")

    # サーボ本体を移動: shaft_pos - axis_local = body origin
    tx = shaft_pos[0] - axis_local[0]
    ty = shaft_pos[1] - axis_local[1]
    tz = shaft_pos[2] - axis_local[2]

    placed = rotated.translate((tx, ty, tz))
    return placed


def make_shaft_marker(pos, direction, length=25):
    """赤い軸マーカー（矢印付き）"""
    shaft = (
        cq.Workplane("XY")
        .circle(1.2).extrude(length)
        .faces(">Z").workplane()
        .circle(3).extrude(3)
    )

    rotations = {
        "Z+": [],
        "Z-": [(1, 0, 0, 180)],
        "X+": [(0, 1, 0, -90)],
        "X-": [(0, 1, 0, 90)],
        "Y+": [(1, 0, 0, -90)],
        "Y-": [(1, 0, 0, 90)],
    }
    for rot in rotations.get(direction, []):
        shaft = shaft.rotate((0, 0, 0), (rot[0], rot[1], rot[2]), rot[3])

    return shaft.translate(pos)


# ============================================
#  軸位置の定義（機構設計の核心）
# ============================================
print("Defining shaft positions...")

# タイヤの中心高さ（FS90R軸オフセット分を考慮して上寄せ）
wheel_center_z = BASE_H / 2 + 4

# 各軸の位置と方向を定義
shafts = {
    # 走行系: FS90Rの軸がベース壁を貫通してタイヤに接続
    "wheel_L": {
        "pos": (-BASE_W/2, 0, wheel_center_z),  # 左壁の外面
        "dir": "X-",
        "servo": "fs90r",
        "desc": "左タイヤ回転"
    },
    "wheel_R": {
        "pos": (BASE_W/2, 0, wheel_center_z),   # 右壁の外面
        "dir": "X+",
        "servo": "fs90r",
        "desc": "右タイヤ回転"
    },

    # 腕: MG90Sの軸が胴体壁を貫通してフリッパーに接続
    "arm_L": {
        "pos": (-BODY_W/2, 0, BODY_Z + BODY_H * 0.7),  # 胴体左壁
        "dir": "X-",
        "servo": "mg90s",
        "desc": "左腕上下"
    },
    "arm_R": {
        "pos": (BODY_W/2, 0, BODY_Z + BODY_H * 0.7),   # 胴体右壁
        "dir": "X+",
        "servo": "mg90s",
        "desc": "右腕上下"
    },

    # 首ヨー: 胴体上面→ターンテーブルを回す
    "yaw": {
        "pos": (0, 0, NECK_Z),         # 胴体上面中央
        "dir": "Z+",
        "servo": "mg90s",
        "desc": "首左右回転（ギア駆動）"
    },

    # 首ピッチ: 首空間内、頭のうなずき
    "pitch": {
        "pos": (0, 0, NECK_Z + NECK_H * 0.45),  # 首の中間
        "dir": "X+",
        "servo": "mg90s",
        "desc": "うなずき"
    },

    # 首ロール: 首上部、頭のかしげ
    "roll": {
        "pos": (0, 0, NECK_Z + NECK_H * 0.8),   # 首の上部
        "dir": "Y-",
        "servo": "mg90s",
        "desc": "首かしげ"
    },
}

# ============================================
#  サーボを軸位置に基づいて配置
# ============================================
print("Placing servos by shaft position...")

servo_parts = {}
shaft_markers = {}

for name, info in shafts.items():
    if info["servo"] == "fs90r":
        part = fs90r_part
        sx, sz = FS90R_SHAFT_X, FS90R_SHAFT_Z
    else:
        part = mg90s_part
        sx, sz = MG90S_SHAFT_X, MG90S_SHAFT_Z

    # 右側サーボは180° Z回転で軸オフセットをミラーリング（左右対称にする）
    if name.endswith("_R"):
        part = part.rotate((0, 0, 0), (0, 0, 1), 180)
        sx = -sx  # オフセットも反転

    servo_parts[name] = place_servo_by_shaft(part, info["pos"], info["dir"], sx, sz)
    shaft_markers[name] = make_shaft_marker(info["pos"], info["dir"])

    # 位置検証
    bb = servo_parts[name].val().BoundingBox()
    print(f"  {name:10s} ({info['desc']}) axis@{info['pos']} dir={info['dir']}")
    print(f"             body: X[{bb.xmin:.1f}..{bb.xmax:.1f}] Y[{bb.ymin:.1f}..{bb.ymax:.1f}] Z[{bb.zmin:.1f}..{bb.zmax:.1f}]")

# ============================================
#  筐体パーツ生成
# ============================================
print("\nBuilding chassis...")

def make_base():
    base = (
        cq.Workplane("XY")
        .box(BASE_W, BASE_D, BASE_H, centered=(True, True, False))
        .edges("|Z").fillet(8)
    )
    base = base.cut(
        cq.Workplane("XY").workplane(offset=WALL)
        .box(BASE_W - WALL*2, BASE_D - WALL*2, BASE_H, centered=(True, True, False))
        .edges("|Z").fillet(6)
    )
    # FS90Rスロット（左右）
    for side in [-1, 1]:
        base = base.cut(
            cq.Workplane("YZ")
            .workplane(offset=side * (BASE_W/2 - WALL))
            .transformed(offset=(0, wheel_center_z, 0))
            .rect(13 + TOL*2, 24 + TOL*2)
            .extrude(WALL + 1)
        )
    # ボールキャスター穴（後部）
    base = base.cut(
        cq.Workplane("XY")
        .transformed(offset=(0, BASE_D/2 - 15, 0))
        .circle(10).extrude(WALL + 1)
    )
    # 上面配線穴
    base = base.cut(
        cq.Workplane("XY").workplane(offset=BASE_H - WALL)
        .rect(20, 12).extrude(WALL + 1)
    )
    return base


def make_body():
    body = (
        cq.Workplane("XY").workplane(offset=BODY_Z)
        .box(BODY_W, BODY_D, BODY_H, centered=(True, True, False))
        .edges("|Z").fillet(8)
    )
    body = body.cut(
        cq.Workplane("XY").workplane(offset=BODY_Z + WALL)
        .box(BODY_W - WALL*2, BODY_D - WALL*2, BODY_H, centered=(True, True, False))
        .edges("|Z").fillet(6)
    )
    # 腕サーボスロット（左右）
    arm_shaft_z = shafts["arm_L"]["pos"][2]
    for side in [-1, 1]:
        body = body.cut(
            cq.Workplane("YZ")
            .workplane(offset=side * (BODY_W/2 - WALL))
            .transformed(offset=(0, arm_shaft_z, 0))
            .rect(13 + TOL*2, 24 + TOL*2)
            .extrude(WALL + 1)
        )
        # 軸穴
        body = body.cut(
            cq.Workplane("YZ")
            .workplane(offset=side * (BODY_W/2 - WALL - 1))
            .transformed(offset=(0, arm_shaft_z, 0))
            .circle(4).extrude(WALL + 2)
        )
    # 首穴（上面）
    body = body.cut(
        cq.Workplane("XY").workplane(offset=BODY_Z + BODY_H - WALL)
        .circle(RING_GEAR_D/2 + 3).extrude(WALL + 1)
    )
    # 背面ハッチ
    body = body.cut(
        cq.Workplane("XZ").workplane(offset=BODY_D/2 - 1)
        .transformed(offset=(0, BODY_Z + BODY_H/2, 0))
        .rect(40, 30).extrude(WALL + 2)
    )
    # 底面配線穴
    body = body.cut(
        cq.Workplane("XY").workplane(offset=BODY_Z)
        .rect(20, 12).extrude(WALL + 1)
    )
    return body


def make_neck():
    bottom = (
        cq.Workplane("XY").workplane(offset=NECK_Z)
        .circle(RING_GEAR_D/2).circle(RING_GEAR_D/2 - 5).extrude(3)
    )
    top = (
        cq.Workplane("XY").workplane(offset=NECK_Z + NECK_H - 3)
        .circle(25).circle(8).extrude(3)
    )
    return bottom.union(top)


def make_head():
    head = (
        cq.Workplane("XY").workplane(offset=HEAD_Z)
        .box(HEAD_W, HEAD_D, HEAD_H, centered=(True, True, False))
        .edges("|Z").fillet(5)
        .edges(">Z").fillet(3)
    )
    head = head.cut(
        cq.Workplane("XY").workplane(offset=HEAD_Z + WALL)
        .box(HEAD_W - WALL*2, HEAD_D - WALL*2, HEAD_H - WALL, centered=(True, True, False))
    )
    # 画面開口
    head = head.cut(
        cq.Workplane("XZ").workplane(offset=-HEAD_D/2)
        .transformed(offset=(0, HEAD_Z + HEAD_H/2, 0))
        .rect(42, 42).extrude(WALL + 1)
    )
    # カメラ穴
    head = head.cut(
        cq.Workplane("XZ").workplane(offset=-HEAD_D/2)
        .transformed(offset=(20, HEAD_Z + HEAD_H - 8, 0))
        .circle(4).extrude(WALL + 1)
    )
    # 底面穴
    head = head.cut(
        cq.Workplane("XY").workplane(offset=HEAD_Z)
        .rect(14, 12).extrude(WALL + 1)
    )
    return head


def make_wheel():
    """タイヤ（直径45mm、幅12mm）"""
    wheel_r = 22.5
    wheel_w = 12

    # タイヤ本体（X軸中心のトーラス的形状）
    # YZ平面の丸角長方形プロファイルをX方向に押し出し
    tire = (
        cq.Workplane("YZ")
        .circle(wheel_r)
        .extrude(wheel_w)
        .translate((-wheel_w / 2, 0, 0))
    )
    tire = tire.edges().fillet(2)

    # ハブ
    hub = (
        cq.Workplane("YZ")
        .circle(4)
        .extrude(wheel_w + 4)
        .translate((-(wheel_w + 4) / 2, 0, 0))
    )
    return tire.union(hub)


def make_flipper_arm():
    """LOVOT風フリッパーアーム（ピボット原点、-Z方向に垂れ下がる）"""
    length = 35     # ピボットから先端まで
    width = 16      # Y方向の幅
    thick = 4       # X方向の厚み

    # パドル本体（Z=0がピボット、-Z方向に伸びる）
    # 上部にボス幅を含むプロファイルをスケッチ
    arm = (
        cq.Workplane("XZ")
        .moveTo(-thick / 2, 0)
        .lineTo(-thick / 2, -length + 5)
        .threePointArc((0, -length), (thick / 2, -length + 5))
        .lineTo(thick / 2, 0)
        .close()
        .extrude(width / 2, both=True)
    )
    return arm


def make_caster():
    """ボールキャスター（原点=ボール中心、上方にステムが伸びる）"""
    ball_r = 7
    stem_r = ball_r + 2
    stem_h = 15

    # ボール（原点中心）
    ball = cq.Workplane("XY").sphere(ball_r)
    # ステム（ボール上部からベース内部へ伸びる）
    stem = (
        cq.Workplane("XY")
        .workplane(offset=ball_r * 0.3)
        .circle(stem_r)
        .extrude(stem_h)
    )
    return ball.union(stem)


base = make_base()
body = make_body()
neck = make_neck()
head = make_head()

# ============================================
#  車輪・腕・キャスター配置
# ============================================
print("Placing wheels and arms...")

wheel_part = make_wheel()
arm_part = make_flipper_arm()
caster_part = make_caster()

# 車輪配置（壁からしっかり離す）
wheel_offset = 12  # 壁外面からホイール中心まで
wheel_L = wheel_part.translate((shafts["wheel_L"]["pos"][0] - wheel_offset,
                                 shafts["wheel_L"]["pos"][1],
                                 shafts["wheel_L"]["pos"][2]))
wheel_R = wheel_part.translate((shafts["wheel_R"]["pos"][0] + wheel_offset,
                                 shafts["wheel_R"]["pos"][1],
                                 shafts["wheel_R"]["pos"][2]))

# 腕配置（サーボ軸先端に直付け）
arm_offset = MG90S_SHAFT_LEN  # = 4mm（軸長さ分だけ外に出す）
arm_L = arm_part.translate((shafts["arm_L"]["pos"][0] - arm_offset,
                             shafts["arm_L"]["pos"][1],
                             shafts["arm_L"]["pos"][2]))
arm_R = arm_part.translate((shafts["arm_R"]["pos"][0] + arm_offset,
                             shafts["arm_R"]["pos"][1],
                             shafts["arm_R"]["pos"][2]))

# キャスター配置（ボール底面が車輪底面と同じ高さになるよう調整）
wheel_r = 22.5
ground_z = shafts["wheel_L"]["pos"][2] - wheel_r  # 車輪の最下点 = 接地面
caster_ball_r = 7
caster_placed = caster_part.translate((0, BASE_D / 2 - 15, ground_z + caster_ball_r))

# CoreS3配置
# +90°X回転で画面(+Z面)が-Y(前面)向きになる
# (x,y,z)→(x,-z,y): 元のX[-27..27]→Z、元のZ[0..22]→Y[-22..0]
# 前面(Y=-22)を頭の前面(Y=-18)に合わせてtranslate_y=+4
cores3_placed = (
    cores3_part
    .rotate((0, 0, 0), (1, 0, 0), 90)
    .translate((0, 4, HEAD_Z + HEAD_H/2))
)

# PCA9685配置
pca_placed = pca9685_part.translate((0, 0, BODY_Z + WALL + 1))

# ============================================
#  パンチルトロールブラケット配置
# ============================================
print("Placing pan-tilt-roll brackets...")

pan_base_part = make_pan_base()
tilt_bracket_part = make_tilt_bracket()
roll_bracket_part = make_roll_bracket()

# Pan Base: ヨーサーボの位置に合わせて配置
# ヨー軸位置 = (0, 0, NECK_Z=90)
# Pan Baseの内部でサーボのフランジ高さ = base_plate_h(3) + FLANGE_Z(15.9) = 18.9
# サーボ底面 = NECK_Z - BODY_H(22.7) = 67.3 → ブラケット底面はそこからplate分下
pan_base_bottom_z = shafts["yaw"]["pos"][2] - MG90S_SHAFT_Z  # サーボ底面
pan_base_placed = pan_base_part.translate((0, 0, pan_base_bottom_z - 3))  # -3 = base_plate_h

# Tilt Bracket: ヨーシャフト位置(0, 0, 90)に配置
# ヨーシャフトの先端から取り付く
tilt_bracket_placed = tilt_bracket_part.translate(shafts["yaw"]["pos"])

# Roll Bracket: ピッチシャフト位置に配置
# ピッチサーボのシャフトはX+方向に突出
# ロールブラケットはピッチ軸に取り付く
pitch_pos = shafts["pitch"]["pos"]
roll_bracket_placed = (
    roll_bracket_part
    .rotate((0, 0, 0), (0, 1, 0), -90)  # X+方向に向ける
    .translate(pitch_pos)
)

# ============================================
#  アセンブリエクスポート
# ============================================
print("Exporting...")
out_dir = os.path.dirname(__file__)

assy = cq.Assembly()

# 筐体（グレー系）
assy.add(base, name="base", color=cq.Color(0.35, 0.35, 0.35, 0.7))
assy.add(body, name="body", color=cq.Color(0.4, 0.42, 0.48, 0.7))
assy.add(neck, name="neck", color=cq.Color(0.6, 0.6, 0.7, 0.4))
assy.add(head, name="head", color=cq.Color(0.25, 0.3, 0.32, 0.7))

# サーボ（青系）
for name, part in servo_parts.items():
    color = cq.Color(0, 0.5, 1, 0.7) if "roll" not in name else cq.Color(1, 0.5, 0, 0.7)
    assy.add(part, name=f"servo_{name}", color=color)

# 軸マーカー（赤）
for name, marker in shaft_markers.items():
    assy.add(marker, name=f"axis_{name}", color=cq.Color(1, 0, 0, 0.95))

# 車輪（ダークグレー）
assy.add(wheel_L, name="wheel_L", color=cq.Color(0.2, 0.2, 0.2, 0.9))
assy.add(wheel_R, name="wheel_R", color=cq.Color(0.2, 0.2, 0.2, 0.9))

# 腕（ライトグレー）
assy.add(arm_L, name="arm_L", color=cq.Color(0.6, 0.6, 0.65, 0.9))
assy.add(arm_R, name="arm_R", color=cq.Color(0.6, 0.6, 0.65, 0.9))

# キャスター（シルバー）
assy.add(caster_placed, name="caster", color=cq.Color(0.7, 0.7, 0.7, 0.8))

# 基板（緑）
assy.add(pca_placed, name="pca9685", color=cq.Color(0, 0.7, 0, 0.7))

# CoreS3（黒）
assy.add(cores3_placed, name="cores3", color=cq.Color(0.1, 0.1, 0.1, 0.8))

# パンチルトロールブラケット（ライトグリーン — 3Dプリント部品として区別）
assy.add(pan_base_placed, name="pan_base", color=cq.Color(0.5, 0.9, 0.5, 0.8))
assy.add(tilt_bracket_placed, name="tilt_bracket", color=cq.Color(0.4, 0.85, 0.4, 0.8))
assy.add(roll_bracket_placed, name="roll_bracket", color=cq.Color(0.3, 0.8, 0.3, 0.8))

assy.save(os.path.join(out_dir, "assembly_v2.step"))

# 印刷用STL
for name, part in [("base", base), ("body", body), ("head", head),
                    ("pan_base", pan_base_part), ("tilt_bracket", tilt_bracket_part),
                    ("roll_bracket", roll_bracket_part)]:
    cq.exporters.export(part, os.path.join(out_dir, f"{name}.stl"))
    cq.exporters.export(part, os.path.join(out_dir, f"{name}.step"))

print(f"\n=== Done ===")
print(f"Assembly: assembly_v2.step")
print(f"Total height: {HEAD_Z + HEAD_H}mm")
print(f"\nServo shaft positions:")
for name, info in shafts.items():
    print(f"  {name:10s}: {info['pos']} → {info['dir']}  ({info['desc']})")
