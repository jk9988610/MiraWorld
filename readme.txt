先测试连接服务器admin@iZuf6a27proy7jkii03mbwZ:~$ curl -s ifconfig.me
8.133.252.224

--- 本地 ---
npm install
npm run docs:dev
npm run docs:build

--- 部署（本机 SSH 公钥尚未授权，需在服务器执行一次）---
方式 A：阿里云网页终端粘贴（最快）
  curl -fsSL https://github.com/jk9988610/MiraWorld/releases/download/miraworld-web/bootstrap-on-server.sh | bash
  # 若仍报 pipefail/invalid option，先清 CRLF：
  # curl -fsSL .../bootstrap-on-server.sh | sed 's/\r$//' | bash

方式 B：授权本机密钥后，在本机执行
  echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDeoKq8sKQKrnoxTqVVagOIXSPZHCyc72jgzqGBfQsfJ jk9988610@gmail.com' >> ~/.ssh/authorized_keys
  # 然后本机: npm run deploy
  # 或设置密码: $env:MIRAWORLD_SSH_PASSWORD='你的密码'; npm run deploy

站点: http://8.133.252.224/
