# GPU 集群构建与模型部署简版

## 1. 核心结论

构建 GPU 集群的目标不是“让模型能跑”，而是让模型服务可以稳定上线、持续运行、方便排障、能逐步扩展。

最推荐的方向：

```text
Kubernetes 管集群
NVIDIA GPU Operator 接 GPU
vLLM / SGLang 跑模型
Gateway / Router 对外提供服务
Prometheus / Grafana 做监控
```

不要一开始堆太多组件。先跑通稳定推理服务，再补调度、灰度、自动扩缩容、多租户和成本优化。

---

## 2. 整体架构

可以把 GPU 集群分成五层：

```text
用户 / 业务系统
    ↓
网关层：Ingress / Gateway / Envoy / Nginx
    ↓
模型层：vLLM / SGLang / TensorRT-LLM
    ↓
集群层：Kubernetes / Kueue / Volcano / Ray
    ↓
GPU 层：Driver / CUDA / Device Plugin / GPU Operator / DCGM
    ↓
硬件层：GPU 服务器 / 高速网络 / 本地 NVMe / 共享存储
```

各层职责：

| 层 | 负责什么 |
|---|---|
| 硬件层 | GPU、CPU、内存、NVMe、高速网络 |
| GPU 层 | 让容器和 K8s 能识别、使用、监控 GPU |
| 集群层 | 调度 Pod / Job，管理资源和生命周期 |
| 模型层 | 加载模型，处理请求，管理 KV Cache 和 batch |
| 网关层 | 鉴权、限流、路由、灰度、日志、计费 |

---

## 3. 最小落地方案

从 0 到 1 建议只上这些：

| 组件 | 作用 |
|---|---|
| Kubernetes | 管节点、Pod、Service、Deployment |
| NVIDIA GPU Operator | 安装和管理 GPU 相关组件 |
| DCGM Exporter | 暴露 GPU 监控指标 |
| Prometheus / Grafana | 采集和展示监控 |
| vLLM 或 SGLang | 部署大模型推理服务 |
| Ingress / Gateway | 对外暴露 API |

这套已经能支撑一个基本可用的 GPU 推理集群。

暂时可以不急着上：

- Kueue；
- Volcano；
- Ray / KubeRay；
- Istio；
- Argo Rollouts；
- 复杂的 Model Router。

这些是后续增强项，不是第一步必需项。

---

## 4. 建设流程

### 4.1 先验收机器

先确认 GPU、驱动、网络、存储正常。

常用检查：

```bash
nvidia-smi
nvidia-smi topo -m
nvcc --version
ibstat
ibv_devinfo
nccl-tests/all_reduce_perf
fio
```

重点看：

- GPU 是否可见；
- 驱动和 CUDA 是否匹配；
- 多卡拓扑是否正常；
- 多机 NCCL 通信是否正常；
- 本地 NVMe / 共享存储性能是否够用。

网络非常关键。多机训练、多机推理基本都依赖 InfiniBand / RoCE / NCCL。

### 4.2 再搭 Kubernetes

Kubernetes 负责把多台 GPU 机器变成统一资源池。

关键动作：

- 安装 Kubernetes / RKE2 / kubeadm / 托管 K8s；
- 配置 containerd；
- 配置 CNI，例如 Calico / Cilium；
- 配置 CSI 存储；
- 给 GPU 节点打 label 和 taint。

示例：

```bash
kubectl label node gpu-node-01 accelerator=nvidia-gpu
kubectl taint node gpu-node-01 nvidia.com/gpu=true:NoSchedule
```

模型 Pod 通过 `nodeSelector` 和 `tolerations` 调度到 GPU 节点。

### 4.3 接入 GPU

推荐直接使用 NVIDIA GPU Operator。它可以统一管理：

- NVIDIA Driver；
- NVIDIA Container Toolkit；
- NVIDIA Device Plugin；
- GPU Feature Discovery；
- DCGM Exporter。

验证：

```bash
kubectl describe node <gpu-node> | grep -A5 nvidia.com/gpu
kubectl get pods -n gpu-operator
```

Pod 内也要能正常执行：

```bash
nvidia-smi
```

### 4.4 部署模型服务

模型推理优先看：

| 框架 | 说明 |
|---|---|
| vLLM | 生态成熟，OpenAI API 兼容好，适合通用推理 |
| SGLang | 性能强，适合结构化生成、多节点推理和实验 |
| TensorRT-LLM | NVIDIA 官方高性能方案，优化深但集成成本更高 |

部署时重点关注：

- 模型权重路径；
- GPU 数量；
- tensor parallel / pipeline parallel；
- 显存使用比例；
- 最大上下文长度；
- 最大并发请求数；
- batch token 上限；
- metrics 暴露。

典型 GPU 资源申请：

```yaml
resources:
  limits:
    nvidia.com/gpu: 1
```

### 4.5 接入网关和监控

模型能跑之后，马上补网关和监控。

请求链路：

```text
Client
  ↓
Gateway / Ingress
  ↓
鉴权 / 限流 / 日志
  ↓
Model Service
  ↓
vLLM / SGLang Pod
  ↓
GPU
```

必须监控：

| 类型 | 关键指标 |
|---|---|
| 节点 | CPU、内存、磁盘、网络、Pod 重启 |
| GPU | 利用率、显存、功耗、温度、XID、ECC |
| 模型 | QPS、TTFT、TPOT、吞吐、队列、KV Cache |
| 业务 | P95/P99、错误率、token 消耗、SLO |

