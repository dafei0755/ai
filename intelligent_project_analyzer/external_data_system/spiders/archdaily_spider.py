"""Compatibility shim for legacy crawler monitor imports."""

from .archdaily_cn_spider import ArchdailyCNSpider as ArchdailySpider

__all__ = ["ArchdailySpider"]
