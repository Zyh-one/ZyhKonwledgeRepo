# 硬件监控指标

## 1. 监控范围

硬件监控描述 Predictor 容器及其所在节点、加速设备的资源状态，包括 CPU、内存、网络、磁盘，以及 GPU/MLU 的利用率、设备内存、温度、功耗和健康状态。

## 2. 典型指标生产者

| 生产者 | 负责的数据 | 典型指标 |
| --- | --- | --- |
| kubelet/cAdvisor | Pod、Container 资源消耗 | `container_cpu_usage_seconds_total`、`container_memory_working_set_bytes` |
| kube-state-metrics | Pod 状态、标签和资源声明 | `kube_pod_labels`、`kube_pod_status_phase` |
| node-exporter | Node 的 CPU、内存、磁盘和网络 | `node_cpu_seconds_total`、`node_memory_*` |
| GPU/DCGM Exporter | NVIDIA GPU 状态 | `dcgm_gpu_utilization` 等 |
| MLU Exporter | 寒武纪 MLU 状态 | `mlu_utilization`、`mlu_memory_utilization` 等 |

## 3. 基本数据链路

```text
容器、Node、GPU 或 MLU
  → kubelet/Exporter → vmagent → VictoriaMetrics
  → monitor-server → PaaS Hardware Monitor
```

## 4. 后续逐项分析模板

1. 图表表达什么；
2. 指标由哪个组件产生；
3. 指标类型和单位；
4. `namespace`、`pod`、`container`、`node`、设备和 `uuid` 标签来源；
5. PromQL 的 `rate`、聚合或 join；
6. 后端与前端的单位、序列转换；
7. 如何验证原始样本和最终查询。

关键难点是把设备或节点指标准确关联到某个 Predictor Pod。
