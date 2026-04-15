#!/usr/bin/env python3
"""
五子棋增强版功能演示
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("五子棋增强版功能演示")
print("="*50)

from gomoku_enhanced import Board, HumanPlayer, AIPlayer, GameStatistics, GameSaver

def demo_board():
    """演示棋盘功能"""
    print("\n1. 棋盘功能演示")
    print("-"*30)
    
    board = Board()
    print("创建空棋盘...")
    print(f"棋盘大小: {Board.SIZE}x{Board.SIZE}")
    print(f"初始落子数: {board.move_count}")
    
    # 演示落子
    print("\n演示落子...")
    board.place_stone(7, 7, Board.BLACK)
    board.place_stone(7, 8, Board.WHITE)
    print(f"落子后棋子数: {board.move_count}")
    print(f"位置(7,7)的棋子: {Board.SYMBOLS[board.grid[7][7]]}")
    print(f"位置(7,8)的棋子: {Board.SYMBOLS[board.grid[7][8]]}")
    
    # 演示胜负判定
    print("\n演示胜负判定...")
    test_board = Board()
    for i in range(5):
        test_board.place_stone(7, 7 + i, Board.BLACK)
    print(f"五连棋是否获胜: {test_board.check_winner(7, 7)}")

def demo_players():
    """演示玩家功能"""
    print("\n2. 玩家功能演示")
    print("-"*30)
    
    # 人类玩家
    human = HumanPlayer("张三", Board.BLACK)
    print(f"人类玩家: {human.name}, 棋子: {human.symbol}")
    
    # AI玩家
    ai_easy = AIPlayer("AI简单", Board.WHITE, "easy")
    ai_medium = AIPlayer("AI中等", Board.WHITE, "medium")
    ai_hard = AIPlayer("AI困难", Board.WHITE, "hard")
    
    print(f"AI简单玩家: {ai_easy.name}, 难度: {ai_easy.difficulty}")
    print(f"AI中等玩家: {ai_medium.name}, 难度: {ai_medium.difficulty}")
    print(f"AI困难玩家: {ai_hard.name}, 难度: {ai_hard.difficulty}")

def demo_statistics():
    """演示统计功能"""
    print("\n3. 游戏统计功能演示")
    print("-"*30)
    
    # 使用临时文件进行演示
    stats = GameStatistics("demo_stats.json")
    
    # 记录一些游戏
    print("记录游戏结果...")
    stats.record_game("human_vs_human", "玩家A", ["玩家A", "玩家B"], 30)
    stats.record_game("human_vs_ai", "AI玩家", ["玩家", "AI玩家"], 25, "medium")
    stats.record_game("human_vs_human", None, ["玩家1", "玩家2"], 40)
    
    print(f"总游戏数: {stats.stats['total_games']}")
    print(f"双人对战胜局: {stats.stats['human_vs_human']['wins']}")
    print(f"双人对战平局: {stats.stats['human_vs_human']['draws']}")
    
    # 显示统计
    print("\n显示统计信息:")
    stats.display_stats()
    
    # 清理演示文件
    if os.path.exists("demo_stats.json"):
        os.remove("demo_stats.json")

def demo_saver():
    """演示保存功能"""
    print("\n4. 游戏保存功能演示")
    print("-"*30)
    
    # 使用临时目录进行演示
    saver = GameSaver("demo_saves")
    
    # 创建测试游戏状态
    board = Board()
    board.place_stone(7, 7, Board.BLACK)
    board.place_stone(7, 8, Board.WHITE)
    
    players = [
        HumanPlayer("玩家1", Board.BLACK),
        AIPlayer("AI玩家", Board.WHITE, "medium")
    ]
    
    print("保存游戏...")
    result = saver.save_game(board, players, 0, "human_vs_ai", "medium")
    print(f"保存结果: {'成功' if result else '失败'}")
    
    # 列出保存的游戏
    print("\n列出保存的游戏:")
    saver.list_saves()
    
    # 清理演示目录
    import shutil
    if os.path.exists("demo_saves"):
        shutil.rmtree("demo_saves")

def demo_ai_moves():
    """演示AI落子"""
    print("\n5. AI落子功能演示")
    print("-"*30)
    
    board = Board()
    board.place_stone(7, 7, Board.BLACK)
    board.place_stone(7, 8, Board.WHITE)
    
    ai_easy = AIPlayer("AI简单", Board.BLACK, "easy")
    ai_hard = AIPlayer("AI困难", Board.WHITE, "hard")
    
    print("当前棋盘状态:")
    print(f"位置(7,7): {Board.SYMBOLS[board.grid[7][7]]}")
    print(f"位置(7,8): {Board.SYMBOLS[board.grid[7][8]]}")
    
    print("\nAI简单选择落子位置...")
    move1 = ai_easy.get_move(board)
    print(f"AI简单选择: ({move1[0]}, {move1[1]})")
    
    print("\nAI困难选择落子位置...")
    move2 = ai_hard.get_move(board)
    print(f"AI困难选择: ({move2[0]}, {move2[1]})")

def main():
    """主演示函数"""
    print("开始演示五子棋增强版功能...")
    
    demo_board()
    demo_players()
    demo_statistics()
    demo_saver()
    demo_ai_moves()
    
    print("\n" + "="*50)
    print("演示完成！")
    print("="*50)
    print("\n要体验完整功能，请运行:")
    print("  python gomoku_enhanced.py")

if __name__ == "__main__":
    main()