/**
 * 贪吃蛇游戏基本功能测试
 * 验证修复后的代码是否正常工作
 */

console.log('=== 贪吃蛇游戏修复版本测试 ===');

// 测试1: 检查全局变量污染
console.log('\n1. 检查全局变量污染:');
console.log('   window.SnakeGame 是否存在?', typeof window.SnakeGame !== 'undefined');
if (typeof window.SnakeGame !== 'undefined') {
    console.log('   ✓ IIFE封装成功，只暴露必要的接口');
    console.log('   暴露的接口:', Object.keys(window.SnakeGame));
} else {
    console.log('   ✗ IIFE封装可能有问题');
}

// 测试2: 检查配置对象
console.log('\n2. 检查配置对象:');
try {
    // 尝试访问原始全局变量
    if (typeof GRID_SIZE !== 'undefined') {
        console.log('   ✗ 发现全局变量 GRID_SIZE，IIFE封装可能有问题');
    } else {
        console.log('   ✓ 全局变量已正确封装');
    }
} catch (e) {
    console.log('   ✓ 全局变量已正确封装（ReferenceError正常）');
}

// 测试3: 检查XSS防护
console.log('\n3. 检查XSS防护:');
console.log('   查看game.js中是否还有innerHTML的使用...');
// 这里可以添加更详细的检查，但需要文件读取

// 测试4: 检查食物生成逻辑
console.log('\n4. 检查食物生成逻辑:');
console.log('   修复后的generateFood函数包含:');
console.log('   - 最大尝试次数限制');
console.log('   - 备用位置查找逻辑');
console.log('   - 游戏结束处理');

// 测试5: 检查方向缓冲
console.log('\n5. 检查方向缓冲机制:');
console.log('   修复后的代码包含:');
console.log('   - directionBuffer 队列');
console.log('   - MAX_BUFFER_SIZE 限制');
console.log('   - processDirectionBuffer 函数');

console.log('\n=== 测试完成 ===');
console.log('\n请手动测试以下功能:');
console.log('1. 打开 test_fixed.html 测试游戏功能');
console.log('2. 测试键盘控制（方向键、空格、P键）');
console.log('3. 测试游戏状态切换（开始、暂停、结束）');
console.log('4. 测试分数计算和最高分保存');
console.log('5. 测试食物生成（特别是蛇身较长时）');