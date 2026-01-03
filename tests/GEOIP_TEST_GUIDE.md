# GeoIP 单元测试文档

## 📋 测试概览

本测试套件为 GeoIP 地理位置服务提供全面的单元测试和集成测试。

## 🗂️ 测试文件结构

```
tests/
├── services/
│   └── test_geoip_service.py       # GeoIP 服务单元测试
├── integration/
│   └── test_geoip_integration.py   # 集成测试
└── run_geoip_tests.py              # 测试运行器
```

## 🧪 测试覆盖范围

### 1. 单元测试 (test_geoip_service.py)

#### TestGeoIPService - 核心功能测试
- ✅ `test_init_with_custom_path` - 自定义数据库路径初始化
- ✅ `test_init_with_default_path` - 默认路径初始化
- ✅ `test_get_client_ip_from_x_forwarded_for` - 从 X-Forwarded-For 获取 IP
- ✅ `test_get_client_ip_from_x_real_ip` - 从 X-Real-IP 获取 IP
- ✅ `test_get_client_ip_from_client_host` - 从 client.host 获取 IP
- ✅ `test_get_client_ip_priority` - IP 获取优先级
- ✅ `test_is_private_ip` - 内网 IP 识别
- ✅ `test_get_localhost_location` - 本地回环地址
- ✅ `test_get_private_ip_location` - 内网 IP 定位
- ✅ `test_get_unknown_location` - 未知 IP
- ✅ `test_get_location_success` - 成功获取地理位置
- ✅ `test_get_location_address_not_found` - IP 不在数据库中
- ✅ `test_singleton_get_geoip_service` - 全局单例

#### TestGeoIPServiceIntegration - 集成场景
- ✅ `test_full_workflow_with_request` - 完整请求处理流程
- ✅ `test_edge_cases` - 边界情况

#### TestGeoIPDataFormat - 数据格式验证
- ✅ `test_location_data_structure` - 数据结构完整性
- ✅ `test_location_data_types` - 数据类型正确性

#### TestGeoIPErrorHandling - 错误处理
- ✅ `test_missing_database_file` - 数据库文件不存在
- ✅ `test_corrupted_database` - 损坏的数据库文件

### 2. 集成测试 (test_geoip_integration.py)

#### TestGeoIPServerIntegration - 与 server.py 集成
- ✅ `test_ip_collection_in_start_analysis` - start_analysis 中的 IP 采集
- ✅ `test_session_metadata_structure` - session metadata 结构

#### TestGeoIPAdminRoutesIntegration - 与 admin_routes.py 集成
- ✅ `test_region_distribution_extraction` - 地区分布提取
- ✅ `test_region_list_with_coords` - 带坐标的地区列表

#### TestGeoIPFallbackMechanism - 回退机制
- ✅ `test_fallback_to_user_input` - 回退到用户输入
- ✅ `test_fallback_chain` - 完整回退链

#### TestGeoIPPerformance - 性能测试
- ✅ `test_batch_ip_lookup` - 批量 IP 查询性能

## 🚀 运行测试

### 方式 1: 使用测试运行器（推荐）

```bash
# 运行所有 GeoIP 测试
python tests/run_geoip_tests.py

# 包含覆盖率报告
python tests/run_geoip_tests.py --cov

# 只运行快速测试（跳过 slow 标记的测试）
python tests/run_geoip_tests.py --fast
```

### 方式 2: 使用 pytest 直接运行

```bash
# 运行所有 GeoIP 测试
pytest tests/services/test_geoip_service.py tests/integration/test_geoip_integration.py -v

# 只运行单元测试
pytest tests/services/test_geoip_service.py -v

# 只运行集成测试
pytest tests/integration/test_geoip_integration.py -v

# 运行特定测试类
pytest tests/services/test_geoip_service.py::TestGeoIPService -v

# 运行特定测试方法
pytest tests/services/test_geoip_service.py::TestGeoIPService::test_get_client_ip_from_x_forwarded_for -v

# 带覆盖率报告
pytest tests/services/test_geoip_service.py --cov=intelligent_project_analyzer.services.geoip_service --cov-report=html

# 跳过慢速测试
pytest tests/ -m "not slow" -v
```

### 方式 3: 运行所有项目测试

```bash
# 运行所有测试
pytest

# 只运行 GeoIP 相关测试
pytest -k "geoip" -v
```

## 📊 覆盖率报告