LLM 推理不能只看 GPU 利用率。TTFT、TPOT、queue length 和 KV Cache 更能反映服务质量。

---

## 5. GPU 使用方式怎么选

| 场景 | 推荐方式 |
|---|---|
| 大模型在线推理 | 独占 GPU 或多卡独占 |
| 大模型训练 | 多卡独占或多节点独占 |
| 小模型推理 | MIG 或 Time-Slicing |
| embedding / reranker | MIG、Time-Slicing 或小卡独占 |
| 开发测试 | Time-Slicing 或 MPS |
| 强隔离多租户 | MIG |

简单判断：

- **独占 GPU**：最稳定，适合大模型和强 SLO；
- **MIG**：硬件切分，隔离更强，适合小模型和多租户；
- **Time-Slicing**：时间片共享，简单但隔离弱；
- **MPS**：多个 CUDA 进程共享 GPU，适合实验。

建议：大模型在线推理优先独占 GPU。不要太早上共享，容易引入延迟抖动、显存抢占和排障复杂度。

---

## 6. 什么时候需要高级调度

第一阶段用 Kubernetes 默认调度器即可。

出现这些需求后，再引入额外组件：

| 需求 | 组件 |
|---|---|
| 多团队共享 GPU、队列、quota | Kueue |
| 分布式训练，需要多个 Pod 同时启动 | Volcano |
| PyTorch / TensorFlow 训练任务 | Kubeflow Training Operator |
| Ray 生态任务 | KubeRay |
| HPC 作业体系 | Slurm |

判断标准：

- 只是部署在线推理：默认 K8s 调度器够用；
- 有大量训练和 batch inference：考虑 Kueue；
- 有 gang scheduling：考虑 Volcano；
- 已经使用 Ray：考虑 KubeRay；
- 已有超算 / HPC 体系：考虑 Slurm。

---

## 7. 大模型推理最该关注什么

### 7.1 显存

显存主要消耗在：

- 模型权重；
- KV Cache；
- runtime buffer；
- batch 中间状态；
- CUDA Graph 等优化结构。

上下文越长、并发越高、batch token 越大，显存压力越大。

### 7.2 延迟

重点看四个指标：

| 指标 | 含义 |
|---|---|
| TTFT | 首 token 延迟 |
| TPOT | 后续 token 平均延迟 |
| E2E latency | 请求总耗时 |
| queue length | 请求排队长度 |

TTFT 高，通常和排队、prefill、长上下文有关。

TPOT 高，通常和 decode、batch、GPU 负载有关。

### 7.3 路由

普通负载均衡只知道 Pod 是否可用，不知道模型实例内部状态。

更好的 Model Router 应该逐步感知：

- waiting queue；
- running requests；
- KV Cache 使用率；
- prefix cache 命中；
- TTFT / TPOT；
- GPU 显存和利用率；
- 模型版本和 LoRA adapter。

这也是后续 AI Infra 优化的重要方向。

---

## 8. 推荐推进路线

### 阶段一：跑通

目标：能在 K8s 上部署一个稳定的 GPU 模型服务。

做这些：

- Kubernetes；
- GPU Operator；
- vLLM / SGLang；
- Service / Ingress；
- Prometheus / Grafana。

### 阶段二：稳定

目标：能长期给业务调用。

补这些：

- 鉴权；
- 限流；
- 日志；
- 告警；
- 模型权重缓存；
- 实例预热；
- 灰度发布；
- 快速回滚。

### 阶段三：优化

目标：提高 GPU 利用率，降低成本，保障 SLO。

再做这些：

- Kueue / Volcano；
- Model Router；
- TTFT / TPOT 感知路由；
- KV Cache 感知调度；
- MIG / Time-Slicing / MPS 实验；
- 自动扩缩容；
- 多模型、多版本、多租户治理。

---

## 9. 学习顺序

建议按这个顺序学：

```text
1. Kubernetes 基础
2. NVIDIA GPU 接入 Kubernetes
3. GPU 独占 / MIG / Time-Slicing / MPS
4. DCGM + Prometheus + Grafana
5. vLLM / SGLang
6. Gateway / Router / 限流 / 灰度
7. Kueue / Volcano / Ray / Slurm
8. TTFT / TPOT / KV Cache / batch 优化
```

---

## 10. 最终判断

最稳的建设路径是：

> 先把 GPU 集群做成一个稳定的模型服务平台，再考虑复杂调度和资源共享。

过早堆组件，会让系统看起来完整，但排障和维护会变得很重。

真正优先级应该是：

```text
能部署 → 能监控 → 能稳定调用 → 能灰度回滚 → 能调度优化 → 能成本优化
```

---

## 11. 参考资料

- Kubernetes：https://kubernetes.io/
- NVIDIA GPU Operator：https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/index.html
- NVIDIA Device Plugin：https://github.com/NVIDIA/k8s-device-plugin
- NVIDIA DCGM Exporter：https://docs.nvidia.com/datacenter/dcgm/latest/gpu-telemetry/dcgm-exporter.html
- Kueue：https://kueue.sigs.k8s.io/
- Volcano：https://volcano.sh/
- vLLM：https://docs.vllm.ai/
- SGLang：https://docs.sglang.ai/
