#!/usr/bin/env python3
"""
Feishu Document Downloader - Web UI
飞书文档下载器 - Web 界面
"""

from flask import Flask, render_template, request, jsonify, send_file, Response, stream_with_context
import os
import json
import queue
import threading
from pathlib import Path
from feishu_downloader import FeishuClient, FeishuDownloader, MarkdownConverter

app = Flask(__name__)

# 配置文件路径
CONFIG_DIR = Path.home() / ".config" / "feishu-downloader"
CONFIG_FILE = CONFIG_DIR / "config.json"

# 进度队列
progress_queues = {}


def load_config():
    """加载配置"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}


def save_config(config):
    """保存配置"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


@app.route("/")
def index():
    """主页"""
    config = load_config()
    # 默认下载路径为系统下载文件夹
    default_download_path = str(Path.home() / "Downloads")
    return render_template("index.html",
                         app_id=config.get("app_id", ""),
                         app_secret=config.get("app_secret", ""),
                         default_download_path=default_download_path)


@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    """配置 API"""
    if request.method == "GET":
        config = load_config()
        return jsonify({
            "app_id": config.get("app_id", ""),
            "app_secret": config.get("app_secret", "")
        })

    elif request.method == "POST":
        data = request.json
        app_id = data.get("app_id", "").strip()
        app_secret = data.get("app_secret", "").strip()

        # 验证凭证格式
        if not app_id or not app_secret:
            return jsonify({"success": False, "message": "app_id 和 app_secret 不能为空"})

        if not app_id.startswith("cli_"):
            return jsonify({"success": False, "message": "app_id 格式错误，应该以 'cli_' 开头"})

        if app_id == app_secret:
            return jsonify({"success": False, "message": "app_id 和 app_secret 不能相同，请检查配置"})

        if len(app_secret) < 20:
            return jsonify({"success": False, "message": "app_secret 长度过短，请检查是否完整"})

        # 测试凭证是否有效
        try:
            client = FeishuClient(app_id, app_secret)
            client.get_tenant_access_token()  # 尝试获取 token
        except Exception as e:
            return jsonify({"success": False, "message": f"凭证验证失败: {str(e)}"})

        # 保存配置
        config = {
            "app_id": app_id,
            "app_secret": app_secret
        }
        save_config(config)
        return jsonify({"success": True, "message": "配置已保存并验证成功！"})


@app.route("/api/download", methods=["POST"])
def api_download():
    """下载文档 API - 启动下载任务"""
    try:
        data = request.json
        doc_urls = data.get("doc_urls", "")
        recursive = data.get("recursive", False)
        output_dir = data.get("output_dir", str(Path.home() / "Downloads"))
        output_format = data.get("output_format", "markdown")

        if not doc_urls:
            return jsonify({"success": False, "message": "请输入文档 URL"})

        # 加载配置
        config = load_config()
        app_id = config.get("app_id")
        app_secret = config.get("app_secret")

        if not app_id or not app_secret:
            return jsonify({"success": False, "message": "请先配置 app_id 和 app_secret"})

        # 解析多个 URL（按行分割）
        urls = [url.strip() for url in doc_urls.split("\n") if url.strip()]

        # 提取文档 ID
        try:
            doc_info_list = []
            for url in urls:
                doc_id, is_wiki = extract_doc_id(url)
                doc_info_list.append((doc_id, is_wiki))
        except ValueError as e:
            return jsonify({"success": False, "message": str(e)})

        if not doc_info_list:
            return jsonify({"success": False, "message": "未找到有效的文档 URL 或 ID"})

        # 路径处理：支持绝对路径和相对路径（相对于当前工作目录）
        try:
            output_dir = Path(output_dir).expanduser().absolute()
        except Exception as e:
            return jsonify({"success": False, "message": f"路径格式错误: {str(e)}"})

        # 生成任务 ID
        import uuid
        task_id = str(uuid.uuid4())

        # 创建进度队列
        progress_queues[task_id] = queue.Queue()

        # 在后台线程中执行下载
        def download_task():
            try:
                # 创建客户端和下载器
                client = FeishuClient(app_id, app_secret)
                downloader = FeishuDownloaderWithProgress(client, str(output_dir), task_id, output_format)

                total = len(doc_info_list)
                progress_queues[task_id].put({
                    "type": "start",
                    "total": total,
                    "message": f"开始下载 {total} 个文档（格式：{output_format.upper()}）..."
                })

                # 批量下载
                if len(doc_info_list) > 1:
                    for i, (doc_id, is_wiki) in enumerate(doc_info_list, 1):
                        if task_id in progress_queues:
                            progress_queues[task_id].put({
                                "type": "progress",
                                "current": i,
                                "total": total,
                                "doc_id": doc_id,
                                "message": f"[{i}/{total}] 正在下载: {doc_id}"
                            })
                        downloader.download_document(doc_id, recursive=recursive, is_wiki=is_wiki)
                        import time
                        time.sleep(0.5)
                else:
                    doc_id, is_wiki = doc_info_list[0]
                    downloader.download_document(doc_id, recursive=recursive, is_wiki=is_wiki)

                count = len(downloader.downloaded_docs)

                if count == 0:
                    progress_queues[task_id].put({
                        "type": "error",
                        "message": "下载失败：未成功下载任何文档\n请检查文档 ID 是否正确，以及应用是否有权限访问"
                    })
                else:
                    progress_queues[task_id].put({
                        "type": "complete",
                        "count": count,
                        "message": f"下载完成！共下载 {count} 个文档，保存在 {output_dir} 目录"
                    })

            except ValueError as e:
                progress_queues[task_id].put({
                    "type": "error",
                    "message": f"参数错误: {str(e)}"
                })
            except Exception as e:
                progress_queues[task_id].put({
                    "type": "error",
                    "message": f"下载失败: {str(e)}"
                })

        thread = threading.Thread(target=download_task)
        thread.daemon = True
        thread.start()

        return jsonify({
            "success": True,
            "task_id": task_id,
            "message": "下载任务已启动"
        })

    except Exception as e:
        return jsonify({"success": False, "message": f"启动下载失败: {str(e)}"})


