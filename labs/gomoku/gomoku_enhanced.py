#!/usr/bin/env python3
"""
五子棋小游戏（Gomoku）增强版
- 15x15 棋盘，命令行界面
- 支持双人对战和AI对战模式
- 支持游戏难度选择（简单、中等、困难）
- 支持游戏记录功能（保存和加载游戏）
- 支持游戏统计（胜率、总游戏数等）
- 改进用户界面，添加菜单系统
"""

import os
import json
import random
import time
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any


class Board:
    """棋盘类，负责棋盘的状态管理和显示"""

    # 棋盘大小
    SIZE = 15

    # 棋子常量
    EMPTY = 0
    BLACK = 1
    WHITE = 2

    # 棋子显示符号
    SYMBOLS = {
        EMPTY: "·",
        BLACK: "●",
        WHITE: "○",
    }

    def __init__(self):
        """初始化空棋盘"""
        self.grid = [[self.EMPTY] * self.SIZE for _ in range(self.SIZE)]
        self.move_count = 0  # 记录已落子数
        self.move_history = []  # 记录落子历史

    def is_valid_position(self, row: int, col: int) -> bool:
        """检查坐标是否在棋盘范围内"""
        return 0 <= row < self.SIZE and 0 <= col < self.SIZE

    def is_empty(self, row: int, col: int) -> bool:
        """检查指定位置是否为空"""
        return self.grid[row][col] == self.EMPTY

    def place_stone(self, row: int, col: int, stone: int) -> bool:
        """
        在指定位置落子
        :param row: 行坐标
        :param col: 列坐标
        :param stone: 棋子类型（BLACK 或 WHITE）
        :return: 是否成功落子
        """
        if not self.is_valid_position(row, col):
            return False
        if not self.is_empty(row, col):
            return False
        self.grid[row][col] = stone
        self.move_count += 1
        self.move_history.append((row, col, stone))
        return True

    def undo_move(self) -> Optional[Tuple[int, int, int]]:
        """撤销最后一步棋"""
        if not self.move_history:
            return None
        
        row, col, stone = self.move_history.pop()
        self.grid[row][col] = self.EMPTY
        self.move_count -= 1
        return (row, col, stone)

    def is_full(self) -> bool:
        """检查棋盘是否已满（平局判定）"""
        return self.move_count >= self.SIZE * self.SIZE

    def check_winner(self, row: int, col: int) -> bool:
        """
        检查最近落子的位置是否形成五连
        从落子点向四个方向（水平、垂直、两条对角线）检查
        :param row: 最近落子的行
        :param col: 最近落子的列
        :return: 是否获胜
        """
        stone = self.grid[row][col]
        if stone == self.EMPTY:
            return False

        # 四个方向：水平、垂直、左上-右下对角线、右上-左下对角线
        directions = [
            (0, 1),   # 水平方向
            (1, 0),   # 垂直方向
            (1, 1),   # 左上到右下对角线
            (1, -1),  # 右上到左下对角线
        ]

        for dr, dc in directions:
            count = 1  # 当前位置本身算一个

            # 正方向计数
            r, c = row + dr, col + dc
            while self.is_valid_position(r, c) and self.grid[r][c] == stone:
                count += 1
                r += dr
                c += dc

            # 反方向计数
            r, c = row - dr, col - dc
            while self.is_valid_position(r, c) and self.grid[r][c] == stone:
                count += 1
                r -= dr
                c -= dc

            # 如果某方向连续棋子数 >= 5，则获胜
            if count >= 5:
                return True

        return False

    def get_empty_positions(self) -> List[Tuple[int, int]]:
        """获取所有空位置"""
        positions = []
        for row in range(self.SIZE):
            for col in range(self.SIZE):
                if self.is_empty(row, col):
                    positions.append((row, col))
        return positions

    def display(self):
        """美观地显示棋盘，带行列标号"""
        # 清屏，提供更好的视觉体验
        os.system("clear" if os.name == "posix" else "cls")

        print("\n  ===== 五子棋 (Gomoku) =====\n")

        # 每个单元格统一占 4 个可视列宽：
        #   全角棋子（●/○占2列）：" ● "  → 1 + 2 + 1 = 4 列
        #   半角空位（·占1列）  ：" ·  " → 1 + 1 + 2 = 4 列

        # 打印列标号（顶部），每列占 4 字符宽度，与棋盘单元格对齐
        header = "     " + "".join(f" {i:2d} " for i in range(self.SIZE))
        print(header)

        # 打印分隔线
        separator = "     " + "-" * (self.SIZE * 4)
        print(separator)

        # 逐行打印棋盘
        for row in range(self.SIZE):
            # 行标号 + 棋子
            row_str = f" {row:2d} |"
            for col in range(self.SIZE):
                cell = self.grid[row][col]
                symbol = self.SYMBOLS[cell]
                if cell == self.EMPTY:
                    # 半角字符·(1列)，补一个额外空格使视觉宽度 = 4 列
                    row_str += f" {symbol}  "
                else:
                    # 全角字符●/○(2列)，视觉宽度已为 4 列
                    row_str += f" {symbol} "
            row_str += "|"
            print(row_str)

        # 打印底部分隔线
        print(separator)
        print()


