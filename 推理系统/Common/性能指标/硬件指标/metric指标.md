# 2. 具体 metric 指标

这一部分以 metric 为中心。每个小节分别说明指标来源、原始类型与单位、采集或计算方式，以及它在当前 PromQL 中代表的含义，不再单独按采集服务罗列。

以下采集链路结论来自 2026-09-04 对黄区生产集群的只读探查。其中 MLU 指标的计算方式参考 Cambricon MLU Exporter 官方源码；黄区当前记录的镜像版本为 `cambricon-mlu-exporter:v2.3.1`，内部镜像是否包含额外修改仍需结合实际镜像确认。

## 2.1 vmagent 的指标抓取逻辑

本文中的原始 metric 最终都由 VictoriaMetrics 的 `vmagent` 采集或接收，但它们并不统一采用“采集间隔 30 秒、抓取超时 5 秒”的策略。2026-09-10 对黄区生产集群的只读查询确认，各采集对象的配置如下：

- kubelet/cAdvisor 使用 `kube-system/VMNodeScrape kubelet-cadvisor`，抓取路径为 `/metrics/cadvisor`，`interval` 明确配置为 30 秒，`scrapeTimeout` 明确配置为 5 秒。本文中的容器内存、CPU、网络和文件系统 metric 来自这条链路。
- Cambricon MLU Exporter 使用 `monitoring/VMServiceScrape kube-prometheus-exporter-mlu-monitoring`，`interval` 为 30 秒，没有在该抓取对象中显式配置 `scrapeTimeout`。
- NVIDIA GPU Exporter 使用 `monitoring/VMServiceScrape gpu-exporter`，`interval` 为 30 秒，没有显式配置 `scrapeTimeout`。
- kube-state-metrics 的两个 endpoint 都采用 30 秒间隔，其中 main endpoint 的 `scrapeTimeout` 明确配置为 30 秒，self endpoint 没有显式配置。
- Cambricon RDMA Exporter 使用 `monitoring/VMServiceScrape kube-prometheus-exporter-rdma-monitoring`，`interval` 为 15 秒，没有显式配置 `scrapeTimeout`。
- node-exporter 使用 `monitoring/VMServiceScrape node-exporter`，`interval` 为 15 秒，没有显式配置 `scrapeTimeout`。

“没有显式配置”不等于超时时间为 5 秒，其实际值取决于 VictoriaMetrics Operator 生成抓取配置时采用的默认值。因此，只有 cAdvisor 可以明确写成 `30s / 5s`。

整个数据链路可以理解为：

```text
硬件、内核或 Kubernetes 对象
  → kubelet / Exporter 生成当前 metric 值
  → vmagent 按各自 interval 抓取并写入 VictoriaMetrics
  → VMSelect 在查询阶段执行 PromQL
  → 前端按 start、end、step 展示结果
```

这里需要区分三种时间概念：

* Exporter 或驱动计算单个样本时采用的内部统计窗口
* vmagent 的抓取间隔
* PromQL 的查询区间。

三者相互独立；PromQL 中的 `:30s` 也不能反推出底层一定每 30 秒采集。

## 2.2 `container_memory_working_set_bytes`

这是一个 Gauge，单位为 bytes，表示容器当前正在积极使用、较难直接回收的 Working Set Memory。

它由每个 Node 上的 kubelet 内置 cAdvisor 通过 `/metrics/cadvisor` 暴露，再由 `VMNodeScrape kubelet-cadvisor` 采集；黄区配置的采集间隔为 30 秒，`scrapeTimeout` 为 5 秒。

Working Set 通常包含进程匿名内存、活跃 page cache 和其他活跃内存，并排除了部分容易回收的 inactive file cache。因此它比 `container_memory_usage_bytes` 更接近容器当前真正形成内存压力的部分，但不能简单等同于进程申请的匿名内存。

典型标签如下：

```promql
container_memory_working_set_bytes{
  cluster="bj-caip",
  container="aaa",
  id="/kubepods/...",
  instance="cambricon-train-080",
  job="kubelet",
  metrics_path="/metrics/cadvisor",
  namespace="...",
  node="cambricon-train-080",
  pod="..."
}
```

