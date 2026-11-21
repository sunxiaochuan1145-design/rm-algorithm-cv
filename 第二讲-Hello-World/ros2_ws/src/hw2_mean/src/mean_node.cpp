#include <functional>
#include <memory>

#include "example_interfaces/msg/float64.hpp"
#include "example_interfaces/msg/float64_multi_array.hpp"
#include "rclcpp/rclcpp.hpp"

#include "hw2_mean/mean_length.hpp"

class MeanNode : public rclcpp::Node
{
public:
    MeanNode() : Node("mean_node")
    {
        pub_ = this->create_publisher<example_interfaces::msg::Float64>("mean_length", 10);
        sub_ = this->create_subscription<example_interfaces::msg::Float64MultiArray>(
            "lengths", 10, std::bind(&MeanNode::on_lengths, this, std::placeholders::_1));
    }

private:
    void on_lengths(const example_interfaces::msg::Float64MultiArray & msg)
    {
        std::optional<double> mean = meanLength(msg.data);

        // 空数组没有均值，只打日志，不发布
        if (!mean.has_value())
        {
            RCLCPP_WARN(this->get_logger(), "收到空数组，跳过发布");
            return;
        }

        example_interfaces::msg::Float64 out;
        out.data = *mean;
        pub_->publish(out);

        RCLCPP_INFO(this->get_logger(), "收到 %zu 个数，均值 %.1f", msg.data.size(), out.data);
    }

    rclcpp::Publisher<example_interfaces::msg::Float64>::SharedPtr pub_;
    rclcpp::Subscription<example_interfaces::msg::Float64MultiArray>::SharedPtr sub_;
};

int main(int argc, char * argv[])
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<MeanNode>());
    rclcpp::shutdown();
    return 0;
}
