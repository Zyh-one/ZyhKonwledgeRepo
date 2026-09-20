# 监控数据采集与查询链路

## 1. 概述

监控仪表盘中的数据不是由某一个业务服务统一生成的。CPU、内存、MLU、GPU、网络、服务请求和大模型推理数据分别来自不同的底层组件。

这些组件将指标以 Prometheus 可识别的格式暴露出来，再由监控系统定期采集、存储和统一查询。平台的 `monitor-server` 作为前端和监控查询后端之间的网关。

## 2. 整体链路

```text
指标生产者
    │
    │ 暴露 Prometheus 格式的指标端点
    ▼
Prometheus 采集体系
    │
    │ 定期抓取指标样本
    ▼
Prometheus 兼容的时序存储与查询后端
    │
    │ PromQL 查询
    ▼
monitor-server
    │
    │ 平台认证、项目权限校验和请求转发
    ▼
Angular 监控页面
    │
    │ 将返回的时间序列转换为图表数据
    ▼
ECharts 监控图表
```

## 3. 指标生产者

监控页面覆盖多种技术领域，因此需要多个指标生产者共同提供数据。

| 指标生产者                | 主要内容                           | 典型指标                                                                        |
| ------------------------- | ---------------------------------- | ------------------------------------------------------------------------------- |
| kubelet / cAdvisor        | 容器 CPU、内存、网络和磁盘         | `container_cpu_usage_seconds_total`、`container_memory_working_set_bytes`   |
| kube-state-metrics        | Kubernetes 资源配置和对象状态      | `kube_pod_container_resource_limits`、`kube_pod_labels`                     |
| MLU Monitoring / Exporter | MLU 计算、设备内存、功耗和 MLULink | `mlu_utilization`、`mlu_memory_utilization`、`mlu_power_usage`            |
| GPU Exporter              | GPU 计算、显存和功耗               | `dcgm_gpu_utilization`、`dcgm_gpu_memory_utilization`、`dcgm_power_usage` |
| 节点和 RDMA 采集组件      | InfiniBand / RDMA 网络             | `node_infiniband_port_data_received_bytes_total`                              |
| Envoy / Ingress           | 服务请求量、状态码和延迟           | Envoy 和 Ingress 请求指标                                                       |
| vLLM                      | 推理请求、队列、Token、延迟和缓存  | TTFT、TPOT、KV Cache 等指标                                                     |
| 业务服务                  | 应用自定义业务指标                 | 由业务约定                                                                      |

指标通常通过 HTTP `/metrics` 端点暴露，但具体路径可由采集配置自定义，不能假设所有服务都使用相同的 URL。

## 4. 指标样本与时间序列

一个指标样本由指标名、标签、数值和采集时间组成。

```text
container_memory_working_set_bytes{
  namespace="ns-xxx",
  pod="predictor-xxx",
  container="main"
} 633507676160
```

其中：

- `container_memory_working_set_bytes` 是指标名；
- `namespace`、`pod`、`container` 是标签；
- `633507676160` 是当前指标值；
- 采集时间由监控系统记录。

同一组标签持续产生的样本会构成一条时间序列。监控折线图展示的就是一条或多条时间序列。

## 5. 采集、存储与查询

### 5.1 采集

Prometheus 采集体系根据配置定期访问各个指标生产者的指标端点。每次抓取会为当前数值记录时间，形成时序样本。

### 5.2 存储

小型环境可以由 Prometheus 自身保存时序数据。大型或多集群环境也可以使用 VictoriaMetrics、Thanos 等兼容 Prometheus API 的存储和查询系统。

因此，“Prometheus 监控”有时指完整的 Prometheus 技术体系，不一定表示实际数据只保存在单个 Prometheus Server 中。

### 5.3 查询

上层使用 PromQL 查询时序数据。查询后端提供 Prometheus 兼容 API，例如：

```http
GET /api/v1/query
GET /api/v1/query_range
```

- `query` 用于查询某一时刻的值；
- `query_range` 用于查询一段时间内的序列。

## 6. monitor-server 的职责

`monitor-server` 是平台层的监控网关，不是 CPU、MLU 等指标的原始生产者，也不是主要的时序数据库。

它的主要职责是：

1. 接收前端的监控查询请求；
2. 验证平台用户身份；
3. 校验用户是否可以访问当前项目；
4. 限定 namespace 查询范围；
5. 将 PromQL 和时间参数转发给配置的查询后端；
6. 将时序查询结果返回给前端。

前端调用的主要接口是：

```http
POST /api/monitor/v1/namespace/{namespace}/range
```

`monitor-server` 再将请求转换为对查询后端 `/api/v1/query_range` 的访问。

## 7. 前端监控页面的职责

前端不负责采集原始指标，主要负责：

1. 获取当前 Predictor 的业务上下文；
2. 管理时间范围、查询步长和筛选条件；
3. 为当前图表选择对应的 PromQL 模板；
4. 将 namespace、Pod、Container 等条件填充到查询中；
5. 调用 `monitor-server`；
6. 把返回的时间序列转换成 ECharts 配置；
7. 在筛选条件变化后停止旧查询并刷新图表。

## 8. Predictor 页面的典型指标映射

| 页面图表       | 基础指标                                                                               | 指标生产者                            |
| -------------- | -------------------------------------------------------------------------------------- | ------------------------------------- |
| CPU 利用率     | `container_cpu_usage_seconds_total` + `kube_pod_container_resource_limits`         | kubelet/cAdvisor + kube-state-metrics |
| 内存用量       | `container_memory_working_set_bytes`                                                 | kubelet/cAdvisor                      |
| 容器网络       | `container_network_receive_bytes_total` + `container_network_transmit_bytes_total` | kubelet/cAdvisor                      |
| 容器磁盘       | `container_fs_reads_bytes_total` + `container_fs_writes_bytes_total`               | kubelet/cAdvisor                      |
| MLU 算力利用率 | `mlu_utilization` + `mlu_container`                                                | MLU Monitoring                        |
| MLU 内存利用率 | `mlu_memory_utilization` + `mlu_container`                                         | MLU Monitoring                        |
| MLU 功耗       | `mlu_power_usage` + `mlu_container`                                                | MLU Monitoring                        |
| GPU 利用率     | `dcgm_gpu_utilization`                                                               | GPU Exporter                          |
| GPU 显存利用率 | `dcgm_gpu_memory_utilization`                                                        | GPU Exporter                          |
| GPU 功耗       | `dcgm_power_usage`                                                                   | GPU Exporter                          |

## 9. 筛选项的数据来源

顶部的版本、Pod、容器和请求路径选项也主要来自监控数据，而不是完全由 Predictor 业务接口提供。

前端通过标签值接口获取：

```http
POST /api/monitor/v1/namespace/{namespace}/label-value/{labelName}
```

例如：

```text
版本       -> label_version
Pod        -> pod
容器       -> container
请求路径   -> path
```

因此，Predictor 业务接口主要提供页面身份和初始配置，`monitor-server` 则提供筛选候选项和图表时序数据。

## 10. 总结

这套监控数据链路可以概括为：

> 多个底层组件分别测量并暴露指标，Prometheus 采集体系统一抓取，时序查询后端统一存储和计算，`monitor-server` 提供平台级权限与接口，前端最终负责组织查询条件和展示结果。