@app.route("/api/progress/<task_id>")
def api_progress(task_id):
    """进度推送 API - Server-Sent Events"""
    def generate():
        if task_id not in progress_queues:
            yield f"data: {json.dumps({'type': 'error', 'message': '任务不存在'})}\n\n"
            return

        q = progress_queues[task_id]
        while True:
            try:
                # 等待进度更新
                progress = q.get(timeout=30)
                yield f"data: {json.dumps(progress)}\n\n"

                # 如果任务完成或出错，结束流
                if progress.get("type") in ["complete", "error"]:
                    # 清理队列
                    del progress_queues[task_id]
                    break
            except queue.Empty:
                # 发送心跳
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


def extract_doc_id(url):
    """从 URL 提取文档 ID，返回 (doc_id, is_wiki)"""
    url = url.strip()

    # 如果已经是纯 ID，直接返回
    if not ("http://" in url or "https://" in url):
        return (url, False)

    # 支持的域名
    if "feishu.cn" not in url and "larksuite.com" not in url:
        raise ValueError(f"不支持的 URL 格式: {url}\n仅支持飞书(feishu.cn)和 Lark(larksuite.com) 链接")

    # 解析 URL
    parts = url.split("/")
    for i, part in enumerate(parts):
        if part in ["docx", "doc", "wiki", "base", "sheets", "mindnote", "file"]:
            if i + 1 < len(parts):
                doc_id = parts[i + 1].split("?")[0].split("#")[0]
                if doc_id:
                    is_wiki = (part == "wiki")
                    return (doc_id, is_wiki)

    raise ValueError(f"无法从 URL 中提取文档 ID: {url}\n请检查 URL 格式是否正确")


class FeishuDownloaderWithProgress(FeishuDownloader):
    """带进度报告的下载器"""

    def __init__(self, client, output_dir, task_id, output_format="markdown"):
        super().__init__(client, output_dir, output_format)
        self.task_id = task_id
        self.total_docs = 0  # 总文档数（包括子页面）

    def download_document(self, doc_id, filename=None, recursive=False, depth=0, is_wiki=False):
        """下载单个文档并报告进度"""
        # 报告进度
        if self.task_id in progress_queues and depth == 0:
            # 只在顶层报告进度
            doc_type = "Wiki 页面" if is_wiki else "文档"
            progress_queues[self.task_id].put({
                "type": "progress",
                "current": len(self.downloaded_docs) + 1,
                "doc_id": doc_id,
                "message": f"正在下载{doc_type}: {doc_id}"
            })
        elif self.task_id in progress_queues and depth > 0:
            # 子页面也报告进度
            doc_type = "子页面" if is_wiki else "子文档"
            progress_queues[self.task_id].put({
                "type": "progress",
                "current": len(self.downloaded_docs) + 1,
                "doc_id": doc_id,
                "message": f"{'  ' * depth}正在下载{doc_type}: {doc_id}"
            })

        # 调用父类方法
        super().download_document(doc_id, filename, recursive, depth, is_wiki)


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 飞书文档下载器 Web UI 已启动")
    print("=" * 60)
    print("📱 请在浏览器中打开: http://localhost:3000")
    print("=" * 60)
    app.run(debug=True, host="0.0.0.0", port=3000)
