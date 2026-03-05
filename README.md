# Feishu Batch Downloader

> 📥 **Batch Download** Feishu Documents | 🌳 **Wiki Sub-pages Recursion** | 📄 Export as **Markdown/PDF**

[中文文档](README_CN.md) | [English Documentation](README.md)

[![Python Version](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## ✨ Core Highlights

### 🎯 Three Core Features

1. **📦 Batch Download** - Download multiple documents at once with batch URL input
2. **🌳 Wiki Sub-pages Recursion** - Automatically download all sub-pages under a Wiki page (unique feature)
3. **📄 Markdown/PDF Export** - Flexible export formats with complete document structure

### 💡 More Features

- 🔄 **Document Links Recursion** - Automatically download all linked documents
- 🎨 **Web UI** - Clean and beautiful web interface
- 📊 **Real-time Progress** - Live progress bar and status updates
- 💾 **Auto-save Config** - Credentials saved automatically
- ✅ **Credential Validation** - Automatic validation when saving config
- 🖥️ **Cross-platform** - Works on Windows, macOS, Linux

## 📸 Screenshots

![Web UI](https://via.placeholder.com/800x500?text=Web+UI+Screenshot)

## 📋 Requirements

- Python 3.7+
- Dependencies:
  - `requests` - HTTP requests
  - `flask` - Web server
  - `markdown` - Markdown conversion (for PDF export)
  - `weasyprint` - PDF generation (for PDF export)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/feishu-batch-downloader.git
cd feishu-batch-downloader
```

### 2. Install Dependencies

**Basic features (Markdown export):**
```bash
pip install -r requirements.txt
```

Or install manually:
```bash
pip install requests flask
```

**Full features (including PDF export):**
```bash
pip install requests flask markdown weasyprint
```

### 3. Start Web UI

```bash
python3 web_ui.py
```

Then open in browser: **http://localhost:3000**

### 4. Configure Feishu App Credentials

#### Complete Configuration Process

**Step 1: Create Application**
1. Visit [Feishu Open Platform](https://open.feishu.cn/app)
2. Click "Create Enterprise Self-built Application"
3. Fill in application name and description

**Step 2: Get Credentials**
1. Enter application management page
2. Go to "Credentials & Basic Info"
3. Copy separately:
   - **App ID** (format: `cli_xxxxxxxxxx`)
   - **App Secret** (long string, different from App ID)

**Step 3: Configure Permissions (Important!)**

Method 1: Batch Import (Recommended)
1. Go to "Permissions & Scopes" page
2. Click "Batch Configure Permissions"
3. Paste the following JSON code:

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

Method 2: Manual Addition
- `docx:document:readonly` - Read document content
- `drive:drive:readonly` - Read drive files
- `wiki:wiki:readonly` - Read wiki content (**Required for Wiki documents**)

**Step 4: Publish Application**
1. Go to "Version Management & Release"
2. Create version
3. Apply for release
4. Publish to internal enterprise

**Step 5: Save Config in Web UI**
1. Enter App ID and App Secret
2. Click "Save Configuration"
3. System will automatically validate credentials

### 5. Start Downloading

**Single Document:**
1. Paste document link
2. Choose save location
3. Select export format (Markdown or PDF)
4. Click "Start Download"

**Batch Download:**
1. Paste one document link per line
2. Choose save location and format
3. Click "Start Download"

**Wiki Sub-pages Recursion:**
1. Paste Wiki parent page link
2. Check "Recursive Download"
3. Automatically downloads all sub-pages
4. Real-time progress display

## 📖 Usage

### Web UI Mode (Recommended)

Easiest way for all users:

```bash
python3 web_ui.py
```

Open browser and visit http://localhost:3000

**Features:**
- **Recursive Wiki**: Downloads all sub-pages under a Wiki page
- **Recursive Documents**: Downloads all linked documents
- **Export Format**: Choose Markdown or PDF
- **Real-time Progress**: Progress bar and status updates

### CLI Mode

For advanced users and automation:

```bash
# Configure credentials
python3 feishu_downloader.py config

# Download single document
python3 feishu_downloader.py download DOC_ID

# Download from URL
python3 feishu_downloader.py download https://example.feishu.cn/docx/xxxxx

# Recursive download
python3 feishu_downloader.py download DOC_ID --recursive

# Specify output directory
python3 feishu_downloader.py download DOC_ID -o ~/Documents/feishu
```

## 🎯 Feature Details

### Wiki Sub-pages Recursion

When entering a Wiki page URL with "Recursive Download" checked:

1. Downloads parent page
2. Automatically discovers all sub-pages
3. Recursively downloads each sub-page
4. Shows real-time progress (e.g., `[1/8]`, `[2/8]`...)
5. Avoids duplicate downloads

**Example:**
```
Input: https://my.feishu.cn/wiki/ParentPageID
Output:
  ├── Parent Page.md
  ├── Sub Page 1.md
  ├── Sub Page 2.md
  └── ...
```

### Batch Download

In the text box, enter one document link per line:

```
https://example.feishu.cn/docx/doc1
https://example.feishu.cn/docx/doc2
https://example.feishu.cn/wiki/wiki1
```

Click download to process all documents sequentially.

### PDF Export

When PDF format is selected:
- Automatically converts Markdown to PDF
- Preserves complete document structure and styles
- Supports Chinese fonts
- Code block syntax highlighting

## ⚙️ Configuration

### Config File Location

`~/.config/feishu-downloader/config.json`

### Config Content

```json
{
  "app_id": "cli_xxx",
  "app_secret": "xxx"
}
```

## 🎨 Supported Features

### Document Elements
- ✅ Text formatting (bold, italic, strikethrough, inline code)
- ✅ Headings (H1-H9)
- ✅ Lists (ordered, unordered)
- ✅ Code blocks
- ✅ Quotes
- ✅ Wiki sub-pages recursion
- ✅ Batch download

### Export Formats
- ✅ Markdown (.md)
- ✅ PDF (.pdf)

### Planned Features
- ⏳ Tables
- ⏳ Image download
- ⏳ Multi-threaded concurrent download

## 🔧 Troubleshooting

### "Failed to get token"

- Check if `app_id` and `app_secret` are correct
- Ensure application has required permissions
- Make sure application is published

### "Failed to get document content"

- Verify document URL is correct
- Check if application has access to the document
- Ensure document exists and is not deleted
- Wiki documents require `wiki:wiki:readonly` permission

### "Rate limiting triggered"

Tool automatically handles rate limiting with retry. If frequently triggered:
- Reduce concurrent downloads
- Increase download interval

### PDF Export Failed

Make sure PDF export dependencies are installed:
```bash
pip install markdown weasyprint
```

## 📁 Project Structure

```
feishu-batch-downloader/
├── feishu_downloader.py    # Core download logic (CLI)
├── web_ui.py               # Web UI server
├── templates/
│   └── index.html          # Web UI interface
├── requirements.txt        # Python dependencies
├── README.md               # English documentation
├── README_CN.md            # Chinese documentation
└── LICENSE                 # MIT License
```

## 🤝 Contributing

Contributions are welcome! Feel free to submit Pull Requests.

### Development Guide

1. Fork the project
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details

## 🙏 Acknowledgments

- Feishu Open Platform for API documentation
- Open source community contributors

## 💬 Support

- Bug Reports: [GitHub Issues](https://github.com/yourusername/feishu-batch-downloader/issues)
- Feature Requests: [GitHub Discussions](https://github.com/yourusername/feishu-batch-downloader/discussions)

## 🎯 Use Cases

1. **Knowledge Base Backup** - Batch backup Feishu knowledge base documents
2. **Wiki Export** - Export entire Wiki space with all pages
3. **Document Migration** - Migrate Feishu documents to other platforms
4. **Offline Reading** - Download as Markdown/PDF for offline access
5. **Version Control** - Include documents in Git version management
6. **Automated Backup** - Integrate into CI/CD for automatic backups

## 🚀 Changelog

### v1.0.0 (2026-03-05)

- ✅ Single/batch document download
- ✅ Wiki sub-pages recursion
- ✅ Markdown and PDF export
- ✅ Web UI interface
- ✅ Real-time progress display
- ✅ Automatic credential validation

---

Made with ❤️ by Open Source Community
