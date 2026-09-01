# AIBrix 数据面部署流程（Kind CPU Mock）

## 1. 本次部署范围

本文记录在已经安装 AIBrix 依赖和控制面之后，部署并验证推理数据面的过程。

本地集群为 `kind-brix`，节点不提供 `nvidia.com/gpu`，因此没有部署 `samples/quickstart/model.yaml` 中需要 NVIDIA GPU 的真实 vLLM 模型，而是使用仓库提供的 CPU Mock：

```text
客户端
  -> Envoy Proxy
  -> AIBrix Gateway Plugin
  -> llama2-7b Service
  -> vLLM Mock + AIBrix Runtime Pod
```

CPU Mock 会实现 OpenAI 兼容接口并返回占位内容，适合验证发现、路由和转发链路，但不执行真实大模型推理。

## 2. 前置检查

进入 AIBrix 仓库：

```bash
cd /home/cambricon/gorepos/aibrix
```

确认当前集群和节点：

```bash
kubectl config current-context
kubectl get nodes -o wide
kubectl get nodes \
  -o custom-columns=NAME:.metadata.name,GPU:.status.allocatable.nvidia\\.com/gpu
```

确认 AIBrix 控制面：

```bash
kubectl get pods -n aibrix-system
kubectl get pods -n envoy-gateway-system
kubectl get gateway,httproute -A
kubectl get svc -A
```

数据面部署前至少应保证以下组件正常：

- `envoy-gateway`：管理 Gateway API 资源并生成 Envoy 数据面。
- `aibrix-controller-manager`：管理 AIBrix 自定义资源和控制循环。
- `aibrix-gateway-plugins`：为 Envoy 提供模型发现、负载感知和路由策略。
- `aibrix-redis-master`：保存 Gateway Plugin 等组件使用的共享状态。

## 3. 本次发现并处理的集群问题

最初 `kube-proxy` 报错：

```text
failed complete: too many open files
```

这导致 Pod 无法通过 Kubernetes Service IP 访问 Redis，进而使 Gateway Plugin 卡在 init 容器。执行了以下恢复命令：

```bash
kubectl rollout restart daemonset/kube-proxy -n kube-system
kubectl rollout restart deployment/coredns -n kube-system

kubectl rollout restart \
  deployment/aibrix-gateway-plugins \
  deployment/aibrix-metadata-service \
  -n aibrix-system
```

`brix-worker2` 上的 kube-proxy 仍受宿主机文件描述符问题影响，因此将 Gateway Plugin 临时固定到网络正常的 `brix-worker`：

```bash
kubectl patch deployment aibrix-gateway-plugins \
  -n aibrix-system \
  --type merge \
  -p '{"spec":{"template":{"spec":{"nodeSelector":{"kubernetes.io/hostname":"brix-worker"}}}}}'

kubectl wait \
  --for=condition=Ready \
  pod \
  -l app=gateway-plugins \
  -n aibrix-system \
  --timeout=120s
```

这个 `nodeSelector` 是本次故障规避措施，不是 AIBrix 的标准安装要求。彻底处理宿主机或 Kind 节点的文件描述符限制后，可以删除它：

```bash
kubectl patch deployment aibrix-gateway-plugins \
  -n aibrix-system \
  --type=json \
  -p='[{"op":"remove","path":"/spec/template/spec/nodeSelector"}]'
```

## 4. 准备 CPU Mock 镜像

仓库中的 Mock Dockerfile 位于：

```text
development/app/Dockerfile
```

标准本地构建命令是：

```bash
cd /home/cambricon/gorepos/aibrix/development/app
docker build -t aibrix/vllm-mock:nightly -f Dockerfile .
cd /home/cambricon/gorepos/aibrix
```

本次构建访问 Debian 软件源较慢，因此最终使用已发布镜像：

```bash
docker pull aibrix/vllm-mock:nightly
docker pull aibrix/runtime:nightly
```

通常可直接加载到 Kind：

```bash
kind load docker-image aibrix/vllm-mock:nightly --name brix
kind load docker-image aibrix/runtime:nightly --name brix
```

本次 `kind load` 被执行环境中断，因此采用了等价的手工导入方式：

```bash
docker save -o /tmp/aibrix-vllm-mock-nightly.tar \
  aibrix/vllm-mock:nightly
docker save -o /tmp/aibrix-runtime-nightly.tar \
  aibrix/runtime:nightly

for node in brix-control-plane brix-worker brix-worker2; do
  docker cp /tmp/aibrix-vllm-mock-nightly.tar \
    "${node}:/aibrix-vllm-mock-nightly.tar"
  docker cp /tmp/aibrix-runtime-nightly.tar \
    "${node}:/aibrix-runtime-nightly.tar"

  docker exec "${node}" ctr -n k8s.io images import \
    /aibrix-vllm-mock-nightly.tar
  docker exec "${node}" ctr -n k8s.io images import \
    /aibrix-runtime-nightly.tar
done
```

