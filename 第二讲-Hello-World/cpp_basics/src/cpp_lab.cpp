#include <cmath>
#include <cstddef>
#include <iostream>
#include <optional>
#include <string>
#include <vector>

#include "cpp_basics/mean_length.hpp"

namespace
{

int failures = 0;

constexpr double kEpsilon = 1e-9;

void check(bool ok, const std::string & name)
{
  if (ok) {
    std::cout << "[PASS] " << name << '\n';
  } else {
    std::cout << "[FAIL] " << name << '\n';
    ++failures;
  }
}

// 浮点数不能直接用 == 比较，允许 1e-9 的误差
void expectOptional(double want, const std::optional<double> & got, const std::string & name)
{
  check(got.has_value() && std::fabs(*got - want) < kEpsilon, name);
}

void expectEmpty(const std::optional<double> & got, const std::string & name)
{
  check(!got.has_value(), name);
}

void expectSize(std::size_t want, std::size_t got, const std::string & name)
{
  check(want == got, name);
}

}  // namespace

int main()
{
  std::cout << "== meanLength ==\n";
  expectEmpty(meanLength(std::vector<double>{}), "空数组 -> nullopt");
  expectOptional(60.0, meanLength(std::vector<double>{40.0, 60.0, 80.0}), "40/60/80 均值 60");
  expectOptional(5.0, meanLength(std::vector<double>{5.0}), "单元素均值 5");
  expectOptional(0.0, meanLength(std::vector<double>{-5.0, 5.0}), "{-5,5} 均值 0（合法的 0）");
  expectOptional(61.0, meanLength(std::vector<double>{60.0, 61.0, 62.0}), "60/61/62 均值 61");

  std::cout << "== countAtLeast ==\n";
  expectSize(2, countAtLeast(std::vector<double>{40.0, 60.0, 80.0}, 60.0),
    "阈值 60：恰好等于的 60 要算进去 -> 2");
  expectSize(3, countAtLeast(std::vector<double>{40.0, 60.0, 80.0}, 40.0),
    "阈值 40：全部不小于 -> 3");
  expectSize(0, countAtLeast(std::vector<double>{40.0, 60.0, 80.0}, 100.0),
    "阈值 100：一个都没有 -> 0");
  expectSize(0, countAtLeast(std::vector<double>{}, 60.0), "空数组 -> 0");
  expectSize(3, countAtLeast(std::vector<double>{50.0, 50.0, 50.0}, 50.0),
    "全部恰好等于阈值 -> 3");

  if (failures == 0) {
    std::cout << "\nALL TESTS PASSED\n";
    return 0;
  }
  std::cout << "\n" << failures << " TEST(S) FAILED\n";
  return 1;  // 有失败时返回非零，交给检查方/CI 判断
}
