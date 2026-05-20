#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
超大规模混乱场景测试脚本
测试目标：
- 10万+实体
- 百万级关系
- 100+并发线程
- 混合读写、大规模删除重建
- 内存压力测试
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import time
import random
import threading
import psutil
import gc
import tracemalloc
from datetime import datetime
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from arkanalyzer.core.knowledge_graph_core import (
    Entity, Relation, KnowledgeGraph, KnowledgeGraphManager,
    EntityType, RelationType
)
from arkanalyzer.core.knowledge_repository import KnowledgeRepository
from arkanalyzer.database.database_connection_manager import initialize_database


class ChaosMetrics:
    """混乱测试指标收集器"""
    
    def __init__(self):
        self.start_time = time.time()
        self.operations = {
            'reads': 0,
            'writes': 0,
            'deletes': 0,
            'searches': 0,
            'errors': 0,
            'locks': 0,
            'retries': 0
        }
        self.latencies = []
        self.memory_samples = []
        self.cpu_samples = []
        self._lock = threading.Lock()
        
    def record_operation(self, op_type: str, latency: float, error: bool = False, lock: bool = False):
        """记录操作"""
        with self._lock:
            if op_type in self.operations:
                self.operations[op_type] += 1
            if error:
                self.operations['errors'] += 1
            if lock:
                self.operations['locks'] += 1
            self.latencies.append(latency)
            
    def record_memory(self, memory_mb: float, cpu_percent: float):
        """记录资源使用"""
        with self._lock:
            self.memory_samples.append(memory_mb)
            self.cpu_samples.append(cpu_percent)
            
    def get_summary(self) -> Dict[str, Any]:
        """获取统计摘要"""
        with self._lock:
            elapsed = time.time() - self.start_time
            total_ops = sum(self.operations.values())
            
            return {
                'elapsed_time': elapsed,
                'total_operations': total_ops,
                'operations_per_second': total_ops / elapsed if elapsed > 0 else 0,
                'operation_counts': self.operations.copy(),
                'avg_latency_ms': sum(self.latencies) / len(self.latencies) * 1000 if self.latencies else 0,
                'max_latency_ms': max(self.latencies) * 1000 if self.latencies else 0,
                'min_latency_ms': min(self.latencies) * 1000 if self.latencies else 0,
                'p95_latency_ms': self._percentile(self.latencies, 0.95) * 1000 if self.latencies else 0,
                'p99_latency_ms': self._percentile(self.latencies, 0.99) * 1000 if self.latencies else 0,
                'avg_memory_mb': sum(self.memory_samples) / len(self.memory_samples) if self.memory_samples else 0,
                'max_memory_mb': max(self.memory_samples) if self.memory_samples else 0,
                'avg_cpu_percent': sum(self.cpu_samples) / len(self.cpu_samples) if self.cpu_samples else 0
            }
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """计算百分位数"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile)
        return sorted_data[min(index, len(sorted_data) - 1)]


class UltraScaleChaosTest:
    """超大规模混乱场景测试"""
    
    def __init__(self, scale: str = "large"):
        self.scale = scale
        self.metrics = ChaosMetrics()
        self.stop_event = threading.Event()
        self.errors = []
        
        # 根据规模设置参数
        self.config = {
            'tiny': {'entities': 1000, 'relations': 5000, 'threads': 10, 'graphs': 3},
            'small': {'entities': 10000, 'relations': 50000, 'threads': 30, 'graphs': 5},
            'medium': {'entities': 50000, 'relations': 250000, 'threads': 60, 'graphs': 10},
            'large': {'entities': 100000, 'relations': 500000, 'threads': 100, 'graphs': 20},
            'huge': {'entities': 200000, 'relations': 1000000, 'threads': 150, 'graphs': 30}
        }[scale]
        
        print(f"🚀 超大规模测试配置 ({scale} 规模):")
        print(f"  - 实体数量: {self.config['entities']:,}")
        print(f"  - 关系数量: {self.config['relations']:,}")
        print(f"  - 并发线程: {self.config['threads']}")
        print(f"  - 图谱数量: {self.config['graphs']}")
        
    def generate_entities(self, count: int, entity_type: str) -> List[Entity]:
        """生成大量实体"""
        entities = []
        for i in range(count):
            entity = Entity(
                entity_name=f"{entity_type}_{i:08d}",
                entity_type=entity_type,
                properties={
                    'index': i,
                    'timestamp': datetime.now().isoformat(),
                    'random_value': random.random(),
                    'data': 'x' * random.randint(10, 1000)  # 可变大小属性
                },
                description=f"测试实体 {entity_type} #{i}",
                confidence=random.uniform(0.7, 1.0)
            )
            entities.append(entity)
        return entities
    
    def generate_relations(self, entities: List[Entity], count: int) -> List[Relation]:
        """生成大量关系"""
        relations = []
        entity_ids = [e.entity_id for e in entities]
        
        for i in range(count):
            src_idx = random.randint(0, len(entity_ids) - 1)
            tgt_idx = random.randint(0, len(entity_ids) - 1)
            
            if src_idx != tgt_idx:
                relation = Relation(
                    source_entity_id=entity_ids[src_idx],
                    target_entity_id=entity_ids[tgt_idx],
                    relation_type=random.choice([
                        r.value for r in RelationType
                    ]),
                    weight=random.uniform(0.1, 1.0),
                    confidence=random.uniform(0.5, 1.0),
                    properties={
                        'index': i,
                        'strength': random.random(),
                        'metadata': 'y' * random.randint(10, 500)
                    },
                    description=f"测试关系 #{i}"
                )
                relations.append(relation)
        return relations
    
    def test_concurrent_reads(self, repo: KnowledgeRepository, graph: KnowledgeGraph, 
                            thread_id: int, duration: int):
        """并发读取测试"""
        end_time = time.time() + duration
        
        while not self.stop_event.is_set() and time.time() < end_time:
            start = time.time()
            try:
                # 随机读取操作
                if graph.entities:
                    random_entity = random.choice(graph.entities)
                    entity = repo.get_entity_by_id(random_entity.entity_id)
                    neighbors = repo.get_neighbors(random_entity.entity_id)
                    stats = repo.get_graph_statistics(graph.graph_id)
                    
                    latency = time.time() - start
                    self.metrics.record_operation('reads', latency)
            except Exception as e:
                self.errors.append(f"Thread-{thread_id} read error: {e}")
                self.metrics.record_operation('reads', time.time() - start, error=True)
    
    def test_concurrent_writes(self, repo: KnowledgeRepository, thread_id: int, 
                              duration: int, entities_per_write: int):
        """并发写入测试"""
        end_time = time.time() + duration
        write_count = 0
        
        while not self.stop_event.is_set() and time.time() < end_time:
            start = time.time()
            try:
                # 创建临时图谱进行写入
                temp_graph = KnowledgeGraph(
                    graph_name=f"temp_graph_{thread_id}_{write_count}",
                    description=f"临时测试图谱"
                )
                
                # 添加随机实体
                for i in range(entities_per_write):
                    entity = Entity(
                        entity_name=f"temp_entity_{thread_id}_{write_count}_{i}",
                        entity_type=random.choice([t.value for t in EntityType]),
                        properties={'thread': thread_id, 'write_num': write_count, 'index': i}
                    )
                    temp_graph.add_entity(entity)
                
                # 保存
                success = repo.save_graph(temp_graph)
                
                # 删除
                if success:
                    repo.delete_graph(temp_graph.graph_id)
                
                latency = time.time() - start
                self.metrics.record_operation('writes', latency)
                write_count += 1
                
            except Exception as e:
                error_str = str(e).lower()
                is_lock = 'locked' in error_str or 'busy' in error_str
                self.errors.append(f"Thread-{thread_id} write error: {e}")
                self.metrics.record_operation('writes', time.time() - start, error=True, lock=is_lock)
                if is_lock:
                    self.metrics.operations['retries'] += 1
    
    def test_concurrent_searches(self, repo: KnowledgeRepository, graph: KnowledgeGraph,
                                thread_id: int, duration: int):
        """并发搜索测试"""
        end_time = time.time() + duration
        
        while not self.stop_event.is_set() and time.time() < end_time:
            start = time.time()
            try:
                # 混合搜索操作
                keyword = f"人物_{random.randint(0, 10000)}"
                results = repo.search_entities(keyword)
                
                # 随机统计查询
                if graph.graph_id:
                    stats = repo.get_graph_statistics(graph.graph_id)
                
                latency = time.time() - start
                self.metrics.record_operation('searches', latency)
                
            except Exception as e:
                self.errors.append(f"Thread-{thread_id} search error: {e}")
                self.metrics.record_operation('searches', time.time() - start, error=True)
    
    def test_massive_delete_rebuild(self, repo: KnowledgeRepository, duration: int):
        """大规模删除重建测试"""
        end_time = time.time() + duration
        
        while not self.stop_event.is_set() and time.time() < end_time:
            start = time.time()
            try:
                # 创建临时图谱
                temp_graph = KnowledgeGraph(
                    graph_name=f"chaos_graph_{int(time.time())}",
                    description="混乱测试图谱"
                )
                
                # 添加实体
                entity_count = random.randint(100, 1000)
                entities = self.generate_entities(entity_count, "混乱测试实体")
                for entity in entities:
                    temp_graph.add_entity(entity)
                
                # 保存
                repo.save_graph(temp_graph)
                
                # 等待一小段时间
                time.sleep(random.uniform(0.1, 0.5))
                
                # 删除
                repo.delete_graph(temp_graph.graph_id)
                
                latency = time.time() - start
                self.metrics.record_operation('writes', latency)
                
            except Exception as e:
                error_str = str(e).lower()
                is_lock = 'locked' in error_str or 'busy' in error_str
                self.metrics.record_operation('writes', time.time() - start, error=True, lock=is_lock)
                if is_lock:
                    self.metrics.operations['retries'] += 1
    
    def test_resource_monitor(self, duration: int):
        """资源监控线程"""
        process = psutil.Process()
        interval = 1.0  # 每秒采样一次
        
        while not self.stop_event.is_set():
            try:
                memory_mb = process.memory_info().rss / 1024 / 1024
                cpu_percent = process.cpu_percent(interval=0.1)
                self.metrics.record_memory(memory_mb, cpu_percent)
                time.sleep(interval)
            except Exception as e:
                print(f"资源监控错误: {e}")
                break
    
    def run_full_chaos_test(self):
        """运行完整混乱场景测试"""
        print("\n" + "="*80)
        print("🔥 开始超大规模混乱场景测试")
        print("="*80)
        
        tracemalloc.start()
        
        # 初始化数据库
        print("\n📦 初始化数据库...")
        initialize_database()
        repo = KnowledgeRepository()
        
        # 创建主测试图谱
        print("\n📊 创建主测试图谱...")
        main_graph = KnowledgeGraph(
            graph_name=f"ultra_scale_chaos_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            description="超大规模混乱测试主图谱"
        )
        
        # 分批生成实体（避免内存溢出）
        batch_size = 10000
        total_entities = self.config['entities']
        entity_types = [t.value for t in EntityType]
        
        print(f"⚙️  生成 {total_entities:,} 个实体 (分批处理)...")
        all_entities = []
        
        for i in range(0, total_entities, batch_size):
            batch_count = min(batch_size, total_entities - i)
            batch_entities = self.generate_entities(batch_count, random.choice(entity_types))
            all_entities.extend(batch_entities)
            
            for entity in batch_entities:
                main_graph.add_entity(entity)
            
            print(f"  进度: {i + batch_count:,}/{total_entities:,} ({(i + batch_count) * 100 // total_entities}%)")
            
            # 定期保存并清理内存
            if (i + batch_count) % 50000 == 0:
                gc.collect()
        
        print(f"✅ 生成了 {len(all_entities):,} 个实体")
        
        # 生成关系
        total_relations = self.config['relations']
        print(f"⚙️  生成 {total_relations:,} 个关系...")
        
        batch_relations = 50000
        for i in range(0, total_relations, batch_relations):
            batch_count = min(batch_relations, total_relations - i)
            relations = self.generate_relations(all_entities, batch_count)
            
            for relation in relations:
                main_graph.add_relation(relation)
            
            if (i + batch_count) % 100000 == 0:
                print(f"  进度: {i + batch_count:,}/{total_relations:,}")
                gc.collect()
        
        print(f"✅ 生成了 {len(main_graph.relations):,} 个关系")
        
        # 保存主图谱
        print("\n💾 保存主图谱到数据库...")
        save_start = time.time()
        repo.save_graph(main_graph)
        save_time = time.time() - save_start
        print(f"✅ 主图谱保存完成，耗时: {save_time:.2f}秒")
        
        # 获取图谱统计
        stats = repo.get_graph_statistics(main_graph.graph_id)
        print(f"\n📈 主图谱统计:")
        print(f"  - 实体数量: {stats['entity_count']:,}")
        print(f"  - 关系数量: {stats['relation_count']:,}")
        print(f"  - 密度: {stats['density']:.6f}")
        
        # 启动资源监控线程
        print("\n📊 启动资源监控...")
        monitor_thread = threading.Thread(target=self.test_resource_monitor, args=(300,))
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # 准备测试
        test_duration = 60  # 测试持续时间（秒）
        threads = self.config['threads']
        
        print(f"\n🚀 启动 {threads} 个并发线程，测试持续 {test_duration} 秒...")
        print("  测试场景:")
        print("  1. 并发读取操作")
        print("  2. 并发写入操作")
        print("  3. 并发搜索操作")
        print("  4. 大规模删除重建操作")
        
        executor = ThreadPoolExecutor(max_workers=threads + 5)
        futures = []
        
        # 分配线程任务
        for i in range(threads):
            task_type = i % 4
            
            if task_type == 0:
                # 并发读取
                future = executor.submit(self.test_concurrent_reads, repo, main_graph, i, test_duration)
            elif task_type == 1:
                # 并发写入
                future = executor.submit(self.test_concurrent_writes, repo, i, test_duration, 50)
            elif task_type == 2:
                # 并发搜索
                future = executor.submit(self.test_concurrent_searches, repo, main_graph, i, test_duration)
            else:
                # 大规模删除重建
                future = executor.submit(self.test_massive_delete_rebuild, repo, test_duration)
            
            futures.append(future)
        
        # 等待测试完成
        print("\n⏳ 测试运行中...")
        try:
            for future in as_completed(futures, timeout=test_duration + 10):
                pass
        except Exception as e:
            print(f"部分任务异常: {e}")
        
        # 停止监控
        self.stop_event.set()
        time.sleep(2)
        
        # 获取测试结果
        print("\n" + "="*80)
        print("📊 测试结果摘要")
        print("="*80)
        
        summary = self.metrics.get_summary()
        
        print(f"\n⏱️  时间统计:")
        print(f"  - 总耗时: {summary['elapsed_time']:.2f} 秒")
        print(f"  - 总操作数: {summary['total_operations']:,}")
        print(f"  - 操作/秒: {summary['operations_per_second']:.2f}")
        
        print(f"\n📈 操作统计:")
        for op_type, count in summary['operation_counts'].items():
            print(f"  - {op_type}: {count:,}")
        
        print(f"\n⚡ 延迟统计:")
        print(f"  - 平均延迟: {summary['avg_latency_ms']:.2f} ms")
        print(f"  - P95延迟: {summary['p95_latency_ms']:.2f} ms")
        print(f"  - P99延迟: {summary['p99_latency_ms']:.2f} ms")
        print(f"  - 最大延迟: {summary['max_latency_ms']:.2f} ms")
        
        print(f"\n💾 资源使用:")
        print(f"  - 平均内存: {summary['avg_memory_mb']:.2f} MB")
        print(f"  - 峰值内存: {summary['max_memory_mb']:.2f} MB")
        print(f"  - 平均CPU: {summary['avg_cpu_percent']:.2f}%")
        
        # 错误分析
        if self.errors:
            print(f"\n❌ 发现 {len(self.errors)} 个错误:")
            error_types = {}
            for error in self.errors[:20]:  # 只显示前20个
                error_key = error.split(':')[0] if ':' in error else error
                error_types[error_key] = error_types.get(error_key, 0) + 1
            
            for error_type, count in error_types.items():
                print(f"  - {error_type}: {count} 次")
            
            if len(self.errors) > 20:
                print(f"  ... 还有 {len(self.errors) - 20} 个错误")
        else:
            print(f"\n✅ 没有发现错误！")
        
        # 内存峰值
        current, peak = tracemalloc.get_traced_memory()
        print(f"\n💡 Python内存追踪:")
        print(f"  - 当前内存: {current / 1024 / 1024:.2f} MB")
        print(f"  - 峰值内存: {peak / 1024 / 1024:.2f} MB")
        tracemalloc.stop()
        
        # 最终验证
        print("\n🔍 验证系统状态...")
        final_stats = repo.get_graph_statistics(main_graph.graph_id)
        print(f"  - 主图谱实体数: {final_stats['entity_count']:,}")
        print(f"  - 主图谱关系数: {final_stats['relation_count']:,}")
        
        all_graphs = repo.get_all_graphs()
        print(f"  - 总图谱数: {len(all_graphs)}")
        
        print("\n" + "="*80)
        print("✅ 超大规模混乱测试完成")
        print("="*80)
        
        return summary, self.errors


def main():
    """主函数"""
    print("="*80)
    print("🔥 Ultra Scale Chaos Test - 超大规模混乱场景测试")
    print("="*80)
    
    # 选择测试规模
    import sys
    scale = sys.argv[1] if len(sys.argv) > 1 else "medium"
    
    valid_scales = ['tiny', 'small', 'medium', 'large', 'huge']
    if scale not in valid_scales:
        print(f"无效的规模: {scale}")
        print(f"可用规模: {', '.join(valid_scales)}")
        print("默认使用 'medium' 规模")
        scale = "medium"
    
    # 运行测试
    test = UltraScaleChaosTest(scale=scale)
    summary, errors = test.run_full_chaos_test()
    
    # 返回结果
    if errors:
        print(f"\n⚠️  测试发现 {len(errors)} 个错误，系统需要优化")
        return 1
    else:
        print(f"\n✅ 测试通过，系统表现良好")
        return 0


if __name__ == "__main__":
    sys.exit(main())
