#!/usr/bin/env python3
"""
Feishu Document Batch Downloader
飞书文档批量下载器

A simple tool to download Feishu documents recursively in Markdown or PDF format.
"""

import os
import sys
import json
import time
import argparse
import requests
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta


class FeishuClient:
    """飞书 API 客户端"""

    BASE_URL = "https://open.feishu.cn/open-apis"

    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.token = None
        self.token_expire_time = None
        self._validate_credentials()

    def _validate_credentials(self):
        """验证凭证格式"""
        if not self.app_id or not self.app_secret:
            raise ValueError("app_id 和 app_secret 不能为空")

        if not self.app_id.startswith("cli_"):
            raise ValueError("app_id 格式错误，应该以 'cli_' 开头")

        if self.app_id == self.app_secret:
            raise ValueError("app_id 和 app_secret 不能相同，请检查配置")

        if len(self.app_secret) < 20:
            raise ValueError("app_secret 长度过短，请检查是否完整")

    def get_tenant_access_token(self) -> str:
        """获取 tenant_access_token"""
        if self.token and self.token_expire_time and datetime.now() < self.token_expire_time:
            return self.token

        url = f"{self.BASE_URL}/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()

            data = response.json()
            if data.get("code") != 0:
                error_msg = data.get('msg', '未知错误')
                error_code = data.get('code')
                raise Exception(f"获取 token 失败 (错误码: {error_code}): {error_msg}\n"
                              f"请检查：\n"
                              f"1. app_id 和 app_secret 是否正确\n"
                              f"2. 应用是否已发布\n"
                              f"3. 应用权限是否已配置")

            self.token = data["tenant_access_token"]
            expire_seconds = data.get("expire", 7200)
            self.token_expire_time = datetime.now() + timedelta(seconds=expire_seconds - 60)

            return self.token

        except requests.exceptions.Timeout:
            raise Exception("连接超时，请检查网络连接")
        except requests.exceptions.ConnectionError:
            raise Exception("无法连接到飞书服务器，请检查网络连接")
        except requests.exceptions.RequestException as e:
            raise Exception(f"网络请求失败: {str(e)}")

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """发送 API 请求"""
        token = self.get_tenant_access_token()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"

        url = f"{self.BASE_URL}/{endpoint}"

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.request(method, url, headers=headers, **kwargs)

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 2 ** attempt))
                    print(f"触发限流，等待 {retry_after} 秒...")
                    time.sleep(retry_after)
                    continue

                response.raise_for_status()
                return response.json()

            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise
                print(f"请求失败，重试 {attempt + 1}/{max_retries}...")
                time.sleep(2 ** attempt)

        raise Exception("请求失败")

    def get_wiki_node_info(self, node_token: str) -> Dict[str, Any]:
        """获取 Wiki 节点信息"""
        endpoint = f"wiki/v2/spaces/get_node"
        params = {"token": node_token}
        result = self._request("GET", endpoint, params=params)

        if result.get("code") != 0:
            error_msg = result.get('msg', '未知错误')
            error_code = result.get('code')
            raise Exception(f"获取 Wiki 节点信息失败 (错误码: {error_code}): {error_msg}\n"
                          f"节点 Token: {node_token}\n"
                          f"请检查：\n"
                          f"1. Wiki URL 是否正确\n"
                          f"2. 应用是否有 wiki:wiki:readonly 权限")

        return result.get("data", {}).get("node", {})

    def get_wiki_child_nodes(self, space_id: str, parent_node_token: str) -> List[Dict[str, Any]]:
        """获取 Wiki 节点的子节点列表"""
        endpoint = f"wiki/v2/spaces/{space_id}/nodes"
        params = {"parent_node_token": parent_node_token, "page_size": 50}

        all_nodes = []
        page_token = None

        while True:
            if page_token:
                params["page_token"] = page_token

            result = self._request("GET", endpoint, params=params)

            if result.get("code") != 0:
                error_msg = result.get('msg', '未知错误')
                error_code = result.get('code')
                print(f"  ⚠️  获取子节点失败 (错误码: {error_code}): {error_msg}")
                break

            data = result.get("data", {})
            nodes = data.get("items", [])
            all_nodes.extend(nodes)

            page_token = data.get("page_token")
            if not page_token or not data.get("has_more"):
                break

        return all_nodes

    def get_document_raw_content(self, document_id: str, is_wiki: bool = False) -> Dict[str, Any]:
        """获取文档原始内容"""
        # 如果是 Wiki 文档，先获取节点信息，然后获取对应的 docx
        if is_wiki:
            try:
                node_info = self.get_wiki_node_info(document_id)
                obj_token = node_info.get("obj_token")
                obj_type = node_info.get("obj_type")
                title = node_info.get("title", "未命名")

                if not obj_token:
                    raise Exception(f"Wiki 节点没有关联的文档对象\n节点 Token: {document_id}")

                # Wiki 节点可能关联 docx 或其他类型
                if obj_type != "docx":
                    raise Exception(f"暂不支持该 Wiki 节点类型: {obj_type}\n"
                                  f"当前仅支持文档类型的 Wiki 节点\n"
                                  f"节点 Token: {document_id}")

                # 使用 obj_token 作为文档 ID
                document_id = obj_token
                print(f"  Wiki 文档: {title}")
                print(f"  对象 Token: {document_id}")

            except Exception as e:
                raise Exception(f"处理 Wiki 文档失败: {str(e)}")

        # 使用 blocks API 获取结构化内容（而不是 raw_content）
        endpoint = f"docx/v1/documents/{document_id}/blocks"
        params = {"page_size": 500}

        all_blocks = []
        page_token = None

        while True:
            if page_token:
                params["page_token"] = page_token

            result = self._request("GET", endpoint, params=params)

            if result.get("code") != 0:
                error_msg = result.get('msg', '未知错误')
                error_code = result.get('code')

                # 提供更详细的错误信息
                if error_code == 99991663:
                    raise Exception(f"文档不存在或无权限访问 (文档ID: {document_id})\n"
                                  f"请检查：\n"
                                  f"1. 文档 URL 是否正确\n"
                                  f"2. 应用是否有权限访问该文档\n"
                                  f"3. 文档是否已被删除或移动")
                elif error_code == 99991401:
                    raise Exception(f"应用无权限访问文档 (文档ID: {document_id})\n"
                                  f"请在飞书开放平台添加权限：\n"
                                  f"- docx:document:readonly\n"
                                  f"- drive:drive:readonly\n"
                                  f"- wiki:wiki:readonly (如果是 Wiki 文档)")
                else:
                    raise Exception(f"获取文档内容失败 (错误码: {error_code}): {error_msg}\n文档ID: {document_id}")

            data = result.get("data", {})
            blocks = data.get("items", [])
            all_blocks.extend(blocks)

            page_token = data.get("page_token")
            if not page_token or not data.get("has_more"):
                break

        # 构造与 raw_content API 兼容的数据结构
        return {
            "content": {
                "blocks": all_blocks
            }
        }

    def list_folder_children(self, folder_token: str) -> List[Dict[str, Any]]:
        """列出文件夹下的子文档"""
        endpoint = "drive/v1/files"
        params = {"folder_token": folder_token, "page_size": 200}

        result = self._request("GET", endpoint, params=params)

        if result.get("code") != 0:
            raise Exception(f"获取子文档列表失败: {result.get('msg')}")

        return result.get("data", {}).get("files", [])

    def get_document_blocks(self, document_id: str) -> List[Dict[str, Any]]:
        """获取文档的所有块（用于查找子文档链接）"""
        endpoint = f"docx/v1/documents/{document_id}/blocks"
        params = {"page_size": 500}

        all_blocks = []
        page_token = None

        while True:
            if page_token:
                params["page_token"] = page_token

            result = self._request("GET", endpoint, params=params)

            if result.get("code") != 0:
                raise Exception(f"获取文档块失败: {result.get('msg')}")

            data = result.get("data", {})
            blocks = data.get("items", [])
            all_blocks.extend(blocks)

            page_token = data.get("page_token")
            if not page_token or not data.get("has_more"):
                break

        return all_blocks


