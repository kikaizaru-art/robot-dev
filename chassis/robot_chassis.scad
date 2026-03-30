// ============================================
// CoreS3 コンパニオンロボット 筐体設計
// Compact Robot Chassis - Cozmo/Vector Style
// ============================================
// 3分割構成: ベース / 胴体 / ヘッド
// プリンタ: Bambu Lab A1 (FDM)
// 単位: mm

// ---- パーツ実寸 ----
// CoreS3: 58 x 65 x 18mm (画面: ~54 x 40mm)
// MG90S: 23 x 12.2 x 29mm (軸含む32mm)
// FS90R: 23 x 12.2 x 22mm (MG90Sより短い)
// PCA9685: 62 x 25 x 10mm
// ボールキャスター: ~16mm高 (小型)

// ---- 設計パラメータ ----
wall = 2.5;          // 壁厚
tol = 0.3;           // はめあい公差
screw_d = 2.5;       // M2.5ネジ穴径
screw_head_d = 5;    // M2.5ネジ頭径

// CoreS3寸法
cs3_w = 58;          // 幅
cs3_d = 65;          // 奥行
cs3_h = 18;          // 厚み
cs3_screen_w = 54;   // 画面幅
cs3_screen_h = 40;   // 画面高

// サーボ寸法
mg90s_w = 23;
mg90s_d = 12.2;
mg90s_h = 29;
mg90s_flange_w = 32.5;  // フランジ幅
mg90s_flange_h = 2.5;   // フランジ厚
mg90s_flange_pos = 17;  // 底からフランジまで

fs90r_w = 23;
fs90r_d = 12.2;
fs90r_h = 22;
fs90r_flange_w = 32.5;
fs90r_flange_h = 2.5;
fs90r_flange_pos = 15.5;

// タイヤ
wheel_d = 60;        // FS90R用ホイール直径
wheel_w = 8;         // ホイール幅

// ボールキャスター
caster_h = 16;       // 小型ボールキャスター高さ
caster_d = 12;       // 取付穴間

// PCA9685
pca_w = 62;
pca_d = 25;
pca_h = 10;

// ============================================
//  表示制御
// ============================================
// コメントアウトで個別パーツ表示切替
show_base = true;
show_body = true;
show_neck = true;
show_head = true;
show_components = true;  // パーツのゴースト表示

// ============================================
//  全体レイアウト
// ============================================
// ベース高さ = キャスター高 + 少しの余裕
base_h = 25;
base_w = 130;        // タイヤと腕の干渉回避のため広め
base_d = 90;

// 胴体
body_h = 55;
body_w = 90;
body_d = 75;
body_z = base_h;  // ベースの上

// 首（3自由度: ヨー(ギア駆動) → ピッチ(直結) → ロール(直結)）
// ヨーサーボは胴体内に水平配置、リングギアで回転台を駆動
// ピッチ・ロールサーボは回転台上にマウント
ring_gear_d = 60;      // リングギア外径
pinion_d = 15;         // ピニオンギア直径
turntable_d = 55;      // 回転台（ターンテーブル）直径
turntable_h = 3;       // 回転台の厚み
bracket_h = mg90s_h + 5;  // ピッチブラケット高さ ~34mm
neck_h = turntable_h + bracket_h + mg90s_d + 5;  // ~55mm
neck_z = body_z + body_h;

// ヘッド（CoreS3マウント）— CoreS3は立てて収納（画面が前）
// CoreS3 standing: X=幅58, Y=厚み18, Z=高さ65
head_w = cs3_w + wall * 2 + tol * 2;       // ~64mm（幅）
head_d = cs3_h + wall * 2 + tol * 2 + 10;  // ~34mm（奥行き=厚み18+余裕）
head_h = cs3_d + wall * 2 + tol * 2;       // ~71mm（高さ=CoreS3の65mm）
head_z = neck_z + neck_h;                   // 首の上

module rounded_box(w, d, h, r=5) {
    // 角丸の箱
    hull() {
        for (x = [r, w-r])
            for (y = [r, d-r])
                translate([x, y, 0])
                    cylinder(r=r, h=h, $fn=32);
    }
}