class Player:
    """玩家基类"""

    def __init__(self, name: str, stone: int):
        """
        初始化玩家
        :param name: 玩家名称
        :param stone: 棋子类型（Board.BLACK 或 Board.WHITE）
        """
        self.name = name
        self.stone = stone
        self.symbol = Board.SYMBOLS[stone]

    def get_move(self, board: Board) -> Optional[Tuple[int, int]]:
        """获取玩家落子位置，子类需要实现"""
        raise NotImplementedError


class HumanPlayer(Player):
    """人类玩家"""

    def get_move(self, board: Board) -> Optional[Tuple[int, int]]:
        """获取人类玩家输入"""
        while True:
            user_input = input(f"  请 {self.name} 输入坐标（行 列）: ").strip().lower()
            
            # 检查是否认输/退出
            if user_input in ("quit", "q", "exit"):
                return None
            
            # 尝试解析坐标
            parts = user_input.split()
            if len(parts) != 2:
                print("  [错误] 请输入两个数字，用空格分隔（如: 7 7）")
                continue

            try:
                row, col = int(parts[0]), int(parts[1])
            except ValueError:
                print("  [错误] 请输入有效的数字坐标")
                continue

            # 验证坐标范围
            if not board.is_valid_position(row, col):
                print(f"  [错误] 坐标超出范围，行和列必须在 0~{Board.SIZE - 1} 之间")
                continue

            # 验证位置是否已有棋子
            if not board.is_empty(row, col):
                print("  [错误] 该位置已有棋子，请选择其他位置")
                continue

            return (row, col)


