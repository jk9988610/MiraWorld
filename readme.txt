先测试连接服务器admin@iZuf6a27proy7jkii03mbwZ:~$ curl -s ifconfig.me
8.133.252.224

--- 本地 ---
npm install
npm run docs:dev
npm run docs:build

--- 部署（保留 bykc 首页，MiraWorld 在子路径）---
方式 A：阿里云网页终端粘贴
  curl -fsSL https://github.com/jk9988610/MiraWorld/releases/download/miraworld-web/bootstrap-on-server.sh | sed 's/\r$//' | bash

方式 B：授权本机密钥后
  npm run deploy

bykc 首页: http://8.133.252.224/
MiraWorld:  http://8.133.252.224/miraworld/
