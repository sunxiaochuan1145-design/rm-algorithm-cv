# -*- coding: utf-8 -*-
"""灯条检测流水线的 Python 复刻版（纯 numpy + Pillow，不需要 OpenCV）。

为什么要写这份：
    本机是 Windows，没有装 OpenCV / cv2，但想把讲义第 2 章的流程完整跑一遍、
    并且把每一步的中间结果存成图片放进 results/。所以这里用 numpy 手写了
    C++ 版里的每个 OpenCV 调用：

        cv::cvtColor(BGR2GRAY)        ->  bt601_gray()
        cv::split + 饱和相减          ->  color_score()
        cv::threshold                 ->  直接比较生成掩膜
        cv::morphologyEx(CLOSE)       ->  erode() / dilate() / close()
        cv::connectedComponents       ->  label_components()（并查集）
        cv::findContours              ->  convex_hull()（外轮廓）
        cv::minAreaRect               ->  min_area_rect()（旋转卡壳，枚举凸包边）
        配对（长度/高度/间距/夹角）     ->  pair_bars()

    与 code/light_bar_detect.cpp 的参数保持一致，方便两边互相对照。

输出（都在 repo/results/ 下）：
    01_gray.png      灰度图
    02_binary.png    颜色差 + 目标通道阈值得到的二值掩膜
    03_morph.png     3x3 闭运算后的掩膜
    04_contours.png  连通区域的外轮廓 / 凸包与面积标注
    05_detected.png  原图叠加：灯条旋转矩形（绿）+ 配对候选（橙）+ 四点编号（红）
    run_log.txt      各阶段数量、耗时与最终配对结果
"""

from __future__ import annotations

import argparse
import math
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------- 参数（与 C++ 版对齐）
COLOR_DIFF_THRESH = 90     # 颜色差阈值：红色分数 = max(R - B, 0) 要严格大于它
TARGET_CHAN_MIN = 100      # 目标通道下限：R 要大于它，排除"相对偏红但很弱"的像素
GRAY_THRESH = 120          # 仅用于对比实验的灰度阈值
MORPH_KERNEL = 3           # 3x3 方形结构元素
DO_CLOSE = True            # 基线：闭运算（补缺口、连邻近）
DO_OPEN = False            # 开运算会把细窄灯条切断，讲义里主例因此丢目标，默认关掉

MIN_CONTOUR_AREA = 20.0    # 轮廓面积下限（平方像素）
MIN_BAR_LENGTH = 6.0       # 灯条长度下限（像素）
MIN_ASPECT = 2.0           # 长宽比下限
MAX_TILT_DEG = 35.0        # 长轴偏离竖直方向的角度上限

MAX_LEN_RATIO = 1.5        # 两灯条长度比上限
MAX_HEIGHT_RATIO = 0.35    # |Δy| / 平均长度 上限
GAP_RATIO_RANGE = (0.8, 3.2)  # 中心距 / 平均长度 的范围
MAX_ANGLE_DIFF = 15.0      # 两长轴夹角上限（度）
MIN_QUAD_AREA = 1.0        # 四点围成的四边形面积下限

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_ROOT / "results"


# ---------------------------------------------------------------- 基础图像操作
def load_rgb(path: Path) -> np.ndarray:
    """读图 -> float32 的 HxWx3（RGB）。"""
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.float32)


def bt601_gray(img: np.ndarray) -> np.ndarray:
    """BT.601 灰度，与 cv::cvtColor(BGR2GRAY) 的加权一致。"""
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    return 0.299 * r + 0.587 * g + 0.114 * b


def color_score(img: np.ndarray) -> np.ndarray:
    """红色分数 = max(R - B, 0)，饱和减法（负数截到 0）。"""
    return np.clip(img[..., 0] - img[..., 2], 0.0, None)


def erode(mask: np.ndarray, k: int = 3) -> np.ndarray:
    """3x3 腐蚀：结构元素覆盖的 9 个位置全是前景才保留（边界按 0 处理）。"""
    pad = k // 2
    p = np.pad(mask, pad, mode="constant", constant_values=False)
    out = mask.copy()
    for dy in range(k):
        for dx in range(k):
            out &= p[dy:dy + mask.shape[0], dx:dx + mask.shape[1]]
    return out


def dilate(mask: np.ndarray, k: int = 3) -> np.ndarray:
    """3x3 膨胀：覆盖范围内只要有一个前景就把中心点亮。"""
    pad = k // 2
    p = np.pad(mask, pad, mode="constant", constant_values=False)
    out = mask.copy()
    for dy in range(k):
        for dx in range(k):
            out |= p[dy:dy + mask.shape[0], dx:dx + mask.shape[1]]
    return out