**唯一标识标签：** 该原始时间序列可由 `(cluster, id)` 定位，其中 `id` 是底层 cgroup 路径；映射到 Kubernetes 业务对象时，使用 `(cluster, namespace, pod, container)`。

![container_memory_working_set_bytes 裸查询](../../../source/推理系统/Common/性能指标/硬件指标/1788493204380.png)

图中纵轴约 `14,900,000,000 bytes`，即对应求值时刻的 Working Set 约为 13.9 GiB。

## 2.3 `container_cpu_usage_seconds_total`

这是一个 Counter，单位为 seconds，由 kubelet 内置 cAdvisor 提供。它表示容器从启动到当前累计消耗的 CPU 时间，而不是当前 CPU 利用率。

对它执行 `rate(...[5m])` 后，单位变为 `seconds/second`，数值可以理解为最近 5 分钟平均使用的 CPU 核数。例如结果为 10，表示平均使用约 10 个 CPU 核；结果大于 1 完全正常。

![container_cpu_usage_seconds_total rate 查询](../../../source/推理系统/Common/性能指标/硬件指标/1788509799680.png)

典型标签：

```promql
container_cpu_usage_seconds_total{
  cluster="bj-caip",
  container="alertmanager",
  cpu="total",
  id="/kubepods/burstable/podf6449424-c18f-4731-a70f-485765606284/fb3d1c8e235f36690e4cf8f2e96fdc0e927374a544280983a3450fc7d023767e",
  image="docker.cambricon.com/library/victoriametrics/alertmanager:v0.28.0",
  instance="cambricon-train-054",
  job="kubelet",
  metrics_path="/metrics/cadvisor",
  name="fb3d1c8e235f36690e4cf8f2e96fdc0e927374a544280983a3450fc7d023767e",
  namespace="monitoring",
  node="cambricon-train-054",
  pod="vmalertmanager-vmalertmanager-0",
  prometheus="monitoring/vmagent"
}
```

**唯一标识标签：** 该原始时间序列可由 `(cluster, id, cpu)` 定位；当前样本的 `cpu="total"` 表示容器 CPU 总量。映射到业务容器时，使用 `(cluster, namespace, pod, container)`。

## 2.4 `container_network_transmit_bytes_total`

这是一个 Counter，单位为 bytes，由 kubelet 内置 cAdvisor 提供，表示 Pod 网络接口从启动到当前累计发送的字节数。Counter 本身反映累计流量；经过 `rate()` 后才表示平均发送速率，单位为 `bytes/s`。

当前前端查询没有使用 `container` 标签过滤，因为 containerd 不一定为 sandbox container 添加该标签。因此该指标在当前页面中实际更接近 Pod 级网络流量，不能严格理解为某个业务容器独占的发送流量。

```promql
container_network_transmit_bytes_total{
  cluster="bj-caip",
  id="/kubepods/burstable/pod189c6597-0fa7-4955-bf4f-d5934d318698/28edb954c40fbef8cfa2cf059eed4e70f065ae4da396bff86809a6aaa709a483",
  image="docker.cambricon.com/library/pause:3.10",
  instance="cam-train-077",
  interface="eth0",
  job="kubelet",
  metrics_path="/metrics/cadvisor",
  name="28edb954c40fbef8cfa2cf059eed4e70f065ae4da396bff86809a6aaa709a483",
  namespace="ns-e23f5b20fb9b42d3ac674f9691a0b9b1",
  node="cam-train-077",
  pod="glm52-pd-0-0-2-roleset-chflh-prefill-7ddfdb-4-1",
  prometheus="monitoring/vmagent"
}
```

**唯一标识标签：** 该原始时间序列可由 `(cluster, id, interface)` 定位。由于它来自 sandbox container 且没有 `container` 标签，业务上应使用 `(cluster, namespace, pod, interface)` 标识，不应强行归属到单个业务容器。

## 2.5 `container_network_receive_bytes_total`

这是一个 Counter，单位为 bytes，同样由 kubelet 内置 cAdvisor 提供，表示 Pod 网络接口累计接收的字节数。经过 `rate()` 后表示平均接收速率，单位为 `bytes/s`。

它和发送指标具有相同的 sandbox container 标签问题，当前查询实际按 Pod 使用。

## 2.6 `container_fs_reads_bytes_total`

