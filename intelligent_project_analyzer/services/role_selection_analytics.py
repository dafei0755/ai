"""
角色选择运行时监控与分析模块 (Role Selection Analytics)

功能:
1. 记录每次角色选择决策
2. 统计协同模式使用频率
3. 追踪keywords匹配效果
4. 生成优化建议报告

数据收集:
- 用户输入
- 选择的协同模式
- 选中的角色组合
- 置信度分数
- 执行结果反馈

输出:
- 实时监控日志
- 月度分析报告
- keywords优化建议
"""

import json
import logging
import sqlite3
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# ============================================================================
# 数据模型定义
# ============================================================================

@dataclass
class RoleSelectionRecord:
    """单次角色选择记录"""
    timestamp: str
    user_request: str
    selected_mode: str  # 单一专家/多专家并行/动态合成
    selected_roles: List[Dict[str, str]]  # [{role_id, role_name, dynamic_role_name}]
    confidence: float
    keywords_matched: List[str]
    execution_time_ms: float
    success: bool
    feedback_score: float | None = None  # 用户反馈评分 (1-5)
    error_message: str | None = None
    
    def to_dict(self):
        return asdict(self)


@dataclass
class AnalyticsSummary:
    """统计分析摘要"""
    period: str  # 统计周期 (daily/weekly/monthly)
    total_selections: int
    mode_distribution: Dict[str, int]  # 协同模式分布
    role_usage_frequency: Dict[str, int]  # 角色使用频率
    avg_confidence: float
    success_rate: float
    avg_feedback_score: float
    top_keywords: List[tuple]  # [(keyword, count), ...]
    avg_response_time_ms: float
    recommendations: List[str]  # 优化建议


# ============================================================================
# 数据存储层 (SQLite)
# ============================================================================

