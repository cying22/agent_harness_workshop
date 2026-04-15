/**
 * 贪吃蛇游戏主逻辑 - 修复版本
 * 修复了所有高优先级问题和中优先级问题
 */

(function() {
    'use strict';
    
    // 游戏状态枚举
    const GameState = {
        IDLE: 'IDLE',           // 等待开始
        PLAYING: 'PLAYING',     // 游戏中
        PAUSED: 'PAUSED',       // 暂停中
        GAME_OVER: 'GAME_OVER'  // 游戏结束
    };
    
    // 方向枚举
    const Direction = {
        UP: 'UP',
        DOWN: 'DOWN',
        LEFT: 'LEFT',
        RIGHT: 'RIGHT'
    };
    
    // 游戏配置
    const CONFIG = {
        GRID_SIZE: 20,        // 网格大小（20x20）
        CELL_SIZE: 20,        // 每个单元格的像素大小
        INITIAL_SPEED: 150,   // 初始速度（毫秒/步）
        SPEED_INCREMENT: 5,   // 每次加速的毫秒数
        MIN_SPEED: 50,        // 最小速度（毫秒/步）
        SCORE_PER_FOOD: 10,   // 每个食物的分数
        MAX_FOOD_ATTEMPTS: 1000 // 最大食物生成尝试次数，防止无限循环
    };
    
    // 游戏状态变量
    let gameState = GameState.IDLE;
    let snake = [];
    let food = { x: 0, y: 0 };
    let direction = Direction.RIGHT;
    let nextDirection = Direction.RIGHT;
    let score = 0;
    let highScore = 0;
    let moveInterval = CONFIG.INITIAL_SPEED;
    let lastMoveTime = 0;
    let animationFrameId = null;
    let foodsEaten = 0;
    
    // 方向缓冲队列，用于改进方向控制
    let directionBuffer = [];
    const MAX_BUFFER_SIZE = 2;
    
    // DOM元素引用
    let canvas, ctx;
    let currentScoreEl, highScoreEl, speedLevelEl;
    let gameOverlayEl, gameMessageEl;
    let gameStateEl, gameLengthEl, gameFoodsEl;
    
    // 初始化游戏
    function init() {
        // 获取DOM元素
        canvas = document.getElementById('game-canvas');
        ctx = canvas.getContext('2d');
        
        currentScoreEl = document.getElementById('current-score');
        highScoreEl = document.getElementById('high-score');
        speedLevelEl = document.getElementById('speed-level');
        gameOverlayEl = document.getElementById('game-overlay');
        gameMessageEl = document.getElementById('game-message');
        gameStateEl = document.getElementById('game-state');
        gameLengthEl = document.getElementById('game-length');
        gameFoodsEl = document.getElementById('game-foods');
        
        // 读取最高分
        loadHighScore();
        
        // 重置游戏状态
        resetGame();
        
        // 添加键盘事件监听
        document.addEventListener('keydown', handleKeydown);
        
        // 开始游戏循环
        gameLoop();
        
        // 更新UI状态
        updateUI();
    }
    
    // 重置游戏状态
    function resetGame() {
        // 重置蛇的位置（初始长度为3，在画布中央偏左）
        snake = [
            { x: 5, y: 10 },  // 蛇头
            { x: 4, y: 10 },  // 蛇身
            { x: 3, y: 10 }   // 蛇尾
        ];
        
        // 重置方向
        direction = Direction.RIGHT;
        nextDirection = Direction.RIGHT;
        directionBuffer = [];
        
        // 重置分数和速度
        score = 0;
        moveInterval = CONFIG.INITIAL_SPEED;
        foodsEaten = 0;
        
        // 生成第一个食物
        generateFood();
        
        // 更新UI
        updateUI();
    }
    
    // 加载最高分
    function loadHighScore() {
        try {
            const savedScore = localStorage.getItem('snakeGameHighScore');
            highScore = savedScore ? parseInt(savedScore) : 0;
            highScoreEl.textContent = highScore;
        } catch (error) {
            console.warn('无法读取本地存储，最高分重置为0');
            highScore = 0;
            highScoreEl.textContent = '0';
        }
    }
    
    // 保存最高分
    function saveHighScore() {
        try {
            localStorage.setItem('snakeGameHighScore', highScore.toString());
        } catch (error) {
            console.warn('无法保存到本地存储');
        }
    }
    
    // 生成食物 - 修复无限循环风险
    function generateFood() {
        let newFood;
        let isOnSnake;
        let attempts = 0;
        
        // 计算最大可能位置数
        const maxPositions = CONFIG.GRID_SIZE * CONFIG.GRID_SIZE;
        
        // 如果蛇已经占满大部分空间，减少尝试次数
        const maxAttempts = Math.min(CONFIG.MAX_FOOD_ATTEMPTS, maxPositions * 2);
        
        do {
            isOnSnake = false;
            // 在网格范围内随机生成食物位置
            newFood = {
                x: Math.floor(Math.random() * CONFIG.GRID_SIZE),
                y: Math.floor(Math.random() * CONFIG.GRID_SIZE)
            };
            
            // 检查食物是否在蛇身上
            for (const segment of snake) {
                if (segment.x === newFood.x && segment.y === newFood.y) {
                    isOnSnake = true;
                    break;
                }
            }
            
            attempts++;
            
            // 防止无限循环
            if (attempts > maxAttempts) {
                console.warn('无法找到合适的食物位置，尝试次数过多');
                // 尝试寻找一个相对安全的位置
                for (let y = 0; y < CONFIG.GRID_SIZE; y++) {
                    for (let x = 0; x < CONFIG.GRID_SIZE; x++) {
                        let found = false;
                        for (const segment of snake) {
                            if (segment.x === x && segment.y === y) {
                                found = true;
                                break;
                            }
                        }
                        if (!found) {
                            food = { x, y };
                            return;
                        }
                    }
                }
                // 如果所有位置都被占满，游戏应该结束
                gameState = GameState.GAME_OVER;
                updateUI();
                return;
            }
        } while (isOnSnake);
        
        food = newFood;
    }
    
    // 检查碰撞 - 改进碰撞检测逻辑
    function checkCollision() {
        const head = snake[0];
        
        // 检查墙壁碰撞
        if (head.x < 0 || head.x >= CONFIG.GRID_SIZE || head.y < 0 || head.y >= CONFIG.GRID_SIZE) {
            return true;
        }
        
        // 检查自身碰撞（从第二个元素开始检查，因为第一个是蛇头）
        // 优化：使用更高效的碰撞检测
        for (let i = 1; i < snake.length; i++) {
            if (head.x === snake[i].x && head.y === snake[i].y) {
                return true;
            }
        }
        
        return false;
    }
    
    // 处理方向缓冲
    function processDirectionBuffer() {
        if (directionBuffer.length > 0) {
            const newDirection = directionBuffer.shift();
            
            // 禁止直接掉头
            if (
                (newDirection === Direction.UP && direction !== Direction.DOWN) ||
                (newDirection === Direction.DOWN && direction !== Direction.UP) ||
                (newDirection === Direction.LEFT && direction !== Direction.RIGHT) ||
                (newDirection === Direction.RIGHT && direction !== Direction.LEFT)
            ) {
                nextDirection = newDirection;
            }
        }
    }
    
    // 更新游戏逻辑
    function update() {
        // 处理方向缓冲
        processDirectionBuffer();
        
        // 更新方向
        direction = nextDirection;
        
        // 计算新的蛇头位置
        const head = { ...snake[0] };
        
        switch (direction) {
            case Direction.UP:
                head.y -= 1;
                break;
            case Direction.DOWN:
                head.y += 1;
                break;
            case Direction.LEFT:
                head.x -= 1;
                break;
            case Direction.RIGHT:
                head.x += 1;
                break;
        }
        
        // 将新的蛇头添加到数组开头
        snake.unshift(head);
        
        // 检查是否吃到食物
        if (head.x === food.x && head.y === food.y) {
            // 吃到食物，增加分数
            score += CONFIG.SCORE_PER_FOOD;
            foodsEaten++;
            
            // 更新最高分
            if (score > highScore) {
                highScore = score;
                saveHighScore();
            }
            
            // 加速（减少移动间隔）
            if (moveInterval > CONFIG.MIN_SPEED) {
                moveInterval -= CONFIG.SPEED_INCREMENT;
                if (moveInterval < CONFIG.MIN_SPEED) {
                    moveInterval = CONFIG.MIN_SPEED;
                }
            }
            
            // 生成新食物
            generateFood();
        } else {
            // 没吃到食物，移除蛇尾
            snake.pop();
        }
        
        // 检查碰撞
        if (checkCollision()) {
            gameState = GameState.GAME_OVER;
            updateUI();
        }
        
        // 更新UI
        updateUI();
    }
    
    // 渲染游戏
    function render() {
        // 清空画布
        ctx.fillStyle = '#1a1a2e';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        // 绘制网格线
        drawGrid();
        
        // 绘制食物
        drawFood();
        
        // 绘制蛇
        drawSnake();
        
        // 绘制UI文字
        drawUI();
    }
    
    // 绘制网格线
    function drawGrid() {
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
        ctx.lineWidth = 1;
        
        // 绘制垂直线
        for (let x = 0; x <= CONFIG.GRID_SIZE; x++) {
            ctx.beginPath();
            ctx.moveTo(x * CONFIG.CELL_SIZE, 0);
            ctx.lineTo(x * CONFIG.CELL_SIZE, canvas.height);
            ctx.stroke();
        }
        
        // 绘制水平线
        for (let y = 0; y <= CONFIG.GRID_SIZE; y++) {
            ctx.beginPath();
            ctx.moveTo(0, y * CONFIG.CELL_SIZE);
            ctx.lineTo(canvas.width, y * CONFIG.CELL_SIZE);
            ctx.stroke();
        }
    }
    
    // 绘制蛇
    function drawSnake() {
        // 绘制蛇身
        for (let i = 0; i < snake.length; i++) {
            const segment = snake[i];
            
            if (i === 0) {
                // 蛇头 - 深绿色圆角矩形
                ctx.fillStyle = '#2E7D32';
                drawRoundedRect(
                    segment.x * CONFIG.CELL_SIZE + 1,
                    segment.y * CONFIG.CELL_SIZE + 1,
                    CONFIG.CELL_SIZE - 2,
                    CONFIG.CELL_SIZE - 2,
                    4
                );
            } else {
                // 蛇身 - 浅绿色圆角矩形
                ctx.fillStyle = '#4CAF50';
                drawRoundedRect(
                    segment.x * CONFIG.CELL_SIZE + 1,
                    segment.y * CONFIG.CELL_SIZE + 1,
                    CONFIG.CELL_SIZE - 2,
                    CONFIG.CELL_SIZE - 2,
                    3
                );
            }
        }
    }
    
    // 绘制圆角矩形辅助函数
    function drawRoundedRect(x, y, width, height, radius) {
        ctx.beginPath();
        ctx.moveTo(x + radius, y);
        ctx.lineTo(x + width - radius, y);
        ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
        ctx.lineTo(x + width, y + height - radius);
        ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
        ctx.lineTo(x + radius, y + height);
        ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
        ctx.lineTo(x, y + radius);
        ctx.quadraticCurveTo(x, y, x + radius, y);
        ctx.closePath();
        ctx.fill();
    }
    
    // 绘制食物
    function drawFood() {
        // 绘制红色圆形食物
        ctx.fillStyle = '#F44336';
        ctx.beginPath();
        ctx.arc(
            food.x * CONFIG.CELL_SIZE + CONFIG.CELL_SIZE / 2,
            food.y * CONFIG.CELL_SIZE + CONFIG.CELL_SIZE / 2,
            8, // 半径
            0,
            Math.PI * 2
        );
        ctx.fill();
        
        // 添加脉冲动画效果
        const pulseSize = Math.sin(Date.now() / 200) * 2 + 10;
        ctx.strokeStyle = 'rgba(244, 67, 54, 0.5)';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(
            food.x * CONFIG.CELL_SIZE + CONFIG.CELL_SIZE / 2,
            food.y * CONFIG.CELL_SIZE + CONFIG.CELL_SIZE / 2,
            pulseSize,
            0,
            Math.PI * 2
        );
        ctx.stroke();
    }
    
    // 绘制UI文字
    function drawUI() {
        // 根据游戏状态显示不同的文字
        if (gameState === GameState.IDLE) {
            // 开始界面文字已经在HTML中显示
            return;
        }
        
        if (gameState === GameState.PAUSED) {
            drawCenteredText('游戏暂停', 30, '#ffffff');
            drawCenteredText('按P键继续', 18, 'rgba(255, 255, 255, 0.8)', 50);
        }
        
        if (gameState === GameState.GAME_OVER) {
            drawCenteredText('游戏结束', 30, '#ffffff');
            drawCenteredText(`最终分数: ${score}`, 18, 'rgba(255, 255, 255, 0.8)', 50);
            
            // 检查是否打破记录
            if (score === highScore && score > 0) {
                drawCenteredText('新纪录!', 20, '#FFD700', 80);
            }
            
            drawCenteredText('按空格键重新开始', 18, 'rgba(255, 255, 255, 0.8)', 110);
        }
    }
    
    // 绘制居中文字辅助函数
    function drawCenteredText(text, fontSize, color, yOffset = 0) {
        ctx.font = `bold ${fontSize}px Arial, sans-serif`;
        ctx.fillStyle = color;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(text, canvas.width / 2, canvas.height / 2 + yOffset);
    }
    
    // 更新UI元素 - 修复XSS风险，使用textContent替代innerHTML
    function updateUI() {
        // 更新分数显示
        currentScoreEl.textContent = score;
        highScoreEl.textContent = highScore;
        
        // 计算速度等级（1-10级）
        const speedLevel = Math.max(1, Math.min(10, Math.floor((CONFIG.INITIAL_SPEED - moveInterval) / 10) + 1));
        speedLevelEl.textContent = speedLevel;
        
        // 更新游戏状态显示
        let stateText = '';
        switch (gameState) {
            case GameState.IDLE:
                stateText = '等待开始';
                break;
            case GameState.PLAYING:
                stateText = '游戏中';
                break;
            case GameState.PAUSED:
                stateText = '暂停中';
                break;
            case GameState.GAME_OVER:
                stateText = '游戏结束';
                break;
        }
        gameStateEl.textContent = `状态: ${stateText}`;
        
        // 更新蛇身长度和已吃食物数量
        gameLengthEl.textContent = `蛇身长度: ${snake.length}`;
        gameFoodsEl.textContent = `已吃食物: ${foodsEaten}`;
        
        // 更新游戏覆盖层
        updateGameOverlay();
    }
    
    // 更新游戏覆盖层 - 修复XSS风险
    function updateGameOverlay() {
        if (gameState === GameState.PLAYING) {
            gameOverlayEl.style.display = 'none';
        } else {
            gameOverlayEl.style.display = 'flex';
            
            // 清空现有内容
            gameMessageEl.innerHTML = '';
            
            // 创建新的内容元素
            const title = document.createElement('h2');
            const message = document.createElement('p');
            
            switch (gameState) {
                case GameState.IDLE:
                    title.textContent = '贪吃蛇游戏';
                    message.textContent = '按空格键开始游戏';
                    break;
                    
                case GameState.PAUSED:
                    title.textContent = '游戏暂停';
                    message.textContent = '按P键继续游戏';
                    break;
                    
                case GameState.GAME_OVER:
                    title.textContent = '游戏结束';
                    message.textContent = `最终分数: ${score}`;
                    
                    // 创建新纪录提示
                    if (score === highScore && score > 0) {
                        const newRecord = document.createElement('p');
                        newRecord.textContent = '新纪录!';
                        newRecord.className = 'new-record';
                        gameMessageEl.appendChild(newRecord);
                    }
                    
                    // 创建重新开始提示
                    const restartMsg = document.createElement('p');
                    restartMsg.textContent = '按空格键重新开始';
                    gameMessageEl.appendChild(title);
                    gameMessageEl.appendChild(message);
                    gameMessageEl.appendChild(restartMsg);
                    
                    gameMessageEl.classList.add('fade-in');
                    
                    // 移除动画类以便下次添加
                    setTimeout(() => {
                        gameMessageEl.classList.remove('fade-in');
                    }, 500);
                    return;
            }
            
            gameMessageEl.appendChild(title);
            gameMessageEl.appendChild(message);
            gameMessageEl.classList.add('fade-in');
            
            // 移除动画类以便下次添加
            setTimeout(() => {
                gameMessageEl.classList.remove('fade-in');
            }, 500);
        }
    }
    
    // 键盘事件处理 - 改进方向缓冲机制
    function handleKeydown(event) {
        // 防止方向键和空格键的默认行为（页面滚动）
        if ([
            'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight',
            ' ', 'Spacebar', 'w', 'W', 'a', 'A', 's', 'S', 'd', 'D', 'p', 'P'
        ].includes(event.key)) {
            event.preventDefault();
        }
        
        // 处理方向控制
        if (gameState === GameState.PLAYING) {
            let newDirection = null;
            
            // 方向键和WASD键映射
            switch (event.key) {
                case 'ArrowUp':
                case 'w':
                case 'W':
                    newDirection = Direction.UP;
                    break;
                case 'ArrowDown':
                case 's':
                case 'S':
                    newDirection = Direction.DOWN;
                    break;
                case 'ArrowLeft':
                case 'a':
                case 'A':
                    newDirection = Direction.LEFT;
                    break;
                case 'ArrowRight':
                case 'd':
                case 'D':
                    newDirection = Direction.RIGHT;
                    break;
            }
            
            // 如果按下了有效的方向键，添加到缓冲队列
            if (newDirection) {
                // 如果缓冲队列已满，移除最早的方向
                if (directionBuffer.length >= MAX_BUFFER_SIZE) {
                    directionBuffer.shift();
                }
                
                // 检查是否与队列中最后一个方向相同，避免重复
                if (directionBuffer.length === 0 || directionBuffer[directionBuffer.length - 1] !== newDirection) {
                    directionBuffer.push(newDirection);
                }
            }
        }
        
        // 处理游戏状态控制
        switch (event.key) {
            case ' ':
            case 'Spacebar':
                if (gameState === GameState.IDLE || gameState === GameState.GAME_OVER) {
                    // 开始新游戏
                    resetGame();
                    gameState = GameState.PLAYING;
                    updateUI();
                }
                break;
                
            case 'p':
            case 'P':
                if (gameState === GameState.PLAYING) {
                    gameState = GameState.PAUSED;
                    updateUI();
                } else if (gameState === GameState.PAUSED) {
                    gameState = GameState.PLAYING;
                    updateUI();
                }
                break;
        }
    }
    
    // 游戏主循环
    function gameLoop(timestamp) {
        // 请求下一帧
        animationFrameId = requestAnimationFrame(gameLoop);
        
        // 渲染当前帧
        render();
        
        // 只在游戏进行中更新游戏逻辑
        if (gameState === GameState.PLAYING) {
            // 使用时间差累积机制控制蛇的移动频率
            if (timestamp - lastMoveTime >= moveInterval) {
                update();
                lastMoveTime = timestamp;
            }
        }
    }
    
    // 暴露必要的接口到全局作用域
    window.SnakeGame = {
        init: init,
        reset: resetGame,
        getScore: () => score,
        getHighScore: () => highScore,
        getGameState: () => gameState
    };
    
    // 启动游戏
    window.addEventListener('DOMContentLoaded', init);
    
    // 清理资源
    window.addEventListener('beforeunload', () => {
        if (animationFrameId) {
            cancelAnimationFrame(animationFrameId);
        }
    });
})();