这是一个 Counter，单位为 bytes，由 kubelet 内置 cAdvisor 提供，表示容器文件系统累计读取的字节数。它可能按不同文件系统设备形成多条时间序列；当前 PromQL 先通过 `rate()` 得到 `bytes/s`，再用 `sum by (cluster, pod, container)` 聚合成容器维度的平均读取速率。

这里描述的是容器文件系统 I/O，不应直接等同于物理磁盘真实读流量，因为 page cache、存储驱动和挂载方式都会影响二者关系。

```promql
container_fs_reads_bytes_total{
  cluster="bj-caip",
  container="acceld",
  device="/dev/sda",
  id="/kubepods/burstable/pod9c2aa3d4-cb28-409a-b9c9-e6c6333750d0/a05140157517d50fc46d32759904d46b984e2d7b96a9a7f1efb686049a5e81c9",
  image="docker.cambricon.com/library/goharbor/harbor-acceld:0.2.25",
  instance="cambricon-train-010",
  job="kubelet",
  metrics_path="/metrics/cadvisor",
  name="a05140157517d50fc46d32759904d46b984e2d7b96a9a7f1efb686049a5e81c9",
  namespace="dragonfly-system",
  node="cambricon-train-010",
  pod="acceld-deployment-dd4695859-prwdt",
  prometheus="monitoring/vmagent"
}
```

**唯一标识标签：** 该原始时间序列可由 `(cluster, id, device)` 定位；同一容器可能对应多个 `device`。映射到业务容器时，使用 `(cluster, namespace, pod, container)`，当前 PromQL 会聚合掉 `device`。

## 2.7 `container_fs_writes_bytes_total`

这是一个 Counter，单位为 bytes，由 kubelet 内置 cAdvisor 提供，表示容器文件系统累计写入的字节数。经过 `rate()` 和容器维度聚合后，前端得到平均写入速率，单位为 `bytes/s`。

与读取指标相同，它描述的是容器文件系统统计口径，不必然等于底层块设备最终落盘流量。

## 2.8 `kube_pod_container_resource_limits`

这是一个 Gauge，由 kube-state-metrics 根据 Kubernetes 对象配置生成。它描述的是容器声明的资源 Limit（pod yaml配置中的内容），不是 kubelet 测得的实际使用量。

当查询条件为 `resource="cpu"` 时，数值表示容器 CPU Limit，单位为 CPU core。例如 Pod 配置 `limits.cpu: "16"`，对应值就是 16。当前 PromQL 使用它作为 `containerCpuUtilization` 的分母：

```text
CPU平均使用核数 / CPU Limit × 100%
```

容器没有配置 CPU Limit 时，可能不存在对应时间序列，派生利用率也可能没有结果。

```promql
kube_pod_container_resource_limits{
  cluster="bj-caip",
  container="aaa",
  instance="10.9.116.5:8443",
  job="kube-state-metrics",
  namespace="ns-52406304506d497ba854e5198374f41f",
  node="cambricon-train-080",
  pod="aaa-v1-645d7f8f8c-jxrdg",
  prometheus="monitoring/vmagent",
  resource="memory",
  uid="068575ce-602e-4fa5-9edd-a930d6d88d9c",
  unit="byte"
}
```

**唯一标识标签：** 该原始时间序列可由 `(cluster, uid, container, resource, unit)` 定位，其中 `uid` 能区分同名但不同时期创建的 Pod；业务查询通常使用 `(cluster, namespace, pod, container, resource)`。

## 2.9 `mlu_utilization`

这是一个 Gauge，单位为 `%`，由 Cambricon MLU Exporter 的 `cndev` collector 提供。物理卡模式下，Exporter 调用 CNDEV 的 `GetDeviceUtil()`，直接把驱动返回的板卡利用率作为指标值；底层忙碌程度如何统计由驱动和 CNDEV 实现，Exporter 本身不再用时间差进行计算。

一张 MLU 内部包含多个计算 Core。因此，`mlu_utilization=80%` 的准确含义是：**底层统计周期内，各 MLU 计算 Core 利用率的平均值约为 80%，**例如，**80% 的 Core 满负载、其余 Core 空闲，或者所有 Core 都处于约 80% 利用率，都可能得到相同的整卡结果。

