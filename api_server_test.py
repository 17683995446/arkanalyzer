#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arkanalyzer API 服务真实测试
启动 Flask 服务器，进行真实 HTTP 请求测试
"""

import os
import sys
import tempfile
import shutil
import json
import time
import threading
import requests
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'arkanalyzer'))

from database.database_connection_manager import initialize_database, DatabaseConnectionConfig


class APIServerTest:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "api_test.db")
        self.server_thread = None
        self.base_url = "http://127.0.0.1:5000"
        self.issues = []
        self.test_results = []
        
        os.environ['ARKANALYZER_DB'] = self.db_path
        
    def start_server(self):
        def run_server():
            try:
                os.chdir(os.path.join(os.path.dirname(__file__), 'arkanalyzer'))
                from api.app import app
                config = DatabaseConnectionConfig(db_path=self.db_path)
                initialize_database(config)
                app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False, threaded=True)
            except Exception as e:
                print(f"  ❌ 服务器启动异常: {e}")
        
        print("  🚀 启动 API 服务器...")
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        
        # 等待服务器启动
        print("  ⏳ 等待服务器就绪...")
        for i in range(30):
            try:
                response = requests.get(f"{self.base_url}/api/health", timeout=1)
                if response.status_code == 200:
                    print(f"  ✅ API 服务器已就绪！")
                    return True
            except:
                pass
            time.sleep(1)
        
        print("  ❌ 服务器启动超时")
        return False
    
    def stop_server(self):
        print("  🛑 停止服务器...")
    
    def test(self, name: str, func):
        print(f"\n  🧪 测试: {name}")
        try:
            start = time.time()
            result = func()
            duration = time.time() - start
            if result:
                print(f"  ✅ {name} 通过 ({duration:.2f}s)")
                self.test_results.append((name, True, duration))
                return True
            else:
                print(f"  ❌ {name} 失败")
                self.test_results.append((name, False, duration))
                return False
        except Exception as e:
            print(f"  ❌ {name} 异常: {str(e)}")
            self.issues.append({'name': name, 'error': str(e)})
            self.test_results.append((name, False, 0))
            return False
    
    def run_all_tests(self):
        print("\n" + "="*80)
        print("🔗 Arkanalyzer API 服务真实测试")
        print("="*80)
        
        if not self.start_server():
            return False
        
        # 测试健康检查
        self.test("健康检查", self.test_health)
        
        # 测试创建图谱
        self.test("创建图谱", self.test_create_graph)
        
        # 测试添加实体
        self.test("添加实体", self.test_add_entities)
        
        # 测试添加关系
        self.test("添加关系", self.test_add_relations)
        
        # 测试搜索
        self.test("搜索实体", self.test_search)
        
        # 测试图谱统计
        self.test("图谱统计", self.test_graph_stats)
        
        # 测试图谱分析
        self.test("图谱分析", self.test_graph_analysis)
        
        # 测试并发请求
        self.test("并发 API 请求", self.test_concurrent_requests)
        
        # 测试错误处理
        self.test("错误处理", self.test_error_handling)
        
        # 总结
        self.print_summary()
        return len(self.issues) == 0
    
    def test_health(self):
        response = requests.get(f"{self.base_url}/api/health", timeout=5)
        return response.status_code == 200
    
    def test_create_graph(self):
        payload = {"name": "API 测试图谱", "description": "通过 API 创建的测试图谱"}
        response = requests.post(f"{self.base_url}/api/graphs", json=payload, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if 'id' in data:
                self.last_graph_id = data['id']
                return True
        return False
    
    def test_add_entities(self):
        if not hasattr(self, 'last_graph_id'):
            return False
        
        entities = [
            {"name": "API 实体1", "type": "概念", "description": "第一个 API 实体"},
            {"name": "API 实体2", "type": "人物", "description": "第二个 API 实体"},
            {"name": "API 实体3", "type": "组织", "description": "第三个 API 实体"}
        ]
        
        for entity in entities:
            payload = {
                "graph_id": self.last_graph_id,
                **entity
            }
            response = requests.post(f"{self.base_url}/api/entities", json=payload, timeout=5)
            if response.status_code != 200:
                return False
        
        return True
    
    def test_add_relations(self):
        if not hasattr(self, 'last_graph_id'):
            return False
        
        # 先获取实体
        response = requests.get(f"{self.base_url}/api/graphs/{self.last_graph_id}", timeout=5)
        if response.status_code != 200:
            return False
        
        data = response.json()
        if not data or 'entities' not in data or len(data['entities']) < 2:
            return False
        
        entities = data['entities']
        
        # 添加关系
        for i in range(2):
            payload = {
                "graph_id": self.last_graph_id,
                "source_id": entities[i]['id'],
                "target_id": entities[i+1]['id'],
                "type": "相关",
                "description": f"关系 {i}"
            }
            response = requests.post(f"{self.base_url}/api/relations", json=payload, timeout=5)
            if response.status_code != 200:
                return False
        
        return True
    
    def test_search(self):
        search_terms = ["API", "实体", "不存在"]
        for term in search_terms:
            response = requests.get(f"{self.base_url}/api/search?query={term}", timeout=5)
            if response.status_code != 200:
                return False
        return True
    
    def test_graph_stats(self):
        if not hasattr(self, 'last_graph_id'):
            return False
        
        response = requests.get(f"{self.base_url}/api/graphs/{self.last_graph_id}/stats", timeout=5)
        if response.status_code != 200:
            return False
        
        data = response.json()
        if 'entity_count' not in data or 'relation_count' not in data:
            return False
        
        return True
    
    def test_graph_analysis(self):
        if not hasattr(self, 'last_graph_id'):
            return False
        
        response = requests.get(f"{self.base_url}/api/graphs/{self.last_graph_id}/analysis", timeout=10)
        if response.status_code != 200:
            return False
        return True
    
    def test_concurrent_requests(self):
        errors = []
        results = []
        
        def worker(id):
            try:
                # 混合请求
                for i in range(5):
                    response = requests.get(f"{self.base_url}/api/health", timeout=3)
                    if response.status_code == 200:
                        results.append(True)
                    else:
                        errors.append(f"Worker {id} request {i} failed: {response.status_code}")
            except Exception as e:
                errors.append(f"Worker {id} error: {str(e)}")
        
        threads = []
        num_threads = 10
        
        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        print(f"    成功: {len(results)}, 错误: {len(errors)}")
        return len(errors) == 0
    
    def test_error_handling(self):
        # 测试无效的图谱 ID
        response = requests.get(f"{self.base_url}/api/graphs/invalid-id-123456", timeout=5)
        # 不要求特定状态码，但服务器不能崩溃
        
        # 测试空搜索
        response = requests.get(f"{self.base_url}/api/search?query=", timeout=5)
        
        # 测试无效的请求体
        response = requests.post(f"{self.base_url}/api/entities", json={}, timeout=5)
        
        return True
    
    def print_summary(self):
        print("\n" + "="*80)
        print("📊 API 服务测试总结")
        print("="*80)
        
        total = len(self.test_results)
        passed = sum(1 for name, success, _ in self.test_results if success)
        failed = total - passed
        
        print(f"  总测试数: {total}")
        print(f"  通过: {passed}")
        print(f"  失败: {failed}")
        
        if self.issues:
            print(f"\n  ⚠️ 发现问题:")
            for issue in self.issues:
                print(f"    - {issue['name']}: {issue['error']}")
        
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
    tester = APIServerTest()
    try:
        success = tester.run_all_tests()
        return 0 if success else 1
    finally:
        tester.cleanup()


if __name__ == "__main__":
    sys.exit(main())
