cmake_minimum_required(VERSION 3.16)
project(hw2_cpp_basics CXX)

# std::optional 是 C++17 才有的
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 两个算法编成静态库
add_library(basics STATIC
    src/mean_length.cpp
    src/count_at_least.cpp
)

# 这样链接库的程序能找到 include 下的头文件
target_include_directories(basics PUBLIC include)

# 带 main 的测试程序
add_executable(cpp_lab src/cpp_lab.cpp)
target_link_libraries(cpp_lab basics)
