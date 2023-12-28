import os
import socket
import argparse
from time import sleep
from cachelib import FileSystemCache
from typing import Sequence, Any, Type
import curses

SERVER_PORT = 12480
RECV_SIZE = 1024


class TerminalScreen:
    refresh_interval = 0.4
    info_zone_buffer_height = 5

    def __init__(self, window: curses.window, info_line_num_start: int):
        self.window = window
        self.info_line_num_start = info_line_num_start
        self.info_line_num_offset = 0

    @property
    def current_info_line_num(self) -> int:
        return self.info_line_num_start + self.info_line_num_offset

    def show_info_message(self, message: str) -> None:
        self.window.move(self.current_info_line_num, 0)
        self.window.clrtoeol()
        self.window.addstr(self.current_info_line_num, 0, message)
        self.info_line_num_offset = (
            self.info_line_num_offset + 1
        ) % self.info_zone_buffer_height
        self.window.move(self.current_info_line_num, 0)
        self.window.refresh()
        sleep(self.refresh_interval)

    def get_ascii_input(self, prompt_message: str) -> str:
        self.show_info_message(prompt_message)
        curses.echo()
        self.window.clrtoeol()
        ascii_input = self.window.getstr(self.current_info_line_num, 0).decode("ascii")
        self.info_line_num_offset = (
            self.info_line_num_offset + 1
        ) % self.info_zone_buffer_height
        curses.noecho()
        return ascii_input

    def get_online_mode(self) -> bool:
        playing_as_host = None
        while playing_as_host == None or playing_as_host not in {0, 1}:
            if playing_as_host:
                self.show_info_message("Invalid choice, 0 for no or 1 for yes.")
            try:
                ascii_input = self.get_ascii_input(
                    "Do you want to play as the host or not? 0 for no, or 1 for yes."
                )
                playing_as_host = int(ascii_input)
            except ValueError:
                self.show_info_message("Wrong format.")
                continue
        return bool(playing_as_host)

    def get_bot_type(self, bot_range: int) -> int:
        bot_type = None
        while bot_type == None or bot_type not in range(bot_range):
            if bot_type:
                self.show_info_message("Invalid choice.")
            try:
                ascii_input = self.get_ascii_input(
                    f"Choose a bot. Range is 1~{bot_range - 1}."
                )
                bot_type = int(ascii_input)
            except ValueError:
                self.show_info_message("Wrong format.")
                continue
        return bot_type


def _random_int(width: int) -> int:
    bres = os.urandom(width)
    ires = int.from_bytes(bres, "little")
    return ires


def random_choice(seq: Sequence):
    return seq[_random_int(1) % len(seq)]


def host_the_game() -> socket.socket:
    host_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host_socket.bind(("localhost", SERVER_PORT))
    host_socket.listen(1)
    return host_socket


def connect_to_host(host_name: str) -> socket.socket:
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host_name, SERVER_PORT))
    return client_socket


def create_board(board_size: int) -> tuple[tuple[None]]:
    return tuple([tuple([None for _ in range(board_size)]) for _ in range(board_size)])


def get_cache_key(board: tuple[tuple[str | None]], player_mark: str) -> str:
    return "".join(
        [mark if mark else " " for row in board for mark in row] + [player_mark]
    )


def get_from_cache(best_move_cache: FileSystemCache, cache_key: str) -> Any:
    move = best_move_cache.get(cache_key)
    return move


class Player:
    def __init__(
        self,
        mark: str,
        bot_init_info: tuple[TerminalScreen, int] = None,
        bot_type: int = None,
    ):
        self.mark = mark  # Is it necessary? Rewrite this class TODO
        self.bot_type = (
            bot_type if bot_type else bot_init_info[0].get_bot_type(bot_init_info[1])
        )


class OnlinePlayer(Player):
    def __init__(
        self, mark: str, is_yourself: bool, bot_init_info: tuple[TerminalScreen, int]
    ):
        self.mark = mark
        self.is_yourself = is_yourself
        self._bot_type = (
            bot_init_info[0].get_bot_type(bot_init_info[1]) if is_yourself else None
        )

    @property
    def bot_type(self) -> int:
        if self.is_yourself:
            return self._bot_type
        else:
            raise AttributeError


