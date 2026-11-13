# 灯条检测练习的构建脚本
# 用法：
#   mkdir -p build && cd build
#   cmake .. && make -j
#   ./light_bar_detect ../demo_board.png ../results

cmake_minimum_required(VERSION 3.16)

project(light_bar_detect LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# 没特别要求优化等级时，默认用 -O2
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

find_package(OpenCV REQUIRED)

add_executable(light_bar_detect light_bar_detect.cpp)
target_link_libraries(light_bar_detect PRIVATE ${OpenCV_LIBS})
target_include_directories(light_bar_detect PRIVATE ${OpenCV_INCLUDE_DIRS})

# 让 g++ 把常见的手滑都报出来，学习阶段很有用
target_compile_options(light_bar_detect PRIVATE -Wall -Wextra)
