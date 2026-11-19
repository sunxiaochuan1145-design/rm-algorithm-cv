#include <chrono>
#include <functional>
#include <memory>
#include <string>
#include <vector>

#include "example_interfaces/msg/float64_multi_array.hpp"
#include "rclcpp/rclcpp.hpp"

#include "hw2_mean/topics.hpp"

using namespace std::chrono_literals;

class LengthPublisher : public rclcpp::Node
{
public:
  LengthPublisher()
  : Node("length_publisher"), index_(0)
  {
    // 话题名来自 topics.hpp，消息类型是 Float64MultiArray
    publisher_ = this->create_publisher<example_interfaces::msg::Float64MultiArray>(
      hw2_topics::kLengths, 10);

    // 三组数据轮流发：第 1、2 组有数据，第 3 组是空数组
    // （模拟“这一帧画面里没看到灯条”，不是错误）
    groups_ = {
      {40.0, 60.0, 80.0},
      {10.0, 20.0},
      {},
    };

    // 每秒发一组
    timer_ = this->create_wall_timer(1s, std::bind(&LengthPublisher::timer_callback, this));
  }

private:
  void timer_callback()
  {
    const std::size_t group_index = index_ % groups_.size();
    const std::vector<double> & lengths = groups_[group_index];

    example_interfaces::msg::Float64MultiArray message;
    message.data = lengths;  // 空组就是空数组，也是一条合法消息

    // 把数组内容拼成 [40, 60, 80] 这种形式打印出来，方便对照检查
    std::string text;
    for (std::size_t i = 0; i < message.data.size(); ++i) {
      if (i > 0) {
        text += ", ";
      }
      text += std::to_string(static_cast<long>(message.data[i]));
    }
    if (text.empty()) {
      text = "空数组";
    }

    RCLCPP_INFO(
      this->get_logger(), "第 %zu 组：发布 %zu 个长度 [%s]",
      index_ + 1, message.data.size(), text.c_str());
    publisher_->publish(message);

    ++index_;
  }

  rclcpp::Publisher<example_interfaces::msg::Float64MultiArray>::SharedPtr publisher_;
  rclcpp::TimerBase::SharedPtr timer_;
  std::vector<std::vector<double>> groups_;
  std::size_t index_;
};

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<LengthPublisher>());
  rclcpp::shutdown();
  return 0;
}
