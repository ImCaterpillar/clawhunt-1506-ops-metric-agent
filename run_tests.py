# -*- coding: utf-8 -*-
"""经营数据 Agent 主流程验证 —— 对应验收标准
「提供匿名指标输入、计算校验及分析示例」

零第三方依赖。打印每条验收标准的实测结果。
"""
import json
import os
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ops_metric_bot import OpsMetricBot, MetricError, validate  # noqa

PASS, FAIL = [], []
OK = "\u2705"
NO = "\u274c"


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    mark = OK if cond else NO
    line = "  " + mark + " " + name
    if detail:
        line += " -- " + detail
    print(line)


print("=" * 78)
print("Ops Metric Agent -- acceptance verification")
print("=" * 78)
print("Acceptance: 匿名指标输入、计算校验及分析示例\n")

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(HERE, "configs")
SCHEMA = os.path.join(HERE, "schema", "metric_config.schema.json")

# 1. schema 可加载 draft-07
schema = json.load(open(SCHEMA, encoding="utf-8"))
check("1. schema loadable, draft-07",
      schema.get("$schema", "").endswith("draft-07/schema#"),
      "title=" + str(schema.get("title")))

# 2. 三个合法指标配置加载
bot = OpsMetricBot(CFG)
check("2. three metric configs loaded", bot.count() == 3,
      f"count={bot.count()}")

# 3. 匿名输入读取（CSV 脱敏样例）
csv_text = open(os.path.join(HERE, "examples",
                             "anonymous_ops_sample.csv"),
                encoding="utf-8").read()
rows = OpsMetricBot.read_csv(csv_text)
check("3. anonymous CSV input parsed",
      len(rows) == 5 and "week" in rows[0], f"rows={len(rows)}")

# 4. 查询：三分输出（fact/calculation/suggestion）
r = bot.query("metric-revenue-01",
              {"rows": rows})
check("4. query returns fact/calculation/suggestion",
      "fact" in r and "calculation" in r and "suggestion" in r,
      f"keys={list(r.keys())}")

# 5. 计算校验：周营收 = SUM(unit_amount*qty) = 100*2+120*1+110*3+90*4+130*2
expected_revenue = 100*2 + 120*1 + 110*3 + 90*4 + 130*2
ok_v, act, exp = bot.verify("metric-revenue-01",
                            {"rows": rows}, expected_revenue)
check("5. revenue calc verified", ok_v,
      f"actual={act} expected={exp}")

# 6. 计算校验反例：错误预期必须判 FALSE
ok_bad, _, _ = bot.verify("metric-revenue-01", {"rows": rows}, 999999)
check("6. wrong expected rejected by verify", not ok_bad,
      f"ok={ok_bad}")

# 7. 分析示例：CAC 比率计算
r2 = bot.query("metric-cac-02", {"rows": rows})
cac = r2["calculation"]["value"]
expected_cac = (800+450+900+600+750) / (5+3+7+4+6)
check("7. CAC ratio calc", abs(cac - expected_cac) < 1e-4,
      f"cac={cac} expected={expected_cac}")

# 8. 建议区分：缺陷率 suggestions
r3 = bot.query("metric-defect-rate-03", {"rows": rows})
check("8. suggestion returned for defect rate",
      "suggestion" in r3 and r3["suggestion"]["trend"] != "",
      f"sugg={r3['suggestion']}")

# 9. 非法配置被拒（缺必填/非法 category/额外字段）
bad = json.load(open(os.path.join(CFG, "metric-invalid-99.json"),
                     encoding="utf-8"))
errs = validate(bad, schema)
check("9. invalid config rejected by schema", len(errs) >= 3,
      f"{len(errs)} errors -> {errs[:3]}")
try:
    bot.register(bad)
    check("9b. invalid config rejected at register", False)
except MetricError:
    check("9b. invalid config rejected at register", True)

# 10. 未知指标查询抛 MetricError
try:
    bot.query("metric-nonexist", {"rows": []})
    check("10. unknown metric raises", False)
except MetricError:
    check("10. unknown metric raises", True)

# 11. 空输入不崩溃
r4 = bot.query("metric-revenue-01", {"rows": []})
check("11. empty input handled", r4["calculation"]["value"] == 0.0,
      f"value={r4['calculation']['value']}")

# 12. 零第三方依赖
src = open(os.path.join(HERE, "ops_metric_bot.py"),
           encoding="utf-8").read()
imports = [l.split()[1].split(".")[0]
           for l in src.splitlines()
           if (l.startswith("import ") or l.startswith("from "))
           and "ops_metric_bot" not in l]
check("12. zero third-party deps",
      all(m in {"csv", "io", "json", "os", "re", "sys"} for m in imports),
      f"imports={imports}")

# 13. demo 可运行
r13 = subprocess.run([sys.executable, "demo.py"], cwd=HERE,
                     capture_output=True, text=True, encoding="utf-8",
                     errors="replace")
check("13. demo.py exit=0", r13.returncode == 0, f"exit={r13.returncode}")

# 14. 交付齐套
refs = ["ops_metric_bot.py", "run_tests.py", "demo.py",
        "schema/metric_config.schema.json",
        "configs/metric-revenue-01.json",
        "configs/metric-cac-02.json",
        "configs/metric-defect-rate-03.json",
        "configs/metric-invalid-99.json",
        "examples/anonymous_ops_sample.csv",
        "README.md", "SETUP.md",
        "docs/验收对照.md", "docs/实现说明.md", "docs/验证记录.md"]
broken = [r for r in refs if not os.path.isfile(os.path.join(HERE, r))]
check("14. delivery set complete (14 files)", not broken,
      "broken=" + str(broken) if broken else str(len(refs)) + " files")

print()
print("=" * 78)
print("Result: PASS " + str(len(PASS)) + "   FAIL " + str(len(FAIL)))
print("=" * 78)
if FAIL:
    print("Failed: " + ", ".join(FAIL))
sys.exit(1 if FAIL else 0)