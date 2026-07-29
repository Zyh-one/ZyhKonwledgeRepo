# aTrust VPN 导致公共 AI 网站无法访问的排查与解决

## 事件概述

在 Ubuntu 24.04 上启动并登录深信服 aTrust VPN 后，浏览器无法正常访问 ChatGPT、Gemini，部分国内 AI 网站也出现页面打不开或加载异常。退出 aTrust 后，希望系统恢复原有网络环境，不遗留 DNS、代理或路由修改。

最终采用“独立 Chrome 配置 + 仅监听本机的专用 HTTP CONNECT 代理 + 指定公共 DNS 解析”的方案。在不修改系统 DNS、NetworkManager、普通 Chrome 和 aTrust 配置的前提下，实现了 aTrust 与 ChatGPT、Gemini、Gmail 同时使用。

## 一、现象

### 1. aTrust 连接状态

aTrust 登录后状态为：

- `status: online`
- `tunnelStatus: tunnelAvailable`
- 创建虚拟接口 `utun7`
- 在线时 `utun7` 获得类似 `10.102.1.36/24` 的地址

### 2. DNS 返回异常

系统表面上仍由 `systemd-resolved` 管理 DNS：

```text
/etc/resolv.conf -> /run/systemd/resolve/stub-resolv.conf
物理网卡：enp2s0
DNS Servers: 10.3.34.10 172.10.80.158
```

但 aTrust 在线时，部分域名查询实际经 `utun7` 返回明显错误的地址，例如：

```text
chatgpt.com       -> 173.234.53.168 / 128.121.146.109 等异常地址
api.openai.com    -> 108.160.163.116
gemini.google.com -> 111.243.214.169 / 104.244.46.21 等异常地址
```

随后访问这些错误地址的 `443` 端口会超时，浏览器表现为页面无法打开。

### 3. 国内 AI 网站的表现并不完全相同

命令行实际测试结果：

- DeepSeek 首页返回 `200`，网络可达；
- DeepSeek Chat 返回 `429`，属于服务端限流或风控，不是完全断网；
- ChatGLM 返回 `200`；
- 智谱 BigModel 返回 `200`。

因此浏览器中“打不开”并不全是同一种故障，还可能叠加浏览器 DNS 缓存、页面子资源解析失败、Service Worker 或服务端风控。

### 4. Codex CLI 暂时不受影响

检查发现 Codex 已建立到正确 Cloudflare 地址的长连接：

```text
192.168.82.45 -> 172.64.155.209:443
```

`172.64.155.209` 是 ChatGPT 的正确地址。Codex 很可能在 aTrust 登录前已经完成解析并建立连接，后续持续复用连接或缓存，所以暂时没有命中错误 DNS。浏览器会频繁解析大量主域名和子资源域名，因此更容易暴露问题。

这不代表 Codex 天然免疫；进程重启或长连接失效后仍可能受到影响。

## 二、问题定位

### 1. 不是简单修改 `/etc/resolv.conf`

aTrust 在线时，`/etc/resolv.conf` 和 `resolvectl status` 表面配置没有发生明显变化，但查询结果却显示来自 `utun7`。因此问题发生在 aTrust 隧道或 DNS 代理层，不能通过观察配置文件判断 DNS 是否正常。

### 2. 公共 DNS 可用性测试

实测：

```text
1.1.1.1:53 -> 超时
8.8.8.8:53 -> 可用，并返回正确地址
```

通过 `8.8.8.8` 查询得到：

```text
chatgpt.com       -> 104.18.32.47, 172.64.155.209
gemini.google.com -> 142.251.*.*
```

强制使用这些正确 IP 发起 HTTPS 请求后：

- ChatGPT 返回 `403`，说明已到达真实站点，未携带正常浏览器会话时触发 Cloudflare 防护；
- Gemini 返回 `200`，访问正常。

由此确认主要故障是 DNS 被错误处理，而不是目标网站路由整体被 aTrust 阻断。

## 三、方案分析

### 方案 A：永久覆盖系统 DNS

例如将所有 DNS 改为 `8.8.8.8`。

未采用，原因：

- 可能破坏 aTrust 或公司内网域名解析；
- aTrust 可能再次覆盖；
- Ubuntu 的 `/etc/resolv.conf` 由 `systemd-resolved` 管理，手工修改不稳定；
- 不满足退出 aTrust 后网络环境完全恢复的要求。

### 方案 B：系统级分流 DNS

利用 `systemd-resolved` routing domain，只将 OpenAI、ChatGPT、Gemini 等域名交给公共 DNS，其他域名保留原 DNS。

该方案技术上可行，但仍属于系统级网络修改，需要守护服务负责启用和撤销。为了优先满足“改动最小、退出 aTrust 后零变化”，暂未采用。

### 方案 C：浏览器内置安全 DNS（DoH）

最初创建独立 Chrome，并通过启动参数指定 Cloudflare DoH：

```text
--dns-over-https-mode=secure
--dns-over-https-templates=https://cloudflare-dns.com/dns-query
```

Cloudflare DoH 和阿里 DoH 的 HTTPS 端点均能通过命令行访问，但 Chrome 150 虽然接收了参数，网络服务仍连接到 aTrust 返回的错误 IP。说明本机当前 Chrome/aTrust 组合下，浏览器内置 DoH 没有真正接管解析，因此该方案失败。

### 方案 D：独立 Chrome + 浏览器专属本地代理

这是最终采用的方案。

工作链路如下：

