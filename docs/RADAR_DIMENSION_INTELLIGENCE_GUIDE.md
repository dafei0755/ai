# Radar Dimension Intelligence Guide

## 📋 Overview

**Version**: v7.147
**Date**: 2026-01-07
**Status**: Production Ready

This guide explains the intelligent dimension selection system for radar charts in the progressive questionnaire flow.

## 🎯 Problem Statement

Previously, radar chart dimensions appeared "hardcoded" because all intelligent features were **disabled by default**. The system fell back to static YAML-based dimension selection, which:
- ❌ Doesn't learn from user behavior
- ❌ Doesn't adapt to unique projects
- ❌ Uses the same dimensions for all users
- ❌ Can't detect special scenarios

## ✨ Solution: 3-Level Intelligence System

The system now has **3 levels of intelligence** that can be enabled via environment variables:

### Level 1: Intelligent Learning (Recommended) ⭐
**Environment Variable**: `ENABLE_DIMENSION_LEARNING=true`

**What it does**:
- Uses `AdaptiveDimensionGenerator` with historical data learning
- Loads past dimension usage from Redis
- Detects special scenes (extreme environment, medical needs, cultural depth, etc.)
- Learns user preference patterns over time
- Optimizes dimension selection continuously

**Performance**: Minimal impact (10s timeout on background data load)
**Cost**: No additional LLM calls
**Requires**: Redis running (auto-fallback to RuleEngine if unavailable)

### Level 2: Dynamic Generation (Advanced)
**Environment Variable**: `USE_DYNAMIC_GENERATION=true`

**What it does**:
- Uses `DynamicDimensionGenerator` with LLM analysis
- Analyzes user input in real-time
- Generates custom dimensions for unique projects
- Covers gaps in existing dimension library

**Performance**: High impact (+2-5s per questionnaire)
**Cost**: Additional LLM token usage
**Requires**: LLM API availability

### Level 3: LLM Recommender (Integrated)
**Environment Variable**: `ENABLE_LLM_DIMENSION_RECOMMENDER=true`

**What it does**:
- Deep requirement understanding via LLM
- Intelligent dimension recommendation
- Context-aware selection

**Performance**: Medium impact
**Cost**: LLM token usage
**Requires**: LLM API availability

---

## 🚀 Quick Start

### For Development

1. Copy `.env.development.example` to `.env.development`
2. Set `ENABLE_DIMENSION_LEARNING=true`
3. Ensure Redis is running: `redis-server`
4. Restart backend: `python scripts/run_server_production.py`

### For Production

1. Copy `.env.production.example` to `.env.production`
2. Set `ENABLE_DIMENSION_LEARNING=true`
3. Verify Redis is accessible
4. Deploy and monitor

---

## 📊 Configuration Matrix

| Environment | ENABLE_DIMENSION_LEARNING | USE_DYNAMIC_GENERATION | FORCE_GENERATE_DIMENSIONS |
|-------------|---------------------------|------------------------|---------------------------|
| **Development** | `true` (recommended) | `false` | `false` |
| **Staging** | `true` | `false` | `false` |
| **Production** | `true` | `false` | `false` |
| **Testing/Demo** | `true` | `true` | `false` |

---

## 🔄 How It Works

### Current Flow (Learning Disabled)
```
User Input
  ↓
RuleEngine (dimension_selector.py)
  ↓
Load radar_dimensions.yaml
  ↓
Return HARDCODED dimensions
```

### New Flow (Learning Enabled)
```
User Input
  ↓
AdaptiveDimensionGenerator
  ↓
Load Historical Data (Redis, 10s timeout)
  ↓
Detect Special Scenes
  ↓
Apply Learning Weights
  ↓
Return INTELLIGENT dimensions
  ↓
(If Redis fails → Fallback to RuleEngine)
```

---

## 📈 Performance Comparison

| Feature | Selection Time | LLM Calls | Redis Calls | Intelligence Level |
|---------|----------------|-----------|-------------|-------------------|
| RuleEngine (default) | <100ms | 0 | 0 | Low (static) |
| Learning Enabled | <500ms | 0 | 1 (background) | High (adaptive) |
| Dynamic Generation | 2-5s | 1 | 0 | Very High (custom) |
| Hybrid (Learning + Dynamic) | 500ms-5s | 0-1 | 1 | Maximum |

---

## 🛡️ Fallback & Error Handling

The system has robust fallback mechanisms:

1. **Redis Unavailable**: Auto-fallback to RuleEngine
2. **Historical Data Corrupted**: Validate on load, use fallback
3. **Timeout (10s)**: Use RuleEngine dimensions
4. **Learning Produces Bad Dimensions**: Monitor user edit rate, add quality checks

**Result**: System NEVER fails, always returns valid dimensions.

---

## 📊 Success Metrics

