#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
utils/asyncio_helper.py
AsyncIO 事件循环辅助工具 - 解决事件循环冲突问题
"""

import asyncio
import threading
import sys
from typing import Optional, Coroutine, Any


class AsyncIOHelper:
    """
    AsyncIO 事件循环辅助类

    解决以下问题：
    1. asyncio.run() 不能在已有事件循环中调用
    2. PyQt5 与 asyncio 的集成
    3. 跨线程的协程调用
    """

    _instance = None
    _loop = None
    _thread = None

    @classmethod
    def get_instance(cls) -> 'AsyncIOHelper':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def get_event_loop(cls) -> asyncio.AbstractEventLoop:
        """
        获取或创建事件循环

        兼容各种环境：
        - 标准 Python 脚本
        - Jupyter Notebook
        - Spyder IDE
        - PyQt5 应用
        """
        # 1. 尝试获取当前线程的事件循环
        try:
            loop = asyncio.get_running_loop()
            return loop
        except RuntimeError:
            pass

        # 2. 尝试获取已设置的事件循环
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return loop
        except RuntimeError:
            pass

        # 3. 创建新的事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        return loop

    @classmethod
    def run_coroutine(cls, coro: Coroutine, timeout: Optional[float] = None) -> Any:
        """
        运行协程（兼容各种环境）

        Args:
            coro: 要运行的协程
            timeout: 超时时间（秒）

        Returns:
            协程的返回值
        """
        # 1. 尝试获取正在运行的事件循环
        try:
            loop = asyncio.get_running_loop()
            # 在已有事件循环中，创建任务并等待
            future = asyncio.ensure_future(coro)
            if timeout:
                future = asyncio.wait_for(future, timeout)
            # 使用 run_until_complete 的替代方案
            # 在已有事件循环中，我们不能阻塞，所以返回 Future
            return future
        except RuntimeError:
            pass

        # 2. 没有运行的事件循环，使用 asyncio.run
        try:
            if timeout:
                coro = asyncio.wait_for(coro, timeout)
            return asyncio.run(coro)
        except RuntimeError as e:
            # asyncio.run() 失败，尝试手动管理事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                if timeout:
                    coro = asyncio.wait_for(coro, timeout)
                return loop.run_until_complete(coro)
            finally:
                # 不要关闭事件循环，可能其他地方还在使用
                pass

    @classmethod
    def run_coroutine_sync(cls, coro: Coroutine, timeout: Optional[float] = None) -> Any:
        """
        同步运行协程（阻塞等待结果）

        Args:
            coro: 要运行的协程
            timeout: 超时时间（秒）

        Returns:
            协程的返回值
        """
        try:
            # 尝试获取运行中的循环
            loop = asyncio.get_running_loop()

            # 在已有事件循环中，使用 asyncio.run_coroutine_threadsafe
            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(coro, loop)

                # 阻塞等待结果
                if timeout:
                    try:
                        return future.result(timeout=timeout)
                    except asyncio.TimeoutError:
                        future.cancel()
                        raise TimeoutError(f"协程执行超时 ({timeout}秒)")
                else:
                    return future.result()
            else:
                # 循环未运行，直接运行
                if timeout:
                    coro = asyncio.wait_for(coro, timeout)
                return loop.run_until_complete(coro)

        except RuntimeError:
            # 没有事件循环，创建新的
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                if timeout:
                    coro = asyncio.wait_for(coro, timeout)
                return loop.run_until_complete(coro)
            finally:
                # 保持循环开启
                pass

    @classmethod
    def create_background_loop(cls) -> asyncio.AbstractEventLoop:
        """
        在后台线程创建并运行事件循环

        Returns:
            事件循环对象
        """
        if cls._loop is not None:
            return cls._loop

        def run_loop():
            cls._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(cls._loop)
            cls._loop.run_forever()

        cls._thread = threading.Thread(target=run_loop, daemon=True)
        cls._thread.start()

        # 等待循环启动
        while cls._loop is None:
            import time
            time.sleep(0.01)

        return cls._loop

    @classmethod
    def run_in_background(cls, coro: Coroutine) -> asyncio.Future:
        """
        在后台事件循环中运行协程

        Args:
            coro: 要运行的协程

        Returns:
            Future 对象
        """
        loop = cls.create_background_loop()

        # 使用 run_coroutine_threadsafe 在后台循环中运行
        future = asyncio.run_coroutine_threadsafe(coro, loop)

        return future

    @classmethod
    def safe_run(cls, main_coro: Coroutine):
        """
        安全运行主协程（兼容各种环境）

        这是 asyncio.run() 的替代品，可以在已有事件循环中使用

        Args:
            main_coro: 主协程

        Usage:
            async def main():
                # 你的异步代码
                pass

            # 替代 asyncio.run(main())
            AsyncIOHelper.safe_run(main())
        """
        try:
            # 尝试在当前事件循环中运行
            loop = asyncio.get_running_loop()

            # 已有事件循环在运行
            # 创建任务并添加到循环
            asyncio.ensure_future(main_coro)

            # 注意：这里不会等待完成，只是添加到循环
            # 如果需要等待，请使用 run_coroutine_sync

        except RuntimeError:
            # 没有运行中的事件循环
            # 使用 asyncio.run 或手动管理
            try:
                asyncio.run(main_coro)
            except RuntimeError:
                # asyncio.run() 也失败了，手动管理
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(main_coro)
                finally:
                    loop.close()


# 便捷函数
def run_async(coro: Coroutine, timeout: Optional[float] = None) -> Any:
    """运行协程（自动检测环境）"""
    return AsyncIOHelper.run_coroutine_sync(coro, timeout)


def run_async_background(coro: Coroutine) -> asyncio.Future:
    """在后台运行协程"""
    return AsyncIOHelper.run_in_background(coro)


def safe_run(main_coro: Coroutine):
    """安全运行主协程（替代 asyncio.run）"""
    AsyncIOHelper.safe_run(main_coro)


# 修复 asyncio.run() 冲突的装饰器
def fix_asyncio_run(func):
    """
    装饰器：修复函数中的 asyncio.run() 调用

    使用方法：
        @fix_asyncio_run
        async def my_async_function():
            await asyncio.sleep(1)

        # 调用时会自动处理事件循环
        my_async_function()
    """
    def wrapper(*args, **kwargs):
        coro = func(*args, **kwargs)
        return run_async(coro)

    return wrapper


if __name__ == "__main__":
    # 测试
    print("测试 AsyncIO Helper")

    async def test_task():
        print("任务开始...")
        await asyncio.sleep(1)
        print("任务完成")
        return "结果"

    # 测试 1: 直接运行
    print("\n测试 1: 直接运行")
    result = run_async(test_task(), timeout=5)
    print(f"返回值: {result}")

    # 测试 2: 后台运行
    print("\n测试 2: 后台运行")
    future = run_async_background(test_task())
    print(f"Future: {future}")

    # 测试 3: safe_run
    print("\n测试 3: safe_run")
    safe_run(test_task())

    print("\n所有测试完成")