该指标同时混合了空间和时间两个维度：空间上有多少 Core 参与工作，时间上每个 Core 在底层统计周期内有多忙。仅凭一个整卡平均值无法还原每个 Core 的具体状态，也不等同于已经达到 80% 的理论峰值算力；算子类型、访存效率和并行度不同，相同利用率下的有效计算量仍可能不同。

`mlu_utilization` 涉及三层时间：

1. CNDEV/驱动内部统计窗口决定单个样本本身代表哪一段时间。官方 Exporter 源码只显示读取 `averageCoreUtilization`，没有公开这个底层窗口的具体长度。
2. 黄区 vmagent 每 30 秒从 MLU Exporter 抓取一次，决定 VictoriaMetrics 多久保存一个观测样本。
3. 前端 PromQL 的 `avg_over_time(mlu_utilization[%(time)s:30s])` 再对已存储样本做查询阶段的时间平均。

虚拟化模式下语义有所不同：sMLU 使用实例的 `IpuUtil`，MIM 会结合实例分配的 Core 和各 Core 利用率计算，部分 env-share 模式则可能把整卡利用率复制到不同 `vf` 标签。因此该指标首先是设备或虚拟实例级利用率，再由 `mlu_container` 映射到容器；不能脱离虚拟化模式一概理解为容器独占利用率。

典型标签：

```promql
mlu_utilization{
  cluster="bj-caip",
  driver="v6.2.28",
  endpoint="http-metrics",
  job="mlu-monitoring",
  mcu="v1.0.1",
  mlu="0",
  model="MLU590-M9DK",
  namespace="kube-system",
  node="cam-train-083",
  node_ip="10.98.66.38",
  pod="cambricon-mlu-monitor-topology-aware-v2b8j",
  prometheus="monitoring/vmagent",
  sn="8028002509100026",
  type="mlu590",
  uuid="26001009-2500-2880-0000-000000000000"
}
```

**唯一标识标签：** 物理 MLU 的设备身份使用 `(cluster, uuid)`；为兼容不同设备类型和虚拟实例，PromQL 关联时使用 `(cluster, uuid, type, vf)`。当前物理卡样本没有 `vf` 标签。

## 2.10 `mlu_memory_utilization`

这是一个 Gauge，单位为 `%`，由 Cambricon MLU Exporter 的 `cndev` collector 计算。物理卡模式下，Exporter 调用 `GetDeviceMemory()` 获取已用内存和总内存，并计算：

```text
mlu_memory_utilization = used / total × 100%
```

sMLU 模式使用实例的 `MemUsed / MemTotal × 100%`；MIM/VF 模式会读取相应实例的内存数据。部分共享模式可能把整卡内存利用率复制给多个 `vf`，因此带 `vf` 标签不一定意味着它是容器独立测得的内存占用比例。

该指标表示板上物理内存的使用比例，不是主机内存，也不是容器 RSS。

## 2.11 `mlu_power_usage`

这是一个 Gauge，单位为 W，由 Cambricon MLU Exporter 调用 CNDEV 的 `GetDevicePower()` 获取。Exporter 直接输出驱动返回的当前功耗，不会根据利用率、电压和电流重新推算。

物理卡模式下它表示整卡当前功耗。部分 env-share、MIM、sMLU 分支可能只是给不同 `vf` 标签复制相同的整卡功耗。因此，通过 `mlu_container` 映射后应理解为“该容器所使用的 MLU 设备当前功耗”，不一定是该容器独自产生的功耗；多个容器共享一张卡时，不能直接把各容器结果相加，否则可能重复计算。

## 2.12 `mlu_mlulink_cntr_read_byte_total`

这是一个 Counter，单位为 bytes，由 Cambricon MLU Exporter 的 `cndev` collector 提供。Exporter 遍历每张 MLU 的每条 MLULink，调用 `GetDeviceMLULinkCounter()`，直接输出硬件累计读取字节计数。

Exporter 不在这里计算带宽。当前 PromQL 使用 `rate(...[5m])` 将累计值转换为平均读取速率，单位为 `bytes/s`。该 metric 原生按 `uuid` 和 `link` 形成多条序列；如果后续没有按设备汇总，前端可能看到每条 Link 的独立结果。

