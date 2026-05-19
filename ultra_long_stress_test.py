#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arkanalyzer 超长时间极端压力测试 - 真实业务场景模拟
持续运行测试，模拟真实生产环境使用，发现潜在问题
"""

import os
import sys
import tempfile
import shutil
import random
import json
import time
import threading
import gc
from datetime import datetime
from typing import Dict, List, Any, Set

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'arkanalyzer'))

from core.knowledge_graph_core import Entity, Relation, KnowledgeGraph
from core.knowledge_repository import KnowledgeRepository
from core.knowledge_graph_analyzer import KnowledgeGraphAnalyzer
from database.database_connection_manager import initialize_database, DatabaseConnectionConfig

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


class UltraStressTest:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "ultra_stress_test.db")
        config = DatabaseConnectionConfig(db_path=self.db_path)
        initialize_database(config)
        self.repo = KnowledgeRepository()
        self.issues = []
        self.operations_completed = 0
        self.start_time = time.time()
        self.process = psutil.Process() if HAS_PSUTIL else None

    def log_issue(self, severity: str, category: str, description: str, details: Any = None):
        issue = {
            'severity': severity,
            'category': category,
            'description': description,
            'details': details,
            'timestamp': datetime.now().isoformat(),
            'operations_completed': self.operations_completed
        }
        self.issues.append(issue)
        icon = '🚨' if severity == 'critical' else '⚠️' if severity == 'warning' else 'ℹ️'
        print(f"{icon} [{severity}] {category}: {description}")

    def log_memory(self, label: str):
        if self.process:
            memory_mb = self.process.memory_info().rss / 1024 / 1024
            print(f"  💾 {label}: {memory_mb:.2f} MB")
            return memory_mb
        return 0

    def test_real_business_scenario_1(self):
        """真实业务场景1：企业知识管理 - 持续添加实体和关系"""
        print("\n" + "="*80)
        print("📦 业务场景1: 企业知识管理系统 - 持续知识录入")
        print("="*80)
        
        graph = KnowledgeGraph(graph_name="企业知识库", description="企业知识图谱")
        graph_id = None
        entity_types = ["员工", "部门", "项目", "文档", "客户", "产品", "技术", "会议"]
        relation_types = ["属于", "参与", "负责", "创建", "引用", "关联", "讨论", "使用"]
        
        try:
            # 初始保存
            self.repo.save_graph(graph)
            graph_id = graph.graph_id
            self.operations_completed += 1
            
            initial_memory = self.log_memory("初始内存")
            
            for round_num in range(50):
                # 每次添加一批实体和关系
                round_entities = []
                
                for i in range(20):
                    et = random.choice(entity_types)
                    entity = Entity(
                        entity_name=f"{et}_{self.operations_completed}_{i}_{random.randint(1, 10000)}",
                        entity_type=et,
                        description=f"这是一个{et}实体，在轮次{round_num}添加",
                        properties={
                            'round': round_num,
                            'timestamp': time.time(),
                            'tags': random.sample(['重要', '普通', '紧急', '归档'], k=random.randint(1, 3))
                        }
                    )
                    round_entities.append(entity)
                    graph.add_entity(entity)
                
                # 添加关系
                for i in range(40):
                    if len(graph.entities) >= 2:
                        src_idx = random.randint(0, len(graph.entities) - 1)
                        tgt_idx = random.randint(0, len(graph.entities) - 1)
                        while tgt_idx == src_idx:
                            tgt_idx = random.randint(0, len(graph.entities) - 1)
                        
                        rel = Relation(
                            source_entity_id=graph.entities[src_idx].entity_id,
                            target_entity_id=graph.entities[tgt_idx].entity_id,
                            relation_type=random.choice(relation_types),
                            weight=random.random(),
                            properties={'round': round_num, 'confidence': random.random()}
                        )
                        graph.add_relation(rel)
                
                # 保存
                save_start = time.time()
                save_success = self.repo.save_graph(graph)
                save_time = time.time() - save_start
                self.operations_completed += 1
                
                if not save_success:
                    self.log_issue('critical', '保存失败', f'第{round_num}轮保存失败')
                
                if save_time > 1.0:
                    self.log_issue('warning', '性能问题', f'保存耗时过长: {save_time:.2f}s')
                
                # 读取验证
                retrieved = self.repo.get_graph(graph_id)
                if not retrieved:
                    self.log_issue('critical', '读取失败', f'第{round_num}轮读取失败')
                elif len(retrieved.entities) != len(graph.entities):
                    self.log_issue('warning', '数据不一致', 
                                    f'实体数量不一致: {len(retrieved.entities)} vs {len(graph.entities)}')
                
                self.operations_completed += 1
                
                if round_num % 10 == 0:
                    print(f"  ✅ 完成 {round_num + 1}/50 轮 - 实体: {len(graph.entities)}, 关系: {len(graph.relations)}")
                    self.log_memory(f"轮次 {round_num}")
            
            final_memory = self.log_memory("业务场景1结束")
            memory_growth = final_memory - initial_memory
            
            if memory_growth > 50:
                self.log_issue('warning', '内存增长', f'内存显著增长: {memory_growth:.2f} MB')
            
            print(f"  ✅ 业务场景1完成 - 总实体: {len(graph.entities)}, 总关系: {len(graph.relations)}")
            return True
            
        except Exception as e:
            self.log_issue('critical', '异常', f'业务场景1异常: {str(e)}')
            import traceback
            traceback.print_exc()
            return False

    def test_real_business_scenario_2(self):
        """真实业务场景2：社交网络分析 - 图算法密集使用"""
        print("\n" + "="*80)
        print("👥 业务场景2: 社交网络分析")
        print("="*80)
        
        try:
            initial_memory = self.log_memory("初始内存")
            
            # 创建大型社交网络图谱
            graph = KnowledgeGraph(graph_name="社交网络", description="用户关系图谱")
            users = []
            
            # 创建用户
            for i in range(500):
                user = Entity(
                    entity_name=f"用户_{i}",
                    entity_type="用户",
                    properties={
                        'age': random.randint(18, 80),
                        'city': random.choice(['北京', '上海', '广州', '深圳', '杭州', '成都']),
                        'join_date': datetime.now().isoformat()
                    }
                )
                users.append(user)
                graph.add_entity(user)
            
            # 创建朋友关系 - 模拟真实社交网络（每个人约10个好友）
            for i in range(5000):
                src_idx = random.randint(0, 499)
                tgt_idx = random.randint(0, 499)
                while tgt_idx == src_idx:
                    tgt_idx = random.randint(0, 499)
                
                rel = Relation(
                    source_entity_id=users[src_idx].entity_id,
                    target_entity_id=users[tgt_idx].entity_id,
                    relation_type="朋友",
                    weight=random.random() * 0.5 + 0.5
                )
                graph.add_relation(rel)
            
            # 保存
            save_start = time.time()
            self.repo.save_graph(graph)
            save_time = time.time() - save_start
            print(f"  💾 保存完成: {save_time:.2f}s")
            
            # 密集执行图分析算法
            print(f"  🔍 开始图分析计算...")
            analyzer = KnowledgeGraphAnalyzer(graph.entities, graph.relations)
            
            for i in range(30):
                # 统计计算
                stat_start = time.time()
                stats = analyzer.calculate_statistics()
                stat_time = time.time() - stat_start
                
                # 关键实体识别
                key_start = time.time()
                key_entities = analyzer.find_key_entities(20)
                key_time = time.time() - key_start
                
                # 社区检测
                comm_start = time.time()
                communities = analyzer.detect_communities_bfs()
                comm_time = time.time() - comm_start
                
                # 路径查找（随机用户对）
                path_start = time.time()
                u1 = random.randint(0, 499)
                u2 = random.randint(0, 499)
                path = analyzer.find_shortest_path(users[u1].entity_id, users[u2].entity_id)
                path_time = time.time() - path_start
                
                self.operations_completed += 1
                
                if i % 5 == 0:
                    print(f"    迭代 {i+1}/30 - 统计: {stat_time:.3f}s, 关键实体: {key_time:.3f}s, 社区: {comm_time:.3f}s")
                
                if stat_time > 0.5:
                    self.log_issue('warning', '性能', f'统计计算慢: {stat_time:.3f}s')
                if comm_time > 2.0:
                    self.log_issue('warning', '性能', f'社区检测慢: {comm_time:.3f}s')
            
            final_memory = self.log_memory("业务场景2结束")
            
            print(f"  ✅ 业务场景2完成 - 关键实体数: {len(key_entities)}, 社区数: {len(communities.communities)}")
            return True
            
        except Exception as e:
            self.log_issue('critical', '异常', f'业务场景2异常: {str(e)}')
            import traceback
            traceback.print_exc()
            return False

    def test_extreme_concurrent_operations(self):
        """极端并发测试 - 真实生产环境负载"""
        print("\n" + "="*80)
        print("🔀 极端并发测试 - 50线程混合读写")
        print("="*80)
        
        errors = []
        lock = threading.Lock()
        graphs_created = []
        
        def worker(worker_id: int):
            try:
                for i in range(50):
                    # 混合操作：创建、保存、读取、搜索、删除
                    if random.random() < 0.3:
                        # 创建图谱
                        g = KnowledgeGraph(graph_name=f"并发图谱_{worker_id}_{i}")
                        for j in range(15):
                            g.add_entity(Entity(entity_name=f"并发实体_{worker_id}_{i}_{j}", entity_type="概念"))
                        success = self.repo.save_graph(g)
                        if success:
                            with lock:
                                graphs_created.append(g.graph_id)
                    elif random.random() < 0.5:
                        # 搜索实体
                        results = self.repo.search_entities(f"并发实体_{worker_id}")
                    elif random.random() < 0.7:
                        # 获取所有图谱
                        all_graphs = self.repo.get_all_graphs()
                    elif random.random() < 0.85 and graphs_created:
                        # 随机读取一个
                        with lock:
                            if graphs_created:
                                gid = random.choice(graphs_created)
                                self.repo.get_graph(gid)
                    elif graphs_created:
                        # 删除
                        with lock:
                            if graphs_created:
                                gid = graphs_created.pop()
                                self.repo.delete_graph(gid)
                    
                    with lock:
                        self.operations_completed += 1
                    
                    time.sleep(random.random() * 0.01)
            except Exception as e:
                with lock:
                    errors.append({'worker': worker_id, 'error': str(e)})
                    self.log_issue('warning', '并发错误', f'线程 {worker_id} 错误: {str(e)}')
        
        num_threads = 50
        print(f"  🚀 启动 {num_threads} 个并发线程...")
        
        start_time = time.time()
        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        total_time = time.time() - start_time
        
        print(f"  ⏱️  总时间: {total_time:.2f}s, 总操作: {self.operations_completed}")
        
        if errors:
            self.log_issue('critical', '并发问题', f'发现 {len(errors)} 个并发错误')
            return False
        
        print(f"  ✅ 极端并发测试通过 - 无错误！")
        return True

    def test_memory_stability_long_running(self):
        """长时间内存稳定性测试 - 持续操作并监控内存"""
        print("\n" + "="*80)
        print("⏱️  长时间内存稳定性测试 - 1000次操作循环")
        print("="*80)
        
        memory_samples = []
        initial_memory = self.log_memory("初始内存")
        memory_samples.append(initial_memory)
        
        for i in range(1000):
            try:
                # 创建图谱
                graph = KnowledgeGraph(graph_name=f"内存测试_{i}")
                for j in range(30):
                    graph.add_entity(Entity(entity_name=f"测试_{i}_{j}", entity_type="概念"))
                for j in range(40):
                    if len(graph.entities) >= 2:
                        s = random.randint(0, len(graph.entities) - 1)
                        t = random.randint(0, len(graph.entities) - 1)
                        while t == s:
                            t = random.randint(0, len(graph.entities) - 1)
                        graph.add_relation(Relation(
                            source_entity_id=graph.entities[s].entity_id,
                            target_entity_id=graph.entities[t].entity_id,
                            relation_type="相关"
                        ))
                
                # 保存和删除
                self.repo.save_graph(graph)
                retrieved = self.repo.get_graph(graph.graph_id)
                self.repo.delete_graph(graph.graph_id)
                
                self.operations_completed += 1
                
                # 内存采样
                if i % 50 == 0:
                    current = self.log_memory(f"迭代 {i}")
                    memory_samples.append(current)
                    gc.collect()
            
            except Exception as e:
                self.log_issue('warning', '内存测试异常', f'迭代 {i} 错误: {str(e)}')
        
        final_memory = self.log_memory("最终内存")
        memory_samples.append(final_memory)
        
        max_memory = max(memory_samples)
        min_memory = min(memory_samples)
        avg_memory = sum(memory_samples) / len(memory_samples)
        growth = final_memory - initial_memory
        
        print(f"\n  📊 内存统计:")
        print(f"    初始: {initial_memory:.2f} MB")
        print(f"    最终: {final_memory:.2f} MB")
        print(f"    增长: {growth:.2f} MB")
        print(f"    最大: {max_memory:.2f} MB")
        print(f"    平均: {avg_memory:.2f} MB")
        
        if growth > 100:
            self.log_issue('warning', '内存泄漏嫌疑', f'内存增长过多: {growth:.2f} MB')
        elif growth > 50:
            self.log_issue('warning', '内存问题', f'内存增长明显: {growth:.2f} MB')
        
        print(f"  ✅ 长时间内存测试完成！")
        return True

    def test_extreme_edge_cases(self):
        """极端边缘情况测试 - 真实用户可能遇到的异常数据"""
        print("\n" + "="*80)
        print("🛡️  极端边缘情况测试")
        print("="*80)
        
        edge_cases_passed = 0
        total_cases = 0
        
        # 1. 超大属性数据
        total_cases +=1
        try:
            graph = KnowledgeGraph(graph_name="大属性测试")
            huge_text = "这是一段超大的文本" * 10000
            entity = Entity(
                entity_name="超大属性实体",
                entity_type="概念",
                description=huge_text,
                properties={'huge': huge_text, 'list': list(range(10000))}
            )
            graph.add_entity(entity)
            self.repo.save_graph(graph)
            retrieved = self.repo.get_graph(graph.graph_id)
            if retrieved and len(retrieved.entities) ==1:
                edge_cases_passed +=1
                print(f"  ✅ 大属性数据测试通过")
            self.repo.delete_graph(graph.graph_id)
        except Exception as e:
            self.log_issue('warning', '边缘情况', f'大属性数据失败: {str(e)}')
        
        # 2. 特殊字符和编码
        total_cases +=1
        try:
            graph = KnowledgeGraph(graph_name="特殊字符测试")
            special_names = [
                '测试"引号',
                "测试'单引号",
                '测试\\反斜杠',
                '测试\n换行\t制表',
                '测试🚀表情🤖符号😊',
                '测试中文한국어日本語',
                '<script>alert(1)</script>',
                'NULL\x00字符'
            ]
            for name in special_names:
                graph.add_entity(Entity(entity_name=name, entity_type="概念"))
            self.repo.save_graph(graph)
            retrieved = self.repo.get_graph(graph.graph_id)
            if retrieved and len(retrieved.entities) == len(special_names):
                edge_cases_passed +=1
                print(f"  ✅ 特殊字符测试通过")
            self.repo.delete_graph(graph.graph_id)
        except Exception as e:
            self.log_issue('warning', '边缘情况', f'特殊字符失败: {str(e)}')
        
        # 3. 极端关系密度
        total_cases +=1
        try:
            graph = KnowledgeGraph(graph_name="高密度关系测试")
            entities = []
            for i in range(100):
                entities.append(Entity(entity_name=f"高密度_{i}", entity_type="概念"))
                graph.add_entity(entities[i])
            
            for i in range(100):
                for j in range(100):
                    if i != j:
                        graph.add_relation(Relation(
                            source_entity_id=entities[i].entity_id,
                            target_entity_id=entities[j].entity_id,
                            relation_type="连接"
                        ))
            
            save_start = time.time()
            self.repo.save_graph(graph)
            save_time = time.time() - save_start
            print(f"  高密度关系保存: {save_time:.2f}s (关系数: {len(graph.relations)})")
            edge_cases_passed +=1
            self.repo.delete_graph(graph.graph_id)
        except Exception as e:
            self.log_issue('warning', '边缘情况', f'高密度关系失败: {str(e)}')
        
        # 4. 空值和None处理
        total_cases +=1
        try:
            graph = KnowledgeGraph(graph_name="空值测试")
            # 各种空值情况
            entity1 = Entity(entity_name="", entity_type="概念")
            entity2 = Entity(entity_name="正常实体", entity_type="")
            graph.add_entity(entity1)
            graph.add_entity(entity2)
            graph.add_relation(Relation(
                source_entity_id=entity1.entity_id,
                target_entity_id=entity2.entity_id,
                relation_type=""
            ))
            self.repo.save_graph(graph)
            edge_cases_passed +=1
            print(f"  ✅ 空值处理测试通过")
            self.repo.delete_graph(graph.graph_id)
        except Exception as e:
            self.log_issue('warning', '边缘情况', f'空值处理失败: {str(e)}')
        
        print(f"\n  📊 边缘情况测试: {edge_cases_passed}/{total_cases} 个通过")
        return edge_cases_passed == total_cases

    def run_all(self):
        print("\n" + "="*80)
        print("🔥 Arkanalyzer 超长时间极端压力测试开始")
        print(f"⏰ 开始时间: {datetime.now().isoformat()}")
        print("="*80)
        
        results = []
        
        results.append(self.test_real_business_scenario_1())
        results.append(self.test_real_business_scenario_2())
        results.append(self.test_extreme_concurrent_operations())
        results.append(self.test_memory_stability_long_running())
        results.append(self.test_extreme_edge_cases())
        
        print("\n" + "="*80)
        print("📊 超长时间压力测试总结")
        print("="*80)
        print(f"✅ 成功: {sum(1 for r in results if r)}/{len(results)}")
        print(f"🚨 发现问题: {len(self.issues)}")
        print(f"🔢 总操作数: {self.operations_completed}")
        print(f"⏱️  总耗时: {time.time() - self.start_time:.2f}s")
        
        if self.issues:
            print(f"\n⚠️  问题详情:")
            for issue in self.issues:
                print(f"  [{issue['severity']}] {issue['category']}: {issue['description']}")
        
        print("="*80)
        
        return len(self.issues) == 0

    def cleanup(self):
        try:
            from database.database_connection_manager import get_database_pool
            pool = get_database_pool()
            pool.close_all()
        except:
            pass
        shutil.rmtree(self.temp_dir, ignore_errors=True)


def main():
    tester = UltraStressTest()
    try:
        success = tester.run_all()
        return 0 if success else 1
    finally:
        tester.cleanup()


if __name__ == "__main__":
    sys.exit(main())
