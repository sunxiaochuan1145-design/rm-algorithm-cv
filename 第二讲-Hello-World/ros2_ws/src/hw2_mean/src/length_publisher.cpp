#include <chrono>
#include <functional>
#include <memory>
#include <vector>

#include "example_interfaces/msg/float64_multi_array.hpp"
#include "rclcpp/rclcpp.hpp"

using namespace std::chrono_literals;

class LengthPublisher : public rclcpp::Node
{
public:
    LengthPublisher() : Node("length_publisher"), index_(0)
    {
        publisher_ = this->create_publisher<example_interfaces::msg::Float64MultiArray>("lengths", 10);
        timer_ = this->create_wall_timer(1s, std::bind(&LengthPublisher::timer_callback, this));
    }

private:
    void timer_callback()
    {
        // 三组数据轮流发，最后一组是空数组
        std::vector<std::vector<double>> groups;
        groups.push_back({40.0, 60.0, 80.0});
        groups.push_back({10.0, 20.0});
        groups.push_back({});

        std::size_t n = index_ % groups.size();

        example_interfaces::msg::Float64MultiArray msg;
        msg.data = groups[n];

        RCLCPP_INFO(this->get_logger(), "发布第 %zu 组，%zu 个数", n + 1, msg.data.size());
        publisher_->publish(msg);

        index_++;
    }

    rclcpp::Publisher<example_interfaces::msg::Float64MultiArray>::SharedPtr publisher_;
    rclcpp::TimerBase::SharedPtr timer_;
    std::size_t index_;
};

int main(int argc, char * argv[])
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<LengthPublisher>());
    rclcpp::shutdown();
    return 0;
}
