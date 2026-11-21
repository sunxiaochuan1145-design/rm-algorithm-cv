#include <cmath>
#include <iostream>
#include <optional>
#include <vector>

#include "cpp_basics/mean_length.hpp"

using std::cout;
using std::vector;

int failed = 0;

void check(bool ok, const char * name)
{
    if (ok)
    {
        cout << "通过  " << name << "\n";
    }
    else
    {
        cout << "失败  " << name << "\n";
        failed++;
    }
}

int main()
{
    const double eps = 1e-6;

    // meanLength
    check(!meanLength(vector<double>{}).has_value(), "空数组没有均值");

    std::optional<double> m = meanLength(vector<double>{40.0, 60.0, 80.0});
    check(m.has_value() && std::fabs(*m - 60.0) < eps, "40 60 80 的均值是 60");

    m = meanLength(vector<double>{5.0});
    check(m.has_value() && std::fabs(*m - 5.0) < eps, "只有一个数 5");

    m = meanLength(vector<double>{-5.0, 5.0});
    check(m.has_value() && std::fabs(*m - 0.0) < eps, "-5 和 5 的均值是 0");

    m = meanLength(vector<double>{60.0, 61.0, 62.0});
    check(m.has_value() && std::fabs(*m - 61.0) < eps, "60 61 62 的均值是 61");

    // countAtLeast
    check(countAtLeast(vector<double>{40.0, 60.0, 80.0}, 60.0) == 2,
          "阈值 60：60 和 80 一共 2 个");
    check(countAtLeast(vector<double>{40.0, 60.0, 80.0}, 40.0) == 3,
          "阈值 40：三个都不小于 40");
    check(countAtLeast(vector<double>{40.0, 60.0, 80.0}, 100.0) == 0,
          "阈值 100：一个都没有");
    check(countAtLeast(vector<double>{}, 60.0) == 0, "空数组个数是 0");
    check(countAtLeast(vector<double>{50.0, 50.0, 50.0}, 50.0) == 3,
          "三个都等于阈值，全算");

    if (failed > 0)
    {
        cout << "\n有 " << failed << " 个用例没通过\n";
        return 1;
    }
    cout << "\n全部用例通过\n";
    return 0;
}
