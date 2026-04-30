"""
增强正则检测器 - 隐私信息和变形规避检测
"""

import re
from typing import List, Dict, Tuple
from loguru import logger


class EnhancedRegexDetector:
    """增强正则检测器"""

    # 隐私信息正则模式
    PRIVACY_PATTERNS = {
        "手机号": {
            "pattern": r'1[3-9]\d{9}',
            "severity": "medium",
            "description": "检测到中国大陆手机号"
        },
        "固定电话": {
            "pattern": r'0\d{2,3}-?\d{7,8}',
            "severity": "low",
            "description": "检测到固定电话号码"
        },
        "身份证号": {
            "pattern": r'\d{17}[\dXx]',
            "severity": "high",
            "description": "检测到18位身份证号"
        },
        "身份证号(15位)": {
            "pattern": r'\d{15}',
            "severity": "high",
            "description": "检测到15位身份证号"
        },
        "电子邮箱": {
            "pattern": r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',
            "severity": "low",
            "description": "检测到电子邮箱地址"
        },
        "银行卡号": {
            "pattern": r'(?<!\d)\d{16,19}(?!\d)',
            "severity": "high",
            "description": "检测到疑似银行卡号"
        },
        "IP地址(IPv4)": {
            "pattern": r'(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)',
            "severity": "low",
            "description": "检测到IPv4地址"
        },
        "IP地址(IPv6)": {
            "pattern": r'\b(?:[A-Fa-f0-9]{1,4}:){7}[A-Fa-f0-9]{1,4}\b',
            "severity": "low",
            "description": "检测到IPv6地址"
        },
        "地址信息": {
            "pattern": r'(?:省|市|区|县|镇|街道|路|号|楼|室|栋).{2,50}(?:号|室|楼)',
            "severity": "medium",
            "description": "检测到详细地址信息"
        },
        "车牌号": {
            "pattern": r'[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-Z][A-HJ-NP-Z0-9]{4,5}[A-HJ-NP-Z0-9挂学警港澳]',
            "severity": "medium",
            "description": "检测到车牌号"
        },
        "护照号": {
            "pattern": r'\b[EGP]\d{8}\b',
            "severity": "high",
            "description": "检测到护照号"
        },
        "组织机构代码": {
            "pattern": r'\b[A-Z0-9]{8}-[A-Z0-9]\b',
            "severity": "low",
            "description": "检测到组织机构代码"
        },
        "统一社会信用代码": {
            "pattern": r'\b[0-9A-HJ-NPQRTUWXY]{2}\d{6}[0-9A-HJ-NPQRTUWXY]{10}\b',
            "severity": "low",
            "description": "检测到统一社会信用代码"
        },
        "MAC地址": {
            "pattern": r'\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b',
            "severity": "low",
            "description": "检测到MAC地址"
        }
    }

    # 变形规避检测模式
    EVASION_PATTERNS = {
        "特殊符号分隔": {
            # 严格模式：仅检测汉字+特殊符号+汉字的组合（真正的规避模式）
            # 排除：文件扩展名、正常的标点符号组合
            "pattern": r'(?<![a-zA-Z\u4e00-\u9fa5])[\u4e00-\u9fa5]\s*[_\*\+\#\$\%\&\@\!]\s*[\u4e00-\u9fa5](?![a-zA-Z])',
            "severity": "low",
            "description": "检测到使用特殊符号分隔的文字（可能的规避手段）",
            "example": "色_情、赌*博、黄.色",
            # 白名单：排除正常的组合（现在正则已经很严格，可能不需要白名单了）
            "whitelist": []
        },
        "谐音替换": {
            "patterns": [
                (r'[色射涩瑟][\s\-_\*\.]*[情亲青清]', "色情", "medium"),
                (r'[毒独读督][\s\-_\*\.]*[品贫拼]', "毒品", "high"),
                (r'[赌睹堵][\s\-_\*\.]*[博勃搏薄]', "赌博", "high"),
                (r'[黄皇蝗][\s\-_\*\.]*[色涩射瑟]', "黄色", "medium"),
            ],
            "description": "检测到谐音字替换（可能的规避手段）"
        },
        "拆字组合": {
            "pattern": r'(?:[\u4e00-\u9fa5][\s\-_\*\.]+){2,}',
            "severity": "low",
            "description": "检测到拆字组合（可能的规避手段）",
            "example": "色 情、毒 品"
        },
        "全角半角混用": {
            "pattern": r'[！？。，；：""''（）【】《》　]',
            "severity": "low",
            "description": "检测到全角符号（可能的规避手段）"
        },
        "数字字母替换": {
            "patterns": [
                (r'[sS][eE][xX]', "性", "medium"),
                (r'[fF][uU][cC][kK]', "脏话", "medium"),
                (r'[pP][oO][rR][nN]', "色情", "high"),
            ],
            "description": "检测到字母拼音表示（可能的规避手段）"
        }
    }

    def __init__(self, enable_privacy_check: bool = True, enable_evasion_check: bool = True):
        """
        初始化增强正则检测器

        Args:
            enable_privacy_check: 是否启用隐私信息检测
            enable_evasion_check: 是否启用变形规避检测
        """
        self.enable_privacy_check = enable_privacy_check
        self.enable_evasion_check = enable_evasion_check

    def check(self, text: str) -> List[Dict]:
        """
        检测文本中的隐私信息和变形规避

        Args:
            text: 待检测文本

        Returns:
            违规列表
        """
        violations = []

        # 1. 隐私信息检测
        if self.enable_privacy_check:
            privacy_violations = self._check_privacy(text)
            violations.extend(privacy_violations)

        # 2. 变形规避检测
        if self.enable_evasion_check:
            evasion_violations = self._check_evasion(text)
            violations.extend(evasion_violations)

        return violations

    def _check_privacy(self, text: str) -> List[Dict]:
        """检测隐私信息"""
        violations = []

        for pattern_name, pattern_info in self.PRIVACY_PATTERNS.items():
            pattern = pattern_info["pattern"]
            matches = re.finditer(pattern, text)

            for match in matches:
                # 特殊处理：避免将正常数字误判为银行卡号
                if pattern_name == "银行卡号":
                    matched_text = match.group()
                    # 检查是否为合法的银行卡号（Luhn算法简单验证）
                    if not self._is_valid_bank_card(matched_text):
                        continue

                violations.append({
                    "category": "隐私信息",
                    "matched_pattern": pattern_name,
                    "matched_text": self._mask_sensitive(match.group(), pattern_name),
                    "severity": pattern_info["severity"],
                    "method": "regex_match",
                    "description": pattern_info["description"]
                })

        return violations

    def _check_evasion(self, text: str) -> List[Dict]:
        """检测变形规避"""
        violations = []

        # 检测特殊符号分隔
        if "特殊符号分隔" in self.EVASION_PATTERNS:
            pattern_info = self.EVASION_PATTERNS["特殊符号分隔"]
            matches = re.finditer(pattern_info["pattern"], text)
            whitelist = pattern_info.get("whitelist", [])

            for match in matches:
                matched_text = match.group()

                # 检查是否在白名单中
                is_whitelisted = False
                for whitelist_pattern in whitelist:
                    if re.search(whitelist_pattern, matched_text, re.IGNORECASE):
                        is_whitelisted = True
                        break

                # 如果在白名单中，跳过
                if is_whitelisted:
                    continue

                violations.append({
                    "category": "变形规避",
                    "matched_pattern": "特殊符号分隔",
                    "matched_text": matched_text,
                    "severity": pattern_info["severity"],
                    "method": "regex_match",
                    "description": pattern_info["description"]
                })

        # 检测谐音替换
        if "谐音替换" in self.EVASION_PATTERNS:
            pattern_list = self.EVASION_PATTERNS["谐音替换"]["patterns"]
            for pattern, word_type, severity in pattern_list:
                matches = re.finditer(pattern, text)
                for match in matches:
                    violations.append({
                        "category": "变形规避",
                        "matched_pattern": f"谐音替换({word_type})",
                        "matched_text": match.group(),
                        "severity": severity,
                        "method": "regex_match",
                        "description": f"检测到\"{word_type}\"的谐音字表达"
                    })

        # 检测拆字组合
        if "拆字组合" in self.EVASION_PATTERNS:
            pattern_info = self.EVASION_PATTERNS["拆字组合"]
            matches = re.finditer(pattern_info["pattern"], text)
            for match in matches:
                # 过滤正常的词语（如"中 国"不应被检测）
                matched_text = match.group()
                if len(matched_text) > 10:  # 太长的可能是正常表达
                    continue

                violations.append({
                    "category": "变形规避",
                    "matched_pattern": "拆字组合",
                    "matched_text": matched_text,
                    "severity": pattern_info["severity"],
                    "method": "regex_match",
                    "description": pattern_info["description"]
                })

        # 检测数字字母替换
        if "数字字母替换" in self.EVASION_PATTERNS:
            pattern_list = self.EVASION_PATTERNS["数字字母替换"]["patterns"]
            for pattern, word_type, severity in pattern_list:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    violations.append({
                        "category": "变形规避",
                        "matched_pattern": f"字母拼音({word_type})",
                        "matched_text": match.group(),
                        "severity": severity,
                        "method": "regex_match",
                        "description": f"检测到\"{word_type}\"的字母表达"
                    })

        return violations

    def _mask_sensitive(self, text: str, pattern_type: str) -> str:
        """脱敏处理敏感信息"""
        if len(text) <= 4:
            return text

        # 根据类型进行不同的脱敏处理
        if pattern_type in ["手机号", "固定电话"]:
            return text[:3] + "****" + text[-4:]
        elif pattern_type == "身份证号":
            return text[:6] + "********" + text[-4:]
        elif pattern_type == "银行卡号":
            return text[:4] + "********" + text[-4:]
        elif pattern_type == "电子邮箱":
            parts = text.split('@')
            if len(parts) == 2:
                return parts[0][:2] + "***@" + parts[1]
        elif pattern_type == "车牌号":
            return text[:2] + "***" + text[-2:]

        # 默认脱敏：保留前后各2个字符
        return text[:2] + "***" + text[-2:]

    def _is_valid_bank_card(self, card_number: str) -> bool:
        """
        使用Luhn算法验证银行卡号

        Args:
            card_number: 银行卡号

        Returns:
            是否为有效银行卡号
        """
        if not card_number.isdigit():
            return False

        # Luhn算法
        digits = [int(d) for d in card_number]
        checksum = 0

        # 从右到左，奇数位不变，偶数位乘2
        for i in range(len(digits) - 1, -1, -1):
            n = digits[i]
            if (len(digits) - i) % 2 == 0:
                n *= 2
                if n > 9:
                    n -= 9
            checksum += n

        return checksum % 10 == 0

    def get_stats(self, violations: List[Dict]) -> Dict:
        """
        统计违规信息

        Args:
            violations: 违规列表

        Returns:
            统计信息
        """
        stats = {
            "total": len(violations),
            "by_category": {},
            "by_severity": {},
            "privacy_count": 0,
            "evasion_count": 0
        }

        for violation in violations:
            category = violation["category"]
            severity = violation["severity"]

            # 按类别统计
            stats["by_category"][category] = stats["by_category"].get(category, 0) + 1

            # 按严重性统计
            stats["by_severity"][severity] = stats["by_severity"].get(severity, 0) + 1

            # 按检测类型统计
            if category == "隐私信息":
                stats["privacy_count"] += 1
            elif category == "变形规避":
                stats["evasion_count"] += 1

        return stats
