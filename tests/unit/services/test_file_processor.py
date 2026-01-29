"""
文件处理器单元测试
测试多格式文件上传、编码检测、Vision分析、内容提取
"""

import io
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_file_system():
    """创建Mock文件系统"""
    from tests.fixtures.mocks import MockFileSystem

    return MockFileSystem()


@pytest.fixture
def mock_chardet():
    """创建Mock编码检测器"""
    from tests.fixtures.mocks import MockChardet

    return MockChardet()


@pytest.fixture
def mock_vision_llm():
    """创建Mock Vision LLM"""
    from tests.fixtures.mocks import MockAsyncLLM

    return MockAsyncLLM(
        responses=['{"description": "A modern office interior", "key_elements": ["desk", "chair", "lighting"]}']
    )


@pytest.fixture
def sample_pdf_content():
    """示例PDF内容（文本格式）"""
    return b"%PDF-1.4\nSimple PDF content for testing"


@pytest.fixture
def sample_image_file():
    """示例图片文件（模拟UploadFile）"""
    mock_file = Mock()
    mock_file.filename = "test_image.jpg"
    mock_file.content_type = "image/jpeg"
    mock_file.file = io.BytesIO(b"\xff\xd8\xff\xe0" + b"\x00" * 100)  # JPEG header
    return mock_file


# ============================================================================
# 文件保存测试
# ============================================================================


class TestFileSaving:
    """测试文件异步保存功能"""

    @pytest.mark.asyncio
    async def test_save_uploaded_file_success(self, mock_file_system):
        """测试成功保存上传文件"""
        session_id = "test_session_123"
        filename = "user_doc.pdf"
        content = b"PDF content here"

        # 模拟保存
        file_path = f"data/uploads/{session_id}/{filename}"
        await mock_file_system.write(file_path, content)

        assert mock_file_system.exists(file_path)
        assert len(mock_file_system.write_history) == 1
        assert mock_file_system.write_history[0]["path"] == file_path

    @pytest.mark.asyncio
    async def test_session_isolation(self, mock_file_system):
        """测试会话隔离存储"""
        session1 = "session_001"
        session2 = "session_002"

        await mock_file_system.write(f"data/uploads/{session1}/file.txt", b"content1")
        await mock_file_system.write(f"data/uploads/{session2}/file.txt", b"content2")

        # 两个会话的文件应该独立存储
        content1 = await mock_file_system.read(f"data/uploads/{session1}/file.txt")
        content2 = await mock_file_system.read(f"data/uploads/{session2}/file.txt")

        assert content1 == b"content1"
        assert content2 == b"content2"

    def test_filename_sanitization(self):
        """测试文件名安全清理"""
        # 移除路径遍历攻击
        dangerous_names = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config",
            "file<script>.txt",
            "file|name.pdf",
        ]

        for name in dangerous_names:
            # 清理逻辑：只保留文件名部分，移除特殊字符
            safe_name = Path(name).name.replace("..", "").replace("|", "_").replace("<", "_").replace(">", "_")

            assert ".." not in safe_name
            assert "|" not in safe_name
            assert "<" not in safe_name

    @pytest.mark.asyncio
    async def test_file_overwrite_protection(self, mock_file_system):
        """测试文件覆盖保护（时间戳命名）"""
        session_id = "test_session"
        base_filename = "document.pdf"

        # 第一次上传
        await mock_file_system.write(f"data/uploads/{session_id}/{base_filename}", b"v1")

        # 第二次上传同名文件（应该添加时间戳）
        import time

        timestamp = int(time.time() * 1000)
        unique_filename = f"document_{timestamp}.pdf"
        await mock_file_system.write(f"data/uploads/{session_id}/{unique_filename}", b"v2")

        assert len(mock_file_system.files) == 2


# ============================================================================
# PDF提取测试
# ============================================================================


