# Milvus 向量数据库知识库 - 快速入门指南

## 概述

本项目已完成 **Milvus + 自建 RAG Pipeline** 深度定制方案的实施，提供高质量的知识检索能力。

### 核心特性

- **6 阶段深度定制 Pipeline**:
  1. 查询理解与改写 (Query Understanding)
  2. 混合检索 (Hybrid Retrieval - 向量+标量过滤)
  3. 粗排 (Coarse Ranking)
  4. 重排序 (Reranking with BGE-Reranker-v2-M3)
  5. 后处理与质量控制 (去重+可信度评分)
  6. 结果组装与监控

- **性能优势**:
  - 检索延迟: <300ms (vs RAGFlow 1800ms)
  - 检索质量: Precision@10 目标 85-90%
  - QPS: 1000+ (vs RAGFlow 100)

- **完整集成**:
  - 无缝替换 RAGFlow
  - 复用现有 SearchQualityControl 和 DeliverableQueryBuilder
  - 兼容 LangChain 工具协议

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

新增依赖:
- `pymilvus>=2.4.0` - Milvus Python SDK
- `langchain-milvus>=0.1.0` - LangChain 集成
- `sentence-transformers>=2.3.0` - Embedding 和 Reranker
- `FlagEmbedding>=1.2.0` - BGE 系列模型

### 2. 启动 Milvus 服务

**🆕 v7.141: 自动启动模式（推荐）**

从 v7.141 版本开始，Milvus 服务已集成到生产服务器启动流程中，无需手动启动：

```bash
python -B scripts\run_server_production.py
```

启动时会自动：
1. 检测 Docker 是否已安装
2. 检查 Milvus 容器是否运行
3. 如未运行，自动启动 Milvus 服务
4. 等待健康检查通过后启动应用

**手动启动模式（可选）**

如需单独启动 Milvus 服务，可使用：

```bash
docker-compose -f docker-compose.milvus.yml up -d
```

服务端口:
- Milvus gRPC: `localhost:19530`
- Milvus Web UI: `localhost:9091`
- Attu 管理界面: `localhost:3000` (可选)

### 3. 配置环境变量

复制并编辑配置文件:

```bash
cp .env.development.example .env
```

关键配置:

```env
# 启用 Milvus 知识库
MILVUS_ENABLED=true

# Milvus 服务器配置
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_COLLECTION_NAME=design_knowledge_base

# Embedding 模型 (中英文支持)
MILVUS_EMBEDDING_MODEL=BAAI/bge-m3
MILVUS_EMBEDDING_DIM=1024

# Reranker 配置
MILVUS_RERANK_ENABLED=true
MILVUS_RERANKER_MODEL=BAAI/bge-reranker-v2-m3
MILVUS_RERANK_WEIGHT=0.7
```

### 4. 导入知识库数据

准备文档文件夹，支持格式:
- `.txt` - 纯文本
- `.md` - Markdown
- `.json` - 结构化数据

运行导入脚本:

```bash
python scripts/import_milvus_data.py \
  --source ./data/knowledge_docs \
  --collection design_knowledge_base \
  --batch-size 32
```

参数说明:
- `--source`: 文档源文件夹路径
- `--collection`: Collection 名称
- `--host`: Milvus 服务器地址 (默认: localhost)
- `--port`: Milvus 端口 (默认: 19530)
- `--embedding-model`: Embedding 模型 (默认: BAAI/bge-m3)
- `--batch-size`: 批量插入大小 (默认: 32)

### 5. 测试运行

运行测试脚本验证:

```bash
python scripts/test_milvus_kb.py
```

测试内容:
1. Milvus 连接测试
2. 基础搜索功能
3. 交付物搜索功能
4. 性能基准测试
5. LangChain 集成测试

### 6. 集成到系统

Milvus 已自动集成到主工作流，所有专家角色将使用 `milvus` 工具:

```python
role_tool_mapping = {
    "V2": ["milvus"],  # 设计总监
    "V3": ["bocha", "tavily", "milvus"],  # 叙事专家
    "V4": ["bocha", "tavily", "arxiv", "milvus"],  # 设计研究员
    "V5": ["bocha", "tavily", "milvus"],  # 场景专家
    "V6": ["bocha", "tavily", "arxiv", "milvus"],  # 总工程师
}
```

## 使用示例

### Python API

```python
from intelligent_project_analyzer.tools.milvus_kb import MilvusKBTool

# 创建工具实例
tool = MilvusKBTool(
    host="localhost",
    port=19530,
    collection_name="design_knowledge_base"
)

# 基础搜索
result = tool.search_knowledge(
    query="现代简约风格的客厅设计要点",
    max_results=10
)

# 交付物搜索
deliverable = {
    "name": "室内设计方案",
    "description": "包含空间规划、材料选择、照明设计"
}
result = tool.search_for_deliverable(
    deliverable=deliverable,
    project_type="residential",
    max_results=10
)

# 健康检查
health = tool.health_check()
print(health)
```

### LangChain 集成