def close(mask: np.ndarray, k: int = 3) -> np.ndarray:
    """闭运算：先膨胀再腐蚀。"""
    return erode(dilate(mask, k), k)


def open_(mask: np.ndarray, k: int = 3) -> np.ndarray:
    """开运算：先腐蚀再膨胀。"""
    return dilate(erode(mask, k), k)


# ---------------------------------------------------------------- 连通域（并查集）
def label_components(mask: np.ndarray) -> tuple[np.ndarray, int]:
    """8 邻域连通域标记，返回 (标签图, 区域数量)。标签从 1 开始，0 为背景。"""
    h, w = mask.shape
    labels = np.zeros((h, w), dtype=np.int32)
    parent: list[int] = [0]

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    ys, xs = np.nonzero(mask)
    for y, x in zip(ys.tolist(), xs.tolist()):
        nbr: list[int] = []
        if x > 0 and labels[y, x - 1]:
            nbr.append(int(labels[y, x - 1]))
        if y > 0:
            if labels[y - 1, x]:
                nbr.append(int(labels[y - 1, x]))
            if x > 0 and labels[y - 1, x - 1]:
                nbr.append(int(labels[y - 1, x - 1]))
            if x + 1 < w and labels[y - 1, x + 1]:
                nbr.append(int(labels[y - 1, x + 1]))
        if nbr:
            m = min(nbr)
            labels[y, x] = m
            for n in nbr:
                union(m, n)
        else:
            parent.append(len(parent))
            labels[y, x] = len(parent) - 1

    lut = np.array([find(i) for i in range(len(parent))], dtype=np.int32)
    labels = lut[labels]

    roots = np.unique(labels)
    roots = roots[roots > 0]
    remap = np.zeros(int(labels.max()) + 1, dtype=np.int32)
    for i, root in enumerate(roots, start=1):
        remap[int(root)] = i
    labels = remap[labels]
    return labels, len(roots)


# ---------------------------------------------------------------- 轮廓与旋转矩形
def convex_hull(points: np.ndarray) -> np.ndarray:
    """Andrew 单调链求凸包，points 为 Nx2 的像素坐标。"""
    pts = np.unique(points, axis=0)
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in pts[::-1]:
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    hull = np.array(lower[:-1] + upper[:-1], dtype=np.float64)
    return hull if len(hull) >= 3 else pts.astype(np.float64)


def polygon_area(poly: np.ndarray) -> float:
    """鞋带公式，返回绝对值（平方像素）。"""
    if len(poly) < 3:
        return 0.0
    x, y = poly[:, 0], poly[:, 1]
    return abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))) / 2.0


def min_area_rect(hull: np.ndarray) -> dict | None:
    """最小外接矩形：枚举凸包每条边为矩形的边方向，取面积最小者。

    讲义强调：长度取长边、宽度取短边，长轴单位向量统一朝图像下方。
    """
    if len(hull) < 3:
        return None
    best = None
    n = len(hull)
    for i in range(n):
        p, q = hull[i], hull[(i + 1) % n]
        dx, dy = q[0] - p[0], q[1] - p[1]
        norm = math.hypot(dx, dy)
        if norm < 1e-9:
            continue
        ex, ey = dx / norm, dy / norm          # 候选长轴方向
        px, py = -ey, ex                       # 垂直方向
        proj_u = hull[:, 0] * ex + hull[:, 1] * ey
        proj_v = hull[:, 0] * px + hull[:, 1] * py
        u0, u1 = proj_u.min(), proj_u.max()
        v0, v1 = proj_v.min(), proj_v.max()
        area = (u1 - u0) * (v1 - v0)
        if best is None or area < best["area"]:
            best = {"area": area, "ex": ex, "ey": ey, "px": px, "py": py,
                    "u0": u0, "u1": u1, "v0": v0, "v1": v1}

    ex, ey = best["ex"], best["ey"]
    px, py = best["px"], best["py"]
    cu, cv = (best["u0"] + best["u1"]) / 2.0, (best["v0"] + best["v1"]) / 2.0
    cx, cy = cu * ex + cv * px, cu * ey + cv * py

    length = best["u1"] - best["u0"]
    width = best["v1"] - best["v0"]
    axis = np.array([ex, ey], dtype=float)
    if axis[1] < 0:                       # 统一朝下
        axis = -axis
    if length < width:                    # 保证 length 是长边
        length, width = width, length
        axis = np.array([-axis[1], axis[0]])
        if axis[1] < 0:
            axis = -axis

    half_l, half_w = length / 2.0, width / 2.0
    perp = np.array([-axis[1], axis[0]])
    corners = [np.array([cx, cy]) + axis * half_l + perp * half_w,
               np.array([cx, cy]) - axis * half_l + perp * half_w,
               np.array([cx, cy]) - axis * half_l - perp * half_w,
               np.array([cx, cy]) + axis * half_l - perp * half_w]

    tilt = math.degrees(math.atan2(abs(float(axis[0])), abs(float(axis[1]))))
    center = np.array([cx, cy])
    return {
        "center": center, "axis": axis, "length": float(length), "width": float(width),
        "tilt": float(tilt), "corners": corners,
        "top": center - axis * half_l, "bottom": center + axis * half_l,
    }