module screw_hole(h=10) {
    cylinder(d=screw_d, h=h, $fn=20);
}

module screw_standoff(h=6, od=6) {
    difference() {
        cylinder(d=od, h=h, $fn=24);
        translate([0, 0, -0.1])
            cylinder(d=screw_d, h=h+0.2, $fn=20);
    }
}

// ============================================
//  1. ベースプレート
// ============================================
module base_plate() {
    color("DimGray", 0.8)
    difference() {
        union() {
            // メインプレート（角丸）
            rounded_box(base_w, base_d, base_h, r=8);

            // 胴体取付用ボス（4箇所）
            body_mount_points = [
                [15, 15], [base_w-15, 15],
                [15, base_d-15], [base_w-15, base_d-15]
            ];
            for (p = body_mount_points) {
                translate([p[0], p[1], base_h])
                    screw_standoff(h=5, od=7);
            }
        }

        // 内部空洞（軽量化 + 配線スペース）
        translate([wall, wall, wall])
            rounded_box(base_w - wall*2, base_d - wall*2, base_h, r=6);

        // ---- FS90R サーボマウント（左右）----
        // 左サーボ
        translate([-1, base_d/2 - fs90r_w/2, base_h/2 - fs90r_d/2])
            cube([wall+2, fs90r_w + tol*2, fs90r_d + tol*2]);
        // 左サーボ フランジスロット
        translate([-1, base_d/2 - fs90r_flange_w/2, base_h/2 - fs90r_d/2 + fs90r_flange_pos])
            cube([wall*2+2, fs90r_flange_w + tol, fs90r_flange_h + tol]);

        // 右サーボ
        translate([base_w - wall - 1, base_d/2 - fs90r_w/2, base_h/2 - fs90r_d/2])
            cube([wall+2, fs90r_w + tol*2, fs90r_d + tol*2]);
        // 右サーボ フランジスロット
        translate([base_w - wall*2 - 1, base_d/2 - fs90r_flange_w/2, base_h/2 - fs90r_d/2 + fs90r_flange_pos])
            cube([wall*2+2, fs90r_flange_w + tol, fs90r_flange_h + tol]);

        // ---- ボールキャスター取付穴（前方中央）----
        translate([base_w/2, 15, -1])
            cylinder(d=12, h=wall+2, $fn=24);
        // キャスター固定ネジ穴
        for (dx = [-8, 8]) {
            translate([base_w/2 + dx, 15, -1])
                cylinder(d=screw_d, h=wall+2, $fn=16);
        }

        // ---- 配線通し穴（上面）----
        translate([base_w/2 - 10, base_d/2 - 5, base_h - wall - 1])
            cube([20, 10, wall + 2]);

        // ---- 底面通気穴 ----
        for (x = [25, 50, 75]) {
            translate([x, base_d/2, -1])
                cylinder(d=5, h=wall+2, $fn=16);
        }
    }
}