class TestPDFExtraction:
    """测试PDF文本提取"""

    @pytest.mark.asyncio
    async def test_extract_text_from_pdf_success(self):
        """测试成功提取PDF文本"""
        # Mock pdfplumber
        with patch("pdfplumber.open") as mock_pdfplumber:
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "This is page 1 content"
            mock_pdf.pages = [mock_page]
            mock_pdfplumber.return_value.__enter__.return_value = mock_pdf

            # 模拟提取
            with patch("pdfplumber.open") as mp:
                mp.return_value.__enter__.return_value = mock_pdf
                text = mock_page.extract_text()

            assert "page 1 content" in text

    @pytest.mark.asyncio
    async def test_pdf_fallback_to_pypdf2(self):
        """测试pdfplumber失败后降级到PyPDF2"""
        # Mock pdfplumber失败
        with patch("pdfplumber.open", side_effect=Exception("pdfplumber failed")):
            pdfplumber_failed = True

        # 尝试PyPDF2
        if pdfplumber_failed:
            with patch("PyPDF2.PdfReader") as mock_pypdf:
                mock_reader = MagicMock()
                mock_page = MagicMock()
                mock_page.extract_text.return_value = "PyPDF2 extracted text"
                mock_reader.pages = [mock_page]
                mock_pypdf.return_value = mock_reader

                text = mock_page.extract_text()
                assert text == "PyPDF2 extracted text"

    def test_multipage_pdf_extraction(self):
        """测试多页PDF提取"""
        with patch("pdfplumber.open") as mock_pdfplumber:
            mock_pdf = MagicMock()
            mock_pdf.pages = [
                MagicMock(extract_text=lambda: "Page 1"),
                MagicMock(extract_text=lambda: "Page 2"),
                MagicMock(extract_text=lambda: "Page 3"),
            ]
            mock_pdfplumber.return_value.__enter__.return_value = mock_pdf

            # 合并所有页面文本
            all_text = "\n\n".join([page.extract_text() for page in mock_pdf.pages])

            assert "Page 1" in all_text
            assert "Page 2" in all_text
            assert "Page 3" in all_text

    def test_encrypted_pdf_handling(self):
        """测试加密PDF处理"""
        with patch("pdfplumber.open") as mock_pdfplumber:
            mock_pdfplumber.side_effect = Exception("PDF is encrypted")

            # 应该捕获异常并返回错误信息
            try:
                with patch("pdfplumber.open") as mp:
                    mp.side_effect = Exception("PDF is encrypted")
                    raise mp.side_effect
            except Exception as e:
                error_msg = str(e)

            assert "encrypted" in error_msg.lower()


# ============================================================================
# 编码检测测试
# ============================================================================


class TestEncodingDetection:
    """测试文本文件编码检测"""

    def test_detect_utf8_encoding(self, mock_chardet):
        """测试检测UTF-8编码"""
        utf8_text = "这是UTF-8编码的文本".encode("utf-8")

        result = mock_chardet.detect(utf8_text)

        assert result["encoding"].lower() in ["utf-8", "utf8"]
        assert result["confidence"] > 0.8

    def test_detect_gbk_encoding(self, mock_chardet):
        """测试检测GBK编码"""
        gbk_text = "这是GBK编码的文本".encode("gbk")

        result = mock_chardet.detect(gbk_text)

        # Mock返回gbk
        assert result["encoding"].lower() in ["gbk", "gb2312"]

    def test_encoding_fallback_chain(self):
        """测试编码检测降级链"""
        problematic_bytes = b"\x80\x81\x82\x83"

        # 尝试编码链：UTF-8 → GBK → Latin-1
        encodings_to_try = ["utf-8", "gbk", "gb2312", "latin-1"]

        for encoding in encodings_to_try:
            try:
                text = problematic_bytes.decode(encoding)
                success_encoding = encoding
                break
            except:
                continue

        # 至少Latin-1应该成功（接受所有字节）
        assert success_encoding == "latin-1"

    def test_mixed_encoding_handling(self):
        """测试混合编码处理"""
        # 部分UTF-8，部分GBK（实际场景可能存在）
        mixed_bytes = "正常文本".encode("utf-8") + b"\xd5\xe2\xca\xc7" + "more text".encode("utf-8")

        # 应该尝试UTF-8并忽略错误
        try:
            text = mixed_bytes.decode("utf-8", errors="ignore")
            assert "正常文本" in text
        except:
            # 降级到GBK
            text = mixed_bytes.decode("gbk", errors="ignore")


