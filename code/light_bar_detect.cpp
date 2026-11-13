// 灯条（装甲板两侧 LED）检测练习 —— C++17 + OpenCV 版
//
// 流程（对应讲义第 2 章）：
//   读图 -> 转灰度 -> 颜色差阈值分割 -> 形态学闭运算 -> 连通域/外轮廓
//        -> minAreaRect 几何筛选 -> 灯条两两配对 -> 画图并保存
//
// 编译（Ubuntu 22.04 + OpenCV 4.x）：
//   mkdir -p build && cd build && cmake .. && make -j
//   ./light_bar_detect ../demo_board.png ../results
//
// 说明：讲义主例的二值掩膜并不是单纯"灰度 > 某值"，而是
//   红色分数 = max(R - B, 0) > 阈值 且 R > 下限
// 因为白色灯管在灰度图上也很亮（讲义 2.3.1 的结论），只按亮度筛不出灯条。
// 所以这里灰度图只用于观察（01_gray.png），真正生成掩膜的是颜色差分数。

#include <opencv2/opencv.hpp>

#include <algorithm>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

namespace {

// ---------------------------------------------------------------- 可调参数
// 与 code/light_bar_detect.py 中的常量保持一致，方便两边对照。
constexpr int    kColorDiffThresh = 90;    // 红色分数阈值
constexpr int    kTargetChanMin   = 100;   // 目标通道（R）下限
constexpr int    kMorphKernelSize = 3;     // 3x3 方形结构元素
constexpr bool   kUseClose        = true;  // 基线用闭运算
constexpr bool   kUseOpen         = false; // 开运算会切断细窄灯条，默认关闭

constexpr double kMinContourArea  = 20.0;  // 轮廓面积下限（平方像素）
constexpr double kMinBarLength    = 6.0;   // 灯条长度下限（像素）
constexpr double kMinAspect       = 2.0;   // 长宽比下限
constexpr double kMaxTiltDeg      = 35.0;  // 偏离竖直方向的角度上限

constexpr double kMaxLenRatio     = 1.5;   // 两灯条长度比
constexpr double kMaxHeightRatio  = 0.35;  // 高度差比
constexpr double kMinGapRatio     = 0.8;   // 间距比下限
constexpr double kMaxGapRatio     = 3.2;   // 间距比上限
constexpr double kMaxAngleDiffDeg = 15.0;  // 两长轴夹角上限
constexpr double kMinQuadArea     = 1.0;   // 四点围成四边形面积下限

// ---------------------------------------------------------------- 数据结构
struct LightBar {
    cv::Point2f center;
    cv::Point2f axis;        // 长轴单位向量，统一朝图像下方（y 增大）
    double      length = 0.0; // 长边
    double      width  = 0.0; // 短边
    double      tiltDeg = 0.0; // 长轴偏离竖直方向的角度
    double      contourArea = 0.0;
    cv::Point2f top, bottom;  // 长轴端点（不是两条长边的中点！）
};

struct BarPair {
    int                   left = 0;
    int                   right = 0;
    std::vector<cv::Point2f> points;  // 0 左上 1 右上 2 右下 3 左下
    double                heightRatio = 0.0;
    double                gapRatio = 0.0;
    double                angleDiff = 0.0;
};

// ---------------------------------------------------------------- 工具函数
double length2(const cv::Point2f& v) { return std::sqrt(v.x * v.x + v.y * v.y); }

// 把一条外轮廓变成灯条几何；顺便把轮廓面积填进去。
bool buildBar(const std::vector<cv::Point>& contour, LightBar& bar) {
    if (contour.size() < 3) return false;

    bar.contourArea = std::fabs(cv::contourArea(contour));
    const cv::RotatedRect rr = cv::minAreaRect(contour);

    cv::Point2f pts[4];
    rr.points(pts);

    // 四条边里挑最长的一条，方向即长轴。
    // 这样处理可以绕开 minAreaRect 的 angle 在不同 OpenCV 版本里的语义差异。
    double      bestEdge = 0.0;
    cv::Point2f bestVec(0.0f, 0.0f);
    for (int i = 0; i < 4; ++i) {
        const cv::Point2f d = pts[(i + 1) % 4] - pts[i];
        const double      l = length2(d);
        if (l > bestEdge) {
            bestEdge = l;
            bestVec  = d;
        }
    }
    if (bestEdge < 1e-6) return false;

    cv::Point2f axis(bestVec.x / static_cast<float>(bestEdge),
                     bestVec.y / static_cast<float>(bestEdge));
    if (axis.y < 0.0f) axis = -axis;  // 统一朝下

    bar.axis    = axis;
    bar.length  = std::max(static_cast<double>(rr.size.width), static_cast<double>(rr.size.height));
    bar.width   = std::min(static_cast<double>(rr.size.width), static_cast<double>(rr.size.height));
    bar.center  = rr.center;
    bar.tiltDeg = std::atan2(std::fabs(axis.x), std::fabs(axis.y)) * 180.0 / CV_PI;

    const float half = static_cast<float>(bar.length * 0.5);
    bar.top    = bar.center - axis * half;
    bar.bottom = bar.center + axis * half;
    return true;
}

// 灯条几何筛选，返回拒绝原因（空串表示通过）
std::string checkBar(const LightBar& bar) {
    if (bar.contourArea < kMinContourArea) {
        return "轮廓面积过小";
    }
    if (bar.length < kMinBarLength) {
        return "长度过短";
    }
    if (bar.width <= 1e-6 || bar.length / bar.width < kMinAspect) {
        return "长宽比不足";
    }
    if (bar.tiltDeg > kMaxTiltDeg) {
        return "倾角过大";
    }
    return "";
}

// 两两配对
std::vector<BarPair> pairBars(const std::vector<LightBar>& bars) {
    std::vector<BarPair> pairs;
    for (std::size_t i = 0; i < bars.size(); ++i) {
        for (std::size_t j = i + 1; j < bars.size(); ++j) {
            const LightBar& a = bars[i];
            const LightBar& b = bars[j];
            if (std::min(a.length, b.length) <= 1e-6) continue;

            // 长度接近
            if (std::max(a.length, b.length) / std::min(a.length, b.length) > kMaxLenRatio) continue;

            const double avgLen = (a.length + b.length) * 0.5;
            const cv::Point2f delta = b.center - a.center;
            cv::Point2f meanAxis = a.axis + b.axis;
            const double meanLen = length2(meanAxis);
            if (meanLen < 1e-6) continue;
            meanAxis *= static_cast<float>(1.0 / meanLen);

            // 高度差：讲义写的是 |Δy| / 平均长度，那是灯条竖直时的情形；
            // 灯条整体倾斜时改用"沿长轴方向"的分量，竖直时两者等价。
            const double axial = std::fabs(static_cast<double>(delta.x * meanAxis.x + delta.y * meanAxis.y));
            if (axial / avgLen > kMaxHeightRatio) continue;

            // 间距合适（用平均长度归一化，一定范围内对远近不敏感）
            const double gap = length2(delta);
            if (gap / avgLen < kMinGapRatio || gap / avgLen > kMaxGapRatio) continue;

            // 方向接近
            double dot = static_cast<double>(a.axis.x * b.axis.x + a.axis.y * b.axis.y);
            dot = std::max(-1.0, std::min(1.0, dot));
            const double angleDiff = std::acos(dot) * 180.0 / CV_PI;
            if (angleDiff > kMaxAngleDiffDeg) continue;

            BarPair p;
            p.left  = static_cast<int>(a.center.x < b.center.x ? i : j);
            p.right = static_cast<int>(a.center.x < b.center.x ? j : i);
            const LightBar& l = bars[p.left];
            const LightBar& r = bars[p.right];
            p.points = {l.top, r.top, r.bottom, l.bottom};

            // 四点应围成不退化的凸四边形
            if (std::fabs(cv::contourArea(p.points)) < kMinQuadArea) continue;

            p.heightRatio = axial / avgLen;
            p.gapRatio    = gap / avgLen;
            p.angleDiff   = angleDiff;
            pairs.push_back(p);
        }
    }
    return pairs;
}

void drawRotatedBox(cv::Mat& img, const LightBar& bar, const cv::Scalar& color) {
    const cv::Point2f perp(-bar.axis.y, bar.axis.x);
    const float hl = static_cast<float>(bar.length * 0.5);
    const float hw = static_cast<float>(bar.width * 0.5);
    cv::Point2f c[4] = {
        bar.center + bar.axis * hl + perp * hw,
        bar.center + bar.axis * hl - perp * hw,
        bar.center - bar.axis * hl - perp * hw,
        bar.center - bar.axis * hl + perp * hw,
    };
    for (int i = 0; i < 4; ++i) {
        cv::line(img, c[i], c[(i + 1) % 4], color, 2, cv::LINE_AA);
    }
}

std::string fmt(double v, int prec = 2) {
    std::ostringstream os;
    os << std::fixed << std::setprecision(prec) << v;
    return os.str();
}

}  // namespace

