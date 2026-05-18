#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arkanalyzer LLM大语言模型连接器模块
提供与硅基流动API的集成，支持多种大语言模型调用
"""

import json
import time
import hashlib
import requests
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
import re


@dataclass
class LLMResponse:
    """LLM响应数据结构"""
    content: str
    model: str
    tokens_used: int
    finish_reason: str
    timestamp: datetime
    raw_response: Dict[str, Any]


class LLMCache:
    """LLM响应缓存"""

    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self.cache: Dict[str, Any] = {}
        self.timestamps: Dict[str, datetime] = {}
        self.max_size = max_size
        self.ttl = ttl

    def _generate_key(self, prompt: str, model: str, **kwargs) -> str:
        """生成缓存键"""
        content = f"{prompt}:{model}:{json.dumps(kwargs, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()

    def get(self, prompt: str, model: str, **kwargs) -> Optional[Any]:
        """获取缓存"""
        key = self._generate_key(prompt, model, **kwargs)
        if key in self.cache:
            if (datetime.now() - self.timestamps[key]).seconds < self.ttl:
                return self.cache[key]
            else:
                del self.cache[key]
                del self.timestamps[key]
        return None

    def set(self, prompt: str, model: str, value: Any, **kwargs):
        """设置缓存"""
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.timestamps.keys(), key=lambda k: self.timestamps[k])
            del self.cache[oldest_key]
            del self.timestamps[oldest_key]

        key = self._generate_key(prompt, model, **kwargs)
        self.cache[key] = value
        self.timestamps[key] = datetime.now()

    def clear(self):
        """清空缓存"""
        self.cache.clear()
        self.timestamps.clear()


class LLMConnector:
    """大语言模型连接器"""

    def __init__(self, api_key: str, base_url: str = "https://api.siliconflow.cn/v1",
                 model: str = "Qwen/Qwen2.5-7B-Instruct",
                 temperature: float = 0.7,
                 max_tokens: int = 2048,
                 timeout: int = 60,
                 retry_times: int = 3,
                 cache_enabled: bool = True):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.retry_times = retry_times
        self.cache_enabled = cache_enabled
        self.cache = LLMCache() if cache_enabled else None
        self.request_count = 0
        self.total_tokens = 0

    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def _build_payload(self, prompt: str, system_prompt: Optional[str] = None,
                       **kwargs) -> Dict[str, Any]:
        """构建请求载荷"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get('temperature', self.temperature),
            "max_tokens": kwargs.get('max_tokens', self.max_tokens)
        }

        if kwargs.get('stream'):
            payload['stream'] = True

        return payload

    def _make_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """发送HTTP请求"""
        url = f"{self.base_url}/chat/completions"
        headers = self._build_headers()

        for attempt in range(self.retry_times):
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response.json()
            except requests.exceptions.Timeout:
                if attempt < self.retry_times - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise TimeoutError(f"请求超时，已重试{self.retry_times}次")
            except requests.exceptions.RequestException as e:
                if attempt < self.retry_times - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise ConnectionError(f"请求失败: {str(e)}")

    def chat(self, prompt: str, system_prompt: Optional[str] = None,
             **kwargs) -> LLMResponse:
        """发送对话请求"""
        if self.cache_enabled and not kwargs.get('stream'):
            cached_result = self.cache.get(prompt, self.model, **kwargs)
            if cached_result:
                return cached_result

        payload = self._build_payload(prompt, system_prompt, **kwargs)
        result = self._make_request(payload)

        response = LLMResponse(
            content=result['choices'][0]['message']['content'],
            model=result.get('model', self.model),
            tokens_used=result.get('usage', {}).get('total_tokens', 0),
            finish_reason=result['choices'][0].get('finish_reason', 'stop'),
            timestamp=datetime.now(),
            raw_response=result
        )

        self.request_count += 1
        self.total_tokens += response.tokens_used

        if self.cache_enabled:
            self.cache.set(prompt, self.model, response, **kwargs)

        return response

    def extract_entities_and_relations(self, text: str, entity_types: Optional[List[str]] = None,
                                       relation_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """使用LLM抽取实体和关系"""
        entity_types_str = entity_types or ["人物", "地点", "组织", "事件", "概念"]
        relation_types_str = relation_types or ["属于", "位于", "相关", "导致", "组成"]

        system_prompt = """你是一个专业的知识图谱抽取助手。
请从给定的文本中抽取实体和关系，并以JSON格式返回。
要求：
1. 实体需要包含名称、类型和属性
2. 关系需要包含源实体、目标实体和关系类型
3. 只返回JSON格式，不要包含其他文字"""

        prompt = f"""请从以下文本中抽取知识图谱：

{text}

实体类型：{', '.join(entity_types_str)}
关系类型：{', '.join(relation_types_str)}

请以以下JSON格式返回：
{{
  "entities": [
    {{"name": "实体名称", "type": "实体类型", "properties": {{}}}}
  ],
  "relations": [
    {{"source": "源实体", "target": "目标实体", "type": "关系类型"}}
  ]
}}"""

        try:
            response = self.chat(prompt, system_prompt)
            return self._parse_extraction_result(response.content)
        except Exception as e:
            return {"entities": [], "relations": [], "error": str(e)}

    def _parse_extraction_result(self, content: str) -> Dict[str, Any]:
        """解析抽取结果"""
        try:
            content = content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.startswith('```'):
                content = content[3:]
            if content.endswith('```'):
                content = content[:-3]

            content = content.strip()
            return json.loads(content)
        except json.JSONDecodeError as e:
            try:
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    return json.loads(json_match.group())
            except:
                pass
            return {"entities": [], "relations": [], "error": f"JSON解析失败: {str(e)}", "raw_content": content}

    def summarize(self, text: str, max_length: int = 200) -> str:
        """文本摘要"""
        system_prompt = "你是一个专业的文本摘要助手，请用简洁的语言总结文本要点。"
        prompt = f"请用不超过{max_length}个字总结以下文本：\n\n{text}"
        response = self.chat(prompt, system_prompt)
        return response.content

    def classify(self, text: str, categories: List[str]) -> Dict[str, float]:
        """文本分类"""
        system_prompt = "你是一个专业的文本分类助手，请对文本进行分类并给出置信度。"
        prompt = f"请判断以下文本属于哪个类别：\n\n{text}\n\n可选类别：{', '.join(categories)}\n\n请以JSON格式返回：{{\"category\": \"类别\", \"confidence\": 0.95}}"
        response = self.chat(prompt, system_prompt)

        try:
            result = json.loads(response.content)
            return result
        except:
            return {"category": "unknown", "confidence": 0.0}

    def answer_question(self, question: str, context: Optional[str] = None) -> str:
        """问答系统"""
        if context:
            system_prompt = "你是一个专业的问答助手，请根据提供的上下文回答问题。"
            prompt = f"上下文：\n{context}\n\n问题：{question}"
        else:
            system_prompt = "你是一个专业的问答助手，请回答用户的问题。"
            prompt = question

        response = self.chat(prompt, system_prompt)
        return response.content

    def generate_code(self, description: str, language: str = "python") -> str:
        """代码生成"""
        system_prompt = f"你是一个专业的{language}程序员，请根据描述生成高质量的代码。"
        prompt = f"请生成{language}代码实现以下功能：\n\n{description}"
        response = self.chat(prompt, system_prompt)
        return response.content

    def translate(self, text: str, target_language: str = "中文") -> str:
        """翻译功能"""
        system_prompt = "你是一个专业的翻译助手，请保持原文风格进行翻译。"
        prompt = f"请将以下内容翻译成{target_language}：\n\n{text}"
        response = self.chat(prompt, system_prompt)
        return response.content

    def get_statistics(self) -> Dict[str, Any]:
        """获取使用统计"""
        return {
            "request_count": self.request_count,
            "total_tokens": self.total_tokens,
            "cache_enabled": self.cache_enabled,
            "cache_size": len(self.cache.cache) if self.cache else 0,
            "model": self.model
        }

    def reset_statistics(self):
        """重置统计"""
        self.request_count = 0
        self.total_tokens = 0

    def clear_cache(self):
        """清空缓存"""
        if self.cache:
            self.cache.clear()

    def set_model(self, model: str):
        """设置模型"""
        self.model = model
        if self.cache:
            self.cache.clear()

    def set_temperature(self, temperature: float):
        """设置温度参数"""
        self.temperature = max(0.0, min(2.0, temperature))

    def set_max_tokens(self, max_tokens: int):
        """设置最大令牌数"""
        self.max_tokens = max_tokens


def create_llm_connector(config: Optional[Dict[str, Any]] = None) -> LLMConnector:
    """创建LLM连接器工厂函数"""
    if config is None:
        from .config_loader import get_config
        config_obj = get_config()
        llm_config = config_obj.get_llm_config()
        config = {
            'api_key': llm_config.api_key,
            'base_url': llm_config.base_url,
            'model': llm_config.model,
            'temperature': llm_config.temperature,
            'max_tokens': llm_config.max_tokens,
            'timeout': llm_config.timeout,
            'retry_times': llm_config.retry_times
        }

    return LLMConnector(**config)
