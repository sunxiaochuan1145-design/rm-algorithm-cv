# -*- coding: utf-8 -*-
"""生成一张用于灯条检测练习的合成测试图。

为什么要有这个脚本：
    本机（Windows）没有装 OpenCV，但换一台 Ubuntu 机器就能直接跑 C++ 版。
    为了在两边都有一份"像样"的输入，这里用 numpy + Pillow 画一张模拟场地：
    暗色背景 + 透视地面 + 一条天花板灯管（干扰项）+ 一块带两条发红灯条的装甲板。

刻意保留的"不干净"：
    - 灯条中心接近白色（讲义 2.1.5 / 2.3.4 的现象），所以按颜色差分割时会变空心；
    - 左上角一条纯白灯管，灰度很高但不是目标，用来提醒"亮不等于目标"；
    - 地面上有一块偏红反光，能通过颜色阈值，但长宽比不合适，靠几何条件筛掉；
    - 整图加了噪声、轻微暗角和透视条带。

输出：code/demo_board.png（1280x1024，与讲义主例一致）
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------- 基本参数
W, H = 1280, 1024
IMG_RNG = np.random.default_rng(20261113)  # 固定种子，保证可重复


# ---------------------------------------------------------------- 小工具
def rot(px: float, py: float, deg: float) -> tuple[float, float]:
    """把点绕原点旋转 deg 度（图像坐标，y 向下）。"""
    t = math.radians(deg)
    c, s = math.cos(t), math.sin(t)
    return px * c - py * s, px * s + py * c


def box_blur(a: np.ndarray, r: int) -> np.ndarray:
    """纯 numpy 的盒式模糊（两次一维滑窗），用来画发光。"""
    if r <= 0:
        return a.copy()

    def blur1(x: np.ndarray, axis: int) -> np.ndarray:
        pad = [(0, 0), (0, 0)]
        pad[axis] = (r + 1, r)
        p = np.pad(x, pad, mode="edge")
        c = np.cumsum(p, axis=axis, dtype=np.float64)
        n = x.shape[axis]
        k = 2 * r + 1
        if axis == 0:
            out = (c[k - 1:k - 1 + n] - np.concatenate([np.zeros((1, p.shape[1])), c[:n - 1]], axis=0)) / k
        else:
            out = (c[:, k - 1:k - 1 + n] - np.concatenate([np.zeros((p.shape[0], 1)), c[:, :n - 1]], axis=1)) / k
        return out

    return blur1(blur1(a, 0), 1)


def add_poly(draw: ImageDraw.ImageDraw, pts, fill):
    draw.polygon([(float(x), float(y)) for x, y in pts], fill=fill)


def quad_from_center(cx, cy, w, h, deg):
    """以中心 + 旋转角生成矩形四角，返回顺时针四点。"""
    out = []
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        dx, dy = rot(sx * w / 2, sy * h / 2, deg)
        out.append((cx + dx, cy + dy))
    return out


# ---------------------------------------------------------------- 背景
def make_background() -> np.ndarray:
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)

    # 竖直渐变：上方偏暗蓝，中部稍亮
    t = (yy / H)
    img = np.stack([
        26 + 18 * t + 10 * np.exp(-((yy - 380) / 260.0) ** 2),
        30 + 20 * t + 10 * np.exp(-((yy - 380) / 260.0) ** 2),
        36 + 22 * t + 12 * np.exp(-((yy - 380) / 260.0) ** 2),
    ], axis=-1).astype(np.float32)

    # 透视地面：从消失点 (560, 300) 向下的梯形条纹
    vp_x, vp_y = 560.0, 300.0
    floor = yy > 470
    for i in range(-9, 10):
        # 沿水平方向的一组"地砖缝"，越远越密
        target_x = vp_x + i * 190.0
        k = (target_x - vp_x) / (vp_y - 1024.0) * -1.0
        line_x = vp_x + (yy - vp_y) * k
        band = np.abs(xx - line_x) < 2.2
        mask = band & floor
        img[mask, 0] += 26
        img[mask, 1] += 30
        img[mask, 2] += 32

    # 远处横向分区线
    for y0 in (520, 640, 800):
        band = np.abs(yy - y0) < 1.8
        img[band, 0] += 20
        img[band, 1] += 22
        img[band, 2] += 24

    return np.clip(img, 0, 255)


def add_ceiling_lamp(img: np.ndarray) -> np.ndarray:
    """左上角的纯白灯管：灰度极高、颜色差接近 0，是典型的假阳性来源。"""
    cx, cy, w, h, deg = 250.0, 95.0, 190.0, 15.0, -7.0
    quad = quad_from_center(cx, cy, w, h, deg)

    glow = np.zeros((H, W), np.float32)
    gimg = Image.fromarray(glow, mode="F")
    add_poly(ImageDraw.Draw(gimg), quad, 255)
    glow = box_blur(np.asarray(gimg, dtype=np.float32), 26) / 255.0
    glow = np.clip(glow * 1.25, 0, 1)[..., None]

    img = img + glow * np.array([210, 216, 226], dtype=np.float32)

    layer = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(layer)
    add_poly(d, quad, (255, 255, 252))
    return np.asarray(layer, dtype=np.float32)


def add_floor_reflection(img: np.ndarray) -> np.ndarray:
    """地上一块偏红的反光：面积够、颜色过阈值，但长宽比不合格。"""
    quad = quad_from_center(215.0, 885.0, 96.0, 74.0, 22.0)
    glow = np.zeros((H, W), np.float32)
    gimg = Image.fromarray(glow, mode="F")
    add_poly(ImageDraw.Draw(gimg), quad, 255)
    glow = box_blur(np.asarray(gimg, dtype=np.float32), 18) / 255.0
    img = img + np.clip(glow, 0, 1)[..., None] * np.array([120, 34, 30], dtype=np.float32)

    layer = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(layer)
    add_poly(d, quad, (146, 38, 34))
    d.line([quad[0], quad[1], quad[2], quad[3], quad[0]], fill=(180, 52, 46), width=3)
    return np.asarray(layer, dtype=np.float32)


def add_dim_red_patch(img: np.ndarray) -> np.ndarray:
    """地面上的一片"暗红雾"：颜色差能过阈值，但 R 值不高。

    讲义 2.3.3 提到目标通道下限用来排除"相对偏红但本身信号很弱"的像素，
    这里就放一块这样的区域，让日志里 R 下限真正筛掉一些像素。
    """
    glow = np.zeros((H, W), np.float32)
    gimg = Image.fromarray(glow, mode="F")
    d = ImageDraw.Draw(gimg)
    d.ellipse([900, 780, 1150, 980], fill=255)
    glow = box_blur(np.asarray(gimg, dtype=np.float32), 34) / 255.0
    a = np.clip(glow * 0.9, 0.0, 1.0)[..., None]
    img = img * (1.0 - a) + a * np.array([72.0, 8.0, 6.0], dtype=np.float32)
    return img


# ---------------------------------------------------------------- 装甲板
def draw_armor(img: np.ndarray, cx: float, cy: float, scale: float, deg: float,
               digit: str = "3") -> np.ndarray:
    """画一块装甲板：深色底板 + 两条发红灯条 + 中间编号。"""
    pw, ph = 268.0 * scale, 116.0 * scale
    board = quad_from_center(cx, cy, pw, ph, deg)

    # 底板（带一点自上而下的亮度变化）
    layer = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(layer)
    add_poly(d, board, (44, 45, 49))

    # 底板内缩一圈的"金属边框"效果
    inner = quad_from_center(cx, cy, pw * 0.94, ph * 0.88, deg)
    add_poly(d, inner, (52, 53, 58))
    for i in range(len(board)):
        d.line([board[i], board[(i + 1) % 4]], fill=(88, 90, 96), width=max(1, int(2 * scale)))

    img = np.asarray(layer, dtype=np.float32)

    # 两条灯条：中心发白，两侧偏红
    bar_w, bar_h = 13.0 * scale, 72.0 * scale
    for sign in (-1, 1):
        bx = cx + rot(sign * pw * 0.335, 0.0, deg)[0]
        by = cy + rot(sign * pw * 0.335, 0.0, deg)[1]
        bar = quad_from_center(bx, by, bar_w, bar_h, deg)

        glow = np.zeros((H, W), np.float32)
        gimg = Image.fromarray(glow, mode="F")
        add_poly(ImageDraw.Draw(gimg), bar, 255)
        glow = box_blur(np.asarray(gimg, dtype=np.float32), max(6, int(14 * scale))) / 255.0
        glow = np.clip(glow * (1.5 if scale >= 1 else 1.9), 0, 1)[..., None]
        img = img + glow * np.array([150, 26, 24], dtype=np.float32)

        layer = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
        d = ImageDraw.Draw(layer)
        add_poly(d, bar, (232, 44, 42))
        # 中心接近白色：这就是讲义里"灯条空心"的成因
        inner_bar = quad_from_center(bx, by, bar_w * 0.30, bar_h * 0.62, deg)
        add_poly(d, inner_bar, (255, 246, 240))
        img = np.asarray(layer, dtype=np.float32)

    # 中间的编号
    layer = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(layer)
    font = load_font(int(62 * scale))
    tw, th = d.textbbox((0, 0), digit, font=font)[2:]
    d.text((cx - tw / 2.0, cy - th / 2.0 - 4 * scale), digit, font=font, fill=(206, 208, 212))
    return np.asarray(layer, dtype=np.float32)


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for name in ("arialbd.ttf", "arial.ttf", "msyh.ttc", "simhei.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # 老版本 Pillow
        return ImageFont.load_default()


# ---------------------------------------------------------------- 组装
def main() -> None:
    img = make_background()
    img = add_ceiling_lamp(img)
    img = add_floor_reflection(img)
    img = add_dim_red_patch(img)

    # 主目标：中偏右、轻微旋转
    img = draw_armor(img, cx=720.0, cy=640.0, scale=1.0, deg=-11.0, digit="3")
    # 远处小目标：考验"配对用平均长度归一化"这件事
    img = draw_armor(img, cx=1046.0, cy=318.0, scale=0.55, deg=7.0, digit="2")

    # 噪声 + 暗角（真实相机不会给你干净矩阵）
    img = img + IMG_RNG.normal(0.0, 3.4, img.shape).astype(np.float32)

    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    rr = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    vig = np.clip(1.0 - 0.28 * np.clip(rr - 0.55, 0, None) ** 1.5, 0.6, 1.0)[..., None]
    img = img * vig

    # 少量亮斑噪点，模拟镜面露光 / 传感器坏点
    for _ in range(26):
        x = int(IMG_RNG.integers(0, W - 4))
        y = int(IMG_RNG.integers(0, H - 4))
        r = int(IMG_RNG.integers(0, 3))
        img[y:y + r + 1, x:x + r + 1] += IMG_RNG.uniform(60, 150)

    out = np.clip(img, 0, 255).astype(np.uint8)
    path = Path(__file__).resolve().parent / "demo_board.png"
    Image.fromarray(out).save(path)
    print(f"[make_demo_image] 已生成 {path}  ({out.shape[1]}x{out.shape[0]})")
    print(f"[make_demo_image] 灰度均值 {out.mean():.1f}，最大通道值 {out.max()}")


if __name__ == "__main__":
    main()
