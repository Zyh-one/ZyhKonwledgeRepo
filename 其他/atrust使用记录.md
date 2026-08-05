
**atrust Ubuntu使用方法**

使用docker-atruts镜像，docker  pull hagb/docker-atrust，它可以很好解决atrust对系统DNS的污染

启动docker-atrust容器

```
docker run -d \
  --name atrust \
  --device /dev/net/tun \
  --cap-add NET_ADMIN \
  --restart unless-stopped \
  -e PASSWORD='AtrustVnc123' \
  -e URLWIN=1 \
  -v "$HOME/.atrust-data:/root" \
  -p 127.0.0.1:5901:5901 \
  -p 127.0.0.1:1080:1080 \
  -p 127.0.0.1:8888:8888 \
  -p 127.0.0.1:54631:54631 \
  --sysctl net.ipv4.conf.default.route_localnet=1 \
  hagb/docker-atrust
```

由于atrust是带有可视化界面的，故下载vncveiwer

```
sudo apt install -y tigervnc-viewer
```

大致原理为vncviewer，通过docker挂载的指定端口，访问docker-atrust内部服务，执行登录vpn操作

vncviewer默认密码：**AtrustVnc123**