class AIPlayer(Player):
    """AI玩家"""

    def __init__(self, name: str, stone: int, difficulty: str = "medium"):
        """
        初始化AI玩家
        :param name: AI名称
        :param stone: 棋子类型
        :param difficulty: 难度级别（easy, medium, hard）
        """
        super().__init__(name, stone)
        self.difficulty = difficulty
        self.opponent_stone = Board.BLACK if stone == Board.WHITE else Board.WHITE

    def get_move(self, board: Board) -> Optional[Tuple[int, int]]:
        """根据难度级别获取AI落子位置"""
        print(f"  {self.name} 正在思考...")
        time.sleep(0.5)  # 模拟思考时间

        if self.difficulty == "easy":
            return self._get_easy_move(board)
        elif self.difficulty == "medium":
            return self._get_medium_move(board)
        else:  # hard
            return self._get_hard_move(board)

    def _get_easy_move(self, board: Board) -> Tuple[int, int]:
        """简单难度：随机落子"""
        empty_positions = board.get_empty_positions()
        return random.choice(empty_positions)

    def _get_medium_move(self, board: Board) -> Tuple[int, int]:
        """中等难度：优先选择中心区域，有一定策略"""
        empty_positions = board.get_empty_positions()
        
        # 优先选择中心区域
        center_positions = [(r, c) for r, c in empty_positions 
                           if 5 <= r <= 9 and 5 <= c <= 9]
        if center_positions:
            return random.choice(center_positions)
        
        # 如果没有中心位置，随机选择
        return random.choice(empty_positions)

    def _get_hard_move(self, board: Board) -> Tuple[int, int]:
        """困难难度：使用简单的评估函数"""
        empty_positions = board.get_empty_positions()
        
        # 如果有可以立即获胜的位置，选择它
        for r, c in empty_positions:
            # 尝试放置自己的棋子
            board.grid[r][c] = self.stone
            if board.check_winner(r, c):
                board.grid[r][c] = Board.EMPTY
                return (r, c)
            board.grid[r][c] = Board.EMPTY
            
            # 检查对手是否有立即获胜的位置，如果有则阻止
            board.grid[r][c] = self.opponent_stone
            if board.check_winner(r, c):
                board.grid[r][c] = Board.EMPTY
                return (r, c)
            board.grid[r][c] = Board.EMPTY
        
        # 使用评估函数选择最佳位置
        best_score = -float('inf')
        best_moves = []
        
        for r, c in empty_positions:
            score = self._evaluate_position(board, r, c)
            if score > best_score:
                best_score = score
                best_moves = [(r, c)]
            elif score == best_score:
                best_moves.append((r, c))
        
        return random.choice(best_moves)

    def _evaluate_position(self, board: Board, row: int, col: int) -> int:
        """评估位置的得分"""
        score = 0
        
        # 中心位置得分更高
        center_distance = abs(row - 7) + abs(col - 7)
        score += (14 - center_distance) * 2
        
        # 检查四个方向的潜在连线
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        
        for dr, dc in directions:
            # 检查自己的潜在连线
            line_score = self._evaluate_direction(board, row, col, dr, dc, self.stone)
            score += line_score * 10
            
            # 检查对手的潜在连线（防守）
            opponent_line_score = self._evaluate_direction(board, row, col, dr, dc, self.opponent_stone)
            score += opponent_line_score * 8
        
        return score

    def _evaluate_direction(self, board: Board, row: int, col: int, 
                           dr: int, dc: int, stone: int) -> int:
        """评估一个方向的潜在连线"""
        count = 1  # 当前位置
        
        # 正方向
        r, c = row + dr, col + dc
        while board.is_valid_position(r, c) and board.grid[r][c] == stone:
            count += 1
            r += dr
            c += dc
        
        # 反方向
        r, c = row - dr, col - dc
        while board.is_valid_position(r, c) and board.grid[r][c] == stone:
            count += 1
            r -= dr
            c -= dc
        
        # 根据连线长度给分
        if count >= 5:
            return 100  # 获胜
        elif count == 4:
            return 50   # 四连
        elif count == 3:
            return 20   # 三连
        elif count == 2:
            return 5    # 二连
        return 0


