
HTTPRoute：K8s Gateway API体系；非K8s内置资源

它通常以 CRD/API 扩展资源的形式由 Gateway API 提供，然后由具体实现方，比如 **Envoy Gateway**、Istio、NGINX Gateway Fabric 等 Controller 去真正执行。

它对标并扩展Ingress，具备更现代、更细粒度、更强扩展性

HTTPRoute只是一个声明式路由配置对象，真正转发流量的是数据面，比如Envoy

```
Client
  ↓
Gateway / Envoy 数据面
  ↓
根据 HTTPRoute 匹配规则
  ↓
Service / Backend
  ↓
Pod
```

也就是说，HTTPRoute描述的是“匹配哪个 Host”，“转发到哪个 Backend”，“匹配哪些 Header”，“是否重写 URL”等等

yaml拆解：

```
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: model-route
  namespace: serving
spec:
  parentRefs:
  - name: aibrix-gateway

  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /v1

    backendRefs:
    - name: model-service
      port: 8000
```

大致含义为：

1. 请求打到网关aibrix-gateway
2. 网关aibrix-gateway结合HTTPRoute中的相关信息
   1. 如果请求符合/v1/xxxx形式，网关aibrix-gateway直接将其转发到model-service:8000上

区别于Ingress：Ingress 通常把很多东西放在一个对象里（hostname，path，TLS等）
