# Prometheus 数据模型与工作机制

## 1. Prometheus 在监控链路中的位置

Prometheus 不是 GPU、CPU、请求量等指标的原始生产者。一个完整的监控链路通常是：

```text
应用 / Exporter
    │
    │ 通过 HTTP /metrics 暴露当前指标
    ▼
Prometheus
    │
    │ 定期抓取、记录时间并保存为时间序列
    ▼
查询服务 / Prometheus HTTP API
    │
    │ 执行 PromQL
    ▼
前端监控页面
    │
    └─ 将时间序列绘制成折线图、统计卡片等
```

各部分的职责可以简化为：

| 部分            | 职责                                       |
| --------------- | ------------------------------------------ |
| 应用或 Exporter | 测量数据并暴露当前值                       |
| Prometheus      | 定时抓取、记录时间、保存历史并提供查询能力 |
| 查询代理        | 处理认证、权限和查询转发                   |
| 前端            | 选择查询条件并展示结果                     |

前端和 Prometheus 都不负责产生真实的 GPU 利用率。真实环境中，这类数据一般由 GPU Exporter 从驱动或设备读取后暴露。

## 2. 指标样本

Prometheus 中一个基本的指标样本可以理解为：

```text
指标名 + 标签集合 + 指标值 + 时间戳
```

例如：

```text
demo_gpu_utilization_percent{
  namespace="demo",
  pod="llm-pod-0",
  container="vllm",
  gpu="0"
} 72.5
```

其中：

- `demo_gpu_utilization_percent` 是指标名；
- `namespace`、`pod`、`container`、`gpu` 是标签；
- `72.5` 是当前指标值；
- 时间戳通常由 Prometheus 抓取时记录，因此在普通的 `/metrics` 输出中可以不写。

指标值必须是数值。描述性信息一般放在标签中，但标签不能被当作可以随意添加的 JSON 元数据。

## 3. 时间序列

一条时间序列由下面两部分唯一确定：

```text
指标名 + 完整标签集合
```

例如：

```text
demo_gpu_utilization_percent{pod="llm-pod-0", gpu="0"} 72.5
demo_gpu_utilization_percent{pod="llm-pod-1", gpu="0"} 44.2
demo_gpu_utilization_percent{pod="llm-pod-1", gpu="1"} 81.3
```

虽然三个样本的指标名相同，但标签集合不同，所以它们属于三条时间序列。

Prometheus 每隔一段时间抓取同一指标：

```text
10:00:00  72.5
10:00:05  74.1
10:00:10  69.8
```

这些带时间的样本共同形成一条曲线。前端折线图展示的就是一条或多条时间序列。

标签发生变化意味着时间序列身份发生变化。例如：

```text
metric{gpu="0"} 70
metric{gpu="1"} 80
```

这不是一条序列的两个说明字段，而是两条不同的序列。

## 4. 标签从哪里产生

标签主要有两个来源：

1. 指标生产者添加的业务或资源标签；
2. Prometheus 抓取时添加的目标标签。

### 4.1 指标生产者添加

指标生产者最清楚数据属于哪个业务对象，因此通常由它添加：

```text
namespace
pod
container
gpu
model
status_code
request_method
```

例如 Go 服务暴露：

```text
demo_gpu_utilization_percent{
  gpu="0",
  model="Simulated-GPU"
} 72.5
```

如果同一个指标端点同时表示多个 GPU，则生产者需要生成多组样本：

```text
demo_gpu_utilization_percent{gpu="0", model="Simulated-GPU"} 72.5
demo_gpu_utilization_percent{gpu="1", model="Simulated-GPU"} 43.8
```

Prometheus YAML 无法根据指标内容自动判断哪个样本属于哪个 GPU。因此，能够区分指标内部对象的标签应由生产者提供。

### 4.2 Prometheus 自动添加

Prometheus 抓取指标时会自动添加：

```text
job
instance
```

例如抓取配置为：

```yaml
scrape_configs:
  - job_name: frontangular-demo-gpu
    static_configs:
      - targets:
          - host.docker.internal:8080
```

存储到 Prometheus 后，时间序列会包含：

```text
job="frontangular-demo-gpu"
instance="host.docker.internal:8080"
```

因此，应用的 `/metrics` 可能是：

```text
demo_gpu_utilization_percent{gpu="0"} 72.5
```

Prometheus 中实际保存的序列则类似：

```text
demo_gpu_utilization_percent{
  gpu="0",
  job="frontangular-demo-gpu",
  instance="host.docker.internal:8080"
} 72.5
```

### 4.3 在抓取配置中补充公共标签

可以在 `prometheus.yml` 中为一个抓取目标统一添加标签：

```yaml
scrape_configs:
  - job_name: frontangular-demo-gpu
    static_configs:
      - targets:
          - host.docker.internal:8080
        labels:
          environment: local
          service: frontangular-backend
```

这些标签会被添加到该 target 抓取到的所有指标中：

```text
environment="local"
service="frontangular-backend"
```

这种方式适合表达目标共有的信息，例如：

- 开发、测试或生产环境；
- 服务名称；
- 区域或数据中心；
- 集群名称。

它不适合区分同一个指标端点内部的不同 GPU、模型或请求。

可以用一句话区分：

> 指标生产者标签描述“这条数据属于谁”，Prometheus 抓取标签描述“这条数据从哪里采集”。

## 6. Prometheus 抓取

指标生产者通常通过 HTTP `/metrics` 暴露当前值：

```text
GET http://应用地址/metrics
```

Prometheus 根据 `scrape_interval` 定期访问：

```yaml
global:
  scrape_interval: 5s
```

每次抓取时，Prometheus 会：

1. 请求指标端点；
2. 解析 Prometheus 文本格式；
3. 补充抓取目标标签；
4. 记录当前抓取时间；
5. 把新样本追加到对应时间序列。

指标生产者只需要维护当前值，不需要自己保存图表使用的历史数组。历史数据由 Prometheus 通过周期抓取形成。

## 7. PromQL 查询

查询所有模拟 GPU 利用率：

```promql
demo_gpu_utilization_percent
```

查询指定 GPU：

```promql
demo_gpu_utilization_percent{gpu="0"}
```

同时指定多个标签：

```promql
demo_gpu_utilization_percent{
  namespace="demo",
  pod="llm-pod-0",
  container="vllm",
  gpu="0"
}
```

使用正则匹配多个 Pod：

```promql
demo_gpu_utilization_percent{
  pod=~"llm-pod-.*",
  gpu=~"0|1"
}
```

增加标签后，原来较宽泛的查询通常仍然有效：

```promql
demo_gpu_utilization_percent{gpu="0"}
```

它会匹配所有满足 `gpu="0"` 的序列，不要求查询表达式列出序列的全部标签。

Prometheus 主要提供两种 HTTP 查询：

```text
/api/v1/query        查询某一时刻
/api/v1/query_range  查询一段时间
```

折线图通常使用 `query_range`，并提供：

```text
query
start
end
step
```

其中 `step` 表示返回数据点之间的时间间隔。