class GameStatistics:
    """游戏统计管理类"""
    
    def __init__(self, stats_file: str = "gomoku_stats.json"):
        """初始化统计管理器"""
        self.stats_file = stats_file
        self.stats = self._load_stats()
    
    def _load_stats(self) -> Dict[str, Any]:
        """加载统计信息"""
        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        
        # 默认统计信息
        return {
            "total_games": 0,
            "human_vs_human": {"wins": 0, "losses": 0, "draws": 0},
            "human_vs_ai": {"wins": 0, "losses": 0, "draws": 0},
            "ai_vs_ai": {"wins": 0, "losses": 0, "draws": 0},
            "game_history": []
        }
    
    def _save_stats(self):
        """保存统计信息"""
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"  保存统计信息失败: {e}")
    
    def record_game(self, game_type: str, winner: Optional[str], 
                   players: List[str], moves: int, difficulty: str = None):
        """记录游戏结果"""
        self.stats["total_games"] += 1
        
        game_record = {
            "timestamp": datetime.now().isoformat(),
            "game_type": game_type,
            "players": players,
            "winner": winner,
            "moves": moves,
            "difficulty": difficulty
        }
        
        # 添加到历史记录
        self.stats["game_history"].append(game_record)
        
        # 更新胜负统计
        if game_type == "human_vs_human":
            stats_key = "human_vs_human"
        elif game_type == "human_vs_ai":
            stats_key = "human_vs_ai"
        else:
            stats_key = "ai_vs_ai"
        
        if winner is None:
            self.stats[stats_key]["draws"] += 1
        elif winner == players[0]:  # 第一个玩家获胜
            self.stats[stats_key]["wins"] += 1
        else:
            self.stats[stats_key]["losses"] += 1
        
        # 保存统计信息
        self._save_stats()
    
    def display_stats(self):
        """显示统计信息"""
        print("\n" + "="*50)
        print("  游戏统计信息")
        print("="*50)
        
        total = self.stats["total_games"]
        print(f"  总游戏数: {total}")
        
        if total > 0:
            print(f"\n  双人对战模式:")
            hvh = self.stats["human_vs_human"]
            hvh_total = hvh["wins"] + hvh["losses"] + hvh["draws"]
            if hvh_total > 0:
                print(f"    游戏数: {hvh_total}")
                print(f"    胜率: {hvh['wins']/hvh_total*100:.1f}%")
                print(f"    平局率: {hvh['draws']/hvh_total*100:.1f}%")
            
            print(f"\n  人机对战模式:")
            hva = self.stats["human_vs_ai"]
            hva_total = hva["wins"] + hva["losses"] + hva["draws"]
            if hva_total > 0:
                print(f"    游戏数: {hva_total}")
                print(f"    胜率: {hva['wins']/hva_total*100:.1f}%")
                print(f"    平局率: {hva['draws']/hva_total*100:.1f}%")
            
            print(f"\n  最近5场游戏记录:")
            history = self.stats["game_history"][-5:]
            for i, game in enumerate(reversed(history), 1):
                timestamp = datetime.fromisoformat(game["timestamp"]).strftime("%m-%d %H:%M")
                winner = game["winner"] if game["winner"] else "平局"
                print(f"    {i}. {timestamp} - {game['game_type']} - 获胜者: {winner}")
        
        print("\n" + "="*50)


