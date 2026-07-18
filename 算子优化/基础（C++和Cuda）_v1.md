

**大致思路**：

1. 什么是算子？算子在实际生产场景中是如何发挥作用？算子和核函数的对比；可以适当以pytorch框架举例强调“pytorch实际就是对算子的封装”
2. 为什么需要自定义算子？这一部分可以利用flash-attention，triton等框架，简单强调这些框架大致做了啥？
3. 基础环境配置（C++和Cuda），不用强调python的环境配置；
4. C++的编译流程，Cmake构建流程，kernel launch等cpu端侧逻辑
5. Cuda执行模型
   1. grid，block，thread，wrap，SM等基础概念
   2. sharedMem，cuda stream
6. C++和Cuda的整体执行链路
7. python和 C++(cuda)的配合使用
8. 总结

V1 (2026.6.22)

# 算子编写基础篇章总结

## 1. 什么是算子？

在深度学习框架中，**算子**可以理解为一个具体的计算操作。

例如：加法、矩阵乘法、卷积、LayerNorm、Softmax、Attention 等，都可以看作算子。

如果把一个深度学习模型比作一条生产流水线，那么每个算子就是流水线上的一个加工步骤：

```text
输入数据 → 算子 A → 中间结果 → 算子 B → 中间结果 → 算子 C → 输出结果
```

例如在神经网络中，一次前向传播可能包含：

```text
Embedding → MatMul → Attention → LayerNorm → MLP → 输出
```

这里的每一步，底层都对应着一个或多个算子。

因此，算子并不是一个抽象难懂的概念。它本质上就是深度学习模型中的基本计算单元。

---

## 2. 算子和核函数的区别

算子和核函数经常一起出现，但它们不是同一个概念。

**算子更偏向上层语义。**

例如：

- 我要做一个矩阵乘法；
- 我要做一个 Softmax；
- 我要做一个 LayerNorm。

这些描述关注的是“我要完成什么计算”。

**核函数更偏向底层实现。**

在 CUDA 编程中，真正运行在 GPU 上的函数通常叫做 kernel，也就是核函数。

可以简单理解为：

```text
算子：我要完成什么计算
核函数：我具体如何在 GPU 上完成这个计算
```

举个例子：

```text
算子：矩阵乘法
核函数：让 GPU 上的大量 thread 分别计算矩阵中的不同区域
```

一个算子底层可能只对应一个 kernel，也可能对应多个 kernel。

例如，一个复杂的 Attention 算子，可能包含多个阶段：

```text
QK^T 计算 → Mask 处理 → Softmax → 乘以 V → 输出结果
```

这些阶段既可以拆成多个 kernel，也可以通过优化手段融合成更少的 kernel。

---

## 3. PyTorch 和算子的关系

平时我们在 PyTorch 中写代码时，经常会使用类似这样的操作：

- `torch.matmul`
- `torch.add`
- `torch.softmax`
- `torch.nn.LayerNorm`

从用户视角看，这些只是简单的 Python API。

但是从框架底层看，它们本质上都是对算子的封装。

也就是说，PyTorch 帮我们把复杂的底层细节隐藏了起来：

```text
Python API
  ↓
PyTorch 算子接口
  ↓
C++ 后端逻辑
  ↓
CUDA kernel
  ↓
GPU 执行
```

所以可以这样理解：

> PyTorch 不是魔法。PyTorch 的很多能力，本质上来自它对大量高性能算子的封装。

我们平时调用一行 `torch.matmul()`，背后可能已经经过了调度、类型检查、设备判断、kernel 选择、显存访问和 GPU 并行计算。

---

## 4. 为什么需要自定义算子？

既然 PyTorch 已经提供了很多算子，为什么还需要自定义算子？

主要原因有三个。

### 4.1 框架自带算子不一定满足特殊需求

有些模型结构比较特殊，已有框架可能没有直接提供对应算子。

此时如果只用 PyTorch 的基础 API 拼接，虽然能实现功能，但可能性能不好。

例如，多个小操作连续执行时，每一步都可能需要读写显存，并产生中间结果。这样会带来额外开销。

自定义算子可以把多个操作合并起来，减少不必要的中间过程。

---

### 4.2 自定义算子可以提升性能

GPU 的计算速度很快，但显存访问、kernel 启动、线程组织不合理都会造成性能浪费。

自定义算子的目标通常不是“把功能写出来”这么简单，而是进一步思考：

- 如何减少显存访问？
- 如何提高数据复用？
- 如何减少 kernel launch 次数？
- 如何让更多 thread 有效工作？
- 如何更好地利用 shared memory？