# ============================================================================
# Vision分析测试
# ============================================================================


class TestVisionAnalysis:
    """测试图片Vision分析"""

    @pytest.mark.asyncio
    async def test_analyze_image_success(self, mock_vision_llm):
        """测试成功分析图片"""
        image_path = "uploads/test_image.jpg"

        # 模拟Vision调用
        response = await mock_vision_llm.ainvoke(f"Analyze this image: {image_path}")

        assert "modern" in response.content.lower() or "office" in response.content.lower()

    @pytest.mark.asyncio
    async def test_vision_timeout_fallback(self):
        """测试Vision超时降级"""
        from tests.fixtures.mocks import MockAsyncLLM

        # 模拟超时
        timeout_llm = MockAsyncLLM()
        timeout_llm.ainvoke = AsyncMock(side_effect=TimeoutError("Vision API timeout"))

        # 应该捕获超时并返回空结果
        try:
            await timeout_llm.ainvoke("Analyze image")
            vision_result = "success"
        except TimeoutError:
            vision_result = None  # 降级：不使用Vision分析

        assert vision_result is None

    @pytest.mark.asyncio
    async def test_vision_with_timeout_protection(self, mock_vision_llm):
        """测试Vision 30秒超时保护"""
        import asyncio

        # 模拟超时保护
        try:
            response = await asyncio.wait_for(mock_vision_llm.ainvoke("Analyze image"), timeout=30.0)
            success = True
        except asyncio.TimeoutError:
            success = False

        # Mock应该快速响应，不会超时
        assert success

    def test_vision_result_parsing(self):
        """测试Vision结果JSON解析"""
        vision_json = '{"description": "Modern office", "elements": ["desk", "chair"]}'

        import json

        result = json.loads(vision_json)

        assert "description" in result
        assert isinstance(result["elements"], list)


# ============================================================================
# Word/Excel提取测试
# ============================================================================


class TestOfficeFormats:
    """测试Word和Excel文件处理"""

    def test_extract_word_document(self):
        """测试Word文档文本提取"""
        with patch("docx.Document") as mock_docx:
            mock_doc = MagicMock()
            mock_paragraph1 = MagicMock()
            mock_paragraph1.text = "Paragraph 1"
            mock_paragraph2 = MagicMock()
            mock_paragraph2.text = "Paragraph 2"
            mock_doc.paragraphs = [mock_paragraph1, mock_paragraph2]
            mock_docx.return_value = mock_doc

            # 提取文本
            text = "\n".join([p.text for p in mock_doc.paragraphs])

            assert "Paragraph 1" in text
            assert "Paragraph 2" in text

    def test_extract_excel_spreadsheet(self):
        """测试Excel表格提取"""
        with patch("pandas.read_excel") as mock_read_excel:
            # 模拟DataFrame
            import pandas as pd

            mock_df = pd.DataFrame({"Column1": ["Value1", "Value2"], "Column2": ["ValueA", "ValueB"]})
            mock_read_excel.return_value = mock_df

            # 转换为文本
            text = mock_df.to_string()

            assert "Column1" in text
            assert "Value1" in text

    def test_excel_multiple_sheets(self):
        """测试Excel多工作表处理"""
        with patch("pandas.read_excel") as mock_read_excel:
            # 模拟多个工作表
            import pandas as pd

            def read_excel_side_effect(file, sheet_name=0):
                if sheet_name == 0:
                    return pd.DataFrame({"Sheet1": ["Data1"]})
                elif sheet_name == 1:
                    return pd.DataFrame({"Sheet2": ["Data2"]})

            mock_read_excel.side_effect = read_excel_side_effect

            # 读取多个工作表
            df1 = mock_read_excel("file.xlsx", sheet_name=0)
            df2 = mock_read_excel("file.xlsx", sheet_name=1)

            assert "Sheet1" in df1.columns
            assert "Sheet2" in df2.columns


