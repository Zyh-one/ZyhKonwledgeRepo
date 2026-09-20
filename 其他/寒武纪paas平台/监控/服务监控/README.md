# 服务监控指标

## 1. 监控范围

服务监控从网络请求和网关视角描述推理服务，包括请求量、请求速率、状态码、成功率、错误率、延迟、路径、上游实例和连接状态。

## 2. 典型指标生产者

| 生产者 | 作用 | 典型数据 |
| --- | --- | --- |
| Envoy Gateway | 统计网关请求和上游通信 | 请求量、状态码、延迟、连接 |
| `envoy-svc-exporter` | 采集或转换服务 Telemetry | 服务、路径、上游实例等维度 |
| Serving/AIBrix 组件 | 补充业务对象信息 | Predictor、模型、路由标签 |

Envoy 通常通过 `/stats/prometheus` 暴露指标；`VMServiceScrape` 描述目标，vmagent 负责实际抓取。

## 3. 基本数据链路

```text
用户请求 → Envoy Gateway → Envoy/exporter 指标
  → vmagent → VictoriaMetrics
  → monitor-server → PaaS Service Monitor
```

## 4. 后续逐项分析模板

1. 指标统计入口请求还是上游请求；
2. Counter 如何转成速率或区间请求量；
3. Histogram 如何计算平均值或 P95/P99；
4. Namespace、服务、path、状态码和 upstream 标签语义；
5. Envoy 原始指标与 exporter 加工指标的关系；
6. PromQL 如何限定 Predictor 或版本；
7. 无数据时如何沿请求链路验证。

关键难点是明确统计口径。