这也是高性能算子优化的核心。

---

### 4.3 大模型推理需要更高效的算子

在大模型推理场景中，算子性能会直接影响整体推理效率。

例如：

- Attention 算子影响长上下文处理能力；
- KVCache 相关算子影响 decode 速度；
- LayerNorm / RMSNorm 影响每层计算开销；
- MatMul 影响整体吞吐。

因此，在 AI Infra 和推理系统中，算子优化不是一个孤立问题，而是和模型性能、吞吐、延迟、显存利用率直接相关。

---

## 5. FlashAttention 和 Triton 大致做了什么？

### 5.1 FlashAttention

FlashAttention 的核心思想是优化 Attention 的计算方式。

普通 Attention 中，可能会显式生成较大的注意力矩阵：

```text
QK^T → Softmax → Attention Score × V
```

当序列长度很长时，中间矩阵会非常大，显存访问压力很高。

FlashAttention 的重要思想是：

> 不把所有中间结果都完整写回显存，而是分块计算，并尽量在片上存储中复用数据。

可以类比为：

```text
普通 Attention：先把所有中间材料都搬到仓库，再统一加工。
FlashAttention：边搬、边算、边合并，尽量减少来回搬运。
```

所以 FlashAttention 的关键价值不是改变 Attention 的数学含义，而是改变 Attention 的底层计算组织方式，让它更加适合 GPU 执行。

---

### 5.2 Triton

Triton 是一个用于编写高性能 GPU kernel 的编程语言和编译框架。

它的目标是降低 CUDA kernel 编写的复杂度。

传统 CUDA 编程需要开发者直接管理很多底层细节，比如：

- thread 如何组织；
- block 如何划分；
- shared memory 如何使用；
- 访存是否连续；
- 同步是否正确。

Triton 则提供了一种更接近“块级计算”的写法。

可以简单理解为：

```text
CUDA：你直接指挥每个工人怎么干活。
Triton：你描述每个小组要处理哪块任务，底层帮你生成 GPU 执行代码。
```

因此，Triton 在大模型推理框架中非常常见，很多算子可以用 Triton 更快地实现原型，并获得不错的性能。

---

## 6. 基础环境配置：C++ 和 CUDA

学习自定义算子，最基础的环境通常包括两部分：

```text
C++ 编译环境
CUDA 编译环境
```

### 6.1 C++ 环境

C++ 主要负责 CPU 端逻辑，例如：

- 参数检查；
- Tensor 形状判断；
- kernel launch 配置；
- 和 Python 层绑定。

常见工具包括：

- `g++`
- `cmake`
- `make`

### 6.2 CUDA 环境

CUDA 主要负责 GPU 端代码编译和执行。

常见工具包括：

- `nvcc`
- CUDA Toolkit
- NVIDIA Driver

这里需要区分两个概念：

```text
NVIDIA Driver：让系统能使用 GPU
CUDA Toolkit：提供 CUDA 编译器、头文件、库文件等开发工具
```

如果只是运行别人已经编译好的程序，可能只需要驱动。

但如果要自己编写和编译 CUDA kernel，通常需要 CUDA Toolkit，尤其是 `nvcc` 编译器。

---

## 7. C++ 编译流程

C++ 程序从源码到可执行文件，大致会经历几个阶段：

```text
源码
  ↓
预处理
  ↓
编译
  ↓
汇编
  ↓
链接
  ↓
可执行文件或动态库
```

在普通项目中，源文件可能很少，直接用命令编译即可。

但在实际工程中，文件通常很多，例如：

- 多个 `.cpp` 文件；
- 多个 `.cu` 文件；
- 多个头文件；
- 多个第三方库。

这时候就需要构建系统来管理编译流程。

---

## 8. CMake 构建流程

CMake 可以理解为一个“工程构建说明书生成器”。

它本身通常不直接编译代码，而是根据 `CMakeLists.txt` 生成真正的构建文件。

大致流程是：

```text
编写 CMakeLists.txt
  ↓
cmake 配置项目
  ↓
生成 Makefile 或 Ninja 文件
  ↓
make / ninja 编译
  ↓
生成可执行文件或动态库
```

在自定义算子项目中，CMake 主要负责：

- 指定 C++ 标准；
- 找到 CUDA 环境；
- 找到 PyTorch 相关库；
- 编译 C++ 文件；
- 编译 CUDA 文件；
- 链接最终动态库。

可以把 CMake 类比为“项目施工图”。

编译器负责真正施工，而 CMake 负责告诉编译器：