// ============================================
//  2. 胴体（ボディ）
// ============================================
module body_shell() {
    color("SlateGray", 0.8)
    translate([base_w/2 - body_w/2, base_d/2 - body_d/2, body_z])
    difference() {
        union() {
            // 外殻（台形っぽい角丸ボックス）
            rounded_box(body_w, body_d, body_h, r=10);
        }

        // 内部空洞
        translate([wall, wall, wall])
            rounded_box(body_w - wall*2, body_d - wall*2, body_h + 1, r=8);

        // ---- 腕サーボマウント（左）---- 上寄り配置（タイヤ干渉回避）
        arm_z = body_h * 0.65 - mg90s_d/2;  // 上2/3の位置
        translate([-1, body_d/2 - mg90s_w/2, arm_z])
            cube([wall+2, mg90s_w + tol*2, mg90s_d + tol*2]);
        // 左 フランジスロット
        translate([-1, body_d/2 - mg90s_flange_w/2, arm_z + mg90s_flange_pos])
            cube([wall*2, mg90s_flange_w + tol, mg90s_flange_h + tol]);
        // 左 軸穴
        translate([-1, body_d/2, arm_z + mg90s_h - 5])
            rotate([0, 90, 0])
                cylinder(d=8, h=wall+2, $fn=24);

        // ---- 腕サーボマウント（右）----
        translate([body_w - wall - 1, body_d/2 - mg90s_w/2, arm_z])
            cube([wall+2, mg90s_w + tol*2, mg90s_d + tol*2]);
        // 右 フランジスロット
        translate([body_w - wall*2, body_d/2 - mg90s_flange_w/2, arm_z + mg90s_flange_pos])
            cube([wall*2, mg90s_flange_w + tol, mg90s_flange_h + tol]);
        // 右 軸穴
        translate([body_w - wall - 1, body_d/2, arm_z + mg90s_h - 5])
            rotate([0, 90, 0])
                cylinder(d=8, h=wall+2, $fn=24);

        // ---- PCA9685マウントスロット（底面内側）----
        // ネジ穴で固定
        translate([body_w/2 - pca_w/2, body_d/2 - pca_d/2, 0])
        for (dx = [3, pca_w-3])
            for (dy = [3, pca_d-3])
                translate([dx, dy, -1])
                    cylinder(d=screw_d, h=wall+2, $fn=16);

        // ---- 背面メンテナンスハッチ ----
        translate([body_w/2 - 25, body_d - wall - 1, 10])
            cube([50, wall + 2, body_h - 20]);

        // ---- 配線穴（底面）----
        translate([body_w/2 - 10, body_d/2 - 5, -1])
            cube([20, 10, wall + 2]);

        // ---- リングギア+回転台 貫通穴（上面中央）----
        translate([body_w/2, body_d/2, body_h - wall - 1])
            cylinder(d=ring_gear_d + 5, h=wall + 2, $fn=32);

        // ---- ベース取付ネジ穴（4箇所）----
        body_offset_x = base_w/2 - body_w/2;
        body_offset_y = base_d/2 - body_d/2;
        mount_pts = [
            [15 - body_offset_x, 15 - body_offset_y],
            [base_w - 15 - body_offset_x, 15 - body_offset_y],
            [15 - body_offset_x, base_d - 15 - body_offset_y],
            [base_w - 15 - body_offset_x, base_d - 15 - body_offset_y]
        ];
        for (p = mount_pts) {
            translate([p[0], p[1], -1])
                cylinder(d=screw_d, h=wall + 2, $fn=16);
        }
    }
}

// ============================================
//  3. 首（ネック）— 可動スペース確保用
// ============================================
// 内部構造（ギア+サーボ+ブラケット）は実物合わせで設計
// ここでは必要な空間とマウントポイントだけ定義
module neck() {
    cx = base_w/2;
    cy = base_d/2;

    // ---- 首の可動空間を示す半透明シリンダ ----
    color("SteelBlue", 0.2)
    translate([cx, cy, neck_z])
        cylinder(d=ring_gear_d, h=neck_h, $fn=36);

    // ---- 回転台ベース（胴体上面に固定）----
    color("Gold", 0.6)
    translate([cx, cy, neck_z])
    difference() {
        cylinder(d=ring_gear_d, h=4, $fn=36);
        translate([0, 0, -1])
            cylinder(d=ring_gear_d - 10, h=6, $fn=36);
    }

    // ---- ヘッド取付台（首の上端）----
    color("Silver", 0.7)
    translate([cx, cy, neck_z + neck_h - 4])
    difference() {
        cylinder(d=40, h=4, $fn=36);
        // ネジ穴
        for (a = [0:90:270])
            rotate([0, 0, a])
                translate([14, 0, -1])
                    cylinder(d=screw_d, h=6, $fn=12);
        // 配線穴
        translate([0, 0, -1])
            cylinder(d=12, h=6, $fn=20);
    }
}

