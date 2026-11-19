cmake_minimum_required(VERSION 3.16)
project(hw2_cpp_basics LANGUAGES CXX)

# 8.1 要求用到 std::optional，所以必须 C++17
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# 算法编成静态库：声明在 include/，定义在 src/
add_library(hw2_cpp_basics STATIC
  src/mean_length.cpp
  src/count_at_least.cpp
)
# PUBLIC：链接这个库的人自动能用 include/ 下的头文件
target_include_directories(hw2_cpp_basics PUBLIC
  ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# 带 main 的测试程序，链接上面的库
add_executable(cpp_lab src/cpp_lab.cpp)
target_link_libraries(cpp_lab PRIVATE hw2_cpp_basics)