```text
有哪些文件要编译
依赖哪些库
最终产物叫什么
如何链接在一起
```

---

## 9. kernel launch：CPU 如何启动 GPU 计算？

CUDA kernel 虽然运行在 GPU 上，但它通常是由 CPU 端代码启动的。

这个过程叫做 kernel launch。

可以简单理解为：

```text
CPU 负责下达任务
GPU 负责并行执行任务
```

CPU 在启动 kernel 时，需要告诉 GPU 几件事：

- 启动多少个 block；
- 每个 block 有多少个 thread；
- 需要多少 shared memory；
- 使用哪个 CUDA stream；
- kernel 参数是什么。

例如在一维向量加法中，CPU 端会先计算：

- 数据有多少个元素；
- 每个 block 放多少个 thread；
- 总共需要多少个 block。

然后再启动 GPU kernel。

所以，自定义算子中 CPU 端逻辑非常重要。它不是直接参与大量计算，而是负责组织任务、检查参数和启动 kernel。

---

## 10. CUDA 执行模型

CUDA 的执行模型可以从几个核心概念理解：

```text
Grid
Block
Thread
Warp
SM
```

### 10.1 Grid

Grid 是一次 kernel launch 启动的整体任务。

可以把 grid 理解为一个完整工程项目。

例如，处理一个长度为 100000 的向量，这整个任务就是一个 grid。

---

### 10.2 Block

Block 是 grid 内部的任务小组。

一个 grid 中可以包含很多 block。

可以类比为：

```text
Grid：整个工厂任务
Block：一个生产小组
Thread：小组里的工人
```

每个 block 之间相对独立。

这意味着：

```text
同一个 block 内的 thread 可以比较方便地协作
不同 block 之间通常不能直接同步
```

---

### 10.3 Thread

Thread 是 GPU 上真正执行计算的基本单位。

在简单算子中，我们经常让一个 thread 处理一个输出元素。

例如：

```text
第 0 个 thread 处理 out[0]
第 1 个 thread 处理 out[1]
第 2 个 thread 处理 out[2]
```

但在复杂算子中，一个 thread 不一定只处理一个元素。

它可能处理：

- 一个元素；
- 多个元素；
- 一个矩阵小块中的一部分；
- 一个 row 的部分数据；
- 一个 tile 的一部分。

因此，算子设计的关键之一就是：

> 如何把计算任务合理分配给 thread。

---

### 10.4 Warp

Warp 是 GPU 实际调度 thread 的基本单位。

在 NVIDIA GPU 中，一个 warp 通常包含 32 个 thread。

也就是说，虽然我们写代码时关注的是 thread，但 GPU 硬件调度时，往往是一组 thread 一起执行。

可以类比为：

```text
Thread：单个工人
Warp：一排同时行动的工人
```

这也解释了为什么 GPU 编程中经常关注分支分化问题。

如果同一个 warp 内的 thread 执行不同分支，执行效率就可能下降。

---

### 10.5 SM

SM 是 Streaming Multiprocessor，可以理解为 GPU 上真正执行计算任务的计算单元。

一个 GPU 中通常有多个 SM。

kernel launch 后，GPU 会把不同 block 分配到不同 SM 上执行。

可以类比为：

```text
GPU：整个工厂
SM：工厂里的车间
Block：分配到车间里的任务小组
Thread：小组里的工人
```

所以 CUDA 执行模型可以整体理解为：

```text
一个 GPU 有多个 SM
一个 kernel launch 产生一个 grid
一个 grid 包含多个 block
block 被调度到 SM 上执行
一个 block 包含多个 thread
thread 以 warp 为单位被调度执行
```

---

## 11. shared memory

shared memory 是 block 内部共享的一块高速内存。

它的特点是：

- 同一个 block 内的 thread 可以共享；
- 不同 block 之间不能共享；
- 访问速度通常比 global memory 更快；
- 容量有限。

可以把 shared memory 类比为“小组桌面”。

```text
global memory：大仓库，容量大，但搬运慢
shared memory：小组桌面，容量小，但拿取快
register：每个工人手里的工具，最快但更私有
```

shared memory 常用于：

- 缓存中间数据；
- 减少 global memory 访问；
- 让 block 内 thread 协作；
- 提升数据复用率。

例如在矩阵乘法中，一个 block 可以把矩阵的一小块数据搬到 shared memory 中，然后让 block 内的多个 thread 重复使用这块数据。

这样就不用每次都从 global memory 里重新读取。

---

## 12. CUDA Stream

CUDA stream 可以理解为 GPU 上的任务队列。

