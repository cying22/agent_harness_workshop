#!/usr/bin/env python3
"""
五子棋小游戏（Gomoku）
- 15x15 棋盘，命令行界面
- 双人对战模式：黑棋(●) 和 白棋(○) 轮流下棋
- 支持胜负判定、输入验证、认输等功能
"""

import os


class Board:
    """棋盘类，负责棋盘的状态管理和显示"""

    # 棋盘大小
    SIZE = 15

    # 棋子常量
    EMPTY = 0
    BLACK = 1
    WHITE = 2

    # 棋子显示符号
    # 注意：●和○在终端中为全角宽度（占2列），空位使用中点·（半角，占1列）
    SYMBOLS = {
        EMPTY: "·",
        BLACK: "●",
        WHITE: "○",
    }

    def __init__(self):
        """初始化空棋盘"""
        self.grid = [[self.EMPTY] * self.SIZE for _ in range(self.SIZE)]
        self.move_count = 0  # 记录已落子数

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
        return True

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
    """玩家类，记录玩家信息"""

    def __init__(self, name: str, stone: int):
        """
        初始化玩家
        :param name: 玩家名称
        :param stone: 棋子类型（Board.BLACK 或 Board.WHITE）
        """
        self.name = name
        self.stone = stone
        self.symbol = Board.SYMBOLS[stone]


class GomokuGame:
    """五子棋游戏主控类，负责游戏流程管理"""

    def __init__(self):
        """初始化游戏"""
        self.board = Board()
        self.players = [
            Player("黑棋玩家", Board.BLACK),
            Player("白棋玩家", Board.WHITE),
        ]
        self.current_player_index = 0  # 黑棋先手

    @property
    def current_player(self) -> Player:
        """获取当前回合的玩家"""
        return self.players[self.current_player_index]

    def switch_player(self):
        """切换到下一位玩家"""
        self.current_player_index = 1 - self.current_player_index

    def parse_input(self, user_input: str) -> tuple:
        """
        解析用户输入
        :param user_input: 用户输入的字符串
        :return: (row, col) 元组，或 None 表示退出，或 False 表示无效输入
        """
        stripped = user_input.strip().lower()

        # 检查是否认输/退出
        if stripped in ("quit", "q", "exit"):
            return None

        # 尝试解析坐标
        parts = stripped.split()
        if len(parts) != 2:
            print("  [错误] 请输入两个数字，用空格分隔（如: 7 7）")
            return False

        try:
            row, col = int(parts[0]), int(parts[1])
        except ValueError:
            print("  [错误] 请输入有效的数字坐标")
            return False

        # 验证坐标范围
        if not self.board.is_valid_position(row, col):
            print(f"  [错误] 坐标超出范围，行和列必须在 0~{Board.SIZE - 1} 之间")
            return False

        # 验证位置是否已有棋子
        if not self.board.is_empty(row, col):
            print("  [错误] 该位置已有棋子，请选择其他位置")
            return False

        return (row, col)

    def play(self):
        """游戏主循环"""
        print("\n" + "=" * 50)
        print("  欢迎来到五子棋游戏！")
        print("  规则：双方轮流落子，先连成5子者获胜")
        print("  输入格式：行 列（如 7 7 表示第7行第7列）")
        print("  输入 quit 认输退出")
        print("=" * 50)
        input("\n  按 Enter 键开始游戏...")

        while True:
            # 显示棋盘
            self.board.display()

            player = self.current_player
            print(f"  当前回合: {player.name} ({player.symbol})")
            print(f"  已落子数: {self.board.move_count}")

            # 获取玩家输入
            user_input = input(f"  请 {player.name} 输入坐标（行 列）: ")
            result = self.parse_input(user_input)

            # 处理退出
            if result is None:
                self.board.display()
                print(f"  {player.name} 认输！")
                opponent = self.players[1 - self.current_player_index]
                print(f"  恭喜 {opponent.name} ({opponent.symbol}) 获胜！\n")
                break

            # 处理无效输入，重新输入
            if result is False:
                input("  按 Enter 继续...")
                continue

            # 落子
            row, col = result
            self.board.place_stone(row, col, player.stone)

            # 检查是否获胜
            if self.board.check_winner(row, col):
                self.board.display()
                print(f"  恭喜 {player.name} ({player.symbol}) 获胜！")
                print(f"  最后落子位置: ({row}, {col})")
                print(f"  总共落子数: {self.board.move_count}\n")
                break

            # 检查是否平局
            if self.board.is_full():
                self.board.display()
                print("  棋盘已满，平局！\n")
                break

            # 切换玩家
            self.switch_player()

        print("  游戏结束，感谢游玩！\n")


def main():
    """程序入口"""
    game = GomokuGame()
    game.play()


if __name__ == "__main__":
    main()
