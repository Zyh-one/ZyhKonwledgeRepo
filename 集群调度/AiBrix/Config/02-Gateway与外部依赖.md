# Gateway 与外部依赖

[返回总览](./README.md)

## Gateway 数据面

`config/gateway` 由 Envoy Gateway 资源和 AIBrix Gateway Plugin 两部分组成。

### `gateway.yaml`

| 资源 | 作用 |
| --- | --- |
| `GatewayClass` | 声明由 Envoy Gateway Controller 管理 |
| `Gateway` | 声明 AIBrix HTTP 入口 |
| `EnvoyProxy` | 配置 Envoy 数据面的副本、调度、资源和镜像 |
| `ClientTrafficPolicy` | 配置客户端连接行为 |
| `EnvoyPatchPolicy` | 增加根据 `target-pod` 动态转发的 `ORIGINAL_DST` Cluster |

Envoy Gateway Controller 观察到 `Gateway` 和 `EnvoyProxy` 后，会自动创建真正处理请求的 Envoy Deployment 和 Service。

### `gateway-plugin/`

该目录主要定义 Gateway Plugin Deployment、Service、`HTTPRoute` 和 `EnvoyExtensionPolicy`。Gateway Plugin 是 Envoy External Processor：

```text
客户端
    → Envoy Proxy
    → ext_proc gRPC
    → AIBrix Gateway Plugin
    → 请求解析、认证、限流和 Router 选路
    → 返回 Header/Body Mutation
    → Envoy 读取 target-pod
    → vLLM/SGLang Pod
```

`EnvoyExtensionPolicy` 将请求接入 Gateway Plugin；`EnvoyPatchPolicy` 将 Plugin 返回的 `target-pod` 转换为真实的后端转发目标。

## 外部依赖：`dependency/`

该目录描述 AIBrix 依赖但不自行实现的 Kubernetes 组件。

### `dependency/envoy-gateway/`

引用 Envoy Gateway 官方安装清单和镜像，并通过 Patch 启用：

```yaml
extensionApis:
  enableEnvoyPatchPolicy: true
```

该模块安装 Envoy Gateway CRD、Controller、RBAC、Service 和证书资源。AIBrix 默认使用上游 Envoy Gateway/Envoy 镜像，不从源码构建它们。

```text
Envoy Gateway Controller
    → dependency/ 安装的第三方控制面

Envoy Proxy
    → 由 gateway/ 中的 Gateway/EnvoyProxy 资源触发创建的数据面
```

### `dependency/kuberay-operator/`

包含 KubeRay CRD、Operator Deployment、ServiceAccount 和 RBAC，用于支持 RayClusterFleet、RayClusterReplicaSet 等分布式推理能力。

`make install` 应用 `config/dependency`，主要先安装 Envoy Gateway 和 KubeRay CRD；`make deploy` 再应用 `config/default`，部署 AIBrix 本身及 KubeRay Operator。