CPU 可以把多个任务提交到不同 stream 中。

在同一个 stream 中，任务通常按顺序执行：

```text
任务 A → 任务 B → 任务 C
```

不同 stream 之间，在条件允许时可能并发执行。

可以类比为：

```text
一个 stream 是一条排队通道。
多个 stream 就是多条排队通道。
```

在 PyTorch 中，很多 CUDA 操作都会被放入当前 CUDA stream 中执行。

这也是为什么自定义算子接入 PyTorch 时，通常需要使用 PyTorch 当前的 CUDA stream，而不是随便创建一个新的 stream。

否则可能出现执行顺序不一致的问题。

---

## 13. C++ 和 CUDA 的整体执行链路

一个自定义 CUDA 算子的整体执行链路可以概括为：

```text
上层调用
  ↓
C++ 接口函数
  ↓
检查输入参数
  ↓
计算 kernel launch 配置
  ↓
启动 CUDA kernel
  ↓
GPU 并行执行
  ↓
写回输出 Tensor
```

其中，C++ 端主要负责“组织任务”，CUDA kernel 主要负责“执行任务”。

可以类比为：

```text
C++：项目经理，负责检查材料、安排人手、下发任务
CUDA kernel：工人团队，负责真正并行干活
GPU：工厂，提供大量工人和车间
```

一个成熟的自定义算子，通常不仅包含 kernel 代码，还包含大量 CPU 端辅助逻辑。

例如：

- 检查输入是否在 GPU 上；
- 检查数据类型是否正确；
- 检查 Tensor 形状是否匹配；
- 计算 block 和 thread 数量；
- 选择合适的 CUDA stream；
- 检查 kernel 是否启动成功。

这些内容虽然不直接参与计算，但决定了算子能否稳定、安全地运行。

---

## 14. Python 和 C++/CUDA 的配合使用

在实际深度学习开发中，Python 通常负责上层模型逻辑，C++/CUDA 负责底层高性能计算。

它们的关系可以理解为：

```text
Python：负责易用性和模型表达
C++：负责工程封装和调度逻辑
CUDA：负责 GPU 上的高性能并行计算
```

一个典型调用链路是：

```text
Python 调用自定义算子
  ↓
进入 C++ binding
  ↓
C++ launch 函数检查参数并启动 kernel
  ↓
CUDA kernel 在 GPU 上执行
  ↓
结果回到 PyTorch Tensor
  ↓
Python 继续执行后续模型逻辑
```

这也是 PyTorch extension 的基本思想。

对用户来说，只需要在 Python 中调用一个函数。

但在底层，这个函数可能已经跨越了：

```text
Python
C++
CUDA
GPU 硬件
```

因此，学习自定义算子的意义不只是学 CUDA 语法，而是理解深度学习框架从上层 API 到底层 GPU 执行的完整路径。

---

## 15. 当前阶段的核心理解

通过基础篇章的学习，可以形成几个关键认知。

第一，算子是深度学习模型中的基本计算单元。

第二，核函数是算子在 GPU 上的一种具体实现方式。

第三，PyTorch 等框架本质上封装了大量算子，让用户可以用简单 API 调用复杂计算。

第四，自定义算子的价值主要体现在特殊功能支持和性能优化上。

第五，CUDA 编程的核心不是简单写代码，而是把计算任务合理映射到 GPU 的并行执行模型上。

第六，C++ 端负责组织和调度，CUDA 端负责并行计算，Python 端负责上层调用和模型表达。

---

## 16. 总结

算子编写是理解 AI Infra 和深度学习框架底层实现的重要入口。

对于新手来说，学习算子不应该一开始就陷入复杂优化，而应该先建立一条清晰主线：

```text
什么是算子？
算子和 kernel 有什么关系？
CPU 如何启动 GPU 计算？
GPU 如何组织 thread 执行任务？
C++、CUDA、Python 分别承担什么角色？
```

当这条主线建立起来之后，再去学习更复杂的算子，例如：

- Reduce
- LayerNorm
- Softmax
- MatMul
- FlashAttention
- KVCache Attention

就会更容易理解它们的设计逻辑。

后续分析复杂算子时，可以始终围绕几个问题展开：

```text
这个算子完成什么计算？
输入和输出分别是什么？
计算任务如何拆分给 thread？
一个 block 负责什么？
是否需要 shared memory？
是否需要同步？
瓶颈在计算还是访存？
它在推理系统中承担什么作用？
```

这套问题框架，可以作为后续继续深入 CUDA 算子、推理框架和 AI Infra 系统优化的基础。
