#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arkanalyzer 真实 API 服务测试 - 启动真实的 Flask 服务器
进行真实的 HTTP 请求测试，模拟生产环境
"""

import os
import sys
import tempfile
import shutil
import json
import time
import threading
import requests
import random
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'arkanalyzer'))


class RealAPITest:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "real_api_test.db")
        self.server_process = None
        self.base_url = "http://127.0.0.1:5000"
        self.issues = []
        self.results = []
        
        # 设置环境变量
        os.environ['ARKANALYZER_DB'] = self.db_path
        
    def start_server(self):
        """启动 Flask 服务器（子进程）"""
        import subprocess
        
        print("  🚀 启动真实的 API 服务器...")
        
        # 启动服务器的脚本
        server_script = os.path.join(os.path.dirname(__file__), 'arkanalyzer', 'api', 'app.py')
        
        # 设置工作目录
        work_dir = os.path.join(os.path.dirname(__file__), 'arkanalyzer')
        
        # 初始化数据库
        from database.database_connection_manager import initialize_database, DatabaseConnectionConfig
        config = DatabaseConnectionConfig(db_path=self.db_path)
        initialize_database(config)
        
        # 启动 Flask 服务器
        env = os.environ.copy()
        env['FLASK_APP'] = 'api.app'
        env['FLASK_ENV'] = 'development'
        env['ARKANALYZER_DB'] = self.db_path
        
        self.server_process = subprocess.Popen(
            [sys.executable, '-m', 'flask', 'run', '--host=127.0.0.1', '--port=5000', '--no-debugger', '--no-reload'],
            cwd=work_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 等待服务器就绪
        print("  ⏳ 等待服务器启动...")
        for i in range(60):
            try:
                response = requests.get(f"{self.base_url}/api/health", timeout=2)
                if response.status_code == 200:
                    print(f"  ✅ API 服务器已就绪！ (耗时 {i} 秒)")
                    return True
            except Exception:
                pass
            time.sleep(1)
        
        print("  ❌ 服务器启动超时！")
        print("  服务器输出:")
        if self.server_process.stdout:
            print(self.server_process.stdout.read())
        if self.server_process.stderr:
            print(self.server_process.stderr.read())
        return False
    
    def stop_server(self):
        """停止服务器"""
        if self.server_process:
            print("  🛑 停止服务器...")
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except:
                self.server_process.kill()
    
    def log_test(self, name, success, details=None):
        icon = "✅" if success else "❌"
        self.results.append((name, success, details))
        print(f"  {icon} {name}", end="")
        if details:
            print(f" - {details}")
        else:
            print()
    
    def test_1_health_check(self):
        """测试1: 健康检查"""
        print("\n" + "="*60)
        print("测试1: 健康检查")
        print("="*60)
        try:
            start = time.time()
            response = requests.get(f"{self.base_url}/api/health", timeout=5)
            duration = time.time() - start
            self.log_test("健康检查", response.status_code == 200, f"{duration:.3f}s")
            return response.status_code == 200
        except Exception as e:
            self.log_test("健康检查", False, str(e))
            return False
    
    def test_2_create_graph(self):
        """测试2: 创建图谱"""
        print("\n" + "="*60)
        print("测试2: 创建图谱")
        print("="*60)
        try:
            payload = {
                "name": "真实 API 测试图谱",
                "description": "通过真实 API 创建的测试图谱"
            }
            start = time.time()
            response = requests.post(f"{self.base_url}/api/graphs", json=payload, timeout=5)
            duration = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                self.current_graph_id = data.get('id')
                self.log_test("创建图谱", True, f"ID: {self.current_graph_id}, {duration:.3f}s")
                return True
            else:
                self.log_test("创建图谱", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("创建图谱", False, str(e))
            return False
    
    def test_3_add_entities_batch(self):
        """测试3: 批量添加实体"""
        print("\n" + "="*60)
        print("测试3: 批量添加实体")
        print("="*60)
        if not hasattr(self, 'current_graph_id'):
            self.log_test("批量添加实体", False, "没有图谱 ID")
            return False
        
        try:
            total_time = 0
            success_count = 0
            
            # 添加 100 个实体
            for i in range(100):
                payload = {
                    "graph_id": self.current_graph_id,
                    "name": f"API 实体 {i+1}",
                    "type": random.choice(["概念", "人物", "地点", "组织", "事件"]),
                    "description": f"这是第 {i+1} 个通过 API 添加的实体"
                }
                start = time.time()
                response = requests.post(f"{self.base_url}/api/entities", json=payload, timeout=10)
                duration = time.time() - start
                total_time += duration
                
                if response.status_code == 200:
                    success_count += 1
            
            success = success_count == 100
            self.log_test(f"批量添加 100 个实体", success, 
                        f"成功: {success_count}/100, 总耗时: {total_time:.2f}s, 平均: {total_time/100:.3f}s/个")
            return success
        except Exception as e:
            self.log_test("批量添加实体", False, str(e))
            return False
    
    def test_4_get_graph(self):
        """测试4: 获取完整图谱"""
        print("\n" + "="*60)
        print("测试4: 获取完整图谱")
        print("="*60)
        if not hasattr(self, 'current_graph_id'):
            self.log_test("获取完整图谱", False, "没有图谱 ID")
            return False
        
        try:
            start = time.time()
            response = requests.get(f"{self.base_url}/api/graphs/{self.current_graph_id}", timeout=10)
            duration = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                entity_count = len(data.get('entities', []))
                relation_count = len(data.get('relations', []))
                self.log_test("获取完整图谱", True, 
                            f"实体: {entity_count}, 关系: {relation_count}, {duration:.3f}s")
                return True
            else:
                self.log_test("获取完整图谱", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("获取完整图谱", False, str(e))
            return False
    
    def test_5_search_entities(self):
        """测试5: 搜索实体"""
        print("\n" + "="*60)
        print("测试5: 搜索实体")
        print("="*60)
        
        try:
            search_terms = ["API", "实体", "10", "50", "不存在"]
            all_success = True
            
            for term in search_terms:
                start = time.time()
                response = requests.get(f"{self.base_url}/api/search?query={term}", timeout=5)
                duration = time.time() - start
                
                if response.status_code == 200:
                    results = response.json()
                    print(f"    搜索 '{term}': 找到 {len(results)} 个结果 ({duration:.3f}s)")
                else:
                    all_success = False
                    print(f"    搜索 '{term}': 失败 (Status {response.status_code})")
            
            self.log_test("搜索实体", all_success)
            return all_success
        except Exception as e:
            self.log_test("搜索实体", False, str(e))
            return False
    
    def test_6_graph_stats(self):
        """测试6: 图谱统计"""
        print("\n" + "="*60)
        print("测试6: 图谱统计")
        print("="*60)
        if not hasattr(self, 'current_graph_id'):
            self.log_test("图谱统计", False, "没有图谱 ID")
            return False
        
        try:
            start = time.time()
            response = requests.get(f"{self.base_url}/api/graphs/{self.current_graph_id}/stats", timeout=5)
            duration = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("图谱统计", True, 
                            f"实体: {data.get('entity_count')}, 关系: {data.get('relation_count')}, {duration:.3f}s")
                return True
            else:
                self.log_test("图谱统计", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("图谱统计", False, str(e))
            return False
    
    def test_7_graph_analysis(self):
        """测试7: 图谱分析"""
        print("\n" + "="*60)
        print("测试7: 图谱分析")
        print("="*60)
        if not hasattr(self, 'current_graph_id'):
            self.log_test("图谱分析", False, "没有图谱 ID")
            return False
        
        try:
            start = time.time()
            response = requests.get(f"{self.base_url}/api/graphs/{self.current_graph_id}/analysis", timeout=10)
            duration = time.time() - start
            
            if response.status_code == 200:
                self.log_test("图谱分析", True, f"{duration:.3f}s")
                return True
            else:
                self.log_test("图谱分析", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("图谱分析", False, str(e))
            return False
    
    def test_8_concurrent_requests(self):
        """测试8: 并发请求"""
        print("\n" + "="*60)
        print("测试8: 并发请求")
        print("="*60)
        
        errors = []
        
        def worker(worker_id):
            try:
                for i in range(10):
                    # 混合请求
                    requests.get(f"{self.base_url}/api/health", timeout=3)
                    if hasattr(self, 'current_graph_id') and random.random() > 0.5:
                        requests.get(f"{self.base_url}/api/graphs/{self.current_graph_id}/stats", timeout=3)
            except Exception as e:
                errors.append(f"Worker {worker_id}: {str(e)}")
        
        threads = []
        num_threads = 20
        
        print(f"    启动 {num_threads} 个并发线程...")
        start = time.time()
        
        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        duration = time.time() - start
        
        success = len(errors) == 0
        self.log_test(f"并发请求 ({num_threads} 线程)", success, 
                    f"错误: {len(errors)}, 耗时: {duration:.2f}s")
        
        if errors:
            for err in errors[:5]:
                print(f"    ❌ {err}")
        
        return success
    
    def test_9_list_all_graphs(self):
        """测试9: 列出所有图谱"""
        print("\n" + "="*60)
        print("测试9: 列出所有图谱")
        print("="*60)
        
        try:
            start = time.time()
            response = requests.get(f"{self.base_url}/api/graphs", timeout=5)
            duration = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("列出所有图谱", True, f"总数: {len(data)}, {duration:.3f}s")
                return True
            else:
                self.log_test("列出所有图谱", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("列出所有图谱", False, str(e))
            return False
    
    def test_10_delete_graph(self):
        """测试10: 删除图谱"""
        print("\n" + "="*60)
        print("测试10: 删除图谱")
        print("="*60)
        if not hasattr(self, 'current_graph_id'):
            self.log_test("删除图谱", False, "没有图谱 ID")
            return False
        
        try:
            start = time.time()
            response = requests.delete(f"{self.base_url}/api/graphs/{self.current_graph_id}", timeout=5)
            duration = time.time() - start
            
            self.log_test("删除图谱", response.status_code == 200, f"{duration:.3f}s")
            return response.status_code == 200
        except Exception as e:
            self.log_test("删除图谱", False, str(e))
            return False
    
    def run_all(self):
        print("\n" + "="*80)
        print("🔗 Arkanalyzer 真实 API 服务测试")
        print("="*80)
        
        if not self.start_server():
            return False
        
        try:
            # 运行所有测试
            self.test_1_health_check()
            self.test_2_create_graph()
            self.test_3_add_entities_batch()
            self.test_4_get_graph()
            self.test_5_search_entities()
            self.test_6_graph_stats()
            self.test_7_graph_analysis()
            self.test_8_concurrent_requests()
            self.test_9_list_all_graphs()
            self.test_10_delete_graph()
            
            # 总结
            self.print_summary()
        finally:
            self.stop_server()
        
        return len([r for r in self.results if not r[1]]) == 0
    
    def print_summary(self):
        print("\n" + "="*80)
        print("📊 真实 API 服务测试总结")
        print("="*80)
        
        total = len(self.results)
        passed = sum(1 for _, s, _ in self.results if s)
        failed = total - passed
        
        print(f"  总测试数: {total}")
        print(f"  通过: {passed}")
        print(f"  失败: {failed}")
        
        if failed > 0:
            print(f"\n  ❌ 失败的测试:")
            for name, success, details in self.results:
                if not success:
                    print(f"    - {name}: {details}")
        else:
            print(f"\n  ✅ 所有测试通过！")
        
        print("="*80)
    
    def cleanup(self):
        self.stop_server()
        try:
            from database.database_connection_manager import get_database_pool
            pool = get_database_pool()
            pool.close_all()
        except:
            pass
        shutil.rmtree(self.temp_dir, ignore_errors=True)


def main():
    tester = RealAPITest()
    try:
        success = tester.run_all()
        return 0 if success else 1
    finally:
        tester.cleanup()


if __name__ == "__main__":
    sys.exit(main())