```

mlu_mlulink_cntr_read_byte_total {
	cluster="bj-caip",driver="v6.2.28",
    endpoint="http-metrics",
    job="mlu-monitoring",
    link="0",mcu="v1.0.1",
    mlu="0",
    model="MLU590-M9DK",
    namespace="kube-system",
    node="cam-train-085",
    node_ip="10.98.66.40",
    pod="cambricon-mlu-monitor-topology-aware-vqf5k",
    prometheus="monitoring/vmagent",
    sn="8028002516101915",
    type="mlu590",
    uuid="15191016-2500-2880-0000-000000000000"
}
```

唯一标识标签：uuid，link

## 2.13 `mlu_mlulink_cntr_write_byte_total`

这是一个 Counter，单位为 bytes，采集方式与读取 Counter 相同，只是取 `GetDeviceMLULinkCounter()` 返回的累计写入字节字段。

当前 PromQL 对它执行 `rate(...[5m])` 后得到 MLULink 平均写入速率，单位为 `bytes/s`，再通过 `mlu_container` 补充容器归属标签。它同样是每条 Link 一条时间序列，而不是天然的整卡 MLULink 总带宽。

## 2.14 `mlu_container`

这是一个值为 0 或 1 的**关联型 Gauge**，由 Cambricon MLU Exporter 的 `podresources` collector 提供。它从 kubelet PodResources API 读取已分配设备与 `namespace`、`pod`、`container` 的关系：已分配给容器的设备记录值为 1，未分配设备可以输出 0。

它不表示利用率、设备数量或资源使用量。在下面的 PromQL 中，乘以值为 1 的 `mlu_container` 主要用于筛选设备并携带容器标签：

```promql
mlu_utilization
* on (uuid, type, vf)
group_right
mlu_container
```

因此，`mlu_container` 应理解为 PromQL 中的设备归属关系表，表示一个container在使用哪张具体的mlu，所以值为0或1

**以下3个gpu的指标应该是和mlu中相关指标对应的**

## 2.15 `dcgm_gpu_utilization`

这是一个 Gauge，单位为 `%`，由 NVIDIA DCGM Exporter 提供，表示 GPU 计算资源在采样周期内的活跃程度。当前环境中的该 metric 已携带 `cluster`、`namespace`、`pod`、`container` 标签，因此前端可以直接按容器筛选，不需要额外的设备归属关联指标。

前端又通过 `avg_over_time()` 对多个采样点求平均，所以页面展示的是指定时间窗口内的平均 GPU 利用率，而不是某个瞬时采样值。

```promql
dcgm_gpu_utilization{
  DCGM_FI_DRIVER_VERSION="570.133.20",
  UUID="GPU-0507ea85-00f6-f0b6-9db6-4c7f6a164c26",
  cluster="bj-caip",
  container="test-qwen-0-0-108",
  device="nvidia3",
  driver="570.133.20",
  endpoint="metrics",
  gpu="3",
  job="gpu-exporter",
  modelName="NVIDIA GeForce RTX 3090",
  namespace="ns-20a73d3287614958ac8d06fc41155c94",
  node="cambricon-train-011",
  pod="qwen3-30b-2507-3090-0-0-1-roleset-jl6qs-standalone-hdkvg",
  prometheus="monitoring/vmagent",
  type="rtx-3090"
}
```

**唯一标识标签：** GPU 设备身份使用 `(cluster, UUID)`；当指标已携带容器标签时，设备与业务容器的关系可由 `(cluster, UUID, namespace, pod, container)` 标识。`gpu` 和 `device` 是节点内编号，不宜脱离 `node` 或 `UUID` 单独使用。

## 2.16 `dcgm_gpu_memory_utilization`

这是一个 Gauge，单位为 `%`，由 NVIDIA DCGM Exporter 提供，表示 GPU 显存相关资源的利用率。需要注意，具体是“显存容量占用比例”还是“显存控制器/拷贝引擎活跃度”，取决于当前 DCGM Exporter 对该自定义 metric 名称所映射的底层 DCGM field；仅凭 metric 名称还不能完全确认。

当前前端对它做时间平均，并依赖其原生容器标签进行筛选。若要把语义精确到 DCGM field，应继续检查黄区 GPU Exporter 的 metrics 配置。

