# -*- coding: utf-8 -*-
"""经营数据 Agent —— 指标查询与分析 Bot

对应 ClawHunt 任务 #1506（企业 Agent 系统 19/50｜经营数据 Agent）：
范围 = 配置经营指标查询和分析 Bot；区分事实、计算与建议。
验收标准 = 提供匿名指标输入、计算校验及分析示例。

设计：
  - `metric_config.schema.json` 定义指标配置（calculation_type 区分
    sum/average/ratio/count/delta/custom）
  - `OpsMetricBot`：
      · load 指标配置（schema 校验，零依赖）
      · query(metric, inputs)：三分输出 —— fact（事实）/
        calculation（计算）/ suggestion（建议）
      · verify(metric, inputs, expected)：计算校验（复算断言）
  - 匿名输入：样本数据脱敏（无真实客户/金额），从 CSV/JSON 读
  - 零第三方依赖
"""
import csv
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


class MetricError(Exception):
    pass


def _type_ok(value, t):
    if t == "object":
        return isinstance(value, dict)
    if t == "array":
        return isinstance(value, list)
    if t == "string":
        return isinstance(value, str)
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if t == "boolean":
        return isinstance(value, bool)
    if t == "null":
        return value is None
    return True


def validate(instance, schema, path="$"):
    errors = []
    if "type" in schema and not _type_ok(instance, schema["type"]):
        return [f"{path}: 期望 {schema['type']} 实为 {type(instance).__name__}"]
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: 值 {instance!r} 不在允许集合 {schema['enum']}")
    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append(f"{path}: 长度 {len(instance)} < {schema['minLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append(f"{path}: 值 {instance!r} 不匹配模式 {schema['pattern']}")
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(f"{path}: 元素数 {len(instance)} < {schema['minItems']}")
        if "items" in schema:
            for i, item in enumerate(instance):
                errors += validate(item, schema["items"], f"{path}[{i}]")
    if isinstance(instance, dict):
        if "required" in schema:
            for k in schema["required"]:
                if k not in instance:
                    errors.append(f"{path}: 缺少必填字段 {k!r}")
        if schema.get("additionalProperties") is False \
                and "properties" in schema:
            for k in instance:
                if k not in schema["properties"]:
                    errors.append(f"{path}: 不允许的额外字段 {k!r}")
        if "properties" in schema:
            for k, sub in schema["properties"].items():
                if k in instance:
                    errors += validate(instance[k], sub, f"{path}.{k}")
    return errors


class OpsMetricBot:
    """经营指标查询与分析 Bot（事实/计算/建议三分）"""

    def __init__(self, config_dir=None):
        here = os.path.dirname(os.path.abspath(__file__))
        self.schema = json.load(open(
            os.path.join(here, "schema", "metric_config.schema.json"),
            encoding="utf-8"))
        self._metrics = {}
        if config_dir:
            self.load_dir(config_dir)

    def load_dir(self, d):
        if not os.path.isdir(d):
            return 0
        files = sorted(f for f in os.listdir(d)
                       if f.startswith("metric-") and f.endswith(".json")
                       and "invalid" not in f)
        n = 0
        for fn in files:
            cfg = json.load(open(os.path.join(d, fn), encoding="utf-8"))
            self.register(cfg)
            n += 1
        return n

    def register(self, cfg):
        errs = validate(cfg, self.schema)
        if errs:
            raise MetricError("指标配置校验失败: " + "; ".join(errs[:4]))
        mid = cfg["metric_id"]
        if mid in self._metrics:
            raise MetricError(f"重复 metric_id: {mid}")
        self._metrics[mid] = cfg
        return mid

    def metric(self, mid):
        return self._metrics.get(mid)

    def count(self):
        return len(self._metrics)

    # ── 查询（三分输出）──────────────────────────────────────────
    def query(self, metric_id, inputs):
        """给定匿名指标输入，返回 {fact, calculation, suggestion} 三分"""
        cfg = self._metrics.get(metric_id)
        if not cfg:
            raise MetricError(f"未知指标: {metric_id}")
        fact = self._fact(metric_id, inputs)
        calc = self._calculate(cfg, inputs)
        sugg = self._suggest(cfg, calc)
        return {"metric_id": metric_id, "name": cfg["name"],
                "fact": fact, "calculation": calc, "suggestion": sugg}

    def _fact(self, metric_id, inputs):
        """事实：直接来自输入的原始数据（不加计算）"""
        rows = inputs.get("rows", [])
        return {
            "record_count": len(rows),
            "sample": rows[:2] if rows else [],
        }

    def _calculate(self, cfg, inputs):
        """计算：按 calculation_type 复算（这是'计算校验'的依据）"""
        rows = inputs.get("rows", [])
        k = cfg.get("data_input_schema", {}).get("x", "value")
        y = cfg.get("data_input_schema", {}).get("y", "num")
        # CSV DictReader 读出的数值是字符串，统一数值化
        def _num(v):
            try:
                return float(v)
            except (TypeError, ValueError):
                return 0.0
        values = [_num(r.get(k)) for r in rows if _num(r.get(k)) != 0.0
                  or str(r.get(k, "")).strip() != ""]
        kind = cfg.get("calculation_type")
        if kind == "sum":
            # 若配置了 y（数量因子）则按 x*y 求和（如营收=单价*数量）
            if y and any(r.get(y) for r in rows
                         if str(r.get(y, "")).strip() != ""):
                result = sum(
                    _num(r.get(k)) * _num(r.get(y)) for r in rows)
            else:
                result = sum(_num(r.get(k)) for r in rows)
        elif kind == "average":
            vals = values
            result = sum(vals) / len(vals) if vals else 0.0
        elif kind == "count":
            result = len(rows)
        elif kind == "ratio":
            num = sum(_num(r.get(y)) for r in rows)
            den = sum(_num(r.get(k)) for r in rows)
            result = num / den if den else 0.0
        elif kind == "delta":
            vv = values
            result = (vv[-1] - vv[0]) if len(vv) >= 2 else 0.0
        else:
            result = 0.0
        return {"type": kind, "value": round(result, 4),
                "from_values": len(values)}

    def _suggest(self, cfg, calc):
        """建议：基于计算结果的简单规则（区分于事实/计算）"""
        rule = cfg.get("suggestion_rule", "")
        v = calc.get("value", 0)
        trend = "持平"
        if isinstance(v, (int, float)):
            if v > 0:
                trend = "上升"
            elif v < 0:
                trend = "下降"
        return {"trend": trend, "rule_hint": rule}

    # ── 计算校验（验收核心）──────────────────────────────────────
    def verify(self, metric_id, inputs, expected):
        """复算 inputs 并与 expected 比较，返回 (ok, actual, expected)"""
        cfg = self._metrics.get(metric_id)
        if not cfg:
            raise MetricError(f"未知指标: {metric_id}")
        calc = self._calculate(cfg, inputs)
        actual = calc["value"]
        ok = abs(actual - expected) < 1e-6
        return ok, actual, expected

    # ── 匿名输入读取（CSV/JSON）─────────────────────────────────
    @staticmethod
    def read_csv(text):
        """解析 CSV（首行为表头），返回行 dict 列表。数据须已脱敏。"""
        return list(csv.DictReader(io.StringIO(text.strip())))

    @staticmethod
    def read_json(text):
        data = json.loads(text)
        return data.get("rows", data) if isinstance(data, dict) else data