## 5. 部署数据面

在仓库根目录执行：

```bash
kubectl apply -k development/app/config/mock
```

检查部署：

```bash
kubectl get deployment,pod,svc -n default -o wide
kubectl get endpointslice \
  -n default \
  -l kubernetes.io/service-name=llama2-7b \
  -o wide
```

本次最终状态：

```text
deployment/mock-llama2-7b   3/3 Available
deployment/mock-qwen3-8b    1/1 Available
service/llama2-7b           已生成可用 Endpoint
```

`mock-qwen3-8b` 是 AIBrix 根据 Mock 配置派生出的附加模型 Deployment。

## 6. 安装的 Kubernetes 资源及作用

### Deployment：mock-llama2-7b

创建 3 个 Mock 模型副本。每个 Pod 包含：

- `llm-engine`：运行 `aibrix/vllm-mock:nightly`，在 8000 端口提供 OpenAI 兼容接口。
- `aibrix-runtime`：运行 `aibrix/runtime:nightly`，统一采集推理引擎指标，并向 AIBrix 控制面暴露运行时状态。

Pod 上的重要标签包括：

```yaml
model.aibrix.ai/name: llama2-7b
model.aibrix.ai/port: "8000"
adapter.model.aibrix.ai/enabled: "true"
```

AIBrix 根据这些标签发现模型名称和服务端口。

### Deployment：mock-qwen3-8b

提供第二个 Mock 模型 `qwen3-8b`，用于验证多模型发现和基于模型名的路由。

### Service：llama2-7b

通过标签选择 `llama2-7b` 的模型 Pod，把 8000 端口暴露为稳定的 Kubernetes Service，并生成 EndpointSlice。

### ServiceAccount：mocked-app-sa

作为 Mock 模型 Pod 的 Kubernetes 身份。

### Role / RoleBinding

授予 `mocked-app-sa` 在 `default` 命名空间读取 Pod 和 Deployment 的权限。Mock 服务利用这些信息识别自身 Pod、Deployment 和副本状态。

### 已有但参与数据面链路的组件

- Envoy Proxy：接受客户端 HTTP 请求，并执行 Gateway/HTTPRoute 生成的转发配置。
- AIBrix Gateway Plugin：读取请求中的模型名和 `routing-strategy`，选择适合的模型 Pod。
- Redis：保存路由插件需要共享的指标或状态。
- AIBrix Controller Manager：监听 Kubernetes/AIBrix 资源并维护期望状态。

## 7. 端到端验证

Kind 默认没有 LoadBalancer External IP，因此 Gateway 的顶层 `PROGRAMMED` 可能显示 `False` 和 `AddressNotAssigned`。只要 Listener 已被正常翻译，仍可使用端口转发测试：

```bash
kubectl port-forward \
  -n envoy-gateway-system \
  service/envoy-aibrix-system-aibrix-eg-903790dc \
  8888:80
```

另开终端查询模型：

```bash
curl --fail-with-body http://localhost:8888/v1/models
```

本次返回了：

```json
{
  "object": "list",
  "data": [
    {"id": "llama2-7b", "object": "model", "owned_by": "aibrix"},
    {"id": "qwen3-8b", "object": "model", "owned_by": "aibrix"}
  ]
}
```

验证 Chat Completion：

```bash
curl --fail-with-body http://localhost:8888/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer test-key-1234567890' \
  -H 'routing-strategy: random' \
  -d '{
    "model": "llama2-7b",
    "messages": [
      {"role": "user", "content": "Say this is a test!"}
    ],
    "temperature": 0.7
  }'
```

本次请求成功，并由 `mock-llama2-7b` Pod 返回占位回答，证明以下链路可用：

```text
localhost:8888
  -> Envoy Gateway 数据面
  -> AIBrix Gateway Plugin
  -> llama2-7b Service/Pod
  -> OpenAI 兼容响应
```

## 8. 与真实模型部署的区别

真实模型示例命令为：

```bash
kubectl apply -f samples/quickstart/model.yaml
```

该示例运行 `vllm/vllm-openai`，加载真实模型并申请：

```yaml
resources:
  requests:
    nvidia.com/gpu: "1"
  limits:
    nvidia.com/gpu: "1"
```

当前 Kind 集群没有 GPU，因此执行该命令会使模型 Pod 长期处于 `Pending`。迁移到安装了 NVIDIA Device Plugin 且节点暴露 `nvidia.com/gpu` 的集群后，才应使用真实模型清单。

## 9. 卸载数据面

删除本次 Mock 数据面资源：

```bash
kubectl delete -k development/app/config/mock
```

该命令只删除 Mock 模型的 Deployment、Service、ServiceAccount 和 RBAC，不删除 `config/dependency` 或 `config/default` 安装的 AIBrix 控制面。
