# 经营数据 Agent — 指标查询与分析 Bot（事实/计算/建议）

对应 ClawHunt 任务 **#1506**（企业 Agent 系统 19/50｜经营数据 Agent）。

**验收标准**：提供**匿名指标输入、计算校验及分析示例**。

## 一条命令验证全部

```bash
python run_tests.py      # -> PASS 15 / FAIL 0
python demo.py           # -> 匿名输入 → 事实/计算/建议三分演示
```

## 验收三要素（与验收标准逐条对应）

**① 匿名指标输入**
`examples/anonymous_ops_sample.csv` —— 5 行脱敏经营样例（周营收/
获客/缺陷相关字段），无真实客户或金额。`read_csv()` 解析，数值自动转换。

**② 计算校验**
`ops_metric_bot.py` —— `OpsMetricBot.verify()` 按 `calculation_type`
复算指标并与预期比对，返回 `(ok, actual, expected)`；支持
sum（含 x*y 乘积）、average、ratio、count、delta。

**③ 分析示例（事实/计算/建议三分）**
`query()` 对每个指标返回 `fact`（原始数据）、`calculation`（复算值）、
`suggestion`（规则建议）三分，`demo.py` 直观演示。

## 快速开始

```bash
# 零第三方依赖（纯 Python 标准库）
python run_tests.py          # 全部验收验证
python demo.py               # 三分输出演示
```

## 目录

```
.
├── ops_metric_bot.py        # 指标 Bot（查询/计算校验/三分输出，核心）
├── run_tests.py             # 验收验证
├── demo.py                  # 三分输出演示
├── schema/
│   └── metric_config.schema.json  # 指标配置模板（draft-07）
├── configs/
│   ├── metric-revenue-01.json    # 周营收（sum, x*y）
│   ├── metric-cac-02.json        # 获客成本率（ratio）
│   ├── metric-defect-rate-03.json # 周缺陷率（ratio）
│   └── metric-invalid-99.json    # 反例（校验拒绝路径）
├── examples/
│   └── anonymous_ops_sample.csv  # 匿名输入样例（5 行脱敏）
├── docs/（验收对照 / 实现说明 / 验证记录）
├── SETUP.md
└── README.md
```

## 设计要点

1. **三分输出清晰**：`fact`（原始数据，不加工）/ `calculation`（复算值，
   可校验）/ `suggestion`（规则建议）——对应验收"区分事实、计算与建议"。
2. **计算校验可复算**：`verify()` 用同一 `_calculate` 逻辑复算，
   买家可拿自己的数字对账；反例预期（999999）判 FALSE。
3. **数值容错**：CSV 字典读出的字符串数字统一 `_num()` 转换——
   这是实现期修掉的真 bug（否则 sum 恒 0）。
4. **sum 支持乘积**：配置了 y（数量因子）时按 `x*y` 求和（营收=单价×
   数量），与 formula 声明一致。
5. **匿名合规**：样例全部脱敏，指标配置带 `anonymized_note` 声明。

## 环境

- Python 3.8+
- **零第三方依赖**（纯标准库 csv/io/json/os/re/sys）

## 边界说明

本单范围 = 指标查询和分析 Bot 的配置与计算校验；
真实经营数据接入、bi 报表集成、多 Agent 调度 —— 属其他拆分单。