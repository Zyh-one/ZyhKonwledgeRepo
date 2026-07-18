# NVIDIA MPS：定位与基本认知

## 1. MPS 是什么

这里的 **MPS** 指的是 **NVIDIA CUDA Multi-Process Service**，不是 Apple 的 MPS。

可以先用一句话理解：

> **MPS 是 NVIDIA 在 CUDA/Driver 体系中提供的 GPU 多进程共享与协调机制，用来让多个 CUDA 进程更高效地共享同一张 GPU。**

它解决的不是“GPU 能不能被多个进程访问”的问题，因为没有 MPS 时，多个 CUDA 进程本来就可以访问同一张 GPU。MPS 主要解决的是：

1. 多个 CUDA 进程之间的 context 切换开销；
2. 单个进程 kernel 没有用满 GPU 时，其他进程难以补上空闲 SM 的问题；
3. 多进程场景下 GPU 计算资源利用率不足的问题；
4. 对 CUDA client 的计算资源进行粗粒度限制，例如 `CUDA_MPS_ACTIVE_THREAD_PERCENTAGE`。

---

## 2. 没有 MPS 时，GPU 多进程如何工作

没有 MPS 时，可以将流程理解为：

```text
进程 A -> CUDA context A -> GPU
进程 B -> CUDA context B -> GPU
进程 C -> CUDA context C -> GPU
```

每个 CUDA 进程通常会有自己的 CUDA context。CUDA context 可以理解为该进程在 GPU 上执行所需的一套状态和资源，包括显存管理、stream、kernel launch 相关状态等。

当多个进程同时使用同一张 GPU 时，GPU/Driver scheduler 通常会在不同 CUDA context 之间进行调度。直观上可以理解为：

```text
时间片 1：执行 context A 的 GPU work
时间片 2：执行 context B 的 GPU work
时间片 3：执行 context C 的 GPU work
```

因此，在没有 MPS 的普通 CUDA 多进程场景下，可以先采用这个直观模型：

> **同一时间片内，GPU compute engine 通常主要服务于某一个 CUDA context。即便这个 context 内的 kernel 没有用满所有 SM，其他进程的 context 也通常不能像同一 context 内的 stream 那样直接补上空闲 SM。**

这也是 MPS 有意义的根本原因。

---

## 3. CUDA context 是什么时候创建的

一个进程要使用 GPU，通常需要先创建或绑定 CUDA context。

如果使用 CUDA Driver API，可能会显式调用：

```cpp
cuCtxCreate(...)
```

但在 PyTorch、SGLang、vLLM、CUDA Runtime API 中，CUDA context 通常是隐式创建的。例如第一次调用：

```python
import torch

torch.empty((1024, 1024), device="cuda")
model.to("cuda")
```

或者 C++ 中第一次调用：

```cpp
cudaSetDevice(0);
cudaMalloc(...);
```

都可能触发 CUDA runtime 初始化，并为当前进程在对应 GPU 上创建或绑定 CUDA context。

整体流程可以理解为：

```text
进程启动
  ↓
第一次调用 CUDA API / PyTorch CUDA 操作
  ↓
创建或绑定 CUDA context
  ↓
kernel / cudaMemcpy / cudaMalloc 等 GPU work 被提交到 context 的 stream / queue
  ↓
GPU/Driver scheduler 调度这些 work
```

---

## 4. 有 MPS 后发生了什么

启动 MPS 后，多个 CUDA 进程会作为 MPS client 接入 MPS server：

```text
进程 A -> MPS client \
进程 B -> MPS client  -> MPS server -> GPU
进程 C -> MPS client /
```

从用户代码角度看，通常不需要修改代码。SGLang、PyTorch、CUDA 程序仍然正常调用 CUDA API。只要后续启动的 CUDA 进程能够连接到同一个 MPS daemon，它会在初始化 CUDA 时自动通过 CUDA Driver 内置的 MPS client runtime 接入 MPS。

更准确的流程是：

```text
启动 MPS control daemon
  ↓
后续启动 Python / SGLang / CUDA 进程
  ↓
第一次调用 CUDA
  ↓
CUDA Driver 发现 MPS daemon 可用
  ↓
该进程作为 MPS client 接入 MPS server
  ↓
后续 GPU work 受 MPS 协调
```

MPS 的主要效果是：

1. 减少不同 CUDA context 之间的切换开销；
2. 让多个进程的 kernel 更容易共同填充 GPU 资源；
3. 提高多进程共享同一 GPU 时的利用率；
4. 通过 `CUDA_MPS_ACTIVE_THREAD_PERCENTAGE` 对计算资源进行粗粒度限制。

---

## 5. MPS 是不是运行在 GPU 上

不是。

MPS 是 NVIDIA 自己开发并集成在 CUDA/Driver 体系中的机制，但 **MPS control daemon 和 MPS server 主要是 CPU 侧的 Linux 进程**。

例如启动命令：

```bash
nvidia-cuda-mps-control -d
```

会在 CPU 侧启动 MPS control daemon。可以通过下面命令查看：

```bash
ps aux | grep mps
```

通常会看到类似：

