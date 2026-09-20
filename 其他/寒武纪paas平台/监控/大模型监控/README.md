# 大模型监控指标

## 1. 监控范围

大模型监控描述 LLM 推理引擎内部的请求调度、Token 处理和缓存状态，包括请求吞吐、运行/等待请求、输入输出 Token、TTFT、TPOT、端到端延迟、KV Cache、Prefix Cache、Spec Decode 和 KV Offload。

## 2. 典型指标生产者

| 生产者 | 作用 | 典型指标形态 |
| --- | --- | --- |
| vLLM 推理容器 | 描述推理引擎内部状态 | vLLM 原始 `/metrics` 指标 |
| AIBrix/Serving 适配组件 | 补充路由、模型或运行时维度 | 带业务标签的指标 |
| `vmalert` recording rules | 预计算 PromQL 并写回新序列 | `vllm:*` 等记录指标 |

带冒号的指标可能由应用直接暴露，也可能由 recording rule 生成，不能只凭命名判断来源。

## 3. 基本数据链路

```text
vLLM/AIBrix Runtime → /metrics → vmagent → VictoriaMetrics
  ├─ vmselect 直接查询
  └─ vmalert 计算 recording rules 后写回
  → monitor-server → PaaS LLM Service Monitor
```

## 4. 后续逐项分析模板

1. 指标对应请求生命周期的哪个阶段；
2. 指标由 vLLM、AIBrix 还是 recording rule 产生；
3. 指标类型和单位；
4. Namespace、Pod、Container、模型和版本标签；
5. Token/s、TTFT、TPOT、P95/P99 的计算；
6. recording rule 的输入与输出；
7. 前端如何组织序列、图例和单位。

关键难点是同时理解推理语义和指标计算语义。
