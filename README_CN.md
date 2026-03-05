# 飞书文档批量下载器 (Feishu Batch Downloader)

> 📥 **批量下载**飞书文档 | 🌳 **Wiki 子页面递归**下载 | 📄 导出为 **Markdown/PDF** 格式

[English Documentation](README.md) | [中文文档](README_CN.md)

[![Python Version](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## ✨ 核心亮点

### 🎯 三大核心功能

1. **📦 批量下载** - 一次性下载多个文档，支持批量 URL 输入
2. **🌳 Wiki 子页面递归** - 自动下载 Wiki 页面下的所有子页面（独特功能）
3. **📄 Markdown/PDF 导出** - 灵活选择导出格式，保留完整文档结构

### 💡 更多特性

- 🔄 **文档链接递归** - 自动下载文档中链接的所有子文档
- 🎨 **Web UI** - 简洁美观的网页界面，操作简单
- 📊 **实时进度** - 实时显示下载进度条和状态信息
- 💾 **自动保存配置** - 凭证自动保存，无需重复输入
- ✅ **凭证验证** - 保存配置时自动验证凭证有效性
- 🖥️ **跨平台** - 支持 Windows、macOS、Linux

## 📸 界面预览

![Web UI](https://via.placeholder.com/800x500?text=Web+UI+Screenshot)

## 📋 环境要求

- Python 3.7+
- 依赖库：
  - `requests` - HTTP 请求
  - `flask` - Web 服务器
  - `markdown` - Markdown 转换（PDF 导出需要）
  - `weasyprint` - PDF 生成（PDF 导出需要）

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/yourusername/feishu-batch-downloader.git
cd feishu-batch-downloader
```

### 2. 安装依赖

**基础功能（Markdown 导出）：**
```bash
pip install -r requirements.txt
```

或手动安装：
```bash
pip install requests flask
```

**完整功能（包含 PDF 导出）：**
```bash
pip install requests flask markdown weasyprint
```

### 3. 启动 Web UI

```bash
python3 web_ui.py
```

然后在浏览器中打开：**http://localhost:3000**

### 4. 配置飞书应用凭证

#### 完整配置流程

**步骤 1：创建应用**
1. 访问 [飞书开放平台](https://open.feishu.cn/app)
2. 点击"创建企业自建应用"
3. 填写应用名称和描述

**步骤 2：获取凭证**
1. 进入应用管理页面
2. 点击"凭证与基础信息"
3. 分别复制：
   - **App ID**（格式：`cli_xxxxxxxxxx`）
   - **App Secret**（长字符串，与 App ID 不同）

**步骤 3：配置权限（重要！）**

方法一：批量导入（推荐）
1. 进入"权限管理"页面
2. 点击"批量配置权限"
3. 粘贴以下 JSON 代码：

```json
{
  "scopes": {
    "tenant": [
      "docx:document:readonly",
      "drive:drive:readonly",
      "wiki:wiki:readonly"
    ],
    "user": [
      "docx:document:readonly",
      "wiki:wiki:readonly"
    ]
  }
}
```

方法二：手动添加
- `docx:document:readonly` - 读取文档内容
- `drive:drive:readonly` - 读取云空间文件
- `wiki:wiki:readonly` - 读取知识库内容（**Wiki 文档必需**）

**步骤 4：发布应用**
1. 进入"版本管理与发布"
2. 创建版本
3. 申请发布
4. 发布到企业内部

**步骤 5：在 Web UI 中保存配置**
1. 输入 App ID 和 App Secret
2. 点击"保存配置"
3. 系统会自动验证凭证是否有效

### 5. 开始下载

**单个文档下载：**
1. 粘贴文档链接
2. 选择保存位置
3. 选择导出格式（Markdown 或 PDF）
4. 点击"开始下载"

**批量下载：**
1. 每行粘贴一个文档链接
2. 选择保存位置和格式
3. 点击"开始下载"

**Wiki 子页面递归下载：**
1. 粘贴 Wiki 父页面链接
2. 勾选"递归下载"
3. 自动下载该页面下的所有子页面
4. 实时显示下载进度

## 📖 使用说明

### Web UI 模式（推荐）

最简单的使用方式，适合所有用户：

```bash
python3 web_ui.py
```

打开浏览器访问 http://localhost:3000

**功能说明：**
- **递归下载 Wiki**：勾选后会下载 Wiki 页面的所有子页面
- **递归下载文档**：勾选后会下载文档中链接的所有子文档
- **导出格式**：选择 Markdown 或 PDF
- **实时进度**：显示下载进度条和当前状态

### 命令行模式

适合高级用户和自动化场景：

```bash
# 配置凭证
python3 feishu_downloader.py config

# 下载单个文档
python3 feishu_downloader.py download DOC_ID

# 下载文档（从 URL）
python3 feishu_downloader.py download https://example.feishu.cn/docx/xxxxx

# 递归下载（含子文档）
python3 feishu_downloader.py download DOC_ID --recursive

# 指定输出目录
python3 feishu_downloader.py download DOC_ID -o ~/Documents/feishu
```

## 🎯 功能详解

### Wiki 子页面递归下载

当输入 Wiki 页面 URL 并勾选"递归下载"时：

1. 下载父页面
2. 自动发现所有子页面
3. 递归下载每个子页面
4. 显示实时进度（如 `[1/8]`, `[2/8]`...）
5. 避免重复下载

**示例：**
```
输入: https://my.feishu.cn/wiki/ParentPageID
输出:
  ├── 父页面.md
  ├── 子页面1.md
  ├── 子页面2.md
  └── ...
```

### 批量下载

在文本框中，每行输入一个文档链接：

```
https://example.feishu.cn/docx/doc1
https://example.feishu.cn/docx/doc2
https://example.feishu.cn/wiki/wiki1
```

点击下载后，会依次下载所有文档。

### PDF 导出

选择 PDF 格式后：
- 自动将 Markdown 转换为 PDF
- 保留完整的文档结构和样式
- 支持中文字体
- 代码块语法高亮

## ⚙️ 配置说明

### 配置文件位置

`~/.config/feishu-downloader/config.json`

### 配置内容

```json
{
  "app_id": "cli_xxx",
  "app_secret": "xxx"
}
```

## 🎨 支持的格式

### 文档元素
- ✅ 文本格式（粗体、斜体、删除线、行内代码）
- ✅ 标题（H1-H9）
- ✅ 列表（有序、无序）
- ✅ 代码块
- ✅ 引用
- ✅ Wiki 子页面递归
- ✅ 批量下载

### 导出格式
- ✅ Markdown (.md)
- ✅ PDF (.pdf)

### 计划支持
- ⏳ 表格
- ⏳ 图片下载
- ⏳ 多线程并发下载

## 🔧 故障排除

### "获取 token 失败"

- 检查 `app_id` 和 `app_secret` 是否正确
- 确认应用已授予必要权限
- 确保应用已发布

### "获取文档内容失败"

- 验证文档 URL 是否正确
- 检查应用是否有权限访问该文档
- 确认文档存在且未被删除
- Wiki 文档需要 `wiki:wiki:readonly` 权限

### "触发限流"

工具会自动处理限流，等待后重试。如果频繁触发：
- 减少并发下载数量
- 增加下载间隔时间

### PDF 导出失败

确保已安装 PDF 导出依赖：
```bash
pip install markdown weasyprint
```

## 📁 项目结构

```
feishu-batch-downloader/
├── feishu_downloader.py    # 核心下载逻辑（CLI）
├── web_ui.py               # Web UI 服务器
├── templates/
│   └── index.html          # Web UI 界面
├── requirements.txt        # Python 依赖
├── README.md               # 英文文档
├── README_CN.md            # 中文文档
└── LICENSE                 # MIT 许可证
```

## 🤝 贡献

欢迎贡献代码！请随时提交 Pull Request。

### 开发指南

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- 飞书开放平台提供的 API 文档
- 开源社区贡献者

## 💬 支持

- 问题反馈：[GitHub Issues](https://github.com/yourusername/feishu-batch-downloader/issues)
- 功能建议：[GitHub Discussions](https://github.com/yourusername/feishu-batch-downloader/discussions)

## 🎯 使用场景

1. **知识库备份** - 批量备份飞书知识库文档
2. **Wiki 导出** - 导出整个 Wiki 空间的所有页面
3. **文档迁移** - 将飞书文档迁移到其他平台
4. **离线阅读** - 下载为 Markdown/PDF 便于离线查看
5. **版本控制** - 将文档纳入 Git 版本管理
6. **自动化备份** - 集成到 CI/CD 流程中自动备份

## 🚀 更新日志

### v1.0.0 (2026-03-05)

- ✅ 支持单个/批量文档下载
- ✅ Wiki 子页面递归下载
- ✅ Markdown 和 PDF 导出
- ✅ Web UI 界面
- ✅ 实时进度显示
- ✅ 凭证自动验证

---

Made with ❤️ by Open Source Community
