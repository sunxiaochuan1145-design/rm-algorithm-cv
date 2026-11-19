#pragma once

// 话题名集中放在这里：检查时如果要求“改一个话题名”，只改这两行即可。
// 两个节点都 include 本文件，所以绝不会改漏一处导致对不上。
namespace hw2_topics
{

// 发布节点 -> 均值节点：一组灯条长度（example_interfaces/msg/Float64MultiArray）
constexpr const char * kLengths = "lengths";

// 均值节点 -> 外部：算出来的均值（example_interfaces/msg/Float64）
constexpr const char * kMeanLength = "mean_length";

}  // namespace hw2_topics