# ---------------------------------------------------------------- 检测主体
def detect(file_log: list[str], img: np.ndarray) -> dict:
    """跑完整流水线，返回各阶段结果（用于画图和写日志）。"""
    t_all = time.perf_counter()
    t = time.perf_counter()
    gray = bt601_gray(img)
    t_gray = time.perf_counter() - t

    t = time.perf_counter()
    score = color_score(img)
    binary = (score > COLOR_DIFF_THRESH) & (img[..., 0] > TARGET_CHAN_MIN)
    t_thresh = time.perf_counter() - t

    t = time.perf_counter()
    morph = binary.copy()
    if DO_CLOSE:
        morph = close(morph, MORPH_KERNEL)
    if DO_OPEN:
        morph = open_(morph, MORPH_KERNEL)
    t_morph = time.perf_counter() - t

    t = time.perf_counter()
    labels, n_regions = label_components(morph)
    t_cc = time.perf_counter() - t

    t = time.perf_counter()
    bars: list[dict] = []
    rejected: list[dict] = []
    hulls: list[tuple[np.ndarray, int]] = []
    for lb in range(1, n_regions + 1):
        pts = np.argwhere(labels == lb)[:, ::-1].astype(np.float64)  # (x, y)
        if len(pts) < 3:
            rejected.append({"pixels": len(pts), "reason": "像素太少", "area": 0.0})
            continue
        hull = convex_hull(pts)
        hulls.append((hull, lb))
        area = polygon_area(hull)
        rect = min_area_rect(hull)
        if rect is None:
            rejected.append({"pixels": len(pts), "reason": "无法拟合矩形", "area": area})
            continue

        reason = ""
        if area < MIN_CONTOUR_AREA:
            reason = f"轮廓面积 {area:.1f} < {MIN_CONTOUR_AREA:.0f}"
        elif rect["length"] < MIN_BAR_LENGTH:
            reason = f"长度 {rect['length']:.1f} < {MIN_BAR_LENGTH:.0f}"
        elif rect["width"] <= 1e-6 or rect["length"] / rect["width"] < MIN_ASPECT:
            ratio = rect["length"] / max(rect["width"], 1e-6)
            reason = f"长宽比 {ratio:.2f} < {MIN_ASPECT:.1f}"
        elif rect["tilt"] > MAX_TILT_DEG:
            reason = f"倾角 {rect['tilt']:.1f}° > {MAX_TILT_DEG:.0f}°"

        item = {**rect, "area": area, "pixels": len(pts), "label": int(lb)}
        if reason:
            item["reason"] = reason
            rejected.append({"pixels": len(pts), "reason": reason, "area": area,
                             "center": rect["center"]})
        else:
            bars.append(item)
    t_geom = time.perf_counter() - t

    t = time.perf_counter()
    pairs = pair_bars(bars)
    t_pair = time.perf_counter() - t

    total = time.perf_counter() - t_all
    file_log.append("")
    file_log.append("=" * 68)
    file_log.append(f"输入图像尺寸: {img.shape[1]} x {img.shape[0]} (宽 x 高)")
    file_log.append(f"灰度范围: [{gray.min():.1f}, {gray.max():.1f}]，均值 {gray.mean():.2f}")
    file_log.append("")
    file_log.append("[阶段 1] 灰度化")
    file_log.append(f"  用时 {t_gray * 1000:.1f} ms")
    file_log.append("")
    file_log.append("[阶段 2] 颜色差阈值分割")
    file_log.append(f"  红色分数 > {COLOR_DIFF_THRESH} 且 R > {TARGET_CHAN_MIN}")
    only_score = int(np.count_nonzero(score > COLOR_DIFF_THRESH))
    both = int(np.count_nonzero(binary))
    only_gray = int(np.count_nonzero(gray > GRAY_THRESH))
    file_log.append(f"  仅颜色差: {only_score} 像素；加 R 下限后: {both} 像素（筛掉 {only_score - both} 个）")
    file_log.append(f"  对照：仅灰度 > {GRAY_THRESH} 会有 {only_gray} 像素"
                    "（白色灯管也会被算进来，说明亮度不能当唯一条件）")
    file_log.append(f"  用时 {t_thresh * 1000:.1f} ms")
    file_log.append("")
    file_log.append("[阶段 3] 形态学处理")
    file_log.append(f"  3x3 闭运算={'开' if DO_CLOSE else '关'}，3x3 开运算={'开' if DO_OPEN else '关'}"
                    f"；前景 {int(np.count_nonzero(morph))} 像素")
    file_log.append(f"  用时 {t_morph * 1000:.1f} ms")
    file_log.append("")
    file_log.append("[阶段 4] 连通域标记（8 邻域）")
    file_log.append(f"  连通区域数: {n_regions}")
    file_log.append(f"  用时 {t_cc * 1000:.1f} ms")
    file_log.append("")
    file_log.append("[阶段 5] 轮廓 / 最小外接矩形 / 几何筛选")
    file_log.append(f"  通过筛选的灯条: {len(bars)} 根")
    for i, b in enumerate(bars, 1):
        c = b["center"]
        file_log.append(f"    #{i}: 中心 ({c[0]:.1f}, {c[1]:.1f}) 长度 {b['length']:.1f} "
                        f"宽度 {b['width']:.1f} 长宽比 {b['length'] / max(b['width'], 1e-6):.2f} "
                        f"倾角 {b['tilt']:.1f}° 轮廓面积 {b['area']:.1f}")
    if rejected:
        file_log.append(f"  被拒绝的区域 {len(rejected)} 个：")
        for r in rejected:
            extra = ""
            if "center" in r:
                extra = f" 中心 ({r['center'][0]:.1f}, {r['center'][1]:.1f})"
            file_log.append(f"    - {r['reason']}；像素 {r['pixels']}，轮廓面积 {r['area']:.1f}{extra}")
    file_log.append(f"  用时 {t_geom * 1000:.1f} ms")
    file_log.append("")
    file_log.append("[阶段 6] 灯条配对")
    file_log.append(f"  配对条件: 长度比 <= {MAX_LEN_RATIO}；高度差比（沿长轴方向 / 平均长度）"
                    f" <= {MAX_HEIGHT_RATIO}；"
                    f"中心距/平均长度 ∈ [{GAP_RATIO_RANGE[0]}, {GAP_RATIO_RANGE[1]}]；"
                    f"长轴夹角 <= {MAX_ANGLE_DIFF}°")
    file_log.append(f"  候选装甲板: {len(pairs)} 个")
    for i, p in enumerate(pairs, 1):
        a, b = p["bars"]
        file_log.append(f"    #{i}: 长度 {a['length']:.1f} / {b['length']:.1f}"
                        f"（比 {max(a['length'], b['length']) / max(min(a['length'], b['length']), 1e-6):.2f}），"
                        f"高度差比 {p['axial_ratio']:.2f}，"
                        f"间距比 {np.linalg.norm(a['center'] - b['center']) / p['avg_len']:.2f}，"
                        f"夹角 {p['angle_diff']:.1f}°")
        file_log.append("         四点: " + " | ".join(
            f"({pt[0]:.1f}, {pt[1]:.1f})" for pt in p["points"]))
    file_log.append(f"  用时 {t_pair * 1000:.1f} ms")
    file_log.append("")
    file_log.append(f"[总计] {total * 1000:.1f} ms")

    return {"gray": gray, "score": score, "binary": binary, "morph": morph,
            "labels": labels, "n_regions": n_regions, "hulls": hulls,
            "bars": bars, "pairs": pairs, "rejected": rejected}