```text
aTrust 专用 Chrome
        |
        | HTTP CONNECT（仅本机）
        v
127.0.0.1:18787 本地代理
        |
        | 使用 dig @8.8.8.8 独立解析目标域名
        v
目标网站的正确 IP:443
```

特点：

- 代理只监听 `127.0.0.1`，外部机器无法连接；
- Chrome 与目标网站之间仍是端到端 HTTPS；
- 代理只负责解析、建立 TCP 连接和转发加密字节流，不解密密码、Cookie 或邮件内容；
- 不修改系统 DNS、路由或代理；
- 不修改普通 Chrome 配置；
- 使用独立 Chrome Profile 保存 ChatGPT、Gemini、Gmail 登录状态；
- aTrust 未在线时拒绝启动；
- aTrust 退出或隧道断开时，自动关闭专用 Chrome 和本地代理。

## 四、实际操作

### 1. 创建独立 Chrome 启动器

脚本路径：

```text
/home/cambricon/.local/bin/atrust-secure-chrome
```

主要职责：

1. 检查 `aTrustTray` 是否运行；
2. 检查 `utun*` 是否获得在线隧道地址；
3. 使用文件锁保证只有一个专用实例；
4. 清理仅属于本方案的孤立代理进程；
5. 启动本地代理；
6. 使用独立 Profile 和代理参数启动 Chrome；
7. 每两秒检查 aTrust 状态；
8. aTrust 断开时关闭专用 Chrome，并由退出钩子关闭代理。

独立 Profile 路径：

```text
/home/cambricon/.local/share/atrust-secure-chrome/profile
```

### 2. 创建浏览器专属本地代理

脚本路径：

```text
/home/cambricon/.local/bin/atrust-browser-proxy
```

代理行为：

- 仅监听 `127.0.0.1:18787`；
- 只接受浏览器常用的 HTTP `CONNECT` 隧道请求；
- 使用 `dig @8.8.8.8` 获取目标域名的 IPv4 地址；
- 依次尝试正确地址并连接目标 `443` 端口；
- 建立连接后透明转发 TLS 加密数据。

### 3. 创建桌面应用入口

桌面文件：

```text
/home/cambricon/.local/share/applications/atrust-secure-chrome.desktop
```

应用菜单名称：

```text
aTrust 专用 Chrome
```

启动时默认打开：

```text
https://chatgpt.com/
https://gemini.google.com/
```

### 4. 处理测试代理残留

首次验证时，测试代理进程没有随测试工具完全退出，导致端口 `18787` 被占用，桌面启动器提示“专用浏览器代理启动失败”。

处理后增加了两层保护：

- 使用 `flock` 实现单实例锁，避免重复启动互相干扰；
- 获得锁后，仅清理命令行精确匹配本方案脚本的孤立代理进程。

随后验证代理正常启动、退出，端口能够释放，无残留进程。

## 五、最终效果

当前达到以下效果：

- aTrust 在线时，可以通过“aTrust 专用 Chrome”访问 ChatGPT；
- 可以访问 Gemini；
- 可以登录并使用 Gmail；
- 登录状态保存在独立 Profile 中，下次不必重新登录；
- 普通 Chrome 的账号、Cookie、扩展和历史记录不受影响；
- 公司内网建议继续使用普通 Chrome；
- aTrust 退出或断开后，专用 Chrome 和代理自动退出；
- 系统 DNS 始终保持原配置；
- `/etc/resolv.conf`、NetworkManager、aTrust 配置均未修改。

## 六、验证与维护

### 查看相关进程

```bash
ps -ef | grep -E 'atrust-secure-chrome|atrust-browser-proxy'
```

### 查看代理监听端口

```bash
ss -ltnp 'sport = :18787'
```

正常情况下，专用 Chrome 运行时可看到 `127.0.0.1:18787`；关闭后监听端口应消失。

### 验证系统 DNS 未变化

```bash
resolvectl status
```

### 手工测试代理连通性

先启动代理，再执行：

```bash
curl -I --proxy http://127.0.0.1:18787 https://chatgpt.com/
curl -I --proxy http://127.0.0.1:18787 https://gemini.google.com/
```

ChatGPT 返回 `403` 不一定代表失败：在没有完整浏览器 Cookie 和 JavaScript 环境的 `curl` 请求中，Cloudflare 可能主动返回 `403`。关键是连接不再超时，并且 Gemini 能返回 `200`。

## 七、回退方式

如需完整删除本方案，先关闭“aTrust 专用 Chrome”，然后删除：

```text
/home/cambricon/.local/bin/atrust-secure-chrome
/home/cambricon/.local/bin/atrust-browser-proxy
/home/cambricon/.local/share/applications/atrust-secure-chrome.desktop
/home/cambricon/.local/share/atrust-secure-chrome/
```

由于本方案没有修改系统 DNS、路由、NetworkManager 或 aTrust，删除上述文件即可完整回退。

## 八、经验总结

1. VPN 导致解析异常时，不能只看 `/etc/resolv.conf`；应同时对比系统解析、指定 DNS 查询结果和实际连接 IP。
2. “进程暂时可用”不代表没有 DNS 问题，已有长连接和缓存可能掩盖故障。
3. 应先分别验证 DNS、TCP 和 HTTPS，避免把限流、风控、DNS 污染和路由故障混为一谈。
4. 浏览器内置 DoH 是否生效必须通过实际目标连接 IP 验证，不能只确认启动参数存在。
5. 当要求退出 VPN 后零残留时，独立 Profile 和进程级代理比系统级 DNS 修改更容易保证隔离与回退。