class MarkdownConverter:
    """将飞书文档转换为 Markdown"""

    @staticmethod
    def convert(content: Dict[str, Any]) -> str:
        """转换文档内容为 Markdown"""
        blocks = content.get("content", {}).get("blocks", [])
        markdown_lines = []

        for block in blocks:
            block_type = block.get("block_type")

            # 根据不同的 block_type 提取内容
            if block_type == 1:  # Page (文档根节点，包含标题)
                text = MarkdownConverter._extract_text_from_block(block, "page")
                if text:
                    markdown_lines.append(f"# {text}")
            elif block_type == 2:  # 文本
                text = MarkdownConverter._extract_text_from_block(block, "text")
                if text:
                    markdown_lines.append(text)
            elif block_type == 3:  # 标题1
                text = MarkdownConverter._extract_text_from_block(block, "heading1")
                if text:
                    markdown_lines.append(f"# {text}")
            elif block_type == 4:  # 标题2
                text = MarkdownConverter._extract_text_from_block(block, "heading2")
                if text:
                    markdown_lines.append(f"## {text}")
            elif block_type == 5:  # 标题3
                text = MarkdownConverter._extract_text_from_block(block, "heading3")
                if text:
                    markdown_lines.append(f"### {text}")
            elif block_type == 6:  # 标题4
                text = MarkdownConverter._extract_text_from_block(block, "heading4")
                if text:
                    markdown_lines.append(f"#### {text}")
            elif block_type == 7:  # 标题5
                text = MarkdownConverter._extract_text_from_block(block, "heading5")
                if text:
                    markdown_lines.append(f"##### {text}")
            elif block_type == 8:  # 标题6
                text = MarkdownConverter._extract_text_from_block(block, "heading6")
                if text:
                    markdown_lines.append(f"###### {text}")
            elif block_type == 9:  # 标题7
                text = MarkdownConverter._extract_text_from_block(block, "heading7")
                if text:
                    markdown_lines.append(f"####### {text}")
            elif block_type == 10:  # 标题8
                text = MarkdownConverter._extract_text_from_block(block, "heading8")
                if text:
                    markdown_lines.append(f"######## {text}")
            elif block_type == 11:  # 标题9
                text = MarkdownConverter._extract_text_from_block(block, "heading9")
                if text:
                    markdown_lines.append(f"######### {text}")
            elif block_type == 12:  # 无序列表
                text = MarkdownConverter._extract_text_from_block(block, "bullet")
                if text:
                    markdown_lines.append(f"- {text}")
            elif block_type == 13:  # 有序列表
                text = MarkdownConverter._extract_text_from_block(block, "ordered")
                if text:
                    markdown_lines.append(f"1. {text}")
            elif block_type == 15:  # 代码块
                text = MarkdownConverter._extract_text_from_block(block, "code")
                language = block.get("code", {}).get("style", {}).get("language", "")
                if text:
                    markdown_lines.append(f"```{language}\n{text}\n```")
            elif block_type == 16:  # 引用
                text = MarkdownConverter._extract_text_from_block(block, "quote")
                if text:
                    markdown_lines.append(f"> {text}")

            markdown_lines.append("")  # 空行

        return "\n".join(markdown_lines)

    @staticmethod
    def _extract_text_from_block(block: Dict[str, Any], field_name: str) -> str:
        """从块中提取文本（支持新的 blocks API 结构）"""
        # 获取对应字段的 elements
        field_data = block.get(field_name, {})
        elements = field_data.get("elements", [])

        text_parts = []
        for element in elements:
            text_run = element.get("text_run", {})
            text = text_run.get("content", "")
            style = text_run.get("text_element_style", {})

            # 处理样式
            if style.get("bold"):
                text = f"**{text}**"
            if style.get("italic"):
                text = f"*{text}*"
            if style.get("strikethrough"):
                text = f"~~{text}~~"
            if style.get("inline_code"):
                text = f"`{text}`"

            text_parts.append(text)

        return "".join(text_parts)

    @staticmethod
    def _extract_text(block: Dict[str, Any]) -> str:
        """提取块中的文本（兼容旧的 raw_content API）"""
        elements = block.get("text", {}).get("elements", [])
        text_parts = []

        for element in elements:
            text = element.get("text_run", {}).get("content", "")
            style = element.get("text_run", {}).get("text_element_style", {})

            # 处理样式
            if style.get("bold"):
                text = f"**{text}**"
            if style.get("italic"):
                text = f"*{text}*"
            if style.get("strikethrough"):
                text = f"~~{text}~~"
            if style.get("inline_code"):
                text = f"`{text}`"

            text_parts.append(text)

        return "".join(text_parts)