def pair_bars(bars: list[dict]) -> list[dict]:
    """两两配对：长度接近、高度接近、间距合适、方向接近，且四点围成有效四边形。"""
    pairs: list[dict] = []
    for i in range(len(bars)):
        for j in range(i + 1, len(bars)):
            a, b = bars[i], bars[j]
            if min(a["length"], b["length"]) <= 0:
                continue
            if max(a["length"], b["length"]) / min(a["length"], b["length"]) > MAX_LEN_RATIO:
                continue

            avg_len = (a["length"] + b["length"]) / 2.0
            delta = b["center"] - a["center"]
            mean_axis = a["axis"] + b["axis"]
            mean_axis = mean_axis / max(float(np.linalg.norm(mean_axis)), 1e-9)

            # 讲义里用 |Δy| / 平均长度，那是"灯条竖直"时的写法；
            # 灯条整体倾斜时改用沿长轴方向的分量，竖直情形下两者等价。
            axial = abs(float(np.dot(delta, mean_axis)))
            if axial / avg_len > MAX_HEIGHT_RATIO:
                continue
            dist = float(np.linalg.norm(delta))
            if not (GAP_RATIO_RANGE[0] <= dist / avg_len <= GAP_RATIO_RANGE[1]):
                continue

            dot = float(np.clip(np.dot(a["axis"], b["axis"]), -1.0, 1.0))
            angle_diff = math.degrees(math.acos(dot))
            if angle_diff > MAX_ANGLE_DIFF:
                continue

            left, right = (a, b) if a["center"][0] < b["center"][0] else (b, a)
            points = [left["top"], right["top"], right["bottom"], left["bottom"]]
            if polygon_area(np.array(points)) < MIN_QUAD_AREA:
                continue

            pairs.append({"bars": (left, right), "points": points, "avg_len": avg_len,
                          "angle_diff": angle_diff, "axial_ratio": axial / avg_len})
    return pairs