// ============================================
//  4. ヘッドマウント（CoreS3ケース）
// ============================================
module head_mount() {
    color("DarkSlateGray", 0.8)
    translate([base_w/2 - head_w/2, base_d/2 - head_d/2, head_z])
    difference() {
        union() {
            // 外殻
            rounded_box(head_w, head_d, head_h, r=6);
            // パンチルト固定は底面ネジ穴のみ（フランジ不要）
        }

        // 内部空洞
        translate([wall, wall, wall])
            rounded_box(head_w - wall*2, head_d - wall*2, head_h - wall, r=4);

        // ---- CoreS3 画面開口（前面）----
        // CoreS3は立てて収納。画面(54x40)が前面中央に来る
        translate([head_w/2 - cs3_screen_w/2 - 1, -1,
                   (head_h - cs3_screen_h) / 2])
            cube([cs3_screen_w + 2, wall + 2, cs3_screen_h + 2]);

        // ---- カメラ穴（前面上部）----
        translate([head_w/2 + 15, -1, head_h - 12])
            cylinder(d=8, h=wall + 2, $fn=24);

        // ---- マイク穴（前面、小穴×3）----
        for (x = [-8, 0, 8]) {
            translate([head_w/2 + x, -1, 8])
                cylinder(d=2, h=wall + 2, $fn=12);
        }

        // ---- CoreS3固定用レール（内側左右）----
        // CoreS3を上からスライドインする構造
        cs3_slot_x = (head_w - cs3_w - tol*2) / 2;
        // 左レール溝
        translate([cs3_slot_x - 1, wall, wall])
            cube([2, head_d - wall*2, head_h]);
        // 右レール溝
        translate([head_w - cs3_slot_x - 1, wall, wall])
            cube([2, head_d - wall*2, head_h]);

        // ---- 上面開口（CoreS3挿入口）----
        translate([wall + 2, wall + 2, head_h - wall - 1])
            cube([head_w - wall*2 - 4, head_d - wall*2 - 4, wall + 2]);

        // ---- パンチルト取付ネジ穴（底面）----
        for (dx = [-10, 10])
            for (dy = [-10, 10])
                translate([head_w/2 + dx, head_d/2 + dy, -6])
                    cylinder(d=screw_d, h=12, $fn=16);

        // ---- 配線穴（底面）----
        translate([head_w/2 - 8, head_d/2 - 5, -6])
            cube([16, 10, 8]);
    }
}

// ============================================
//  4. 腕（フリッパー）
// ============================================
module flipper_arm() {
    color("Gray", 0.8)
    difference() {
        union() {
            // 丸みのある腕形状
            hull() {
                cylinder(d=14, h=4, $fn=24);
                translate([20, 0, 0])       // 短め（タイヤ干渉回避）
                    cylinder(d=10, h=4, $fn=24);
            }
        }
        // サーボホーン取付穴
        translate([0, 0, -1])
            cylinder(d=screw_d, h=6, $fn=16);
        // サーボホーンのスプライン穴
        translate([0, 0, 2])
            cylinder(d=5, h=3, $fn=20);
    }
}

// ============================================
//  ゴースト表示（パーツ配置確認用）
// ============================================
module ghost_cores3() {
    // CoreS3を立てた状態: X=幅58, Y=厚み18, Z=高さ65
    color("Black", 0.3)
    cube([cs3_w, cs3_h, cs3_d]);    // [58, 18, 65]
    // 画面（前面 Y=0 に配置）
    color("Cyan", 0.2)
    translate([(cs3_w - cs3_screen_w)/2, -0.5, (cs3_d - cs3_screen_h)/2])
        cube([cs3_screen_w, 1, cs3_screen_h]);  // [54, 1, 40]
}

module ghost_servo(type="mg90s") {
    w = (type == "fs90r") ? fs90r_w : mg90s_w;
    d = (type == "fs90r") ? fs90r_d : mg90s_d;
    h = (type == "fs90r") ? fs90r_h : mg90s_h;
    color("DodgerBlue", 0.3)
    translate([-w/2, -d/2, 0])
        cube([w, d, h]);
}

module ghost_pca9685() {
    color("Green", 0.3)
    cube([pca_w, pca_d, pca_h]);
}