运行带覆盖率的测试后，会生成 HTML 报告：

```bash
python tests/run_geoip_tests.py --cov
```

查看报告：
- 终端：直接显示覆盖率百分比
- HTML：打开 `htmlcov/index.html` 查看详细报告

**目标覆盖率**: >90%

## 🔍 测试标记

测试使用 pytest 标记进行分类：

- `@pytest.mark.slow` - 慢速测试（如性能测试）
- `@pytest.mark.integration` - 集成测试

跳过特定标记的测试：
```bash
pytest -m "not slow"  # 跳过慢速测试
pytest -m "integration"  # 只运行集成测试
```

## 🐛 调试测试

### 打印详细输出

```bash
pytest tests/services/test_geoip_service.py -v -s
```

- `-v`: 详细模式
- `-s`: 显示 print 输出

### 调试失败的测试

```bash
pytest tests/services/test_geoip_service.py --pdb
```

失败时会自动进入 Python 调试器。

### 只运行上次失败的测试

```bash
pytest --lf  # last-failed
```

## 📝 测试数据

### Mock 数据示例

**模拟 Request**:
```python
mock_request = Mock()
mock_request.headers.get = Mock(side_effect=lambda key: {
    "X-Forwarded-For": "1.2.3.4",
    "X-Real-IP": "5.6.7.8",
    "User-Agent": "Mozilla/5.0"
}.get(key))
mock_request.client = Mock(host="9.10.11.12")
```

**模拟地理位置响应**:
```python
{
    "ip": "1.2.3.4",
    "country": "中国",
    "province": "广东省",
    "city": "深圳市",
    "latitude": 22.5431,
    "longitude": 114.0579,
    "timezone": "Asia/Shanghai",
    "is_valid": True
}
```

## ⚠️ 测试注意事项

### 1. 数据库依赖

测试使用 Mock 避免依赖真实的 GeoLite2 数据库：

```python
# 在测试开始前 mock geoip2 模块
sys.modules['geoip2'] = MagicMock()
sys.modules['geoip2.database'] = MagicMock()
sys.modules['geoip2.errors'] = MagicMock()
```

### 2. 网络隔离

所有测试都是离线的，不依赖外部网络或 API。

### 3. 测试环境

确保安装测试依赖：

```bash
pip install pytest pytest-cov pytest-mock
```

## 📈 持续集成

### GitHub Actions 配置

```yaml
name: GeoIP Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-cov
      - run: python tests/run_geoip_tests.py --cov
      - run: pytest --cov-report=xml
      - uses: codecov/codecov-action@v2
```

## 🎯 测试最佳实践

### 1. 测试命名

遵循 `test_<功能>_<场景>` 模式：
- `test_get_client_ip_from_x_forwarded_for`
- `test_get_location_success`
- `test_fallback_to_user_input`

### 2. 使用 Fixtures

为重复的测试数据使用 fixtures：

```python
@pytest.fixture
def mock_request(self):
    """创建模拟的 FastAPI Request"""
    request = Mock()
    # ... 配置
    return request
```

### 3. 参数化测试

为多个输入使用参数化：

```python
@pytest.mark.parametrize("ip,expected", [
    ("10.0.0.1", True),
    ("192.168.1.1", True),
    ("8.8.8.8", False),
])
def test_is_private_ip(self, ip, expected):
    service = GeoIPService()
    assert service._is_private_ip(ip) == expected
```

## 🔧 故障排查

### 问题 1: 导入错误

**症状**: `ModuleNotFoundError: No module named 'intelligent_project_analyzer'`

**解决**: 确保从项目根目录运行测试，或设置 PYTHONPATH：

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest tests/
```

### 问题 2: Mock 失败

**症状**: `AttributeError: 'MagicMock' object has no attribute 'city'`

**解决**: 确保 Mock 对象配置正确：

```python
mock_reader = Mock()
mock_reader.city = Mock(return_value=mock_response)
```

### 问题 3: 测试超时

**症状**: 测试运行时间过长

**解决**: 跳过慢速测试：

```bash
pytest -m "not slow"
```

## 📚 参考资料

- [pytest 文档](https://docs.pytest.org/)
- [unittest.mock 文档](https://docs.python.org/3/library/unittest.mock.html)
- [GeoIP2 Python API](https://geoip2.readthedocs.io/)

---

**文档版本**: v1.0  
**更新日期**: 2026年1月3日