int main(int argc, char** argv) {
    const std::string inPath  = (argc > 1) ? argv[1] : "demo_board.png";
    const std::string outDir  = (argc > 2) ? argv[2] : "../results";

    cv::Mat src = cv::imread(inPath, cv::IMREAD_COLOR);
    if (src.empty()) {
        std::cerr << "读不到图片: " << inPath << std::endl;
        return 1;
    }
    cv::Mat gray;
    cv::cvtColor(src, gray, cv::COLOR_BGR2GRAY);

    // ---- 颜色差分数：注意 OpenCV 读进来是 BGR，R 在通道 2
    std::vector<cv::Mat> ch;
    cv::split(src, ch);
    cv::Mat diff;
    cv::subtract(ch[2], ch[0], diff);  // R - B，8 位无符号会饱和到 0

    cv::Mat mDiff, mChan, mask;
    cv::threshold(diff, mDiff, kColorDiffThresh, 255, cv::THRESH_BINARY);
    cv::threshold(ch[2], mChan, kTargetChanMin, 255, cv::THRESH_BINARY);
    cv::bitwise_and(mDiff, mChan, mask);

    // ---- 形态学：闭运算补缺口，开运算去小碎块（可选）
    const cv::Mat kernel = cv::getStructuringElement(
        cv::MORPH_RECT, cv::Size(kMorphKernelSize, kMorphKernelSize));
    cv::Mat morph = mask.clone();
    if (kUseClose) cv::morphologyEx(morph, morph, cv::MORPH_CLOSE, kernel);
    if (kUseOpen)  cv::morphologyEx(morph, morph, cv::MORPH_OPEN, kernel);

    // ---- 外轮廓 + 几何筛选
    std::vector<std::vector<cv::Point>> contours;
    cv::findContours(morph, contours, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_SIMPLE);

    std::vector<LightBar> bars;
    int rejected = 0;
    for (const auto& c : contours) {
        LightBar bar;
        if (!buildBar(c, bar)) {
            ++rejected;
            continue;
        }
        const std::string why = checkBar(bar);
        if (why.empty()) {
            bars.push_back(bar);
        } else {
            ++rejected;
            std::cout << "  [拒绝] " << why << "  中心=(" << fmt(bar.center.x, 1) << ", "
                      << fmt(bar.center.y, 1) << ") 长=" << fmt(bar.length, 1)
                      << " 宽=" << fmt(bar.width, 1) << std::endl;
        }
    }

    std::vector<BarPair> pairs = pairBars(bars);

    // ---- 输出统计
    std::cout << "图像: " << inPath << "  (" << src.cols << " x " << src.rows << ")\n";
    std::cout << "外轮廓: " << contours.size() << "  通过几何筛选的灯条: " << bars.size()
              << "  被拒绝: " << rejected << "\n";
    for (std::size_t i = 0; i < bars.size(); ++i) {
        const LightBar& b = bars[i];
        std::cout << "  灯条 #" << (i + 1) << ": 中心=(" << fmt(b.center.x, 1) << ", "
                  << fmt(b.center.y, 1) << ") 长度=" << fmt(b.length, 1)
                  << " 宽度=" << fmt(b.width, 1)
                  << " 长宽比=" << fmt(b.length / std::max(b.width, 1e-6), 2)
                  << " 倾角=" << fmt(b.tiltDeg, 1) << "°" << std::endl;
    }
    std::cout << "配对候选: " << pairs.size() << "\n";
    for (std::size_t i = 0; i < pairs.size(); ++i) {
        const BarPair& p = pairs[i];
        std::cout << "  候选 #" << (i + 1) << ": 高度差比=" << fmt(p.heightRatio)
                  << " 间距比=" << fmt(p.gapRatio) << " 夹角=" << fmt(p.angleDiff, 1) << "°\n";
        std::cout << "         四点: ";
        for (const auto& pt : p.points) {
            std::cout << "(" << fmt(pt.x, 1) << ", " << fmt(pt.y, 1) << ") ";
        }
        std::cout << std::endl;
    }

    // ---- 画图：灯条（绿）+ 配对四边形与四点编号（橙/红）
    cv::Mat vis = src.clone();
    for (const auto& b : bars) {
        drawRotatedBox(vis, b, cv::Scalar(0, 255, 90));
    }
    for (const auto& p : pairs) {
        for (std::size_t k = 0; k < p.points.size(); ++k) {
            cv::line(vis, p.points[k], p.points[(k + 1) % p.points.size()],
                     cv::Scalar(0, 200, 255), 3, cv::LINE_AA);
        }
        for (std::size_t k = 0; k < p.points.size(); ++k) {
            cv::circle(vis, cv::Point(cvRound(p.points[k].x), cvRound(p.points[k].y)), 4,
                       cv::Scalar(40, 40, 255), -1, cv::LINE_AA);
            cv::putText(vis, std::to_string(k),
                        cv::Point(cvRound(p.points[k].x) + 6, cvRound(p.points[k].y) - 6),
                        cv::FONT_HERSHEY_SIMPLEX, 0.5, cv::Scalar(140, 240, 255), 1, cv::LINE_AA);
        }
    }

    // ---- 保存
    cv::imwrite(outDir + "/01_gray.png", gray);
    cv::imwrite(outDir + "/02_binary.png", mask);
    cv::imwrite(outDir + "/03_morph.png", morph);
    cv::imwrite(outDir + "/05_detected.png", vis);

    // 04：在掩膜上画出保留下来的外轮廓
    cv::Mat contourVis;
    cv::cvtColor(morph, contourVis, cv::COLOR_GRAY2BGR);
    cv::drawContours(contourVis, contours, -1, cv::Scalar(0, 220, 90), 1, cv::LINE_AA);
    for (const auto& b : bars) {
        cv::circle(contourVis, cv::Point(cvRound(b.center.x), cvRound(b.center.y)), 3,
                   cv::Scalar(0, 200, 255), -1, cv::LINE_AA);
    }
    cv::imwrite(outDir + "/04_contours.png", contourVis);

    std::cout << "结果已写入 " << outDir << "/" << std::endl;
    return 0;
}
