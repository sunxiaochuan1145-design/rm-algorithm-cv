#include <functional>
#include <memory>

#include "example_interfaces/msg/float64.hpp"
#include "example_interfaces/msg/float64_multi_array.hpp"
#include "rclcpp/rclcpp.hpp"

#include "hw2_mean/mean_length.hpp"  // 8.1 的 meanLength
#include "hw2_mean/topics.hpp"

class MeanNode : public rclcpp::Node
{
public:
  MeanNode()
  : Node("mean_node")
  {
    // 算法结果 -> 发布到 mean_length（Float64）
    publisher_ = this->create_publisher<example_interfaces::msg::Float64>(
      hw2_topics::kMeanLength, 10);

    // 订阅 lengths（Float64MultiArray），回调里调 meanLength
    subscription_ = this->create_subscription<example_interfaces::msg::Float64MultiArray>(
      hw2_topics::kLengths, 10,
      std::bind(&MeanNode::lengths_callback, this, std::placeholders::_1));
  }

private:
  void lengths_callback(const example_interfaces::msg::Float64MultiArray & message)
  {
    const std::optional<double> mean = meanLength(message.data);

    if (!mean.has_value()) {
      // 没有数据就没有结果：只打日志，不发布，更不发布 0 或上一次的值
      RCLCPP_WARN(this->get_logger(), "收到空数组，跳过发布");
      return;
    }

    example_interfaces::msg::Float64 out;
    out.data = *mean;  // optional 里有值时才用 *mean 取出来
    publisher_->publish(out);

    RCLCPP_INFO(
      this->get_logger(), "收到 %zu 个长度，均值 = %.1f，已发布到 %s",
      message.data.size(), out.data, hw2_topics::kMeanLength);
  }

  rclcpp::Publisher<example_interfaces::msg::Float64>::SharedPtr publisher_;
  rclcpp::Subscription<example_interfaces::msg::Float64MultiArray>::SharedPtr subscription_;
};

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<MeanNode>());
  rclcpp::shutdown();
  return 0;
}
