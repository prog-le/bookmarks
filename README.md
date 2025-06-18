# 书签智能分类与管理（Intelligent Classification and Management of Bookmarks）

[项目主页 @GitHub](https://github.com/prog-le/bookmarks)

## 项目简介
本项目是一款面向个人和团队的书签解析、智能分类、可视化编辑与导出工具，支持主流浏览器（Chrome/Firefox/Edge）导出的 HTML 书签文件。支持多种智能分类方式、实时日志推送、可视化操作与批量管理，兼容中文，界面友好。

---

## ✨ 主要特性
- **多方式智能分类**：关键词、TF-IDF聚类、自定义规则、原始文件夹、域名、智能关键词（实时抓取网页标题）
- **WebSocket 实时日志**：分类过程日志实时推送，体验流畅
- **可视化与交互**：树形/卡片视图，支持拖拽、重命名、批量操作、标签管理
- **强大导入导出**：兼容主流浏览器书签格式，导出结构可直接导入浏览器
- **错误处理健全**：自动识别文件格式、编码、空文件、异常URL等
- **分类统计与搜索**：支持分类统计（饼图）、全文搜索
- **支持中文分词与聚类**

---

## 技术栈
- **后端**：Python 3.8+，Flask，Flask-SocketIO，scikit-learn，lxml，jieba，chardet
- **前端**：React 18，Ant Design，echarts，socket.io-client，axios

---

## 快速开始

### 1. 安装后端依赖
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 启动后端服务
```bash
cd backend
python app.py
```

### 3. 安装前端依赖
```bash
cd frontend
npm install
```

### 4. 启动前端开发服务器
```bash
cd frontend
npm start
```

前端默认端口为 3000，访问 http://localhost:3000 即可。

---

## 目录结构
```
mark/
  backend/    # Flask后端
  frontend/   # React前端
  README.md
```

---

## 书签文件格式支持
- Chrome/Firefox/Edge 导出的 HTML 书签

---

## 典型流程
1. 上传书签
2. 自动解析与多方式智能分类
3. 可视化调整、批量管理
4. 导出新书签.html（可直接导入浏览器）

---

## 进阶功能
- 书签搜索、批量操作（暂未实现）
- 实时日志区（WebSocket）
- "无法识别""没有标题"自动归类

---

## 截图与演示
> （此处可放置功能截图或动图，建议上传到GitHub后补充）

---

## 贡献方式
欢迎提交 Issue、PR 或建议！
- Fork 本仓库，创建分支进行开发
- 提交 Pull Request
- 详细描述你的改动和用途

---

## License
MIT License

---

## 联系与反馈
如有问题或建议，欢迎在 [GitHub Issues](https://github.com/prog-le/bookmarks/issues) 留言。 