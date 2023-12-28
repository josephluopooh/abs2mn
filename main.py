import curses
import argparse
import sys
from time import sleep

import utils
from tictactoe import TicTacToeGame, OnlineTicTacToeGame

REPEAT_TIMES = 10000
GAMEEND_TIMEOUT = 1000
BOT_NUM = BOARD_SIZE = 3
INFO_LINE_NUM_START = BOARD_SIZE + 4


# Do I need a separate class for move?
def do_pre_calculations() -> None:
    def calculate_and_cache_for_state(
        board: list[list[str | None]], is_maximizing_players_turn
    ) -> None:
        player_a = utils.Player("x", bot_type=2)
        player_b = utils.Player("o", bot_type=2)
        game = TicTacToeGame(
            None,
            board,
            player_a if is_maximizing_players_turn else player_b,
            player_a,
            player_b,
        )
        game.minimax_pruning_with_cache_bot()
        for valid_move in game.get_legal_moves():
            game.board = board  # reset board set by previous move
            game.make_move(valid_move)
            if game.is_winning() or game.is_draw():
                continue
            calculate_and_cache_for_state(game.board, not is_maximizing_players_turn)

    calculate_and_cache_for_state(utils.create_board(BOARD_SIZE), True)


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Play the selected abstract board game over the internet or against the bot."
    )
    parser.add_argument(
        "-o", "--online", action="store_true", help="play the game online"
    )
    parser.add_argument(
        "-c",
        "--compare_bots",
        dest="bots_type",
        type=int,
        default=00,
        help=f"compare two bots by playing {REPEAT_TIMES} games",
    )
    parser.add_argument(
        "-p",
        "--pre_calculation",
        action="store_true",
        help="do the calculations for all possible board states to speed up the bot",
    )
    return parser.parse_args()


def run_game(
    window: curses.window, info_line_num_start: int, bot_num: int, board_size: int
) -> None:
    terminal_screen = utils.TerminalScreen(window, info_line_num_start)
    game = utils.initialize_game(
        terminal_screen, args, TicTacToeGame, OnlineTicTacToeGame, bot_num, board_size
    )

    game.render()
    while True:
        game.make_a_move_from_current_player()
        game.render()
        if game.is_winning():
            terminal_screen.show_info_message(
                f'Winner is "{game.current_player.mark}"!'
            )
            break
        if game.is_draw():
            terminal_screen.show_info_message("It's a draw!")
            break
        game.take_turn()

    game.close()  # close socket
    sleep(GAMEEND_TIMEOUT)


if __name__ == "__main__":
    args = get_args()

    if args.bots_type:
        bot_type_one = args.bots_type // 10
        bot_type_two = args.bots_type % 10
        if bot_type_one not in range(1, BOT_NUM) or bot_type_two not in range(
            1, BOT_NUM
        ):
            print("Wrong bot type!")
            sys.exit(1)
        utils.repeat_games(
            bot_type_one, bot_type_two, TicTacToeGame, BOARD_SIZE, REPEAT_TIMES
        )
    elif args.pre_calculation:
        do_pre_calculations()
        pass
    else:
        curses.wrapper(run_game, INFO_LINE_NUM_START, BOT_NUM, BOARD_SIZE)