class GameSaver:
    """游戏保存/加载管理类"""
    
    def __init__(self, save_dir: str = "saves"):
        """初始化保存管理器"""
        self.save_dir = save_dir
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
    
    def save_game(self, board: Board, players: List[Player], 
                 current_player_index: int, game_type: str, difficulty: str = None):
        """保存游戏状态"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"gomoku_save_{timestamp}.json"
        filepath = os.path.join(self.save_dir, filename)
        
        save_data = {
            "timestamp": datetime.now().isoformat(),
            "game_type": game_type,
            "difficulty": difficulty,
            "current_player_index": current_player_index,
            "board": {
                "grid": board.grid,
                "move_count": board.move_count,
                "move_history": board.move_history
            },
            "players": [
                {
                    "name": player.name,
                    "stone": player.stone,
                    "type": "human" if isinstance(player, HumanPlayer) else "ai"
                }
                for player in players
            ]
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            print(f"  游戏已保存到: {filepath}")
            return True
        except Exception as e:
            print(f"  保存游戏失败: {e}")
            return False
    
    def load_game(self) -> Optional[Dict[str, Any]]:
        """加载游戏状态"""
        # 列出所有保存文件
        saves = []
        for filename in os.listdir(self.save_dir):
            if filename.endswith('.json') and filename.startswith('gomoku_save_'):
                filepath = os.path.join(self.save_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        save_data = json.load(f)
                    saves.append((filepath, save_data))
                except Exception:
                    continue
        
        if not saves:
            print("  没有找到保存的游戏")
            return None
        
        # 显示保存的游戏列表
        print("\n  保存的游戏列表:")
        for i, (filepath, save_data) in enumerate(saves, 1):
            timestamp = datetime.fromisoformat(save_data["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
            print(f"  {i}. {timestamp} - {save_data['game_type']} - 步数: {save_data['board']['move_count']}")
        
        # 让用户选择
        while True:
            try:
                choice = input("\n  请选择要加载的游戏编号 (0取消): ")
                if choice == "0":
                    return None
                
                index = int(choice) - 1
                if 0 <= index < len(saves):
                    return saves[index][1]
                else:
                    print("  无效的选择")
            except ValueError:
                print("  请输入有效的数字")
    
    def list_saves(self):
        """列出所有保存的游戏"""
        saves = []
        for filename in os.listdir(self.save_dir):
            if filename.endswith('.json') and filename.startswith('gomoku_save_'):
                filepath = os.path.join(self.save_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        save_data = json.load(f)
                    saves.append((filepath, save_data))
                except Exception:
                    continue
        
        if not saves:
            print("  没有找到保存的游戏")
            return
        
        print("\n  所有保存的游戏:")
        for i, (filepath, save_data) in enumerate(saves, 1):
            timestamp = datetime.fromisoformat(save_data["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
            game_type = save_data.get("game_type", "未知")
            moves = save_data["board"]["move_count"]
            print(f"  {i}. {timestamp} - {game_type} - 步数: {moves}")


class GomokuGame:
    """五子棋游戏主控类，负责游戏流程管理"""

    def __init__(self):
        """初始化游戏"""
        self.board = Board()
        self.players = []
        self.current_player_index = 0
        self.game_type = ""  # human_vs_human, human_vs_ai, ai_vs_ai
        self.difficulty = None
        self.stats = GameStatistics()
        self.saver = GameSaver()
        self.is_paused = False

    @property
    def current_player(self) -> Player:
        """获取当前回合的玩家"""
        return self.players[self.current_player_index]

    def switch_player(self):
        """切换到下一位玩家"""
        self.current_player_index = 1 - self.current_player_index

    def setup_game(self):
        """设置游戏模式"""
        while True:
            os.system("clear" if os.name == "posix" else "cls")
            print("\n" + "="*50)
            print("  五子棋游戏 - 主菜单")
            print("="*50)
            print("  1. 双人对战模式")
            print("  2. 人机对战模式")
            print("  3. 机机对战模式")
            print("  4. 加载游戏")
            print("  5. 查看游戏统计")
            print("  6. 查看保存的游戏")
            print("  7. 退出游戏")
            print("="*50)
            
            choice = input("\n  请选择模式 (1-7): ").strip()
            
            if choice == "1":
                self._setup_human_vs_human()
                return True
            elif choice == "2":
                self._setup_human_vs_ai()
                return True
            elif choice == "3":
                self._setup_ai_vs_ai()
                return True
            elif choice == "4":
                if self._load_game():
                    return True
            elif choice == "5":
                self.stats.display_stats()
                input("\n  按 Enter 键返回主菜单...")
            elif choice == "6":
                self.saver.list_saves()
                input("\n  按 Enter 键返回主菜单...")
            elif choice == "7":
                return False
            else:
                print("  无效的选择，请重新输入")
                input("  按 Enter 键继续...")

    def _setup_human_vs_human(self):
        """设置双人对战模式"""
        self.game_type = "human_vs_human"
        player1_name = input("  请输入玩家1（黑棋）名称: ").strip() or "黑棋玩家"
        player2_name = input("  请输入玩家2（白棋）名称: ").strip() or "白棋玩家"
        
        self.players = [
            HumanPlayer(player1_name, Board.BLACK),
            HumanPlayer(player2_name, Board.WHITE)
        ]
        self.current_player_index = 0

    def _setup_human_vs_ai(self):
        """设置人机对战模式"""
        self.game_type = "human_vs_ai"
        
        # 选择难度
        while True:
            print("\n  请选择AI难度:")
            print("  1. 简单")
            print("  2. 中等")
            print("  3. 困难")
            diff_choice = input("  请选择 (1-3): ").strip()
            
            if diff_choice == "1":
                self.difficulty = "easy"
                break
            elif diff_choice == "2":
                self.difficulty = "medium"
                break
            elif diff_choice == "3":
                self.difficulty = "hard"
                break
            else:
                print("  无效的选择")
        
        # 选择执棋方
        while True:
            print("\n  请选择执棋方:")
            print("  1. 玩家执黑（先手）")
            print("  2. 玩家执白（后手）")
            side_choice = input("  请选择 (1-2): ").strip()
            
            player_name = input("  请输入玩家名称: ").strip() or "人类玩家"
            ai_name = f"AI玩家 ({self.difficulty})"
            
            if side_choice == "1":
                self.players = [
                    HumanPlayer(player_name, Board.BLACK),
                    AIPlayer(ai_name, Board.WHITE, self.difficulty)
                ]
                break
            elif side_choice == "2":
                self.players = [
                    AIPlayer(ai_name, Board.BLACK, self.difficulty),
                    HumanPlayer(player_name, Board.WHITE)
                ]
                break
            else:
                print("  无效的选择")
        
        self.current_player_index = 0

    def _setup_ai_vs_ai(self):
        """设置机机对战模式"""
        self.game_type = "ai_vs_ai"
        
        # 选择AI难度
        print("\n  请选择AI1的难度:")
        print("  1. 简单")
        print("  2. 中等")
        print("  3. 困难")
        diff1_choice = input("  请选择 (1-3): ").strip()
        
        diff1 = "easy" if diff1_choice == "1" else "medium" if diff1_choice == "2" else "hard"
        
        print("\n  请选择AI2的难度:")
        print("  1. 简单")
        print("  2. 中等")
        print("  3. 困难")
        diff2_choice = input("  请选择 (1-3): ").strip()
        
        diff2 = "easy" if diff2_choice == "1" else "medium" if diff2_choice == "2" else "hard"
        
        self.players = [
            AIPlayer(f"AI1 ({diff1})", Board.BLACK, diff1),
            AIPlayer(f"AI2 ({diff2})", Board.WHITE, diff2)
        ]
        self.current_player_index = 0

    def _load_game(self) -> bool:
        """加载游戏"""
        save_data = self.saver.load_game()
        if not save_data:
            return False
        
        # 恢复棋盘状态
        self.board.grid = save_data["board"]["grid"]
        self.board.move_count = save_data["board"]["move_count"]
        self.board.move_history = save_data["board"]["move_history"]
        
        # 恢复玩家状态
        self.players = []
        for player_data in save_data["players"]:
            if player_data["type"] == "human":
                player = HumanPlayer(player_data["name"], player_data["stone"])
            else:
                # 从保存的数据中获取难度
                difficulty = save_data.get("difficulty", "medium")
                player = AIPlayer(player_data["name"], player_data["stone"], difficulty)
            self.players.append(player)
        
        self.current_player_index = save_data["current_player_index"]
        self.game_type = save_data["game_type"]
        self.difficulty = save_data.get("difficulty")
        
        print("  游戏加载成功！")
        return True

    def show_game_menu(self):
        """显示游戏内菜单"""
        print("\n  游戏菜单:")
        print("  1. 继续游戏")
        print("  2. 保存游戏")
        print("  3. 认输")
        print("  4. 返回主菜单")
        
        choice = input("  请选择 (1-4): ").strip()
        
        if choice == "1":
            return True
        elif choice == "2":
            self.saver.save_game(self.board, self.players, self.current_player_index, 
                               self.game_type, self.difficulty)
            input("  按 Enter 键继续游戏...")
            return True
        elif choice == "3":
            # 当前玩家认输
            winner = self.players[1 - self.current_player_index]
            print(f"  {self.current_player.name} 认输！")
            print(f"  恭喜 {winner.name} ({winner.symbol}) 获胜！")
            return False
        elif choice == "4":
            self.is_paused = True
            return False
        else:
            print("  无效的选择，继续游戏")
            return True

    def play(self):
        """游戏主循环"""
        print("\n" + "="*50)
        print("  欢迎来到五子棋游戏增强版！")
        print("="*50)
        
        while True:
            # 设置游戏
            if not self.setup_game():
                break
            
            self.is_paused = False
            game_start_time = time.time()
            
            while not self.is_paused:
                # 显示棋盘
                self.board.display()
                
                player = self.current_player
                print(f"  当前回合: {player.name} ({player.symbol})")
                print(f"  已落子数: {self.board.move_count}")
                print(f"  游戏模式: {self.game_type}")
                if self.difficulty:
                    print(f"  难度级别: {self.difficulty}")
                print()
                print("  输入 'menu' 打开游戏菜单")
                print("  输入 'undo' 撤销上一步（仅限双人对战）")
                
                # 获取玩家落子
                move = player.get_move(self.board)
                
                # 处理菜单命令
                if move is None and isinstance(player, HumanPlayer):
                    # 人类玩家输入了quit
                    print(f"  {player.name} 认输！")
                    winner = self.players[1 - self.current_player_index]
                    print(f"  恭喜 {winner.name} ({winner.symbol}) 获胜！")
                    break
                
                # 处理撤销
                if isinstance(move, str) and move == "undo":
                    if self.game_type == "human_vs_human" and self.board.move_history:
                        undone = self.board.undo_move()
                        if undone:
                            self.switch_player()  # 切换到上一步的玩家
                            print(f"  已撤销 {self.current_player.name} 的最后一步棋")
                            input("  按 Enter 键继续...")
                            continue
                    else:
                        print("  撤销功能仅限双人对战模式使用")
                        input("  按 Enter 键继续...")
                        continue
                
                # 处理菜单
                if isinstance(move, str) and move == "menu":
                    if not self.show_game_menu():
                        break
                    continue
                
                # 落子
                row, col = move
                self.board.place_stone(row, col, player.stone)
                
                # 检查是否获胜
                if self.board.check_winner(row, col):
                    self.board.display()
                    print(f"  恭喜 {player.name} ({player.symbol}) 获胜！")
                    print(f"  最后落子位置: ({row}, {col})")
                    print(f"  总共落子数: {self.board.move_count}")
                    
                    # 记录游戏结果
                    player_names = [p.name for p in self.players]
                    self.stats.record_game(self.game_type, player.name, 
                                         player_names, self.board.move_count, 
                                         self.difficulty)
                    break
                
                # 检查是否平局
                if self.board.is_full():
                    self.board.display()
                    print("  棋盘已满，平局！")
                    
                    # 记录游戏结果
                    player_names = [p.name for p in self.players]
                    self.stats.record_game(self.game_type, None, 
                                         player_names, self.board.move_count, 
                                         self.difficulty)
                    break
                
                # 切换玩家
                self.switch_player()
            
            # 游戏结束，询问是否继续
            if not self.is_paused:
                print("\n" + "="*50)
                print("  游戏结束")
                print("="*50)
            
            choice = input("\n  是否返回主菜单？(y/n): ").strip().lower()
            if choice != 'y':
                break
            
            # 重置游戏状态
            self.board = Board()
            self.players = []
            self.current_player_index = 0
            self.game_type = ""
            self.difficulty = None
        
        print("\n  感谢游玩五子棋游戏增强版！\n")


def main():
    """程序入口"""
    game = GomokuGame()
    game.play()


if __name__ == "__main__":
    main()