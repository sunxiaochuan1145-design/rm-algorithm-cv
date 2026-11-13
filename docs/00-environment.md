# 开发环境准备

按讲义 4.1 的要求，把「C++ + OpenCV」和「ROS2 Humble」两套环境准备好。这里记录我在自己机器上实际用的步骤和验证命令，换机器时按顺序来一遍即可。

---

## 1. 基础工具链（C++ / CMake / git）

```bash
sudo apt update
sudo apt install -y build-essential g++ cmake git pkg-config
```

验证：

```bash
g++ --version          # 需要 C++17 支持（g++ 9 及以上）
cmake --version        # 3.16 及以上即可
git --version
```

写 CMakeLists 时注意两件事：`set(CMAKE_CXX_STANDARD 17)`、以及用 `find_package(OpenCV REQUIRED)` 而不是手写 include 路径。

---

## 2. OpenCV 开发库

最省事的是发行版打包版：

```bash
sudo apt install -y libopencv-dev
pkg-config --modversion opencv4     # 打印版本号即成功
```

如果讲义要求某个特定版本（或者要用 `cv::cuda` 之类打包版没开的模块），才需要源码编译；源码编译时记得只打开用得到的模块，否则一次要编半小时以上，而且内存吃紧的机器容易 OOM。

> Windows 上的替代路线：官方 prebuilt 的 `opencv-4.x.x-windows.exe` 解压后把 `build\x64\vc16\bin` 加进 `PATH`，CMake 里用 `-DOpenCV_DIR=<...>\build` 指定。

---

## 3. ROS2 Humble

Humble 对应 Ubuntu 22.04。安装方式按「鱼香ROS」的一键脚本走（讲义推荐的教程），本质是配好 apt 源再装桌面版：

```bash
# 参考 https://fishros.org.cn 的安装脚本，注意别把不同发行版的源混用
source /opt/ros/humble/setup.bash
ros2 --help
```

每个新终端都要 `source`，不想每次都敲就把这行写进 `~/.bashrc`。

---

## 4. 跑通本仓库的练习

```bash
# 纯 Python 版（只要 numpy + Pillow，任何平台都能跑）
python code/make_demo_image.py --out code/demo_board.png
python code/light_bar_detect.py --image code/demo_board.png --out results

# C++ 版（需要 OpenCV 开发库）
cd code && mkdir -p build && cd build
cmake .. && make -j
./light_bar_detect ../demo_board.png ../../results
```

`results/` 下的 5 张图就是这条流水线各阶段的输出，`run_log.txt` 里是每次运行打印的数量统计。

---

## 5. 踩过的坑

- **`find_package(OpenCV)` 找不到**：多半是没装 `libopencv-dev`，或者装了但 CMake 版本太老不认 `OpenCV_DIR`。先 `pkg-config --modversion opencv4` 确认库在不在。
- **链接期 `undefined reference to cv::imread`**：CMakeLists 里漏了 `target_link_libraries(... ${OpenCV_LIBS})`。
- **编译能过、运行报 `error while loading shared libraries: libopencv_core.so.4xx`**：装的是源码版而没跑 `sudo ldconfig`，或者 `LD_LIBRARY_PATH` 没指过去。
- **`source /opt/ros/humble/setup.bash` 之后 OpenCV 版本变了**：ROS 自带的 OpenCV 可能和系统版本冲突，`pkg-config` 与 `cv::getBuildInformation()` 各看一遍再排查。
