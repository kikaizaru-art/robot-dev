"""
パンチルトロールブラケット 単体確認用
サーボをブラケットに嵌めた状態で個別にエクスポート

出力:
  bracket_check_pan.step    — Pan Base + ヨーサーボ
  bracket_check_tilt.step   — Tilt Bracket + ピッチサーボ
  bracket_check_roll.step   — Roll Bracket + ロールサーボ
  bracket_check_all.step    — 3軸組み上げた全体
"""
import cadquery as cq
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "parts"))
from mg90s import make_mg90s
from pan_tilt_bracket import make_pan_base, make_tilt_bracket, make_roll_bracket

out_dir = os.path.dirname(__file__)

# MG90S寸法定数
SHAFT_OFFSET_X = 5.9
SHAFT_Z = 22.7       # ボディ底面からシャフト根元まで
SHAFT_H = 4.0
FLANGE_Z = 15.9
FLANGE_H = 2.5
BODY_H = 22.7

WALL = 3.0  # ブラケット底板厚

servo = make_mg90s()

# ============================================
#  1. Pan Base + ヨーサーボ
# ============================================
print("1. Pan Base + yaw servo...")
pan_base = make_pan_base()

# サーボをPan Base内に配置
# サーボ底面 = base_plate_h = WALL = 3.0
servo_bottom_z = WALL
yaw_servo = servo.translate((0, 0, servo_bottom_z))

pan_assy = cq.Assembly()
pan_assy.add(pan_base, name="pan_base", color=cq.Color(0.5, 0.9, 0.5, 0.6))
pan_assy.add(yaw_servo, name="yaw_servo", color=cq.Color(0, 0.5, 1, 0.85))
pan_assy.save(os.path.join(out_dir, "bracket_check_pan.step"))

yaw_shaft_tip_z = servo_bottom_z + SHAFT_Z + SHAFT_H
bb = pan_base.val().BoundingBox()
print(f"   Servo bottom: Z={servo_bottom_z}")
print(f"   Flange rests at: Z={servo_bottom_z + FLANGE_Z}")
print(f"   Servo shaft tip: Z={yaw_shaft_tip_z}")
print(f"   Pan Base bbox: X[{bb.xmin:.1f}..{bb.xmax:.1f}] Y[{bb.ymin:.1f}..{bb.ymax:.1f}] Z[{bb.zmin:.0f}..{bb.zmax:.1f}]")

# ============================================
#  2. Tilt Bracket + ピッチサーボ
# ============================================
print("\n2. Tilt Bracket + pitch servo...")
tilt_bracket = make_tilt_bracket()

# ピッチサーボをTilt Bracket内に配置
# Tilt Bracketはフォーク構造、サーボはX方向に水平
# フォーク内: サーボのD方向(12.2)がY、W方向(22.8)がX、H方向(22.7)がZ
# フランジ受け棚の高さ = plate_h(3) + FLANGE_Z(15.9) = 18.9
# サーボ底面 = plate_h(3)
pitch_servo = servo.translate((0, 0, WALL))

tilt_assy = cq.Assembly()
tilt_assy.add(tilt_bracket, name="tilt_bracket", color=cq.Color(0.4, 0.85, 0.4, 0.6))
tilt_assy.add(pitch_servo, name="pitch_servo", color=cq.Color(0, 0.5, 1, 0.85))
tilt_assy.save(os.path.join(out_dir, "bracket_check_tilt.step"))

# ============================================
#  3. Roll Bracket + ロールサーボ
# ============================================
print("\n3. Roll Bracket + roll servo...")
roll_bracket = make_roll_bracket()

# ロールサーボをRoll Bracket上に配置
# Roll BracketのL字: 垂直面(XZ) + 水平面(XY, Z=20)
# サーボは水平面の上に載る（フランジで固定）
# 水平面上面 = vert_h(20) + horiz_t(3) = 23
# サーボはフランジ下面が水平面に載る → サーボ底面は水平面上面 - FLANGE_Z
# ただしサーボは逆さに吊り下げ（シャフトが下に突き出る）ので
# ここでは水平面の上にフランジを置く形で配置
roll_servo = servo.translate((SHAFT_OFFSET_X, 0, 20 + WALL))

roll_assy = cq.Assembly()
roll_assy.add(roll_bracket, name="roll_bracket", color=cq.Color(0.3, 0.8, 0.3, 0.6))
roll_assy.add(roll_servo, name="roll_servo", color=cq.Color(0, 0.5, 1, 0.85))
roll_assy.save(os.path.join(out_dir, "bracket_check_roll.step"))

# ============================================
#  4. 3軸組み上げ全体
# ============================================
print("\n4. Full pan-tilt-roll assembly...")

# 原点 = ヨー軸の位置（Pan Base底面が Z=0）
# ヨーサーボ: Z=WALL(3) から上にBODY_H(22.7)
# ヨー軸先端: Z = WALL + SHAFT_Z + SHAFT_H = 3 + 22.7 + 4 = 29.7
yaw_top = WALL + SHAFT_Z + SHAFT_H  # = 29.7

# Tilt Bracket: ヨー軸先端に載る
tilt_z = yaw_top
tilt_placed = tilt_bracket.translate((0, 0, tilt_z))
pitch_servo_in_tilt = servo.translate((0, 0, tilt_z + WALL))

# ピッチ軸先端の位置
pitch_shaft_z = tilt_z + WALL + SHAFT_Z + SHAFT_H  # tilt内でのサーボ軸先端
print(f"   Yaw shaft tip: Z={yaw_top}")
print(f"   Tilt bracket bottom: Z={tilt_z}")
print(f"   Pitch servo bottom: Z={tilt_z + WALL}")
print(f"   Pitch shaft tip: Z={pitch_shaft_z}")

# Roll Bracket: ピッチ軸に取り付く（簡易配置 — 実際はX+方向に回転）
roll_z = pitch_shaft_z
roll_placed = roll_bracket.translate((0, 0, roll_z))
roll_servo_in_bracket = servo.translate((SHAFT_OFFSET_X, 0, roll_z + 20 + WALL))

full_assy = cq.Assembly()
# Pan Base
full_assy.add(pan_base, name="pan_base", color=cq.Color(0.5, 0.9, 0.5, 0.55))
full_assy.add(yaw_servo, name="yaw_servo", color=cq.Color(0, 0.45, 0.9, 0.85))
# Tilt
full_assy.add(tilt_placed, name="tilt_bracket", color=cq.Color(0.4, 0.85, 0.4, 0.55))
full_assy.add(pitch_servo_in_tilt, name="pitch_servo", color=cq.Color(0.9, 0.45, 0, 0.85))
# Roll
full_assy.add(roll_placed, name="roll_bracket", color=cq.Color(0.3, 0.8, 0.3, 0.55))
full_assy.add(roll_servo_in_bracket, name="roll_servo", color=cq.Color(0.9, 0, 0.45, 0.85))

full_assy.save(os.path.join(out_dir, "bracket_check_all.step"))

total_h = roll_z + 20 + WALL + BODY_H + SHAFT_H
print(f"\n   Total stack height: ~{total_h:.1f}mm")

print("\n=== Export complete ===")
print("  bracket_check_pan.step   - Pan Base + yaw servo")
print("  bracket_check_tilt.step  - Tilt Bracket + pitch servo")
print("  bracket_check_roll.step  - Roll Bracket + roll servo")
print("  bracket_check_all.step   - Full 3-axis stack")