```text
nvidia-cuda-mps-control
nvidia-cuda-mps-server
```

这些是主机侧进程，不是运行在 GPU SM 上的 CUDA kernel。

更准确的结构是：

```text
CPU 侧：

Python / SGLang 进程
        ↓
CUDA Driver + MPS client runtime
        ↓
MPS control daemon / MPS server

GPU 侧：

执行 CUDA kernels
执行 memcpy / compute work
由 GPU scheduler / hardware 执行底层调度
```

所以可以总结为：

> **MPS 的控制和协调逻辑主要运行在 CPU 侧；GPU 侧负责执行被提交后的 CUDA work，并配合 NVIDIA Driver / GPU scheduler 完成底层调度。**

---

## 6. MPS client 中是否还保留 CUDA context

需要避免一个误解：

> MPS 并不意味着所有 CUDA context 都被完整搬到 MPS server 里。

在现代 NVIDIA GPU，尤其是 Volta 及之后的架构中，MPS client 进程仍然保留自己的 CUDA context 和 GPU address space。MPS server 更多是负责协调共享资源、调解多个 client 的执行，而不是完全代替 client 保存所有状态。

可以这样理解：

```text
MPS client 进程：
    保留自己的 CUDA context
    保留自己的 GPU address space
    通过 CUDA Driver 与 MPS server 协调

MPS server：
    负责协调多个 client
    管理/调解共享调度资源
    支持 active thread percentage 等限制
```

所以更准确的图是：

```text
进程 A -> CUDA context A -> MPS client runtime \
进程 B -> CUDA context B -> MPS client runtime  -> MPS server -> GPU
进程 C -> CUDA context C -> MPS client runtime /
```

---

## 7. MPS 是否会自动管控所有 GPU 进程

不能简单说“所有 GPU 进程都会被 MPS 管控”。更准确是：

> **后续启动的、能够连接到同一个 MPS daemon 的 CUDA 进程，会在应用无感知的情况下作为 MPS client 接入 MPS server。**

需要满足几个条件：

1. 进程是后续启动的 CUDA 进程；
2. 进程尚未在 MPS 启动前创建好 CUDA context；
3. 进程能够找到同一个 `CUDA_MPS_PIPE_DIRECTORY`；
4. 进程所在用户、容器、权限环境允许连接该 MPS daemon；
5. workload 是 CUDA compute work，而不是图形桌面、视频编码等其他 GPU workload。

因此，从 SGLang / PyTorch 程序角度看，通常是无感知的，但不是系统上所有 GPU 进程都会无条件进入 MPS。

---

## 8. MPS 主要管什么资源

MPS 主要管的是 GPU 计算执行资源，而不是推理框架内部的显存分配策略。

在 profiling 脚本中，核心参数是：

```bash
export CUDA_MPS_ACTIVE_THREAD_PERCENTAGE=$percentage
```

它主要影响的是：

```text
kernel 执行速度
SM 利用率
compute-bound 阶段耗时
prefill / decode 中偏计算部分的吞吐
```

但是它不会直接决定：

```text
模型权重占多少显存
KV Cache pool 分配多大
PyTorch caching allocator 如何缓存显存
SGLang 的 mem_fraction_static / max_total_tokens 如何划分显存
多个进程之间是否共享模型权重
```

即使设置：

```bash
CUDA_MPS_ACTIVE_THREAD_PERCENTAGE=20
```

也不代表该进程只能使用 20% 显存。它仍然可能加载完整模型权重，申请完整 KV Cache pool，甚至出现 OOM。

更准确的区分是：

```text
MPS：偏计算资源调节，尤其是 SM / active thread 限制
SGLang 参数：偏运行时调度、显存池、KV Cache 容量管理
CUDA_VISIBLE_DEVICES：控制进程能看到哪些 GPU
MIG：硬件级 GPU 资源切分和隔离
```

---

## 9. 放到当前课题中的定位

在当前推理系统 profiling / 动态调节课题中，MPS 可以被定位为一种 **纵向资源调节手段**。

它不是横向扩缩容，也不是修改 SGLang 内部调度策略，而是在进程外部对 GPU 计算资源进行约束。

在实验中，可以用它模拟不同 GPU 计算资源条件：

```text
100% SM：完整 GPU 计算资源
80% SM：轻微受限
50% SM：中等受限
20% SM：严重受限
10% SM：极端受限
```

然后观察：

```text
TTFT 如何变化
TPOT 如何变化
吞吐如何变化
SLO 违约率是否升高
max_running_requests 的合适取值是否发生变化
prefill-heavy 和 decode-heavy 场景对 SM 限制的敏感度是否不同
```

---

## 10. 一句话总结

> **MPS 是 NVIDIA CUDA/Driver 体系提供的 GPU 多进程共享与计算资源协调机制。没有 MPS 时，多进程主要在 CUDA context 之间 time-slicing；有 MPS 后，多个 CUDA client 可以通过 MPS server 更高效地共享 GPU，并可以通过 active thread percentage 对计算资源进行粗粒度限制。但 MPS 主要影响计算执行资源，不负责推理框架内部的显存/KV Cache 分配策略。**
