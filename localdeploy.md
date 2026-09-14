如果只在本地部署，不上传远程服务器，分为两种情况。

## 方案一：本地开发模式，推荐

这种模式支持热更新，修改代码后网页自动刷新。

### 1. 启动本地 API

打开第一个 PowerShell：

```powershell
cd E:\MiraWorld
powershell -ExecutionPolicy Bypass -File .\scripts\dev-api.ps1
```

API 地址：

```text
http://127.0.0.1:8787
```

### 2. 启动本地网页

打开第二个 PowerShell：

```powershell
cd E:\MiraWorld
npm run docs:dev
```

访问：

```text
http://localhost:5173/miraworld/
```

本地网页请求：

```text
/miraworld/api/*
```

会通过 `docs/.vitepress/config.ts` 自动代理到：

```text
http://127.0.0.1:8787
```

所以本地开发时不需要修改前端 API 地址。

---

## 方案二：本地生产构建并预览

先构建网页：

```powershell
cd E:\MiraWorld
npm run docs:build
```

再启动本地预览服务器：

```powershell
npm run docs:preview
```

访问：

```text
http://localhost:4173/miraworld/
```

但是要注意：`docs:preview` 只负责预览静态网页，VitePress 的开发代理不会用于生产预览。也就是说，网页中的 API 请求可能无法自动转发到本地 `127.0.0.1:8787`。

因此，想在本地完整测试登录、生产、成品仓等功能，建议使用：

```powershell
npm run docs:dev
```

而不是只使用：

```powershell
npm run docs:preview
```

---

## 最简单的本地完整启动方式

第一个终端：

```powershell
cd E:\MiraWorld
powershell -ExecutionPolicy Bypass -File .\scripts\dev-api.ps1
```

第二个终端：

```powershell
cd E:\MiraWorld
npm run docs:dev
```

浏览器打开：

```text
http://localhost:5173/miraworld/
```

---

## 如果还没有安装依赖

首次使用前执行：

```powershell
cd E:\MiraWorld
npm install
```

API 脚本会自动创建 Python 虚拟环境并安装后端依赖。如果希望手动安装，也可以执行：

```powershell
cd E:\MiraWorld
python -m venv server\.venv
server\.venv\Scripts\python.exe -m pip install -U pip
server\.venv\Scripts\python.exe -m pip install -r server\requirements.txt
```

---

## 本地检查 API 是否正常

API 启动后，另开终端执行：

```powershell
curl.exe http://127.0.0.1:8787/health
```

正常返回：

```json
{"ok":true}
```

---

## 本地检查成品仓生产流程

本地 API 启动后，可以运行：

```powershell
npm run smoke:production
```

但这个命令默认测试远程服务器，不是本地 API。

要测试本地 API，使用：

```powershell
python deploy\smoke_demo.py --v22-prod --base http://127.0.0.1:8787
```

如果本地 API 的路由前缀与脚本预期一致，也可以使用：

```powershell
python deploy\smoke_demo.py --v22-prod --base http://127.0.0.1:8787/miraworld/api
```

当前 `scripts/dev-api.ps1` 启动的 FastAPI 通常直接监听：

```text
http://127.0.0.1:8787
```

所以优先使用第一条：

```powershell
python deploy\smoke_demo.py --v22-prod --base http://127.0.0.1:8787
```

---

## 本地生产构建检查

只检查网页能不能构建：

```powershell
npm run docs:build
```

检查 Python 代码：

```powershell
python -m compileall -q server deploy
```

完整本地流程：

```powershell
cd E:\MiraWorld
npm run docs:build
python -m compileall -q server deploy
```

本地开发通常不需要执行：

```powershell
python deploy\deploy.py
python deploy\sync_api.py
```

这两个命令是上传到远程服务器用的。