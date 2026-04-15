#!/usr/bin/env python3
"""
测试五子棋增强版功能
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gomoku_enhanced import Board, HumanPlayer, AIPlayer, GameStatistics, GameSaver

def test_board():
    """测试棋盘功能"""
    print("测试棋盘功能...")
    board = Board()
    
    # 测试落子
    assert board.place_stone(7, 7, Board.BLACK) == True
    assert board.grid[7][7] == Board.BLACK
    assert board.move_count == 1
    
    # 测试重复落子
    assert board.place_stone(7, 7, Board.WHITE) == False
    assert board.move_count == 1
    
    # 测试无效位置
    assert board.place_stone(20, 20, Board.WHITE) == False
    
    # 测试胜负判定
    board = Board()
    for i in range(5):
        board.place_stone(7, 7 + i, Board.BLACK)
    assert board.check_winner(7, 7) == True
    
    print("棋盘功能测试通过！")

def test_players():
    """测试玩家功能"""
    print("\n测试玩家功能...")
    
    # 测试人类玩家
    human = HumanPlayer("测试玩家", Board.BLACK)
    assert human.name == "测试玩家"
    assert human.stone == Board.BLACK
    assert human.symbol == "●"
    
    # 测试AI玩家
    ai_easy = AIPlayer("AI简单", Board.WHITE, "easy")
    assert ai_easy.name == "AI简单"
    assert ai_easy.stone == Board.WHITE
    assert ai_easy.difficulty == "easy"
    
    ai_medium = AIPlayer("AI中等", Board.WHITE, "medium")
    assert ai_medium.difficulty == "medium"
    
    ai_hard = AIPlayer("AI困难", Board.WHITE, "hard")
    assert ai_hard.difficulty == "hard"
    
    print("玩家功能测试通过！")

def test_game_statistics():
    """测试游戏统计功能"""
    print("\n测试游戏统计功能...")
    
    stats = GameStatistics("test_stats.json")
    
    # 初始统计应为0
    assert stats.stats["total_games"] == 0
    
    # 记录游戏
    stats.record_game("human_vs_human", "玩家1", ["玩家1", "玩家2"], 30)
    assert stats.stats["total_games"] == 1
    assert stats.stats["human_vs_human"]["wins"] == 1
    
    # 记录平局
    stats.record_game("human_vs_ai", None, ["玩家", "AI"], 25, "medium")
    assert stats.stats["total_games"] == 2
    assert stats.stats["human_vs_ai"]["draws"] == 1
    
    # 清理测试文件
    if os.path.exists("test_stats.json"):
        os.remove("test_stats.json")
    
    print("游戏统计功能测试通过！")

def test_game_saver():
    """测试游戏保存功能"""
    print("\n测试游戏保存功能...")
    
    saver = GameSaver("test_saves")
    
    # 创建测试棋盘
    board = Board()
    board.place_stone(7, 7, Board.BLACK)
    board.place_stone(7, 8, Board.WHITE)
    
    # 创建测试玩家
    players = [
        HumanPlayer("玩家1", Board.BLACK),
        AIPlayer("AI玩家", Board.WHITE, "medium")
    ]
    
    # 测试保存
    result = saver.save_game(board, players, 0, "human_vs_ai", "medium")
    assert result == True
    
    # 检查保存文件是否存在
    save_files = [f for f in os.listdir("test_saves") if f.endswith('.json')]
    assert len(save_files) > 0
    
    # 清理测试目录
    import shutil
    if os.path.exists("test_saves"):
        shutil.rmtree("test_saves")
    
    print("游戏保存功能测试通过！")

def test_ai_moves():
    """测试AI落子功能"""
    print("\n测试AI落子功能...")
    
    board = Board()
    ai_easy = AIPlayer("AI简单", Board.BLACK, "easy")
    ai_medium = AIPlayer("AI中等", Board.WHITE, "medium")
    ai_hard = AIPlayer("AI困难", Board.BLACK, "hard")
    
    # 测试简单AI
    move = ai_easy.get_move(board)
    assert move is not None
    assert 0 <= move[0] < Board.SIZE
    assert 0 <= move[1] < Board.SIZE
    
    # 测试中等AI
    move = ai_medium.get_move(board)
    assert move is not None
    
    # 测试困难AI
    move = ai_hard.get_move(board)
    assert move is not None
    
    print("AI落子功能测试通过！")

def run_all_tests():
    """运行所有测试"""
    print("开始测试五子棋增强版功能...")
    print("="*50)
    
    try:
        test_board()
        test_players()
        test_game_statistics()
        test_game_saver()
        test_ai_moves()
        
        print("\n" + "="*50)
        print("所有测试通过！")
        print("="*50)
        
    except AssertionError as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)