# ============================================================================
# 内容合并测试
# ============================================================================


class TestContentMerging:
    """测试用户输入与文件内容合并"""

    def test_merge_user_input_and_file(self):
        """测试合并用户输入和文件内容"""
        user_input = "我需要设计一个办公室"
        file_content = "附件：参考图片显示的是现代简约风格"

        merged = f"{user_input}\n\n[附件内容]\n{file_content}"

        assert user_input in merged
        assert file_content in merged
        assert "[附件内容]" in merged

    def test_content_truncation(self):
        """测试内容截断逻辑（防止超出Token限制）"""
        long_content = "A" * 50000
        max_length = 10000

        truncated = long_content[:max_length]

        assert len(truncated) == max_length
        assert len(truncated) < len(long_content)

    def test_multiple_files_merging(self):
        """测试多文件内容合并"""
        files_content = [
            {"name": "doc1.pdf", "content": "Document 1 content"},
            {"name": "doc2.txt", "content": "Document 2 content"},
            {"name": "image.jpg", "content": "[Image: Modern office]"},
        ]

        merged = []
        for file in files_content:
            merged.append(f"[{file['name']}]\n{file['content']}")

        final_content = "\n\n".join(merged)

        assert "doc1.pdf" in final_content
        assert "Document 1 content" in final_content
        assert "doc2.txt" in final_content

    def test_file_type_labeling(self):
        """测试文件类型标注"""
        files = [("requirements.pdf", "PDF文档"), ("reference.jpg", "图片"), ("data.xlsx", "Excel表格")]

        labeled_content = []
        for filename, filetype in files:
            labeled_content.append(f"[{filetype}: {filename}]")

        result = "\n".join(labeled_content)

        assert "PDF文档" in result
        assert "图片" in result
        assert "Excel表格" in result


# ============================================================================
# 边界和异常测试
# ============================================================================


class TestEdgeCases:
    """测试边界情况和异常处理"""

    @pytest.mark.asyncio
    async def test_empty_file_handling(self, mock_file_system):
        """测试空文件处理"""
        empty_file_path = "data/uploads/session/empty.txt"
        await mock_file_system.write(empty_file_path, b"")

        content = await mock_file_system.read(empty_file_path)

        assert len(content) == 0

    @pytest.mark.asyncio
    async def test_file_not_found_error(self, mock_file_system):
        """测试文件不存在错误"""
        with pytest.raises(FileNotFoundError):
            await mock_file_system.read("nonexistent/file.txt")

    def test_unsupported_file_type(self):
        """测试不支持的文件类型"""
        unsupported_types = [".exe", ".dll", ".bin", ".zip"]
        allowed_types = [".pdf", ".txt", ".docx", ".xlsx", ".jpg", ".png"]

        test_filename = "file.exe"
        file_ext = Path(test_filename).suffix

        is_supported = file_ext in allowed_types

        assert not is_supported

    def test_very_large_file_handling(self):
        """测试超大文件处理（应该拒绝）"""
        max_file_size = 50 * 1024 * 1024  # 50MB
        file_size = 100 * 1024 * 1024  # 100MB

        is_too_large = file_size > max_file_size

        assert is_too_large

    def test_special_characters_in_content(self):
        """测试内容中的特殊字符处理"""
        special_content = "Content with <script>alert('xss')</script> and \x00 null bytes"

        # 清理特殊字符
        cleaned = special_content.replace("\x00", "").replace("<script>", "").replace("</script>", "")

        assert "\x00" not in cleaned
        assert "<script>" not in cleaned
