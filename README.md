# 学生活动物资与场地借用管理系统

这是一个轻量级的数据库网页项目，用来管理学生活动物资、场地借用、物资借出登记，以及库存数量的自动计算和展示。

## 当前功能

- 首页显示本周场地借用和今日物资数量
- 物资借用登记、修改和删除
- 物资库存列表、总数量修改和按日期统计
- 点击库存条形图查看某项物资未来 10 天剩余数量
- 场地借用日历登记
- 违规记录登记
- 数据仓库文档上传、预览和多级文件夹管理
- 用户登录和退出
- 管理员用户管理，支持查看、修改和删除普通用户
- 普通用户注册后需要管理员审核通过才能登录
- SQLite 本地数据库
- 使用 Flask 后端提供接口，前端使用 HTML、CSS、JavaScript

## 本地运行

首次运行先创建并使用项目内虚拟环境：

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
```

之后启动服务：

```powershell
.\.venv\Scripts\python server.py
```

然后在浏览器打开：

```text
http://localhost:8000
```

服务启动时会自动创建数据库文件：`data/app.sqlite3`。

首次进入登录页可以先注册账号。注册时需要填写：

```text
学号：10 位数字，之后作为登录账号
姓名：真实姓名
手机号：11 位数字
密码：至少 6 位
```

普通用户提交注册后会进入待审核状态，需要管理员在“用户管理”里点击“通过”。

系统也会保留一个特殊管理员账号：

```text
账号：admin
密码：admin123
```

## 项目结构

```text
app/
  __init__.py      Flask 应用创建入口
  database.py      SQLite 表结构、示例数据和数据库操作
  routes.py        页面路由和 JSON 接口
data/
  .gitkeep         本地数据库目录占位文件
web/
  login.html       登录页面
  index.html       主页面
  styles.css       页面样式
  app.js           前端交互和接口请求
server.py          Flask 本地启动入口
requirements.txt  Python 依赖清单
README.md
```

## 后续计划

- 增加多用户和权限管理
- 支持导出 Excel 表格
- 支持正式部署到云服务器
- 支持自动备份数据库