class FeishuDownloader:
    """飞书文档下载器"""

    def __init__(self, client: FeishuClient, output_dir: str = "./downloads", output_format: str = "markdown"):
        self.client = client
        self.output_dir = Path(output_dir).expanduser().absolute()
        self.output_format = output_format.lower()  # "markdown" or "pdf"

        # 验证输出目录
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            raise Exception(f"无权限创建目录: {self.output_dir}\n请检查目录权限或选择其他位置")
        except OSError as e:
            raise Exception(f"创建目录失败: {self.output_dir}\n错误: {str(e)}")

        if not os.access(self.output_dir, os.W_OK):
            raise Exception(f"目录不可写: {self.output_dir}\n请检查目录权限")

        self.downloaded_docs = set()  # 记录已下载的文档，避免重复

    def download_document(self, doc_id: str, filename: Optional[str] = None, recursive: bool = False, depth: int = 0, is_wiki: bool = False):
        """下载单个文档"""
        # 避免重复下载
        if doc_id in self.downloaded_docs:
            print(f"  {'  ' * depth}⊙ 跳过已下载: {doc_id}")
            return

        indent = "  " * depth
        doc_type = "Wiki 文档" if is_wiki else "文档"
        print(f"{indent}📄 正在下载{doc_type}: {doc_id}")

        try:
            # 如果是 Wiki 文档且需要递归，先获取子节点
            wiki_children = []
            if is_wiki and recursive:
                try:
                    node_info = self.client.get_wiki_node_info(doc_id)
                    space_id = node_info.get("space_id")
                    has_child = node_info.get("has_child", False)

                    if has_child and space_id:
                        print(f"{indent}  🔍 查找子页面...")
                        wiki_children = self.client.get_wiki_child_nodes(space_id, doc_id)
                        if wiki_children:
                            print(f"{indent}  📂 发现 {len(wiki_children)} 个子页面")
                except Exception as e:
                    print(f"{indent}  ⚠️  获取子页面失败: {e}")

            # 下载当前文档
            content = self.client.get_document_raw_content(doc_id, is_wiki=is_wiki)

            # 转换为 Markdown
            markdown = MarkdownConverter.convert(content)

            # 生成文件名
            if not filename:
                if is_wiki:
                    # Wiki 文档从节点信息获取标题
                    node_info = self.client.get_wiki_node_info(doc_id)
                    title = node_info.get("title", doc_id)
                else:
                    # 普通文档从内容获取标题
                    title_elements = content.get("content", {}).get("title", {}).get("elements", [])
                    if title_elements:
                        title = title_elements[0].get("text_run", {}).get("content", doc_id)
                    else:
                        title = doc_id
                filename = self._sanitize_filename(title)

            # 保存文件
            if self.output_format == "pdf":
                filepath = self.output_dir / f"{filename}.pdf"
                self._save_as_pdf(markdown, filepath, filename)
            else:
                filepath = self.output_dir / f"{filename}.md"
                filepath.write_text(markdown, encoding="utf-8")

            self.downloaded_docs.add(doc_id)
            print(f"{indent}✓ 已保存: {filepath}")

            # 递归下载 Wiki 子页面
            if wiki_children:
                for i, child_node in enumerate(wiki_children, 1):
                    child_token = child_node.get("node_token")
                    child_title = child_node.get("title", child_token)
                    if child_token:
                        print(f"{indent}  [{i}/{len(wiki_children)}] 下载子页面: {child_title}")
                        self.download_document(child_token, child_title, recursive=True, depth=depth + 1, is_wiki=True)
                        # 添加小延迟，让进度更新有时间显示
                        time.sleep(0.3)

            # 递归下载文档内链接的子文档（原有功能）
            if recursive and not is_wiki:
                child_docs = self._find_child_documents(doc_id)
                if child_docs:
                    print(f"{indent}📂 发现 {len(child_docs)} 个链接文档")
                    for child_id, child_title in child_docs:
                        # 子文档可能也是 wiki 链接，需要检测
                        child_is_wiki = "wiki" in child_id or len(child_id) > 30
                        self.download_document(child_id, child_title, recursive=True, depth=depth + 1, is_wiki=child_is_wiki)

        except Exception as e:
            print(f"{indent}✗ 下载失败: {e}")

    def download_batch(self, doc_ids: List[str], recursive: bool = False):
        """批量下载多个文档"""
        total = len(doc_ids)
        print(f"📦 开始批量下载 {total} 个文档...")
        print("=" * 60)

        for i, doc_id in enumerate(doc_ids, 1):
            print(f"\n[{i}/{total}] 处理文档: {doc_id}")
            self.download_document(doc_id, recursive=recursive)
            time.sleep(0.5)  # 避免请求过快

        print("\n" + "=" * 60)
        print(f"✅ 批量下载完成！共下载 {len(self.downloaded_docs)} 个文档")

    def _find_child_documents(self, doc_id: str) -> List[tuple]:
        """查找文档中的子文档链接"""
        try:
            blocks = self.client.get_document_blocks(doc_id)
            child_docs = []

            for block in blocks:
                block_type = block.get("block_type")

                # 检查是否是文档链接块
                if block_type == 27:  # 文档链接类型
                    doc_link = block.get("doc_link", {})
                    child_doc_id = doc_link.get("doc_id")
                    if child_doc_id:
                        title = doc_link.get("title", child_doc_id)
                        child_docs.append((child_doc_id, title))

                # 检查文本中的链接
                elif block_type in [1, 2, 3, 4]:  # 文本、标题
                    elements = block.get("text", {}).get("elements", [])
                    for element in elements:
                        link = element.get("text_run", {}).get("text_element_style", {}).get("link", {})
                        url = link.get("url", "")
                        if "feishu.cn/docx/" in url or "feishu.cn/wiki/" in url:
                            # 提取文档 ID
                            parts = url.split("/")
                            for j, part in enumerate(parts):
                                if part in ["docx", "wiki"]:
                                    if j + 1 < len(parts):
                                        child_doc_id = parts[j + 1].split("?")[0]
                                        child_docs.append((child_doc_id, child_doc_id))
                                        break

            return child_docs

        except Exception as e:
            print(f"  查找子文档失败: {e}")
            return []

    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, "_")
        return filename[:200]  # 限制长度

    def _save_as_pdf(self, markdown_content: str, filepath: Path, title: str):
        """将 Markdown 转换为 PDF"""
        try:
            import markdown
            from weasyprint import HTML, CSS
            from io import BytesIO

            # 转换 Markdown 到 HTML
            html_content = markdown.markdown(
                markdown_content,
                extensions=['extra', 'codehilite', 'tables', 'fenced_code']
            )

            # 添加 CSS 样式
            css_style = """
            <style>
                body {
                    font-family: "PingFang SC", "Microsoft YaHei", "Helvetica Neue", Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 40px auto;
                    padding: 20px;
                }
                h1, h2, h3, h4, h5, h6 {
                    margin-top: 24px;
                    margin-bottom: 16px;
                    font-weight: 600;
                    line-height: 1.25;
                }
                h1 { font-size: 2em; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }
                h2 { font-size: 1.5em; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }
                h3 { font-size: 1.25em; }
                code {
                    background-color: #f6f8fa;
                    padding: 2px 6px;
                    border-radius: 3px;
                    font-family: "Courier New", monospace;
                    font-size: 0.9em;
                }
                pre {
                    background-color: #f6f8fa;
                    padding: 16px;
                    border-radius: 6px;
                    overflow-x: auto;
                }
                pre code {
                    background-color: transparent;
                    padding: 0;
                }
                blockquote {
                    border-left: 4px solid #dfe2e5;
                    padding-left: 16px;
                    color: #6a737d;
                    margin: 0;
                }
                table {
                    border-collapse: collapse;
                    width: 100%;
                    margin: 16px 0;
                }
                table th, table td {
                    border: 1px solid #dfe2e5;
                    padding: 8px 12px;
                }
                table th {
                    background-color: #f6f8fa;
                    font-weight: 600;
                }
                a {
                    color: #0366d6;
                    text-decoration: none;
                }
                a:hover {
                    text-decoration: underline;
                }
            </style>
            """

            full_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>{title}</title>
                {css_style}
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """

            # 转换为 PDF
            HTML(string=full_html).write_pdf(filepath)

        except ImportError:
            raise Exception("PDF 导出需要安装依赖：pip install markdown weasyprint")
        except Exception as e:
            raise Exception(f"PDF 转换失败: {str(e)}")


def load_config() -> Dict[str, str]:
    """加载配置文件"""
    config_path = Path.home() / ".config" / "feishu-downloader" / "config.json"

    if config_path.exists():
        with open(config_path, "r") as f:
            return json.load(f)

    return {}


def save_config(config: Dict[str, str]):
    """保存配置文件"""
    config_dir = Path.home() / ".config" / "feishu-downloader"
    config_dir.mkdir(parents=True, exist_ok=True)

    config_path = config_dir / "config.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="飞书文档批量下载器 / Feishu Document Batch Downloader"
    )

    subparsers = parser.add_subparsers(dest="command", help="命令")

    # config 命令
    config_parser = subparsers.add_parser("config", help="配置凭证")
    config_parser.add_argument("--app-id", help="应用 ID")
    config_parser.add_argument("--app-secret", help="应用密钥")

    # download 命令
    download_parser = subparsers.add_parser("download", help="下载文档")
    download_parser.add_argument("doc_id", help="文档 ID 或 URL")
    download_parser.add_argument("-o", "--output", default=str(Path.home() / "Downloads"), help="输出目录（默认为系统下载文件夹）")
    download_parser.add_argument("-r", "--recursive", action="store_true", help="递归下载子文档")
    download_parser.add_argument("--app-id", help="应用 ID（覆盖配置）")
    download_parser.add_argument("--app-secret", help="应用密钥（覆盖配置）")

    args = parser.parse_args()

    if args.command == "config":
        config = load_config()

        if args.app_id:
            config["app_id"] = args.app_id
        if args.app_secret:
            config["app_secret"] = args.app_secret

        if not args.app_id and not args.app_secret:
            # 交互式输入
            app_id = input("请输入应用 ID (app_id): ").strip()
            app_secret = input("请输入应用密钥 (app_secret): ").strip()

            if app_id:
                config["app_id"] = app_id
            if app_secret:
                config["app_secret"] = app_secret

        save_config(config)
        print("✓ 配置已保存")

    elif args.command == "download":
        config = load_config()

        app_id = args.app_id or config.get("app_id")
        app_secret = args.app_secret or config.get("app_secret")

        if not app_id or not app_secret:
            print("错误: 请先配置凭证")
            print("运行: python feishu_downloader.py config")
            sys.exit(1)

        # 从 URL 提取文档 ID
        doc_id = args.doc_id
        if "feishu.cn" in doc_id or "larksuite.com" in doc_id:
            # 简单提取 ID（实际可能需要更复杂的解析）
            parts = doc_id.split("/")
            for i, part in enumerate(parts):
                if part in ["docx", "doc", "wiki", "base"]:
                    if i + 1 < len(parts):
                        doc_id = parts[i + 1].split("?")[0]
                        break

        client = FeishuClient(app_id, app_secret)
        downloader = FeishuDownloader(client, args.output)

        downloader.download_document(doc_id, recursive=args.recursive)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
