"""
违规记录器 - 记录所有违规尝试
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
from loguru import logger


class ViolationLogger:
    """违规记录器"""
    
    def __init__(self, log_file: str = "logs/security/violations.jsonl"):
        """
        初始化违规记录器
        
        Args:
            log_file: 日志文件路径
        """
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
    
    def log(self, violation: Dict[str, Any]):
        """
        记录违规事件
        
        Args:
            violation: 违规详情
        """
        try:
            # 添加时间戳
            if "timestamp" not in violation:
                violation["timestamp"] = datetime.now().isoformat()
            
            # 写入JSONL格式
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(violation, ensure_ascii=False) + '\n')
            
            logger.info(f"📝 违规记录已保存: {violation.get('violation_type', 'unknown')}")
            
        except Exception as e:
            logger.error(f"❌ 保存违规记录失败: {e}")
    
    def get_statistics(self, time_range: str = "24h") -> Dict[str, Any]:
        """
        获取违规统计
        
        Args:
            time_range: 时间范围（如"24h", "7d"）
            
        Returns:
            统计数据
        """
        try:
            if not self.log_file.exists():
                return {"total": 0}
            
            violations = []
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        violations.append(json.loads(line))
                    except:
                        continue
            
            # 简化统计
            total = len(violations)
            by_type = {}
            for v in violations:
                vtype = v.get("violation_type", "unknown")
                by_type[vtype] = by_type.get(vtype, 0) + 1
            
            return {
                "total_violations": total,  # 统一字段名
                "total": total,  # 兼容旧版
                "by_type": by_type,
                "recent": violations[-10:] if violations else []
            }
            
        except Exception as e:
            logger.error(f"❌ 获取违规统计失败: {e}")
            return {"total": 0, "error": str(e)}
