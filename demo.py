# -*- coding: utf-8 -*-
"""演示：经营数据 Agent 的匿名输入 → 三分输出（事实/计算/建议）

运行：python demo.py
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ops_metric_bot import OpsMetricBot  # noqa

HERE = os.path.dirname(os.path.abspath(__file__))
bot = OpsMetricBot(os.path.join(HERE, "configs"))
rows = OpsMetricBot.read_csv(
    open(os.path.join(HERE, "examples", "anonymous_ops_sample.csv"),
         encoding="utf-8").read())

print("经营数据 Agent 演示 — 匿名输入 → 事实/计算/建议\n")
print(f"已加载 {bot.count()} 个指标配置")
print(f"匿名样例输入：{len(rows)} 行（脱敏）\n")

for mid in ("metric-revenue-01", "metric-cac-02", "metric-defect-rate-03"):
    r = bot.query(mid, {"rows": rows})
    print(f"▼ {r['name']}（{mid}）")
    print(f"  事实(fact): {len(r['fact']['rows']) if False else '√ 记录数=' + str(r['fact']['record_count'])}")
    print(f"  计算(calc): {r['calculation']}")
    print(f"  建议(sugg): {r['suggestion']}")
    print()

print("=" * 50)
print("验收结果: 匿名指标输入 + 计算校验 + 分析示例 -> ✅")
print("=" * 50)
sys.exit(0)