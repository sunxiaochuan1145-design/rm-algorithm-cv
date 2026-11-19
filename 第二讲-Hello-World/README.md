# 第二讲作业：C++ 均值库 + ROS 2 发布/订阅

本仓库是第二讲作业（8.1 / 8.2 / 8.3）的完整实现，只有一个目的：**用一个小工程把"C++ 库 + CMake + ROS 2 节点 + 话题通信"串起来**。

- 8.1：`meanLength`（空数组返回 `std::nullopt`）与 `countAtLeast`（不小于阈值的个数），声明在 `include/`、定义在 `src/`、编成静态库；`cpp_lab` 测试程序链接该库，任何用例失败时进程返回非零值。
- 8.2：`length_publisher` 每秒发布一组长度（三组轮流，其中一组是空数组）；`mean_node` 订阅这些长度、调用 8.1 的 `meanLength`、把均值发布到另一个话题，收到空数组时只打印日志不发布。
- 8.3：源码 + README（本文件），仓库里不含 `build/` 等构建产物。

---

## 1. 目录结构

```
hw2/
├── cpp_basics/                         # 8.1 独立的 CMake 工程
│   ├── CMakeLists.txt
│   ├── include/cpp_basics/mean_length.hpp   # 声明（只放函数原型）
│   ├── src/mean_length.cpp                  # 定义：均值 + 空数组处理
│   ├── src/count_at_least.cpp               # 定义：不小于阈值的计数
│   └── src/cpp_lab.cpp                      # 带 main 的测试程序
├── ros2_ws/                            # 8.2 的 colcon 工作空间
│   └── src/hw2_mean/
│       ├── package.xml
│       ├── CMakeLists.txt
│       ├── include/hw2_mean/mean_length.hpp # 8.1 的声明复制进包
│       ├── include/hw2_mean/topics.hpp      # 话题名集中在这里
│       └── src/mean_length.cpp              # 8.1 的定义复制进包
│       └── src/length_publisher.cpp         # 发布节点
│       └── src/mean_node.cpp                # 均值节点
└── README.md
```

`cpp_basics` 与 `ros2_ws` 是两个独立工程：8.1 用 CMake 直接构建，8.2 的包交给 colcon 构建；ROS 包里复制了一份 8.1 的代码，这样 `ros2 run` 时不需要额外安装一个库包（作业允许"算法与通信分开"，但共享方式可以自选）。

---

## 2. 环境要求

- Ubuntu 22.04 + ROS 2 Humble（`/opt/ros/humble`），已安装 `rclcpp`、`example_interfaces`
- `g++`（支持 C++17）、`cmake` ≥ 3.16、`colcon`（`python3-colcon-common-extensions`）
- 检查：

```bash
g++ --version | head -1
cmake --version | head -1
ls /opt/ros/humble/setup.bash
ros2 pkg prefix example_interfaces
```

---

## 3. 构建与运行命令

### 3.1 8.1 的 C++ 工程

```bash
cd cpp_basics
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug   # 配置
cmake --build build --parallel                 # 编译 + 链接库和 cpp_lab
./build/cpp_lab                                # 跑测试
echo $?                                        # 0 = 全部通过
```

实测输出（10 个用例全部 PASS，退出码 0）：

```
== meanLength ==
[PASS] 空数组 -> nullopt
[PASS] 40/60/80 均值 60
[PASS] 单元素均值 5
[PASS] {-5,5} 均值 0（合法的 0）
[PASS] 60/61/62 均值 61
== countAtLeast ==
[PASS] 阈值 60：恰好等于的 60 要算进去 -> 2
[PASS] 阈值 40：全部不小于 -> 3
[PASS] 阈值 100：一个都没有 -> 0
[PASS] 空数组 -> 0
[PASS] 全部恰好等于阈值 -> 3

ALL TESTS PASSED
```

故意写坏一个结果（把期望值改错）时，程序会打印 `[FAIL]` 并 `return 1`，`echo $?` 得到 1 —— 这就是"结果不对时返回非零值"。