# ---------------------------------------------------------------- 画图
def to_u8(a: np.ndarray) -> np.ndarray:
    return np.clip(a, 0, 255).astype(np.uint8)


def font(size: int = 16):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def draw_pipeline(img: np.ndarray, res: dict) -> tuple[np.ndarray, np.ndarray]:
    """返回 (04_contours, 05_detected) 两张 RGB 图。"""
    # 04：在掩膜上画每个连通区域的凸包
    cont = Image.fromarray(np.stack([to_u8(res["morph"] * 255)] * 3, axis=-1))
    d = ImageDraw.Draw(cont)
    f = font(15)
    ok_labels = {b["label"] for b in res["bars"]}
    for hull, lb in res["hulls"]:
        ok = lb in ok_labels
        color = (60, 220, 90) if ok else (255, 165, 40)
        pts = [(float(p[0]), float(p[1])) for p in hull]
        if len(pts) >= 2:
            d.line(pts + [pts[0]], fill=color, width=1)
        cx, cy = float(hull[:, 0].mean()), float(hull[:, 1].mean())
        d.text((cx + 4, cy - 6), f"{polygon_area(hull):.0f}", fill=color, font=f)

    # 05：原图叠加
    det = Image.fromarray(to_u8(img))
    d = ImageDraw.Draw(det)
    for b in res["bars"]:
        corners = [(float(p[0]), float(p[1])) for p in b["corners"]]
        d.line(corners + [corners[0]], fill=(0, 255, 90), width=2)

    for p in res["pairs"]:
        pts = [(float(q[0]), float(q[1])) for q in p["points"]]
        d.line(pts + [pts[0]], fill=(255, 200, 0), width=3)
        for idx, (x, y) in enumerate(pts):
            d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(255, 40, 40))
            d.text((x + 6, y - 8), str(idx), fill=(255, 240, 140), font=font(16))
    return np.asarray(cont), np.asarray(det)


def main() -> None:
    ap = argparse.ArgumentParser(description="灯条检测（numpy 复刻版）")
    ap.add_argument("--image", default=str(Path(__file__).resolve().parent / "demo_board.png"))
    ap.add_argument("--out", default=str(RESULTS_DIR))
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    img = load_rgb(Path(args.image))

    log: list[str] = ["# 灯条检测运行日志（Python / numpy 复刻版）",
                      f"# 图像: {Path(args.image).name}",
                      f"# 时间: {time.strftime('%Y-%m-%d %H:%M:%S')}"]

    print("[1/4] 读数并跑流水线 ...")
    res = detect(log, img)

    print("[2/4] 保存中间结果 ...")
    Image.fromarray(to_u8(res["gray"])).save(out_dir / "01_gray.png")
    Image.fromarray(to_u8(res["binary"] * 255)).save(out_dir / "02_binary.png")
    Image.fromarray(to_u8(res["morph"] * 255)).save(out_dir / "03_morph.png")

    print("[3/4] 绘制轮廓与检测结果 ...")
    cont, det = draw_pipeline(img, res)
    Image.fromarray(cont).save(out_dir / "04_contours.png")
    Image.fromarray(det).save(out_dir / "05_detected.png")

    print("[4/4] 写日志 ...")
    (out_dir / "run_log.txt").write_text("\n".join(log) + "\n", encoding="utf-8")

    print(f"  灯条 {len(res['bars'])} 根，配对候选 {len(res['pairs'])} 个，"
          f"连通区域 {res['n_regions']} 个")
    print(f"  结果目录: {out_dir}")


if __name__ == "__main__":
    main()
