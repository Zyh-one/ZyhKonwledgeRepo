完整的流量转发链路：GatewayClass，Gateway，HTTPRoute，Service/Backend

```
GatewayClass
    ↓
定义“谁来实现 Gateway”
    ↓
Gateway
    ↓
定义“在哪里接收流量”
    ↓
HTTPRoute
    ↓
定义“什么请求转到哪里”
    ↓
Backend / Service
    ↓
真正业务 Pod
```

GatewayClass / Gateway / HTTPRoute都只是“声明式配置”（内部没有真正运行的代码逻辑来处理请求转发）

* 本质上就是配置文件
* 它们需要被 K8s 中特定的网关 Pod 读取和解释（Envoy Gateway，Istio，Kong Gateway Operator等等）

```
GatewayClass / Gateway / HTTPRoute
            │
            │ 都只是 K8s API 中的声明式配置
            ▼
   Gateway Controller
            │
            │ watch / reconcile / 翻译配置
            ▼
        Proxy Pod
            │
            │ 真正监听端口、匹配路由、转发请求
            ▼
Backend Service / Pod
```

**问题：** 它们都是配置文件，需要配合特定的网关工具，那么在不同的网关工具下，它们各自的作用和关联是否会发生变化？

答：不会，它们的核心语义和职责划分在所有网关实现中是高度一致的，因为**Gateway API**（统一的标准规范）

**GatewayClass（集群级别）**

GatewayClass  --->  绑定Controller实现

```
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: envoy-gateway-class
spec:
  controllerName: gateway.envoyproxy.io/gatewayclass-controller
```

“所有引用这个 GatewayClass 的 Gateway，由 Envoy Gateway Controller 来负责。”

**Gateway（命名空间级别）**

其中最重要就是 listeners 字段；流量真正开始进入 Gateway 的地方

```
spec:
  gatewayClassName: envoy-gateway-class

  listeners:
  - name: http
    protocol: HTTP
    port: 80
```

“需要创建一个80的HTTP端口”   ---> Envoy数据面pod会出现相应的Listener

此时client才能将请求打到Envoy listener，然后由Envoy数据面pod执行后续转发请求，比如匹配HTTPRoute等等

**HTTPRoute（命名空间级别）**

参考上面的介绍

其yaml中配置信息大致分为三类:

1. parentRefs：关联的Gateway
2. matches：匹配对应的请求（body，header等）
3. backendRef：请求转发目标（Service）

**下面以Envoy-gateway举例**

Envoy-Gateway在k8s集群中的部署形态

![1787299370554](../../../source/集群调度/k8s基本/GatewayAPI/Gateway%20API流量链路/1787299370554.png)

* “envoy-aibrix-system-aibrix-eg-xxxxx”为envoy的数据面Pod，执行实际的请求转发
  * service/envoy-aibrix-system-aibrix-eg负责暴露该数据面Pod的相关端口
* “envoy-gateway-5d4444bf96-tfc7c”为Envoy Controller Pod
  * 监听整个 Gateway API 相关资源体系，并持续生成/更新 Envoy 数据面Pod
  * Controller监听的资源包含HTTPRoute，所以数据面pod在接受请求就能直接获知请求转发规则
* 为什么 `envoy-gateway-system` 里面看不到 Gateway / HTTPRoute？
  * Controller 在哪个 namespace 运行，和它管理的资源在哪个 namespace，没有必然关系。
