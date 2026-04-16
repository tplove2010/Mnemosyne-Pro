#!/usr/bin/env python3
"""
Embedding Client - 统一嵌入工具层
从 OpenClaw 配置读取 embedding provider/model，支持 BGE-M3
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Optional

import requests

# 读取 OpenClaw 配置
OPENCLAW_DIR = Path(__file__).resolve().parents[1].parent
CONFIG_FILE = OPENCLAW_DIR / 'openclaw.json'

# 默认配置
DEFAULT_MODEL = 'BAAI/bge-m3'
DEFAULT_PROVIDER = 'siliconflow'
DEFAULT_BASE_URL = 'https://api.siliconflow.cn/v1'


def load_openclaw_config() -> dict:
    """读取 OpenClaw 配置"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def get_embedding_config() -> dict:
    """获取 embedding 配置"""
    config = load_openclaw_config()
    
    # 从 agents.defaults.memorySearch 读取
    ms_config = config.get('agents', {}).get('defaults', {}).get('memorySearch', {})
    
    return {
        'model': ms_config.get('model', DEFAULT_MODEL),
        'base_url': ms_config.get('remote', {}).get('baseUrl', DEFAULT_BASE_URL),
        'api_key': ms_config.get('remote', {}).get('apiKey', ''),
        'provider': ms_config.get('provider', DEFAULT_PROVIDER),
    }


def compute_text_hash(text: str) -> str:
    """计算文本 hash"""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]


def get_embedding(text: str, cache_dir: Optional[Path] = None) -> list[float]:
    """
    获取文本嵌入向量
    支持缓存
    """
    text_hash = compute_text_hash(text)
    
    # 尝试从缓存读取
    if cache_dir:
        cache_file = cache_dir / f"{text_hash}.json"
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached = json.load(f)
                return cached['embedding']
    
    # 调用 API
    cfg = get_embedding_config()
    
    payload = {
        'model': cfg['model'],
        'input': text
    }
    
    headers = {
        'Authorization': f"Bearer {cfg['api_key']}",
        'Content-Type': 'application/json'
    }
    
    response = requests.post(
        f"{cfg['base_url']}/embeddings",
        headers=headers,
        json=payload,
        timeout=30
    )
    
    if response.status_code != 200:
        raise RuntimeError(f"Embedding API error: {response.text}")
    
    result = response.json()
    embedding = result['data'][0]['embedding']
    
    # 存入缓存
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / f"{text_hash}.json"
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump({
                'text_hash': text_hash,
                'embedding': embedding,
                'model': cfg['model']
            }, f, ensure_ascii=False)
    
    return embedding


def get_embeddings_batch(texts: list[str], cache_dir: Optional[Path] = None) -> list[list[float]]:
    """
    批量获取嵌入向量
    """
    return [get_embedding(t, cache_dir) for t in texts]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """计算余弦相似度"""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return dot / (norm_a * norm_b)


def find_similar(text: str, corpus: dict[str, str], cache_dir: Optional[Path] = None, top_k: int = 5, min_similarity: float = 0.5) -> list[dict]:
    """
    查找与文本最相似的 corpus 项
    
    Args:
        text: 查询文本
        corpus: {id: text} 字典
        cache_dir: 缓存目录
        top_k: 返回 top k 结果
        min_similarity: 最小相似度阈值
        
    Returns:
        [{
            'id': str,
            'text': str,
            'similarity_score': float,
            'hint_only': True  # 始终是 hint，不替代主规则
        }]
    """
    query_embedding = get_embedding(text, cache_dir)
    
    results = []
    for item_id, item_text in corpus.items():
        item_embedding = get_embedding(item_text, cache_dir)
        similarity = cosine_similarity(query_embedding, item_embedding)
        
        if similarity >= min_similarity:
            results.append({
                'id': item_id,
                'text': item_text,
                'similarity_score': round(similarity, 4),
                'matched_target': item_id,
                'reason': f'semantic similarity: {similarity:.2%}',
                'hint_only': True  # 标记为辅助信号
            })
    
    # 按相似度排序
    results.sort(key=lambda x: x['similarity_score'], reverse=True)
    
    return results[:top_k]


if __name__ == '__main__':
    # 测试
    cfg = get_embedding_config()
    print(f"Embedding config: {cfg['model']} @ {cfg['base_url']}")
    
    # 简单测试
    emb1 = get_embedding("用户喜欢结论先行")
    emb2 = get_embedding("prefers conclusion first")
    
    sim = cosine_similarity(emb1, emb2)
    print(f"Similarity: {sim:.4f}")