```promql
dcgm_gpu_memory_utilization{
  DCGM_FI_DRIVER_VERSION="570.133.20",
  UUID="GPU-0507ea85-00f6-f0b6-9db6-4c7f6a164c26",
  cluster="bj-caip",
  container="test-qwen-0-0-108",
  device="nvidia3",
  driver="570.133.20",
  endpoint="metrics",
  gpu="3",
  job="gpu-exporter",
  modelName="NVIDIA GeForce RTX 3090",
  namespace="ns-20a73d3287614958ac8d06fc41155c94",
  node="cambricon-train-011",
  pod="qwen3-30b-2507-3090-0-0-1-roleset-jl6qs-standalone-hdkvg",
  prometheus="monitoring/vmagent",
  type="rtx-3090"
}
```

**唯一标识标签：** GPU 设备身份使用 `(cluster, UUID)`；当指标已携带容器标签时，设备与业务容器的关系可由 `(cluster, UUID, namespace, pod, container)` 标识。

## 2.17 `dcgm_power_usage`

这是一个 Gauge，单位为 W，由 NVIDIA DCGM Exporter 提供，表示 GPU 当前功耗。当前指标原生携带容器相关标签，前端通过 `avg_over_time()` 得到查询窗口内的平均功耗。

如果一张 GPU 存在共享使用场景，也需要确认 Exporter 标签是否只是把设备级功耗关联到多个容器，避免把设备功耗误认为容器独占功耗。

## 2.18 `rdma_container`

这是一个0或1的关联指标，由 Cambricon RDMA Exporter 提供。它描述 一张具体rdma网卡(`cluster`、`node`、`device` )与一个具体容器( `namespace`、`pod`、`container`) 的对应关系，本身不包含 RDMA 收发流量。

当前 PromQL 使用它与 node-exporter 的 InfiniBand 端口 Counter 做向量匹配，从而把 Node 设备级流量映射到 Pod/container。它与 `mlu_container` 的作用类似，核心价值是提供归属标签。

```promql
rdma_container{
  cluster="bj-caip",
  container="deepseekv4-flash-0-0-9",
  device="mlx5_0",
  job="rdma-push-monitoring",
  namespace="ns-e23f5b20fb9b42d3ac674f9691a0b9b1",
  node="cam-train-075",
  pod="deepseek-v4-dp2tp4-0-0-1-roleset-22t4h-standalone-54b9d4-0-0"
}
```

**唯一标识标签：** 这条关联关系由 `(cluster, node, device, namespace, pod, container)` 唯一标识；其中 `(cluster, node, device)` 标识 RDMA 设备，后半部分标识使用它的容器。

## 2.19 `node_infiniband_port_data_received_bytes_total`

这是一个 Counter，单位为 bytes，由 node-exporter 提供，表示 Node 上某个 InfiniBand 设备端口累计接收的字节数。它原生观测的是 Node 和 device，而不是容器。

当前 PromQL 先使用 `rate(...[5m])` 得到端口平均接收速率，再按 `cluster`、`node`、`device` 与 `rdma_container` 关联，最终映射到容器。若同一个 device 被多个容器共享，映射后的值不一定能代表每个容器的独立流量。

```promql
node_infiniband_port_data_received_bytes_total{
  cluster="bj-caip",
  container="kube-rbac-proxy",
  device="bnxt_re0",
  endpoint="https",
  job="node-exporter",
  namespace="monitoring",
  node="cam-train-131",
  node_ip="10.98.66.131",
  pod="node-exporter-pwr7j",
  port="1",
  prometheus="monitoring/vmagent",
  service="node-exporter"
}
```

**唯一标识标签：** 被观测的 InfiniBand 端口由 `(cluster, node, device, port)` 标识。样本中的 `namespace`、`pod`、`container` 属于 node-exporter 自身，不是使用该 RDMA 端口的业务容器。

## 2.20 `node_infiniband_port_data_transmitted_bytes_total`

这是一个 Counter，单位为 bytes，同样由 node-exporter 提供，表示 Node 上某个 InfiniBand 设备端口累计发送的字节数。经过 `rate(...[5m])` 后，单位变为 `bytes/s`，表示端口平均发送速率。

它也需要通过 `rdma_container` 补充容器归属。最终数据的准确粒度取决于 RDMA device 是否由单个容器独占，不能仅因为结果带有 `pod/container` 标签，就断定底层流量已经按容器完成硬件级拆分。