class Game:
    def __init__(
        self,
        terminal_screen: TerminalScreen,
        board: list[list[str | None]],
        current_player: Player,
        player_a: Player,
        player_b: Player,
    ):
        self.terminal_screen = terminal_screen
        self.board = board
        self.board_size = len(self.board)
        self.current_player = current_player
        self.player_a = player_a  # max player
        self.player_b = player_b  # min player
        self.generating_moves_funcs = []

    @property
    def is_maximizing_players_turn(self) -> bool:
        return True if self.current_player == self.player_a else False

    def is_winning(self) -> bool:
        pass

    def take_turn(self) -> None:
        self.current_player = (
            self.player_a if self.current_player == self.player_b else self.player_b
        )

    def is_draw(self) -> bool:
        pass

    def render(self) -> None:
        def render_line(line: str) -> None:
            nonlocal j
            self.terminal_screen.window.addstr(j, 0, line)
            j += 1

        j = 0
        render_line("    " + " ".join([str(i) for i in range(self.board_size)]))
        render_line("   " + " ".join(["-" for _ in range(self.board_size + 1)]))
        for i, row in enumerate(self.board):
            out_str = [f"{i} | "]
            for cell in row:
                out_str.append(cell + " " if cell else "  ")
            out_str.append("|")
            render_line("".join(out_str))
        render_line("   " + " ".join(["-" for _ in range(self.board_size + 1)]))
        self.terminal_screen.window.refresh()
        sleep(self.terminal_screen.refresh_interval)

    def generate_move_from_current_player(self) -> Any:
        next_move = self.generating_moves_funcs[self.current_player.bot_type]()
        return next_move

    def close(self) -> None:
        pass

    def get_legal_moves(self) -> list[Any]:
        pass

    def make_move(self, move: Any) -> None:
        pass

    def make_a_move_from_current_player(self) -> None:
        self.make_move(self.generate_move_from_current_player())

    def minimax_pruning_with_cache_bot(self, board: tuple[tuple[str | None]]) -> Any:
        pass


class OnlineGame(Game):
    recv_size = 1024

    def __init__(
        self,
        gaming_sock: socket.socket,
        playing_as_host: bool,
        _waiting_sock: socket.socket = None,
    ):
        self.gaming_sock = gaming_sock
        self.playing_as_host = playing_as_host
        self._waiting_sock = _waiting_sock

    @property
    def waiting_sock(self) -> socket.socket:
        if self.playing_as_host:
            return self._waiting_sock
        else:
            raise AttributeError

    def close(self) -> None:
        if self.playing_as_host:
            self.waiting_sock.close()
        self.gaming_sock.close()

    def generate_move_from_current_player(self) -> Any | str:
        # Online game? Need to send the move to your opponent.
        if self.current_player.is_yourself:
            next_move = super().generate_move_from_current_player()
            self.gaming_sock.sendall(bytes(next_move))
            self.terminal_screen.show_info_message(
                "Your move has been sent to your opponent."
            )
            # decoded type
        else:
            self.terminal_screen.show_info_message("Waiting for your opponent to move.")
            next_move = self.gaming_sock.recv(self.recv_size)
            # str type
        return next_move


def play_bots(
    bot_type_one: int, bot_type_two: int, game_type_class: Type, board_size: int
) -> int:
    player_one, player_two = Player("x", bot_type=bot_type_one), Player(
        "o", bot_type=bot_type_two
    )
    game: Game = game_type_class(
        None,
        board_size,
        player_one,
        player_one,
        player_two,
    )
    while True:
        game.make_a_move_from_current_player()
        if game.is_winning():
            result = 1 if game.current_player == player_one else 2
            break
        if game.is_draw():
            result = 0
            break
        game.take_turn()

    game.close()
    return result


def repeat_games(
    bot_type_one: int,
    bot_type_two: int,
    game_type_class: Type,
    board_size: int,
    repeat_times: int,
) -> None:
    results = [0, 0, 0]
    for _ in range(repeat_times):
        results[play_bots(bot_type_one, bot_type_two, game_type_class, board_size)] += 1
    print(
        f"Games played: {repeat_times}\n"
        f"Draw: {results[0] * 100 / repeat_times}%\n"
        f"First bot winning: {results[1] * 100 / repeat_times}%\n"
        f"Second bot winning: {results[2] * 100 / repeat_times}%"
    )


def initialize_game(
    terminal_screen: TerminalScreen,
    args: argparse.Namespace,
    game_class: Type,
    online_game_class: Type,
    max_bot_index: int,
    board_size: int,
) -> Game:
    if args.online:
        playing_as_host = terminal_screen.get_online_mode()
        # host
        if playing_as_host:
            waiting_sock = host_the_game()
            terminal_screen.show_info_message("Waiting for connection.")
            gaming_sock, _ = waiting_sock.accept()
            terminal_screen.show_info_message(f"A player has joined your game!")
        # not host
        else:
            terminal_screen.show_info_message("Connecting.")
            gaming_sock = connect_to_host("localhost")
        is_yourself_player_a = True if playing_as_host else False
        player_a = OnlinePlayer(
            "x", is_yourself_player_a, (terminal_screen, max_bot_index)
        )
        player_b = OnlinePlayer(
            "o", not is_yourself_player_a, (terminal_screen, max_bot_index)
        )
        game = online_game_class(
            terminal_screen,
            create_board(board_size),
            player_a,
            player_a,
            player_b,
            gaming_sock,
            playing_as_host,
            waiting_sock if playing_as_host else None,
        )
    else:
        player_a = Player("x", (terminal_screen, max_bot_index))
        player_b = Player("o", (terminal_screen, max_bot_index))
        game = game_class(
            terminal_screen, create_board(board_size), player_a, player_a, player_b
        )
    return game