### 3.2 8.2 的 ROS 2 包

**每个终端都先执行**（避免收到别人节点的数据）：

```bash
export ROS_LOCALHOST_ONLY=1
source /opt/ros/humble/setup.bash
```

终端 A（构建）：

```bash
cd hw2/ros2_ws
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Debug
source install/setup.bash
```

终端 B（发布节点）：

```bash
source /opt/ros/humble/setup.bash
cd hw2/ros2_ws && source install/setup.bash
export ROS_LOCALHOST_ONLY=1
ros2 run hw2_mean length_publisher
```

终端 C（均值节点）：

```bash
source /opt/ros/humble/setup.bash
cd hw2/ros2_ws && source install/setup.bash
export ROS_LOCALHOST_ONLY=1
ros2 run hw2_mean mean_node
```

终端 D（观察结果）：

```bash
ros2 topic list                      # 看到 /lengths 和 /mean_length
ros2 node list                       # /length_publisher 和 /mean_node
ros2 topic echo /lengths             # 看三组数据轮流出现
ros2 topic echo /mean_length --field data   # 60.0 / 15.0 / (2 秒空档) / 60.0 ...
ros2 topic hz /lengths               # ≈ 1.000 Hz
ros2 topic hz /mean_length           # ≈ 0.667 Hz
```

实测的 `ros2 topic hz` 输出：

```
average rate: 1.000        # /lengths
average rate: 0.666        # /mean_length（3 条发 2 条，空数组那条不发）
```

---

## 4. 节点、话题、消息类型一览

| 节点名 | 可执行文件 | 订阅 | 发布 |
| --- | --- | --- | --- |
| `length_publisher` | `hw2_mean/length_publisher` | 无 | `/lengths`，`example_interfaces/msg/Float64MultiArray` |
| `mean_node` | `hw2_mean/mean_node` | `/lengths`，`Float64MultiArray` | `/mean_length`，`example_interfaces/msg/Float64` |

- `Float64MultiArray` 字段：`layout`（`MultiArrayLayout`，本作业不用）与 `data`（`float64[]`），长度数组就放在 `data` 里。
- `Float64` 字段：`float64 data`，均值放在这里。
- 两个节点都用默认 QoS：`keep last` / `depth 10` / `reliable` / `volatile`，所以能正常配对。
- 话题名定义在 `include/hw2_mean/topics.hpp` 的两个常量里，两个节点都引用它，改名字只改一处。

---

## 5. 每组输入对应的输出（实际运行核对）

| 第 N 组 | 发布节点发出（`/lengths.data`） | 均值节点日志 | `/mean_length` 上看到 |
| --- | --- | --- | --- |
| 1 | `[40, 60, 80]` | `收到 3 个长度，均值 = 60.0，已发布到 mean_length` | `60.0` |
| 2 | `[10, 20]` | `收到 2 个长度，均值 = 15.0，已发布到 mean_length` | `15.0` |
| 3 | `[ ]`（空数组） | `收到空数组，跳过发布`（WARN） | **没有消息**（约 2 秒空档） |
| 4 | `[40, 60, 80]` | 同第 1 行 | `60.0` |

实际日志（节选）：

```
[length_publisher] 第 1 组：发布 3 个长度 [40, 60, 80]
[length_publisher] 第 2 组：发布 2 个长度 [10, 20]
[length_publisher] 第 3 组：发布 0 个长度 [空数组]
[mean_node] 收到 3 个长度，均值 = 60.0，已发布到 mean_length
[mean_node] 收到 2 个长度，均值 = 15.0，已发布到 mean_length
[mean_node] 收到空数组，跳过发布
```

所以 `/mean_length` 上的序列是 `60.0, 15.0, 60.0, 15.0, ...`，两条之间有时 1 秒、有时 2 秒——**空数组那一条被跳过，所以平均频率不是 1 Hz 而是 0.667 Hz**。这正是"空数组不发布"的直接证据。

---

## 6. 为什么空数组的均值不能返回 0