```python
from intelligent_project_analyzer.services.tool_factory import ToolFactory

# 通过工厂创建
milvus_tool = ToolFactory.create_milvus_tool()

# 使用 LangChain 工具
result = milvus_tool.func("现代简约风格设计要点")
```

## 数据结构

### Collection Schema

```python
fields = [
    FieldSchema(name="id", dtype=VARCHAR, is_primary=True),
    FieldSchema(name="title", dtype=VARCHAR),
    FieldSchema(name="content", dtype=VARCHAR),
    FieldSchema(name="vector", dtype=FLOAT_VECTOR, dim=1024),
    FieldSchema(name="document_type", dtype=VARCHAR),  # 设计规范/案例库/技术知识
    FieldSchema(name="tags", dtype=ARRAY),
    FieldSchema(name="project_type", dtype=VARCHAR),  # residential/commercial等
    FieldSchema(name="source_file", dtype=VARCHAR),
]
```

### 搜索结果格式

```json
{
  "success": true,
  "query": "原始查询",
  "results": [
    {
      "title": "文档标题",
      "content": "文档内容",
      "snippet": "内容摘要 (300字)",
      "relevance_score": 0.85,
      "credibility_score": 0.9,
      "reference_number": 1,
      "source": "milvus",
      "metadata": {
        "document_type": "设计规范",
        "tags": ["现代", "简约"],
        "project_type": "residential",
        "source_file": "design_standards.txt"
      }
    }
  ],
  "total_results": 10,
  "execution_time": 0.285,
  "pipeline_metrics": {
    "query_processing_time": 0.010,
    "retrieval_time": 0.150,
    "reranking_time": 0.100,
    "candidates_count": 50,
    "filtered_count": 10
  }
}
```

## 性能调优

### 检索参数优化

```env
# 粗排相似度阈值 (降低阈值可增加召回，但降低精度)
MILVUS_SIMILARITY_THRESHOLD=0.6

# 候选集扩大倍数 (增加倍数可提升重排序质量)
MILVUS_CANDIDATE_MULTIPLIER=5

# 重排序分数权重 (调整向量检索和重排序的权重比例)
MILVUS_RERANK_WEIGHT=0.7  # 0.7表示70%重排+30%向量
```

### HNSW 索引参数

修改 `scripts/import_milvus_data.py`:

```python
index_params = {
    "index_type": "HNSW",
    "metric_type": "COSINE",
    "params": {
        "M": 16,  # 增加M可提升召回率，但增加内存
        "efConstruction": 256  # 增加可提升索引质量
    }
}

# 搜索参数
search_params = {
    "params": {
        "ef": 128  # 增加ef可提升召回率
    }
}
```

## 监控与运维

### 健康检查

```bash
curl http://localhost:9091/healthz
```

### Attu 管理界面

访问 `http://localhost:3000`:
- 查看 Collection 统计
- 执行向量搜索
- 管理索引和数据

### 性能监控

Pipeline 自动记录指标:

```python
# 查看日志
tail -f logs/milvus_kb.log

# 关键指标
- query_processing_time: 查询处理耗时
- retrieval_time: 向量检索耗时
- reranking_time: 重排序耗时
- candidates_count: 候选文档数
- filtered_count: 最终文档数
```

## 故障排除

### Milvus 连接失败

```bash
# 检查 Milvus 服务状态
docker ps | grep milvus

# 查看日志
docker logs milvus-standalone

# 重启服务
docker-compose -f docker-compose.milvus.yml restart
```

### 模型加载失败

```python
# 手动下载模型
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("BAAI/bge-m3")  # 自动下载到 ~/.cache/huggingface
```

### 检索质量不佳

1. 调整相似度阈值: `MILVUS_SIMILARITY_THRESHOLD`
2. 增加候选集倍数: `MILVUS_CANDIDATE_MULTIPLIER`
3. 启用重排序: `MILVUS_RERANK_ENABLED=true`
4. 优化文档质量: 检查导入的文档内容

## 扩展与定制

### 添加新的文档类型

修改 `scripts/import_milvus_data.py`:

```python
# 支持 .pdf 文件
import PyPDF2

if file_path.suffix == ".pdf":
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        content = "\n".join([page.extract_text() for page in reader.pages])
        documents.append({...})
```

### 自定义 Pipeline 阶段

修改 `intelligent_project_analyzer/tools/milvus_kb.py`:

```python
# 添加自定义后处理逻辑
class CustomPostProcessor(PostProcessor):
    def process(self, reranked_docs, deliverable_context=None):
        # 自定义逻辑
        processed = super().process(reranked_docs, deliverable_context)
        # 额外处理
        return processed
```

## 下一步

- 导入实际知识库数据
- 调整检索参数以匹配业务场景
- 集成到生产环境
- 监控性能指标并持续优化

## 支持

如有问题，请查看:
- [Milvus 官方文档](https://milvus.io/docs)
- [BGE 模型文档](https://github.com/FlagOpen/FlagEmbedding)
- 项目 Issues
