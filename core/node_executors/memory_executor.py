"""
MEMORY 节点执行器
负责记忆变量的读写（持久化存储）
"""

import json
from typing import Dict, Any, Optional
from pathlib import Path
import os

from core.node_executors.base import BaseExecutor
from core.node_types import Node, MemoryConfig
from core.variable_manager import VariableManager


class MemoryExecutor(BaseExecutor):
    """MEMORY节点执行器"""
    
    def __init__(self, storage_dir: str = None):
        """
        初始化
        
        Args:
            storage_dir: 存储目录，默认为 ./memory_storage
        """
        self.storage_dir = Path(storage_dir or "./memory_storage")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # 内存缓存
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
    
    async def execute(self, node: Node, var_manager: VariableManager) -> Dict[str, Any]:
        """执行MEMORY节点"""
        config: MemoryConfig = node.config
        
        if config.operation == "read":
            return await self._read(config, var_manager)
        elif config.operation == "write":
            return await self._write(config, var_manager)
        else:
            raise ValueError(f"未知的MEMORY操作: {config.operation}")
    
    async def _read(self, config: MemoryConfig, var_manager: VariableManager) -> Dict[str, Any]:
        """读取记忆变量"""
        
        # 从var_manager获取用户ID（用于隔离不同用户的记忆）
        user_id = var_manager.get("user_id", "default")
        
        result = {}
        
        for var_name in config.variables:
            # 优先从内存缓存读取
            if user_id in self.memory_cache and var_name in self.memory_cache[user_id]:
                value = self.memory_cache[user_id][var_name]
            else:
                # 从文件读取
                value = self._read_from_file(user_id, var_name)
            
            result[var_name] = value
            
            # 同步到当前对话的变量管理器
            var_manager.set(var_name, value)
        
        return result
    
    async def _write(self, config: MemoryConfig, var_manager: VariableManager) -> Dict[str, Any]:
        """写入记忆变量"""
        
        user_id = var_manager.get("user_id", "default")
        
        result = {}
        
        for var_name in config.variables:
            # 从当前对话的变量管理器获取值
            value = var_manager.get(var_name)
            
            # 写入内存缓存
            if user_id not in self.memory_cache:
                self.memory_cache[user_id] = {}
            self.memory_cache[user_id][var_name] = value
            
            # 写入文件（持久化）
            self._write_to_file(user_id, var_name, value)
            
            result[var_name] = value
        
        return result
    
    def _read_from_file(self, user_id: str, var_name: str) -> Any:
        """从文件读取"""
        file_path = self.storage_dir / user_id / f"{var_name}.json"
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("value")
        except:
            return None
    
    def _write_to_file(self, user_id: str, var_name: str, value: Any):
        """写入文件"""
        user_dir = self.storage_dir / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = user_dir / f"{var_name}.json"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({
                "value": value,
                "timestamp": str(os.times())
            }, f, ensure_ascii=False, indent=2)
    
    def clear_user_memory(self, user_id: str):
        """清除用户的记忆"""
        # 清除内存缓存
        if user_id in self.memory_cache:
            del self.memory_cache[user_id]
        
        # 清除文件
        user_dir = self.storage_dir / user_id
        if user_dir.exists():
            import shutil
            shutil.rmtree(user_dir)
    
    def get_user_memory(self, user_id: str) -> Dict[str, Any]:
        """获取用户的所有记忆"""
        if user_id in self.memory_cache:
            return self.memory_cache[user_id].copy()
        return {}


# 使用示例
if __name__ == '__main__':
    import asyncio
    
    async def test():
        # 创建执行器
        executor = MemoryExecutor(storage_dir="./test_memory")
        
        # 创建变量管理器
        vm = VariableManager()
        vm.set("user_id", "user_123")
        vm.set("talk_context", '["1", "1", "2"]')
        
        # 测试写入
        from core.node_types import MemoryConfig
        
        write_node = Node(
            node_id="test_write",
            node_type="MEMORY",
            config=MemoryConfig(
                operation="write",
                variables=["talk_context"]
            )
        )
        
        print("=== 测试写入 ===")
        result = await executor.execute(write_node, vm)
        print(f"写入结果: {result}")
        
        # 测试读取
        vm2 = VariableManager()
        vm2.set("user_id", "user_123")
        
        read_node = Node(
            node_id="test_read",
            node_type="MEMORY",
            config=MemoryConfig(
                operation="read",
                variables=["talk_context"]
            )
        )
        
        print("\n=== 测试读取 ===")
        result = await executor.execute(read_node, vm2)
        print(f"读取结果: {result}")
        print(f"var_manager中的值: {vm2.get('talk_context')}")
        
        # 清理测试数据
        executor.clear_user_memory("user_123")
    
    asyncio.run(test())