1. **0 是合法结果，无法和"没有数据"区分。** 例如 `{-5, 5}` 的均值就是 0，如果空数组也返回 0，调用方无法判断"均值是 0"还是"根本没有数据"。
2. **0/0 在浮点里是 `nan`（not a number），而 nan 会传染。** 一旦把它带进后续计算，`nan + 1` 仍是 `nan`，比较永远为 false，错误会静默扩散到最后一步才暴露。
3. **业务上"没有检测到灯条"和"灯条长度均值为 0 像素"是两件事。** 前者应该跳过这一帧，后者应该报警或按 0 处理，混在一起会让控制逻辑做出错误决策。
4. **C++ 用 `std::optional<double>` 表达"可能有、也可能没有"。** 空数组返回 `std::nullopt`，调用方必须写 `if (!mean.has_value())` 显式处理，编译器不会让你无意中把"没有结果"当数字用。ROS 节点在 `nullopt` 时只打 WARN、不发布，也就不会向下游发送 0 或重发上一次的结果（重发会让下游误以为有新的测量值）。

---

## 7. 遇到的问题与解决方案

| 问题 | 原因 | 解决 |
| --- | --- | --- |
| `std::optional` 找不到 / 编译报 `std::optional is not a member` | 默认只到 C++14 | 两个工程都设置 `CMAKE_CXX_STANDARD 17` |
| 均值为 0 或小数被吞 | `sum / lengths.size()` 里 `size()` 是整数，整数除法会截断 | 先 `static_cast<double>(lengths.size())` 再除 |
| 测试里浮点数比较偶尔失败 | 二进制浮点无法精确表示 | 用 `std::fabs(a - b) < 1e-9` 而不是 `==` |
| `fatal error: cpp_basics/mean_length.hpp: No such file` | 头文件目录没告诉编译器 | `target_include_directories(hw2_cpp_basics PUBLIC include)`，并让可执行文件链接这个库 |
| 链接报 `undefined reference to meanLength` | 定义所在的 `.cpp` 没进 `add_library` | 把 `src/mean_length.cpp`、`src/count_at_least.cpp` 都列进库的源文件 |
| `ros2 run hw2_mean length_publisher` 报找不到可执行文件 | 没安装 / 没 source 工作空间 | 必须有 `install(TARGETS ... DESTINATION lib/${PROJECT_NAME})`，并 `source install/setup.bash` |
| 均值节点收不到消息 | 话题名拼错、类型或 QoS 不匹配、订阅者被销毁、没在 spin | 两个节点都用 `topics.hpp` 的常量；检查 `ros2 topic info -v`；订阅者保存在成员变量里；`rclcpp::spin()` 持续运行 |
| 别人的节点数据混进来 | 同网段多个 ROS 2 用户共享 DDS 域 | 每个终端 `export ROS_LOCALHOST_ONLY=1` |
| `ament_target_dependencies` 之后又 `target_link_libraries` 会不会冲突 | 前者加 ROS 依赖，后者加自己的静态库，二者不冲突 | 保持顺序：先 `ament_target_dependencies`，再 `target_link_libraries(节点 hw2_cpp_basics)` |
| 改代码每次都要重新 `colcon build` | 普通安装是拷贝 | 用 `--symlink-install` 加速（改 CMakeLists 时仍需重新 build） |

---

## 8. 现场检查（会要求改一条计算规则或一个话题名）

所有可能的现场改动、对应文件行号、改完怎么验证，都写在 [答辩速查.md](答辩速查.md) 里，包括：

- 改话题名：`ros2_ws/src/hw2_mean/include/hw2_mean/topics.hpp:9` 与 `:12`
- 改发布频率：`ros2_ws/src/hw2_mean/src/length_publisher.cpp:33`
- 改数据组：`length_publisher.cpp:26-30`
- 改计算规则（例：均值 → 中位数）：`cpp_basics/src/mean_length.cpp:3-16`（ROS 包里的副本同步改），现有测试用例仍然全部成立
- 改阈值：`cpp_basics/src/cpp_lab.cpp:55`
