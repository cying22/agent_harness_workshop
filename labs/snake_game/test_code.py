#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
贪吃蛇游戏代码测试脚本
"""

import re

def read_file(filepath):
    """读取文件内容"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def test_iife(code):
    """测试IIFE封装"""
    has_iife = '(function() {' in code and '})();' in code
    print("=== 测试1: IIFE封装检查 ===")
    print(f"IIFE封装: {'✅ 通过' if has_iife else '❌ 失败'}")
    return has_iife

def test_strict_mode(code):
    """测试严格模式"""
    has_strict = "'use strict';" in code
    print("=== 测试2: 严格模式检查 ===")
    print(f"严格模式: {'✅ 通过' if has_strict else '❌ 失败'}")
    return has_strict

def test_xss_protection(code):
    """测试XSS防护"""
    innerhtml_matches = re.findall(r'innerHTML', code)
    dangerous_innerhtml = 'innerHTML =' in code and "innerHTML = ''" not in code
    
    print("=== 测试3: XSS防护检查 ===")
    print(f"innerHTML使用次数: {len(innerhtml_matches)}")
    print(f"危险innerHTML使用: {'❌ 存在风险' if dangerous_innerhtml else '✅ 安全'}")
    
    # 检查是否使用textContent
    has_textcontent = 'textContent' in code
    print(f"使用textContent: {'✅ 是' if has_textcontent else '❌ 否'}")
    
    return not dangerous_innerhtml and has_textcontent

def test_food_generation(code):
    """测试食物生成防护"""
    has_max_attempts = 'MAX_FOOD_ATTEMPTS' in code
    has_attempts_counter = 'attempts++' in code
    has_max_attempts_check = 'attempts > maxAttempts' in code
    
    print("=== 测试4: 食物生成防护检查 ===")
    print(f"MAX_FOOD_ATTEMPTS配置: {'✅ 存在' if has_max_attempts else '❌ 缺失'}")
    print(f"attempts计数器: {'✅ 存在' if has_attempts_counter else '❌ 缺失'}")
    print(f"最大尝试检查: {'✅ 存在' if has_max_attempts_check else '❌ 缺失'}")
    
    return has_max_attempts and has_attempts_counter and has_max_attempts_check

def test_direction_buffer(code):
    """测试方向缓冲"""
    has_direction_buffer = 'directionBuffer' in code
    has_process_buffer = 'processDirectionBuffer' in code
    
    print("=== 测试5: 方向缓冲检查 ===")
    print(f"directionBuffer变量: {'✅ 存在' if has_direction_buffer else '❌ 缺失'}")
    print(f"processDirectionBuffer函数: {'✅ 存在' if has_process_buffer else '❌ 缺失'}")
    
    return has_direction_buffer and has_process_buffer

def test_global_interface(code):
    """测试全局接口"""
    has_snakegame = 'window.SnakeGame' in code
    has_init = 'init: init' in code
    has_reset = 'reset: resetGame' in code
    
    print("=== 测试6: 全局接口检查 ===")
    print(f"window.SnakeGame对象: {'✅ 存在' if has_snakegame else '❌ 缺失'}")
    print(f"init方法: {'✅ 存在' if has_init else '❌ 缺失'}")
    print(f"reset方法: {'✅ 存在' if has_reset else '❌ 缺失'}")
    
    return has_snakegame and has_init and has_reset

def test_config_object(code):
    """测试配置对象"""
    has_config = 'const CONFIG = {' in code
    has_grid_size = 'GRID_SIZE:' in code
    has_max_attempts_in_config = 'MAX_FOOD_ATTEMPTS:' in code
    
    print("=== 测试7: 配置对象检查 ===")
    print(f"CONFIG对象: {'✅ 存在' if has_config else '❌ 缺失'}")
    print(f"GRID_SIZE配置: {'✅ 存在' if has_grid_size else '❌ 缺失'}")
    print(f"MAX_FOOD_ATTEMPTS配置: {'✅ 存在' if has_max_attempts_in_config else '❌ 缺失'}")
    
    return has_config and has_grid_size and has_max_attempts_in_config

def main():
    """主测试函数"""
    try:
        code = read_file('game.js')
        
        print("贪吃蛇游戏代码测试报告")
        print("=" * 50)
        
        tests = [
            test_iife(code),
            test_strict_mode(code),
            test_xss_protection(code),
            test_food_generation(code),
            test_direction_buffer(code),
            test_global_interface(code),
            test_config_object(code)
        ]
        
        print("\n" + "=" * 50)
        print("=== 测试总结 ===")
        
        passed = sum(1 for t in tests if t)
        total = len(tests)
        
        print(f"通过测试: {passed}/{total}")
        
        if passed == total:
            print("测试结果: ✅ 所有测试通过")
            print("代码质量: 优秀")
        elif passed >= total * 0.8:
            print("测试结果: ⚠️ 大部分测试通过")
            print("代码质量: 良好")
        else:
            print("测试结果: ❌ 测试未通过")
            print("代码质量: 需要改进")
        
        # 详细测试结果
        print("\n详细测试结果:")
        test_names = [
            "IIFE封装",
            "严格模式",
            "XSS防护",
            "食物生成防护",
            "方向缓冲",
            "全局接口",
            "配置对象"
        ]
        
        for i, (name, result) in enumerate(zip(test_names, tests)):
            status = "✅ 通过" if result else "❌ 失败"
            print(f"  {i+1}. {name}: {status}")
        
        return passed == total
        
    except FileNotFoundError:
        print("❌ 错误: 找不到 game.js 文件")
        return False
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        return False

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)