# PromQL汇总

```TypeScript
export const containerMemoryUsage = `
sum by (cluster, pod, container) (
  avg_over_time(
    container_memory_working_set_bytes{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      container=~"%(container)s",
      pod=~"%(pod)s"
    }[%(time)s:30s]
  )
)
`;

export const containerCpuUsage = `
sum by (cluster, pod, container) (
  avg_over_time(
    rate(
      container_cpu_usage_seconds_total{
        cluster=~"%(cluster)s",
        namespace="%(namespace)s",
        container=~"%(container)s",
        pod=~"%(pod)s"
      }[5m]
    )[%(time)s:30s]
  )
)
`;

export const containerCpuUtilization = `
sum by (cluster, pod, container) (
  avg_over_time(
    rate(
      container_cpu_usage_seconds_total{
        cluster=~"%(cluster)s",
        namespace="%(namespace)s",
        container=~"%(container)s",
        pod=~"%(pod)s"
      }[5m]
    )[%(time)s:30s]
  )
)
/
sum by (cluster, pod, container) (
  kube_pod_container_resource_limits{
    cluster=~"%(cluster)s",
    resource="cpu",
    namespace="%(namespace)s",
    container=~"%(container)s",
    pod=~"%(pod)s"
  }
)
* 100
`;


// NetworkTransmitBytes only support pod.
// Avoid using the filter 'container!=""' as containerd does not append this label
// to sandbox containers.
// https://github.com/containerd/cri/issues/922
export const containerNetworkTransmitBytes = `
sum by (cluster, pod, container) (
  avg_over_time(
    rate(
      container_network_transmit_bytes_total{
        cluster=~"%(cluster)s",
        namespace="%(namespace)s",
        pod=~"%(pod)s"
      }[5m]
    )[%(time)s:30s]
  )
)
`;


// NetworkReceiveBytes only support pod.
// Avoid using the filter 'container!=""' as containerd does not append this label
// to sandbox containers.
// https://github.com/containerd/cri/issues/922
export const containerNetworkReceiveBytes = `
sum by (cluster, pod, container) (
  avg_over_time(
    rate(
      container_network_receive_bytes_total{
        cluster=~"%(cluster)s",
        namespace="%(namespace)s",
        pod=~"%(pod)s"
      }[5m]
    )[%(time)s:30s]
  )
)
`;

export const containerMluUtilization = `
avg_over_time(
  mlu_utilization{
    cluster=~"%(cluster)s"
  }[%(time)s:30s]
)
*
on (uuid, type, vf)
group_right
mlu_container{
  cluster=~"%(cluster)s",
  namespace="%(namespace)s",
  pod=~"%(pod)s",
  container=~"%(container)s"
}
`;

export const containerMluMemUtilization = `
avg_over_time(
  mlu_memory_utilization{
    cluster=~"%(cluster)s"
  }[%(time)s:30s]
)
*
on (uuid, type, vf)
group_right
mlu_container{
  cluster=~"%(cluster)s",
  namespace="%(namespace)s",
  pod=~"%(pod)s",
  container=~"%(container)s"
}
`;

export const containerMluPowerConsumption = `
avg_over_time(
  mlu_power_usage{
    cluster=~"%(cluster)s"
  }[%(time)s:30s]
)
*
on (uuid, type, vf)
group_right
mlu_container{
  cluster=~"%(cluster)s",
  namespace="%(namespace)s",
  pod=~"%(pod)s",
  container=~"%(container)s"
}
`;

export const containerMluLinkReadBytes = `
avg_over_time(
  rate(
    mlu_mlulink_cntr_read_byte_total{
      cluster=~"%(cluster)s"
    }[5m]
  )[%(time)s:30s]
)
*
on (uuid, type)
group_left(namespace, pod, container)
mlu_container{
  cluster=~"%(cluster)s",
  namespace="%(namespace)s",
  pod=~"%(pod)s",
  container=~"%(container)s"
}
`;

export const containerMluLinkWriteBytes = `
avg_over_time(
  rate(
    mlu_mlulink_cntr_write_byte_total{
      cluster=~"%(cluster)s"
    }[5m]
  )[%(time)s:30s]
)
*
on (uuid, type)
group_left(namespace, pod, container)
mlu_container{
  cluster=~"%(cluster)s",
  namespace="%(namespace)s",
  pod=~"%(pod)s",
  container=~"%(container)s"
}
`;

export const containerGpuUtilization = `
avg_over_time(
  dcgm_gpu_utilization{
    cluster=~"%(cluster)s",
    container=~"%(container)s",
    namespace="%(namespace)s",
    pod=~"%(pod)s"
  }[%(time)s:30s]
)
`;

export const containerGpuMemUtilization = `
avg_over_time(
  dcgm_gpu_memory_utilization{
    cluster=~"%(cluster)s",
    container=~"%(container)s",
    namespace="%(namespace)s",
    pod=~"%(pod)s"
  }[%(time)s:30s]
)
`;

export const containerGpuPowerConsumption = `
avg_over_time(
  dcgm_power_usage{
    cluster=~"%(cluster)s",
    container=~"%(container)s",
    namespace="%(namespace)s",
    pod=~"%(pod)s"
  }[%(time)s:30s]
)
`;

export const containerRdmaReceivedBytes = `
(
  sum by (cluster, node, pod, container, device) (
    rdma_container{
      cluster=~"%(cluster)s",
      container=~"%(container)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s"
    }
  )
)
*
on (cluster, node, device)
group_left()
(
  sum by (cluster, node, device) (
    avg_over_time(
      rate(
        node_infiniband_port_data_received_bytes_total{
          cluster=~"%(cluster)s"
        }[5m]
      )[%(time)s:30s]
    )
  )
)
`;

export const containerRdmaTransmittedBytes = `
(
  sum by (cluster, node, pod, container, device) (
    rdma_container{
      cluster=~"%(cluster)s",
      container=~"%(container)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s"
    }
  )
)
*
on (cluster, node, device)
group_left()
(
  sum by (cluster, node, device) (
    avg_over_time(
      rate(
        node_infiniband_port_data_transmitted_bytes_total{
          cluster=~"%(cluster)s"
        }[5m]
      )[%(time)s:30s]
    )
  )
)
`;

export const containerDiskReadBytes = `
sum by (cluster, pod, container) (
  avg_over_time(
    rate(
      container_fs_reads_bytes_total{
        cluster=~"%(cluster)s",
        namespace="%(namespace)s",
        pod=~"%(pod)s",
        container=~"%(container)s"
      }[5m]
    )[%(time)s:30s]
  )
)
`;

export const containerDiskWriteBytes = `
sum by (cluster, pod, container) (
  avg_over_time(
    rate(
      container_fs_writes_bytes_total{
        cluster=~"%(cluster)s",
        namespace="%(namespace)s",
        pod=~"%(pod)s",
        container=~"%(container)s"
      }[5m]
    )[%(time)s:30s]
  )
)
`;
```

# 硬件性能指标

前端展示的一个硬件指标，通常不是单个原始 metric，而是以下环节的组合：

```text
前端指标 = 原始 metric + 时间统计 + 标签聚合
         + 设备与容器的归属映射（可选）+ 指标间计算（可选）
```

因此，本文不再逐条重复解释每条 PromQL，而是分成两部分：

1. **统计范式**：PromQL 如何把原始样本计算成前端展示值。
2. **具体 metric 指标**：每个 metric 由谁提供、类型、单位、含义及观测对象。