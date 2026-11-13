# 上传清单（GitHub 网页端逐个建文件用）

> 说明：按下面的顺序在 GitHub 网页端新建文件 / 上传文件，一次提交一个或一小批，commit message 直接抄「建议 commit message」列。
> `README.md` 排第一：先把仓库门面立起来，后面提交链接才有地方指。
> 图片（`.png`）不要用「新建文件 + 粘贴」的方式，走 *Add file → Upload files* 或者拖拽上传。

| 顺序 | 文件路径 | 建议 commit message | 大致行数 |
| :--: | --- | --- | --- |
| 1 | `README.md` | `docs: 添加仓库说明、第一讲知识地图与运行说明` | 187 |
| 2 | `.gitignore` | `chore: 忽略构建产物、缓存与 IDE 配置` | 38 |
| 3 | `notes/01-computer-vision.md` | `docs(notes): 第一讲 计算机视觉 学习笔记` | 200 |
| 4 | `docs/upload_manifest.md` | `docs: 添加文件上传顺序清单` | 30 |
| 5 | `code/make_demo_image.py` | `feat(code): 添加模拟装甲板测试图生成脚本` | 258 |
| 6 | `code/demo_board.png` | `test(code): 添加模拟测试图 demo_board.png` | 图片（1280×1024） |
| 7 | `code/light_bar_detect.py` | `feat(code): 添加 numpy/Pillow 版灯条检测流水线` | 506 |
| 8 | `code/light_bar_detect.cpp` | `feat(code): 添加 OpenCV 版灯条检测` | 320 |
| 9 | `code/CMakeLists.txt` | `build(code): 添加 CMake 构建脚本` | 27 |
| 10 | `results/01_gray.png` | `test(results): 添加灰度化结果` | 图片（1280×1024） |
| 11 | `results/02_binary.png` | `test(results): 添加颜色差掩膜结果` | 图片（1280×1024） |
| 12 | `results/03_morph.png` | `test(results): 添加形态学闭运算结果` | 图片（1280×1024） |
| 13 | `results/04_contours.png` | `test(results): 添加外轮廓与几何筛选结果` | 图片（1280×1024） |
| 14 | `results/05_detected.png` | `test(results): 添加最终检测结果` | 图片（1280×1024） |
| 15 | `results/run_log.txt` | `test(results): 添加运行日志与各阶段候选数量` | 45 |

## 提交备注

- 第 1 步提交完，仓库首页就会有知识地图；第 3 步之后笔记链接才不 404。
- 图片共 6 张，总计约 3 MB，网页端上传一次别塞太多，分两批比较稳。
- `results/` 里的 5 张图是 Python 版跑出来的；装上 OpenCV 后用 C++ 版重跑会覆盖同名文件，内容基本一致（`04_contours.png` 的画法略有差异）。
- 所有行数按当前文件实际统计，改完内容记得回来更新这一列。
