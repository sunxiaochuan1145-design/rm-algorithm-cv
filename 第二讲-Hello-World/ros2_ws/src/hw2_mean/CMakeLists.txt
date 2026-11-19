cmake_minimum_required(VERSION 3.16)
project(hw2_mean)

# std::optional 需要 C++17
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(example_interfaces REQUIRED)

# 8.1 的算法做成静态库，两个节点共用（算法与通信分离）
add_library(hw2_cpp_basics STATIC
  src/mean_length.cpp
)
target_include_directories(hw2_cpp_basics PUBLIC
  ${CMAKE_CURRENT_SOURCE_DIR}/include
)

add_executable(length_publisher src/length_publisher.cpp)
ament_target_dependencies(length_publisher rclcpp example_interfaces)
target_link_libraries(length_publisher hw2_cpp_basics)

add_executable(mean_node src/mean_node.cpp)
ament_target_dependencies(mean_node rclcpp example_interfaces)
target_link_libraries(mean_node hw2_cpp_basics)

# ros2 run 只能找到 install 过的可执行文件
install(TARGETS
  length_publisher
  mean_node
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
