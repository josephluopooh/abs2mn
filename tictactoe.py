import socket
from functools import cache
import os

from cachelib import FileSystemCache

import utils

BOARD_SIZE_TTT = 3
CACHE_DIR = os.getcwd() + ("\\.cache" if os.name == "nt" else "/.cache") # check os library for this

best_move_cache = FileSystemCache(CACHE_DIR, 0, 0)


class TicTacToeGame(utils.Game):
    def __init__(
        self,
        terminal_screen: utils.TerminalScreen,
        board: list[list[str | None]],
        current_player: utils.Player,
        player_a: utils.Player,
        player_b: utils.Player,
    ):
        utils.Game.__init__(
            self, terminal_screen, board, current_player, player_a, player_b
        )
        self.generating_moves_funcs = [
            self.get_move,
            self.generate_random_move_bot,
            self.minimax_pruning_with_cache_bot,
        ]

    def is_winning(self) -> bool:
        return _find_winner(self.board)

    def is_draw(self) -> bool:
        return _is_draw_state(self.board)

    def get_legal_moves(self) -> list[tuple[int, int]]:
        return _get_legal_moves(self.board)

    def make_move(self, move: tuple[int, int]) -> None:
        self.board = _make_move(self.board, move, self.is_maximizing_players_turn)

    def minimax_pruning_with_cache_bot(self) -> tuple[int, int]:
        cache_key = utils.get_cache_key(
            self.board, _get_player_mark(self.is_maximizing_players_turn)
        )
        best_move = utils.get_from_cache(best_move_cache, cache_key)
        if not best_move:
            print(f"CACHE NOT FOUND FOR {cache_key}!")
            legal_moves = _get_legal_moves(self.board)
            best_move = utils.random_choice(legal_moves)
            best_move_score = _minimax_score_pruning(
                _make_move(self.board, best_move, self.is_maximizing_players_turn),
                not self.is_maximizing_players_turn,
                None,
            )
            for move in legal_moves:
                current_move_score = _minimax_score_pruning(
                    _make_move(self.board, move, self.is_maximizing_players_turn),
                    not self.is_maximizing_players_turn,
                    best_move_score,
                )
                if (
                    self.is_maximizing_players_turn
                    and current_move_score > best_move_score
                ) or (
                    not self.is_maximizing_players_turn
                    and current_move_score < best_move_score
                ):
                    best_move, best_move_score = move, current_move_score
            best_move_cache.set(cache_key, best_move)
        return best_move

    def get_move(self) -> tuple[int, int]:
        move = None
        legal_moves = self.get_legal_moves()
        while move == None or move not in legal_moves:
            if move:
                self.terminal_screen.show_info_message(
                    "Invalid move, please type another one."
                )
            try:
                ascii_input = self.terminal_screen.get_ascii_input(
                    f'What\'s your("{_get_player_mark(self.is_maximizing_players_turn)}"\'s) next move? Format: "<x> <y>" like "1 2".'
                )
                x, y = ascii_input.split(" ")
                move = (int(x), int(y))
            except ValueError:
                self.terminal_screen.show_info_message(
                    'Wrong format. Please input "<x> <y>" like "1 2".'
                )
                continue
        return move

    def generate_random_move_bot(self) -> tuple[int, int]:
        return utils.random_choice(self.get_legal_moves())


class OnlineTicTacToeGame(TicTacToeGame, utils.OnlineGame):
    def __init__(
        self,
        terminal_screen: utils.TerminalScreen,
        board: list[list[str | None]],
        current_player: utils.Player,
        player_a: utils.Player,
        player_b: utils.Player,
        gaming_sock: socket.socket,
        playing_as_host: bool,
        _waiting_sock: socket.socket = None,
    ):
        TicTacToeGame.__init__(
            self, terminal_screen, board, current_player, player_a, player_b
        )
        utils.OnlineGame.__init__(self, gaming_sock, playing_as_host, _waiting_sock)


# "x": maximizing player
# "o": minimizing player
def _get_player_mark(is_maximizing_players_turn: bool) -> str:
    return "x" if is_maximizing_players_turn else "o"


def _get_legal_moves(board: tuple[tuple[str | None]]) -> list[tuple[int, int]]:
    return [
        (x, y)
        for y in range(len(board))
        for x in range(len(board[y]))
        if not board[y][x]
    ]


def _make_move(
    board: tuple[tuple[str | None]],
    move: tuple[int, int] | str,
    is_maximizing_players_turn: int,
) -> tuple[tuple[str | None]]:
    if type(move) == str:
        move = (int(move[0]), int(move[1]))
    new_board = tuple(
        tuple(
            _get_player_mark(is_maximizing_players_turn)
            if x == move[0] and y == move[1]
            else mark
            for x, mark in enumerate(row)
        )
        for y, row in enumerate(board)
    )
    return new_board


def _find_winner(board: tuple[tuple[str | None]]) -> str | None:
    def check_line(line: list[str | None]) -> bool:
        return line[0] and len(set(line)) == 1

    lines = []
    for row in board:
        lines.append(list(row))
    for i in range(BOARD_SIZE_TTT):
        lines.append([board[j][i] for j in range(BOARD_SIZE_TTT)])
    lines.append([board[j][j] for j in range(BOARD_SIZE_TTT)])
    lines.append([board[j][BOARD_SIZE_TTT - 1 - j] for j in range(BOARD_SIZE_TTT)])

    for line in lines:
        if check_line(line):
            return line[0]
    return None


def _is_draw_state(board: tuple[tuple[str | None]]) -> bool:
    return all([cell for row in board for cell in row])


@cache
def _minimax_score_pruning(
    board: tuple[tuple[str | None]],
    is_maximizing_players_turn: bool,
    threshold: int | None,
) -> int:
    winner = _find_winner(board)
    if winner:
        return 1 if winner == "x" else -1
    if _is_draw_state(board):
        return 0

    legal_moves = _get_legal_moves(board)
    current_best_score = None
    for move in legal_moves:
        new_board = _make_move(board, move, is_maximizing_players_turn)
        score = _minimax_score_pruning(
            new_board,
            not is_maximizing_players_turn,
            current_best_score,
        )
        if threshold != None and (
            (is_maximizing_players_turn and score >= threshold)
            or (not is_maximizing_players_turn and score <= threshold)
        ):
            current_best_score = score
            break
        if current_best_score == None:
            current_best_score = score
        else:
            current_best_score = (
                max(current_best_score, score)
                if is_maximizing_players_turn
                else min(current_best_score, score)
            )

    return current_best_score
