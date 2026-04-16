#!/usr/bin/env python3
"""
Semantic Utilities - 语义工具层
提供 pattern 聚类、事件归并、Recall 构建等辅助函数
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from embedding_client import (
    compute_text_hash,
    cosine_similarity,
    find_similar,
    get_embedding,
    get_embeddings_batch,
)

# Pattern 类型优先级 (从高到低)
PATTERN_PRIORITY = {
    'style_preference': 0,
    'failure_avoidance': 1,
    'workflow_rule': 2,
    'task_tactic': 3,
    'recall_hint': 4,
}


def load_patterns(patterns_dir: Path) -> dict[str, dict]:
    """
    加载已批准的 patterns
    返回: {pattern_id: {type, text, ...}}
    """
    patterns = {}
    
    if not patterns_dir.exists():
        return patterns
    
    for f in patterns_dir.glob('*.md'):
        # 从文件名解析 pattern_id (简化处理)
        pattern_id = f.stem
        
        content = f.read_text(encoding='utf-8')
        
        # 提取 pattern type
        pattern_type = 'recall_hint'
        if 'style_preference' in content:
            pattern_type = 'style_preference'
        elif 'failure_avoidance' in content:
            pattern_type = 'failure_avoidance'
        elif 'workflow_rule' in content:
            pattern_type = 'workflow_rule'
        elif 'task_tactic' in content:
            pattern_type = 'task_tactic'
        
        patterns[pattern_id] = {
            'type': pattern_type,
            'text': content,
            'path': str(f)
        }
    
    return patterns


def calculate_pattern_similarity(text1: str, text2: str, cache_dir: Optional[Path] = None) -> float:
    """计算两个 pattern 文本的相似度"""
    emb1 = get_embedding(text1, cache_dir)
    emb2 = get_embedding(text2, cache_dir)
    return cosine_similarity(emb1, emb2)


def merge_similar_patterns(
    new_patterns: list[dict],
    existing_patterns: dict[str, dict],
    cache_dir: Optional[Path] = None,
    min_similarity: float = 0.8
) -> list[dict]:
    """
    合并相似 pattern
    
    Args:
        new_patterns: 新生成的 pattern 候选列表
        existing_patterns: 已批准的 patterns
        cache_dir: 嵌入缓存目录
        min_similarity: 最小相似度阈值
        
    Returns:
        合并后的 pattern 列表，附带 merge hint
    """
    merged = []
    processed = set()
    
    # === 第一步：新 candidate 与已批准 pattern 比较 ===
    for new_p in new_patterns:
        # 跳过没有 id 的条目（如类型建议）
        if 'id' not in new_p:
            merged.append(new_p)
            continue
        
        if new_p['id'] in processed:
            continue
        
        # 安全获取 statement(text) - candidate 使用 'statement'
        new_text = new_p.get('statement', new_p.get('text', ''))
        if not new_text:
            merged.append(new_p)
            continue
            
        similar_to_existing = []
        
        # 与已批准 pattern 比较
        for exist_id, exist_p in existing_patterns.items():
            exist_text = exist_p.get('text', exist_p.get('statement', ''))
            sim = calculate_pattern_similarity(
                new_text,
                exist_text,
                cache_dir
            )
            
            if sim >= min_similarity:
                similar_to_existing.append({
                    'id': exist_id,
                    'similarity': sim,
                    'type': exist_p.get('type', 'unknown')
                })
        
        if similar_to_existing:
            # 标记为与已有 pattern 相似，不自动合并
            new_p['semantic_merge_hint'] = {
                'similar_to': similar_to_existing,
                'action': 'review_required',
                'reason': f'similarity >= {min_similarity}'
            }
        
        merged.append(new_p)
    
    # === 第二步：新 candidate 之间聚类 ===
    # 注意：这里不检查 processed，因为我们要比较所有 candidate 对
    cluster_hints = []
    for i, p1 in enumerate(merged):
        if 'id' not in p1:
            continue
            
        p1_text = p1.get('statement', p1.get('text', ''))
        if not p1_text:
            continue
            
        similar_candidates = []
        for j, p2 in enumerate(merged):
            if i >= j:
                continue
            if 'id' not in p2:
                continue
                
            p2_text = p2.get('statement', p2.get('text', ''))
            if not p2_text:
                continue
            
            # 检查 outcome 是否相同（同为 success 或 failure）
            outcome1 = p1.get('outcome', '')
            outcome2 = p2.get('outcome', '')
            if outcome1 and outcome2 and outcome1 != outcome2:
                continue  # 不同 outcome 不聚类
            
            sim = calculate_pattern_similarity(p1_text, p2_text, cache_dir)
            if sim >= min_similarity:
                similar_candidates.append({
                    'id': p2['id'],
                    'topic': p2.get('topic', ''),
                    'similarity': sim,
                    'outcome': p2.get('outcome', '')
                })
        
        if similar_candidates:
            cluster_hints.append({
                'primary_id': p1['id'],
                'topic': p1.get('topic', ''),
                'similar_candidates': similar_candidates,
                'cluster_type': 'candidate_cluster',
                'action': 'consider_merge'
            })
    
    # 将聚类 hint 附加到第一个相关 candidate
    for hint in cluster_hints:
        for p in merged:
            if p.get('id') == hint['primary_id']:
                p['semantic_cluster_hint'] = hint
                break
    
    return merged


def rank_recall_results(
    results: list[dict],
    pattern_priority: dict[str, int] = None,
    explicit_weight: float = 0.3,
    similarity_weight: float = 0.7
) -> list[dict]:
    """
    Recall 结果排序
    综合: 显式标签权重 + 语义相似度权重 + Pattern 类型优先级
    
    Args:
        results: [{"type": "style_preference", "similarity_score": 0.9, ...}, ...]
        pattern_priority: pattern 类型优先级
        explicit_weight: 显式/关键词匹配权重
        similarity_weight: 语义相似度权重
        
    Returns:
        排序后的结果
    """
    if pattern_priority is None:
        pattern_priority = PATTERN_PRIORITY
    
    scored = []
    
    for r in results:
        ptype = r.get('type', 'recall_hint')
        priority_score = pattern_priority.get(ptype, 99)
        
        # 显式标记加分
        explicit_bonus = 0.2 if r.get('explicitness') == 'explicit' else 0.0
        
        # 综合分数 = 相似度 * 权重 + 优先级(反转) + 显式加分
        final_score = (
            r.get('similarity_score', 0) * similarity_weight +
            (1.0 / (priority_score + 1)) * explicit_weight +
            explicit_bonus
        )
        
        scored.append({
            **r,
            'final_score': round(final_score, 4)
        })
    
    # 按最终分数排序
    scored.sort(key=lambda x: x['final_score'], reverse=True)
    
    return scored


def build_semantic_hints(
    new_text: str,
    existing_texts: dict[str, str],
    cache_dir: Optional[Path] = None,
    top_k: int = 3,
    min_similarity: float = 0.6
) -> list[dict]:
    """
    为新内容生成语义相似提示
    
    用于:
    - reconcile 阶段的 duplicate hint
    - review 阶段的 related memory hint
    """
    hints = find_similar(
        new_text,
        existing_texts,
        cache_dir=cache_dir,
        top_k=top_k,
        min_similarity=min_similarity
    )
    
    # 统一格式
    for h in hints:
        h['hint_type'] = 'semantic'
        h['hint_only'] = True  # 标记为辅助提示
    
    return hints


def classify_event_type(event_text: str, cache_dir: Optional[Path] = None) -> dict:
    """
    事件类型语义分类 (Evolve 用) - 基于 embedding
    返回: {predicted_type, confidence, reason, hint_only}
    """
    # 类型模板（用于 embedding 匹配）
    type_templates = {
        'style_preference': [
            "The user prefers to receive direct answers",
            "User likes concise explanations without fluff",
            "User wants recommendations not explanations",
            "用户喜欢直接给出答案而不是解释"
        ],
        'failure_avoidance': [
            "This failed because of a configuration error",
            "The old service was still running causing issues",
            "This workaround did not work as expected",
            "The process failed due to missing dependencies"
        ],
        'workflow_rule': [
            "Always check the logs before troubleshooting",
            "Use recall to find similar past issues first",
            "Verify config before each restart",
            "每次都要先验证配置再重启服务"
        ],
        'task_tactic': [
            "For this specific task I used debugging logs",
            "This particular job required manual intervention",
            "A different approach was needed for this assignment"
        ],
        'recall_hint': [
            "Remember to check the config file",
            "Note that the API may have rate limits",
            "Keep in mind the gateway needs restart after changes"
        ]
    }
    
    if not cache_dir:
        cache_dir = Path('.mnemosyne-evolve/cache/embeddings')
    
    # 优先 keyword 快速匹配 (更精确的模式)
    keyword_patterns = {
        'style_preference': ['prefers', 'prefers ', 'likes ', 'likes to', 'wants to', 'wants ', '用户喜欢', '希望', 'dislikes', 'fluffy', 'direct answer', 'concise'],
        'failure_avoidance': ['failed to', 'failed because', 'error: ', 'wrong result', 'issue: ', 'problem: ', 'did not work', 'went wrong', 'not working'],
        'workflow_rule': ['always ', 'every time', 'workflow: ', 'before you', 'before starting', 'always check'],
        'task_tactic': ['this task required', 'for this task', 'particular job', 'specific task'],
    }
    
    text_lower = event_text.lower()
    for ptype, keywords in keyword_patterns.items():
        for kw in keywords:
            if kw in text_lower:
                return {
                    'predicted_type': ptype,
                    'confidence': 0.85,
                    'reason': f'keyword match: {kw}',
                    'hint_only': True,
                    'method': 'keyword'
                }
    
    # Keyword 未匹配时，用 embedding
    query_emb = get_embedding(event_text, cache_dir)
    
    best_match = None
    best_score = 0.0
    
    for ptype, templates in type_templates.items():
        for template in templates:
            template_emb = get_embedding(template, cache_dir)
            score = cosine_similarity(query_emb, template_emb)
            
            if score > best_score:
                best_score = score
                best_match = {
                    'type': ptype,
                    'score': score,
                    'template': template
                }
    
    # 阈值判断
    if best_score >= 0.5:
        return {
            'predicted_type': best_match['type'],
            'confidence': round(best_match['score'], 2),
            'reason': f'semantic match with score {best_match["score"]:.2%}',
            'hint_only': True,
            'method': 'embedding',
            'template': best_match['template'][:50]
        }
    
    # 未匹配到，返回默认
    return {
        'predicted_type': 'recall_hint',
        'confidence': 0.3,
        'reason': 'no confident match, defaulting to recall_hint',
        'hint_only': True,
        'method': 'fallback'
    }


if __name__ == '__main__':
    # 测试相似度计算
    sim = calculate_pattern_similarity(
        "用户喜欢结论先行",
        "prefers conclusion first"
    )
    print(f"Pattern similarity test: {sim:.4f}")