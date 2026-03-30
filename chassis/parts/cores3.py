"""
M5Stack CoreS3 精密モデル
公式ドキュメント準拠寸法: https://docs.m5stack.com/en/core/CoreS3
"""
import cadquery as cq


def make_cores3():
    """M5Stack CoreS3の3Dモデルを生成"""

    # ---- 公式寸法 (mm) ----
    w = 54.0          # 幅
    d = 54.0          # 奥行き（正方形）
    h = 22.0          # 高さ（厚み）

    corner_r = 4.0    # 角丸半径

    # 画面（2インチ IPS, 320x240）
    screen_w = 40.0   # 画面表示エリア幅
    screen_h = 30.0   # 画面表示エリア高さ
    screen_bezel = 3.0  # ベゼル幅

    # カメラ（GC0308, 前面）
    cam_d = 6.0       # カメラ穴径
    cam_x = 20.0      # 中心からのXオフセット
    cam_y = -20.0     # 中心からのYオフセット（上部）

    # ボタン（前面下部）
    btn_w = 8.0
    btn_h = 3.0

    # USB-C（底面）
    usbc_w = 9.0
    usbc_h = 3.5

    # Port A/B（側面、Grove端子）
    grove_w = 10.0
    grove_h = 8.0

    # ---- モデリング ----
    # メインボディ（角丸の箱）
    body = (
        cq.Workplane("XY")
        .box(w, d, h, centered=(True, True, False))
        .edges("|Z")
        .fillet(corner_r)
        .edges(">Z or <Z")
        .fillet(1.5)
    )

    # 画面のくぼみ（前面=+Z面に画面）
    # CoreS3は画面が上面
    screen_recess = (
        cq.Workplane("XY")
        .workplane(offset=h - 0.5)
        .rect(screen_w + screen_bezel * 2, screen_h + screen_bezel * 2)
        .extrude(0.5)
    )

    # 画面部分を色分けのためカット
    body = body.cut(
        cq.Workplane("XY")
        .workplane(offset=h - 0.3)
        .rect(screen_w, screen_h)
        .extrude(0.5)
    )

    # カメラレンズ穴
    body = body.cut(
        cq.Workplane("XY")
        .workplane(offset=h)
        .transformed(offset=(cam_x, cam_y, 0))
        .circle(cam_d / 2)
        .extrude(-3)
    )

    # USB-Cポート（前面=-Y面の底部）
    body = body.cut(
        cq.Workplane("XZ")
        .workplane(offset=-d / 2)
        .transformed(offset=(0, usbc_h / 2 + 2, 0))
        .rect(usbc_w, usbc_h)
        .extrude(-2)
    )

    return body


if __name__ == "__main__":
    core = make_cores3()
    cq.exporters.export(core, "cores3.step")
    cq.exporters.export(core, "cores3.stl")
    print("CoreS3 model exported: cores3.step, cores3.stl")
