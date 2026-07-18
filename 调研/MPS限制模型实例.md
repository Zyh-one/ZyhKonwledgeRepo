1. 通过CUDA MPS前期实验，熟悉了CUDA MPS的基本结构，工作原理，使用流程
2. CUDA MPS的前期实验验证了两点：
	1. 在多进程并发使用GPU的场景下，CUDA MPS确实可以通过节省cuda context的频繁切换，提高GPU的处理效率，缩短计算进程的执行时间
	2. CUDA MPS确实可以通过环境变量CUDA_MPS_ACTIVE_THREAD_PERCENTAGE限制GPU的计算资源，确实会造成计算任务的延迟增加
3. 下一步讨论，限制计算资源会对sglang推理服务实例产生哪些影响（优先从上层SLO指标进行分析）
4. 同一个 SGLang 模型推理实例，在不同资源约束和不同请求负载下，会暴露出不同的服务特性。
	1. 因此，实验设计不能只围绕“跑通模型”展开，而应该先明确希望分析的实例特性，再根据该特性反向设计 workload、监控指标和实验流程。




# 实验思路

1. 不断切换MPS Percentage，设计不同的工作负载，观察固定模版参数下的sglang推理实例的SLO指标，其中包含3部分工作
	1. 固定sglang模版参数：采取默认参数
	2. MPS Percentage的变化：经过此前对MPS的验证，了解CUDA MPS由Nvidia原生支持，使用方法极其简单，并且对SM处理器的限制得到有效限制
	3. 设计不同负载 + 确定监控的SLO指标：这部分目前可以交给Ai设计
		1. 工作负载的设计和SLO指标的监控必须一一对应，本质上都是服务于分析sglang模型推理的某一方面特性
## sglang模版参数的固定

- 初步实验对象：Qwen3-0.6B。
- SGLang 实例参数保持不变，暂不主动调节调度参数。
- 所有启动参数以实际命令和日志为准，并记录当前 SGLang 版本下的默认值。
- 该模版参数也将作为对照实验（计算资源不限）的实验配置

## MPS Percentage

1. 本实验使用 CUDA MPS Active Thread Percentage 作为计算资源限制手段。  
	```
	
	
	
	
	
	
	```
	1. 
2. 每次切换 MPS Percentage 后，最好重新启动 SGLang server。

## 推理实例的特性

- 一个具体的模型推理实例在不同资源，不同工作负载的场景下，所暴露或侧重的特性不一样，故需要根据具体分析的特性来设计实验思路和流程
### SLO Capacity

- SLO Capacity 表示 SGLang 实例在满足 TTFT / TPOT / SLO 违约率约束下，能够承载的最大请求压力。
- 大致实验设计

| 项目       | 设计                                          |
| -------- | ------------------------------------------- |
| Workload | 固定 input/output 长度                          |
| 压力变量     | request_rate 或 max_concurrency 逐步增加         |
| 主要指标     | p99 TTFT、p99 TPOT、violation rate、throughput |
| 资源变量     | MPS=100/80/60/40/20                         |
| 关注问题     | 每个资源档位下，SLO 拐点在哪里？                          |
- 预期：**暂无**

### Prefill 计算能力

- Prefill 计算能力表示 SGLang 实例在处理长输入请求时，完成首 token 前计算阶段的能力。
- 因此当 MPS 降低可用计算资源时，长输入请求的 **TTFT** 应该会最先体现退化。
```
	打我的大伟大的

```
	
- 大致实验设计如下

| 项目       | 设计                                      |
| -------- | --------------------------------------- |
| Workload | 长输入、短输出                                 |
| 示例       | input_len=2048/4096/8192，output_len=128 |
| 主要指标     | TTFT、p95 TTFT、p99 TTFT                  |
| 资源变量     | MPS=100/80/60/40/20                     |
| 关注问题     | 计算资源下降是否显著拉高 TTFT？                      |
	·- 预期：MPS Percentage 降低 ---> prefill batch 执行时间变长 ---> TTFT 上升 ---> 长输入请求更容易违反 TTFT SLO


### Decode 逐 token 生成能力

- Decode 生成能力表示 SGLang 实例在持续生成 token 时，维持稳定 TPOT / ITL 的能力。
- 大致实验设计：

| 项目       | 设计                                         |
| -------- | ------------------------------------------ |
| Workload | 短输入、长输出                                    |
| 示例       | input_len=128/512，output_len=512/1024/2048 |
| 主要指标     | TPOT、ITL、E2E latency                       |
| 资源变量     | MPS=100/80/60/40/20                        |
| 关注问题     | 计算资源下降是否拉高每 token 生成时间？                    |
- 预期：MPS Percentage 降低 --> 每步 decode forward 变慢 --> TPOT / ITL 上升 --> 长输出请求 E2E latency 明显增加


# 实验平台

- 以下为实验平台流程图：

![实验平台流程图](../source/调研/MPS限制模型实例/Pasted%20image%2020260704163156.png)

- 当前实验平台主要依赖一个Yaml配置文件进行具体实验流程，配置文件如下：
```YAML
experiment:
  name: local_qwen3_smoke
  result_dir: results/local_qwen3_smoke

engine:
  framework: sglang
  model_path: /home/zyh-ub/models/Qwen3-0.6B
  host: 127.0.0.1
  port: 18001
  cuda_visible_devices: "0"
  tp_size: 1
  ready_timeout_sec: 120
  args:
    mem_fraction_static: 0.75
    max_running_requests: 4
    max_total_tokens: 8192

workload:
  name: local_smoke
  model: default
  prompt_tokens: 32
  max_tokens: 4
  concurrency: 1
  num_requests: 1
  timeout_sec: 120

monitor:
  interval_sec: 1
  gpu_ids: [0]
```
	- 补充：我认为后续所有相关实验配置都放在一个yaml文件统一管理，方便构造不同实验

- 实验流程：利用.sh构造计算受限的不同情况，读取 YAML 配置描述实验，自动启动服务，发送请求负载，采集指标，结果落盘并生成报告
	- 当前实验平台采用统一的yaml配置执行主要实验流程
	- MPS也是利用环境变量对计算资源进行限制
	- 故选择依托.sh文件进行具体实验
- 关于实验平台的详细细节，可见 **xxxxx**
	


# 实验设计

- 经过前文的“实验设计”和“实验平台"，接下来