Track these metrics to measure effectiveness:

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Dimension Intelligence | 80% sessions using learning | Log dimension selection method |
| User Edit Rate | <15% | % users who modify dimensions |
| Coverage Score | >75% | Average coverage from analyzer |
| Selection Time | <500ms | Time to select dimensions |
| User Satisfaction | >4.0/5.0 | Post-questionnaire survey |

---

## 🔧 Troubleshooting

### Issue: Dimensions still appear hardcoded

**Check**:
1. Verify `ENABLE_DIMENSION_LEARNING=true` in `.env` file
2. Check Redis is running: `redis-cli ping` (should return `PONG`)
3. Check logs for: `"📊 [维度选择] 使用 AdaptiveDimensionGenerator 混合策略"`
4. If you see `"使用传统 RuleEngine"`, learning is disabled

**Solution**: Set environment variable and restart server

### Issue: Slow dimension selection

**Check**:
1. Check if `USE_DYNAMIC_GENERATION=true` (adds 2-5s delay)
2. Check Redis connection latency
3. Check historical data load time in logs

**Solution**:
- Disable dynamic generation if not needed
- Optimize Redis connection
- Reduce historical data limit

### Issue: Redis connection errors

**Check**:
1. Redis server running: `redis-cli ping`
2. Redis host/port correct in `.env`
3. Network connectivity

**Solution**: System auto-falls back to RuleEngine, but fix Redis for learning to work

---

## 🎓 Best Practices

### Development
- ✅ Enable learning to test intelligent behavior
- ✅ Use local Redis for development
- ✅ Monitor logs for dimension selection method
- ✅ Test with various project types

### Staging
- ✅ Enable learning for 1-2 weeks
- ✅ Collect user feedback
- ✅ Monitor performance metrics
- ✅ Analyze dimension quality

### Production
- ✅ Enable learning after staging validation
- ✅ Keep dynamic generation disabled (unless needed)
- ✅ Monitor error rates and fallbacks
- ✅ Track user satisfaction

---

## 📚 Related Files

### Configuration
- `.env.development.example` - Development environment template
- `.env.production.example` - Production environment template

### Core Logic
- `intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py:354-465` - Dimension selection logic
- `intelligent_project_analyzer/services/adaptive_dimension_generator.py` - Learning-based generator
- `intelligent_project_analyzer/services/dynamic_dimension_generator.py` - LLM-based generator
- `intelligent_project_analyzer/services/dimension_selector.py` - RuleEngine fallback

### Data Files
- `intelligent_project_analyzer/config/prompts/radar_dimensions.yaml` - Static dimension library
- `intelligent_project_analyzer/config/prompts/task_dimension_mapping.yaml` - Task-to-dimension mappings
- `intelligent_project_analyzer/config/prompts/answer_to_dimension_rules.yaml` - Answer inference rules

---

## 🔍 Monitoring & Analytics

### Log Messages to Watch

**Learning Enabled**:
```
📊 [维度选择] 使用 AdaptiveDimensionGenerator 混合策略
📚 [历史数据] 成功加载 X 条记录
📊 [AdaptiveDimGen] 选择了 X 个智能维度
```

**Learning Disabled (Fallback)**:
```
📊 [维度选择] 使用传统 RuleEngine 规则引擎（ENABLE_DIMENSION_LEARNING=false）
📊 [RuleEngine] 选择了 X 个传统维度
```

**Redis Failure (Auto-Fallback)**:
```
⚠️ [历史数据] 加载失败: [error], 使用空列表继续
🛡️ [降级] 使用静态默认维度列表
```

### Metrics Dashboard (Optional)

Track in your monitoring system:
- `dimension_selection_method` (learning/ruleengine/dynamic)
- `dimension_selection_time_ms`
- `user_dimension_edit_rate`
- `coverage_score`
- `redis_connection_failures`

---

## 🚀 Deployment Checklist

### Pre-Deployment
- [ ] Redis is running and accessible
- [ ] Environment variables set correctly
- [ ] Tested in staging for 1-2 weeks
- [ ] Performance metrics look good
- [ ] User feedback is positive

### Deployment
- [ ] Update `.env.production` with `ENABLE_DIMENSION_LEARNING=true`
- [ ] Restart backend service
- [ ] Verify logs show learning is enabled
- [ ] Monitor error rates for 24 hours
- [ ] Check user satisfaction metrics

### Post-Deployment
- [ ] Historical data is accumulating in Redis
- [ ] Dimension selection is working correctly
- [ ] No performance degradation
- [ ] User edit rate is decreasing over time
- [ ] Document any issues and resolutions

---

## 📞 Support

For issues or questions:
1. Check this guide first
2. Review logs for error messages
3. Check Redis connectivity
4. Verify environment variables
5. Consult the implementation plan: [valiant-toasting-beaver.md](C:\Users\SF\.claude\plans\valiant-toasting-beaver.md)

---

**Last Updated**: 2026-01-07
**Version**: v7.147
**Status**: ✅ Production Ready
