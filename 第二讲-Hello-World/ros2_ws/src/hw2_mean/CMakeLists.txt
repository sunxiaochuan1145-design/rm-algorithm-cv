cmake_minimum_required(VERSION 3.16)
project(hw2_mean)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(example_interfaces REQUIRED)

add_executable(length_publisher src/length_publisher.cpp)
ament_target_dependencies(length_publisher rclcpp example_interfaces)

# mean_node 要用 8.1 的 meanLength，所以把 mean_length.cpp 一起编译
add_executable(mean_node src/mean_node.cpp src/mean_length.cpp)
ament_target_dependencies(mean_node rclcpp example_interfaces)
target_include_directories(mean_node PRIVATE include)

install(TARGETS
  length_publisher
  mean_node
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
