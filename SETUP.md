# 设置与运行

零第三方依赖，无需安装任何包。

## 环境要求

- Python 3.8+（标准库：csv / io / json / os / re / sys）

## 快速验证

```bash
# 在项目根目录
python run_tests.py        # 验收断言，期望 PASS 15 / FAIL 0
python demo.py             # 三分输出演示，期望退出码 0
```

## 在自己的代码中使用

```python
from ops_metric_bot import OpsMetricBot

bot = OpsMetricBot("configs")            # 自动加载并校验指标配置

# 匿名输入（CSV 文本）
rows = OpsMetricBot.read_csv(
    open("examples/anonymous_ops_sample.csv", encoding="utf-8").read())

# 查询（三分输出）
r = bot.query("metric-revenue-01", {"rows": rows})
print(r["fact"])          # 事实：记录数 + 样例
print(r["calculation"])   # 计算：{"type": "sum", "value": 1270}
print(r["suggestion"])    # 建议：趋势 + 规则提示

# 计算校验
ok, actual, expected = bot.verify(
    "metric-revenue-01", {"rows": rows}, 1270)
print(ok, actual, expected)   # True 1270.0 1270
```

## 新增一个指标

1. 复制 `configs/metric-revenue-01.json`
2. 改 `metric_id`（`metric-` 前缀，唯一）、`name`、`category`
   （revenue/cost/customers/operations/quality/finance）、
   `calculation_type`（sum/average/ratio/count/delta/custom）、
   `data_input_schema.x/y`（CSV 列名）
3. 放入 `configs/`，`OpsMetricBot` 自动校验注册

## 常见问题

- **CSV 读出的数字是字符串？** `_calculate` 已用 `_num()` 自动转换，
  无需预处理。
- **sum 怎么算乘积？** `data_input_schema` 配置了 `y` 且数据含该列时，
  sum 按 `x * y` 求和，否则按 `x` 求和。
- **Windows 中文乱码？** 脚本已内置 UTF-8 重配置。