class SelectionDatabase:
    """角色选择数据库"""
    
    def __init__(self, db_path: Path | None = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent / "data" / "role_selection_analytics.db"
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 创建选择记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS selection_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    user_request TEXT NOT NULL,
                    selected_mode TEXT NOT NULL,
                    selected_roles TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    keywords_matched TEXT,
                    execution_time_ms REAL,
                    success INTEGER NOT NULL,
                    feedback_score REAL,
                    error_message TEXT
                )
            """)
            
            # 创建keywords匹配记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS keyword_matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_id INTEGER NOT NULL,
                    keyword TEXT NOT NULL,
                    role_id TEXT NOT NULL,
                    match_score REAL,
                    FOREIGN KEY (record_id) REFERENCES selection_records(id)
                )
            """)
            
            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON selection_records(timestamp)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_selected_mode 
                ON selection_records(selected_mode)
            """)
            
            conn.commit()
    
    def insert_record(self, record: RoleSelectionRecord) -> int:
        """插入选择记录"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO selection_records (
                    timestamp, user_request, selected_mode, selected_roles,
                    confidence, keywords_matched, execution_time_ms,
                    success, feedback_score, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.timestamp,
                record.user_request,
                record.selected_mode,
                json.dumps(record.selected_roles, ensure_ascii=False),
                record.confidence,
                json.dumps(record.keywords_matched, ensure_ascii=False),
                record.execution_time_ms,
                1 if record.success else 0,
                record.feedback_score,
                record.error_message
            ))
            conn.commit()
            return cursor.lastrowid
    
    def query_records(
        self, 
        start_date: str | None = None,
        end_date: str | None = None,
        mode: str | None = None
    ) -> List[RoleSelectionRecord]:
        """查询选择记录"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM selection_records WHERE 1=1"
            params = []
            
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date)
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date)
            if mode:
                query += " AND selected_mode = ?"
                params.append(mode)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            records = []
            for row in rows:
                records.append(RoleSelectionRecord(
                    timestamp=row[1],
                    user_request=row[2],
                    selected_mode=row[3],
                    selected_roles=json.loads(row[4]),
                    confidence=row[5],
                    keywords_matched=json.loads(row[6]) if row[6] else [],
                    execution_time_ms=row[7],
                    success=bool(row[8]),
                    feedback_score=row[9],
                    error_message=row[10]
                ))
            
            return records


# ============================================================================
# 分析引擎
# ============================================================================

class RoleSelectionAnalytics:
    """角色选择分析引擎"""
    
    def __init__(self, db_path: Path | None = None):
        self.db = SelectionDatabase(db_path)
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志器"""
        logger = logging.getLogger("RoleSelectionAnalytics")
        logger.setLevel(logging.INFO)
        
        # 控制台输出
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 文件输出
        log_dir = Path(__file__).parent.parent / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(
            log_dir / "role_selection_analytics.log",
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        
        # 格式化
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        
        return logger
    
    def record_selection(
        self,
        user_request: str,
        selected_mode: str,
        selected_roles: List[Dict[str, str]],
        confidence: float,
        keywords_matched: List[str],
        execution_time_ms: float,
        success: bool = True,
        error_message: str | None = None
    ) -> int:
        """
        记录一次角色选择
        
        Args:
            user_request: 用户需求原文
            selected_mode: 选择的协同模式 (单一专家/多专家并行/动态合成)
            selected_roles: 选中的角色列表
            confidence: 置信度分数 (0-1)
            keywords_matched: 匹配到的keywords
            execution_time_ms: 执行耗时(毫秒)
            success: 是否成功
            error_message: 错误信息(如有)
        
        Returns:
            记录ID
        """
        record = RoleSelectionRecord(
            timestamp=datetime.now().isoformat(),
            user_request=user_request,
            selected_mode=selected_mode,
            selected_roles=selected_roles,
            confidence=confidence,
            keywords_matched=keywords_matched,
            execution_time_ms=execution_time_ms,
            success=success,
            error_message=error_message
        )
        
        record_id = self.db.insert_record(record)
        
        self.logger.info(
            f"记录选择决策 [ID:{record_id}] "
            f"模式:{selected_mode} 角色数:{len(selected_roles)} "
            f"置信度:{confidence:.2f} 耗时:{execution_time_ms:.1f}ms"
        )
        
        return record_id
    
    def generate_summary(
        self,
        period: str = "monthly",
        start_date: str | None = None,
        end_date: str | None = None
    ) -> AnalyticsSummary:
        """
        生成统计摘要
        
        Args:
            period: 统计周期 (daily/weekly/monthly)
            start_date: 开始日期 (ISO格式)
            end_date: 结束日期 (ISO格式)
        
        Returns:
            统计摘要对象
        """
        records = self.db.query_records(start_date, end_date)
        
        if not records:
            self.logger.warning("没有找到记录,返回空摘要")
            return self._empty_summary(period)
        
        # 统计协同模式分布
        mode_distribution = Counter(r.selected_mode for r in records)
        
        # 统计角色使用频率
        role_usage = defaultdict(int)
        for record in records:
            for role in record.selected_roles:
                role_id = role.get("role_id", "unknown")
                role_usage[role_id] += 1
        
        # 计算平均置信度
        avg_confidence = sum(r.confidence for r in records) / len(records)
        
        # 计算成功率
        success_count = sum(1 for r in records if r.success)
        success_rate = success_count / len(records)
        
        # 计算平均反馈评分
        feedback_scores = [r.feedback_score for r in records if r.feedback_score is not None]
        avg_feedback_score = sum(feedback_scores) / len(feedback_scores) if feedback_scores else 0.0
        
        # 统计高频keywords
        all_keywords = []
        for record in records:
            all_keywords.extend(record.keywords_matched)
        top_keywords = Counter(all_keywords).most_common(20)
        
        # 计算平均响应时间
        avg_response_time = sum(r.execution_time_ms for r in records) / len(records)
        
        # 生成优化建议
        recommendations = self._generate_recommendations(
            mode_distribution,
            role_usage,
            avg_confidence,
            success_rate,
            top_keywords
        )
        
        summary = AnalyticsSummary(
            period=period,
            total_selections=len(records),
            mode_distribution=dict(mode_distribution),
            role_usage_frequency=dict(role_usage),
            avg_confidence=avg_confidence,
            success_rate=success_rate,
            avg_feedback_score=avg_feedback_score,
            top_keywords=top_keywords,
            avg_response_time_ms=avg_response_time,
            recommendations=recommendations
        )
        
        self.logger.info(f"生成{period}统计摘要: {len(records)}条记录")
        
        return summary
    
    def _generate_recommendations(
        self,
        mode_distribution: Counter,
        role_usage: Dict[str, int],
        avg_confidence: float,
        success_rate: float,
        top_keywords: List[tuple]
    ) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        # 1. 协同模式建议
        total = sum(mode_distribution.values())
        synthesis_ratio = mode_distribution.get("动态合成", 0) / total if total > 0 else 0
        
        if synthesis_ratio > 0.3:
            recommendations.append(
                f"️ 动态合成模式使用率较高({synthesis_ratio:.1%}), "
                "建议检查是否需要新增常用角色到基因库"
            )
        
        # 2. 角色使用建议
        sorted_roles = sorted(role_usage.items(), key=lambda x: x[1], reverse=True)
        if sorted_roles:
            top_role, top_count = sorted_roles[0]
            if top_count / total > 0.5:
                recommendations.append(
                    f" 角色 {top_role} 使用率过高({top_count/total:.1%}), "
                    "建议优化其他角色的keywords以分散负载"
                )
        
        # 3. 置信度建议
        if avg_confidence < 0.7:
            recommendations.append(
                f"️ 平均置信度较低({avg_confidence:.2f}), "
                "建议优化角色基因库或增强语义意图匹配能力"
            )
        
        # 4. 成功率建议
        if success_rate < 0.9:
            recommendations.append(
                f"️ 成功率较低({success_rate:.1%}), "
                "建议检查失败案例并优化错误处理机制"
            )
        
        # 5. Keywords建议
        if top_keywords:
            high_freq_keywords = [kw for kw, count in top_keywords[:5]]
            recommendations.append(
                f" 高频keywords: {', '.join(high_freq_keywords)}, "
                "建议检查是否需要细分或优化"
            )
        
        return recommendations
    
    def _empty_summary(self, period: str) -> AnalyticsSummary:
        """返回空摘要"""
        return AnalyticsSummary(
            period=period,
            total_selections=0,
            mode_distribution={},
            role_usage_frequency={},
            avg_confidence=0.0,
            success_rate=0.0,
            avg_feedback_score=0.0,
            top_keywords=[],
            avg_response_time_ms=0.0,
            recommendations=["暂无数据,无法生成建议"]
        )
    
    def export_report(
        self,
        summary: AnalyticsSummary,
        output_path: Path | None = None
    ) -> Path:
        """
        导出分析报告
        
        Args:
            summary: 统计摘要
            output_path: 输出路径 (默认: reports/目录)
        
        Returns:
            报告文件路径
        """
        if output_path is None:
            report_dir = Path(__file__).parent.parent / "reports"
            report_dir.mkdir(parents=True, exist_ok=True)
            output_path = report_dir / f"role_selection_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        # 生成Markdown报告
        report_content = self._format_report(summary)
        
        output_path.write_text(report_content, encoding='utf-8')
        self.logger.info(f"报告已导出: {output_path}")
        
        return output_path
    
    def _format_report(self, summary: AnalyticsSummary) -> str:
        """格式化报告为Markdown"""
        report = f"""# 角色选择分析报告

**统计周期**: {summary.period}  
**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

##  核心指标

| 指标 | 数值 |
|------|------|
| 总选择次数 | {summary.total_selections} |
| 平均置信度 | {summary.avg_confidence:.2%} |
| 成功率 | {summary.success_rate:.2%} |
| 平均反馈评分 | {summary.avg_feedback_score:.2f}/5.0 |
| 平均响应时间 | {summary.avg_response_time_ms:.1f}ms |

---

##  协同模式分布

"""
        for mode, count in summary.mode_distribution.items():
            percentage = count / summary.total_selections * 100
            report += f"- **{mode}**: {count}次 ({percentage:.1f}%)\n"
        
        report += "\n---\n\n##  角色使用频率 Top 10\n\n"
        
        sorted_roles = sorted(
            summary.role_usage_frequency.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        for i, (role_id, count) in enumerate(sorted_roles, 1):
            report += f"{i}. **{role_id}**: {count}次\n"
        
        report += "\n---\n\n##  高频Keywords Top 20\n\n"
        
        for i, (keyword, count) in enumerate(summary.top_keywords, 1):
            report += f"{i}. `{keyword}`: {count}次\n"
        
        report += "\n---\n\n##  优化建议\n\n"
        
        for i, recommendation in enumerate(summary.recommendations, 1):
            report += f"{i}. {recommendation}\n"
        
        report += "\n---\n\n*本报告由 RoleSelectionAnalytics 自动生成*\n"
        
        return report


# ============================================================================
# 使用示例
# ============================================================================

if __name__ == "__main__":
    # 创建分析引擎实例
    analytics = RoleSelectionAnalytics()
    
    # 模拟记录一些选择数据
    print("="*80)
    print("角色选择运行时监控演示")
    print("="*80)
    
    # 示例1: 单一专家模式
    analytics.record_selection(
        user_request="为150㎡现代简约别墅做室内设计",
        selected_mode="单一专家深潜",
        selected_roles=[{
            "role_id": "2-1",
            "role_name": "居住空间设计总监",
            "dynamic_role_name": "现代简约别墅室内设计专家"
        }],
        confidence=0.92,
        keywords_matched=["居住空间设计", "住宅空间设计", "别墅设计"],
        execution_time_ms=245.6,
        success=True
    )
    
    # 示例2: 多专家并行模式
    analytics.record_selection(
        user_request="三代同堂家庭住宅,考虑代际关系",
        selected_mode="多专家并行",
        selected_roles=[
            {"role_id": "3-1", "role_name": "个体叙事专家", "dynamic_role_name": "家庭关系叙事专家"},
            {"role_id": "2-1", "role_name": "居住空间设计总监", "dynamic_role_name": "多代居住空间设计师"},
            {"role_id": "5-1", "role_name": "居住场景专家", "dynamic_role_name": "家庭生活模式策略师"}
        ],
        confidence=0.85,
        keywords_matched=["家庭叙事", "居住空间设计", "居住场景运营"],
        execution_time_ms=512.3,
        success=True
    )
    
    # 示例3: 动态合成模式
    analytics.record_selection(
        user_request="宋代美学精品酒店",
        selected_mode="动态合成",
        selected_roles=[{
            "role_id": "3-3+2-4+5-4",
            "role_name": "文化驱动的酒店体验设计专家",
            "dynamic_role_name": "宋代美学精品酒店体验总设计师"
        }],
        confidence=0.78,
        keywords_matched=["文化符号转译", "酒店设计", "酒店运营管理"],
        execution_time_ms=823.7,
        success=True
    )
    
    print("\n 已记录3条模拟数据")
    
    # 生成分析报告
    print("\n生成分析报告...")
    summary = analytics.generate_summary(period="demo")
    
    print("\n 统计摘要:")
    print(f"   总选择次数: {summary.total_selections}")
    print(f"   平均置信度: {summary.avg_confidence:.2%}")
    print(f"   成功率: {summary.success_rate:.2%}")
    print(f"   协同模式分布: {summary.mode_distribution}")
    
    # 导出报告
    report_path = analytics.export_report(summary)
    print(f"\n 报告已导出: {report_path}")
    
    print("\n" + "="*80)
    print(" 监控系统部署完成")
    print("="*80)