module ghost_wheel() {
    color("DarkGray", 0.3)
    rotate([0, 90, 0])
        cylinder(d=wheel_d, h=wheel_w, $fn=32, center=true);
}

// ============================================
//  組み立て表示
// ============================================

// ベース
if (show_base) base_plate();

// 胴体
if (show_body) body_shell();

// 首
if (show_neck) neck();

// ヘッド
if (show_head) head_mount();

// 腕（左右）— サーボ位置に合わせて高め配置
if (show_body) {
    body_left = base_w/2 - body_w/2;
    body_right = base_w/2 + body_w/2;
    by = base_d/2;
    arm_axis_z = body_z + body_h * 0.65 - mg90s_d/2 + mg90s_h - 5;
    // 左腕
    translate([body_left - 2, by, arm_axis_z])
        rotate([0, -90, 0])
            flipper_arm();
    // 右腕
    translate([body_right + 2, by, arm_axis_z])
        rotate([0, 90, 0])
            flipper_arm();
}

// ゴーストパーツ（全パーツ表示）
if (show_components) {
    // CoreS3（ヘッド内、立てた状態）
    translate([base_w/2 - cs3_w/2,
               base_d/2 - head_d/2 + wall + tol,   // 前壁の内側
               head_z + wall + tol])                 // 底壁の上
        ghost_cores3();

    // PCA9685（胴体内）
    translate([base_w/2 - pca_w/2, base_d/2 - pca_d/2, body_z + wall + 2])
        ghost_pca9685();

    // ---- FS90Rサーボ + タイヤ（ベース左右）----
    // 左FS90R
    translate([wall + fs90r_d/2, base_d/2, base_h/2 - fs90r_h/2])
        rotate([0, 0, 90])
            ghost_servo("fs90r");
    // 左タイヤ
    translate([0, base_d/2, base_h/2])
        ghost_wheel();
    // 右FS90R
    translate([base_w - wall - fs90r_d/2, base_d/2, base_h/2 - fs90r_h/2])
        rotate([0, 0, 90])
            ghost_servo("fs90r");
    // 右タイヤ
    translate([base_w, base_d/2, base_h/2])
        ghost_wheel();

    // ---- 腕サーボ MG90S（胴体左右）----
    g_body_left = base_w/2 - body_w/2;
    g_body_right = base_w/2 + body_w/2;
    g_arm_z = body_z + body_h * 0.65 - mg90s_d/2;
    // 左腕サーボ
    translate([g_body_left + wall/2, base_d/2, g_arm_z])
        rotate([0, 0, 90])
            ghost_servo("mg90s");
    // 右腕サーボ
    translate([g_body_right - wall/2, base_d/2, g_arm_z])
        rotate([0, 0, 90])
            ghost_servo("mg90s");

    // ---- 首サーボ ×3（概念配置）----
    // ヨーサーボは胴体内に配置（ギアで回転台を駆動）
    color("DodgerBlue", 0.25)
    translate([base_w/2 + 20, base_d/2, body_z + body_h - mg90s_h - wall])
        ghost_servo("mg90s");
    // 「NECK: 3DOF」ラベル代わりのマーカー
    // ピッチ・ロールサーボは首空間内（実物合わせ）

    // ボールキャスター位置
    color("Yellow", 0.3)
    translate([base_w/2, 15, 0])
        sphere(d=10, $fn=16);
}

// ============================================
//  印刷用エクスポート（個別モジュール）
// ============================================
// OpenSCADのCustomizerまたはコマンドラインで
// 個別パーツをSTLエクスポート:
//
// openscad -D "show_base=true;show_body=false;show_neck=false;show_head=false;show_components=false" -o base.stl robot_chassis.scad
// openscad -D "show_body=true;show_base=false;show_neck=false;show_head=false;show_components=false" -o body.stl robot_chassis.scad
// openscad -D "show_neck=true;show_base=false;show_body=false;show_head=false;show_components=false" -o neck.stl robot_chassis.scad
// openscad -D "show_head=true;show_base=false;show_body=false;show_neck=false;show_components=false" -o head.stl robot_chassis.scad
