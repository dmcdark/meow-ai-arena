"""Browser-controlled Bomberman duel. Uses the official engine and bot protocol."""
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import secrets
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
ENGINE = ROOT / 'workspace' / 'engine'
sys.path.insert(0, str(ENGINE))
from engine import Game, config_for, DIRS
from arena import ProcessBot

CACHE = ROOT / '.build' / 'human-play'
SOURCES = {p.stem: p for p in sorted((ROOT / 'bots').glob('*.cpp'))}
SOURCES['baseline'] = ROOT / 'workspace' / 'baseline.cpp'
MOVE_MS = 50
INIT_MS = 2000


def executable(source):
    digest = hashlib.sha1(source.read_bytes()).hexdigest()[:12]
    suffix = '.exe' if sys.platform == 'win32' else ''
    return CACHE / f'{source.stem}_{digest}{suffix}'


def prepare_bot(source):
    exe = executable(source)
    if not exe.is_file():
        CACHE.mkdir(parents=True, exist_ok=True)
        subprocess.run([sys.executable, str(ENGINE / 'build.py'), '--compile',
                        '--source', str(source), '--output', str(exe)], check=True)
    return exe


class SimpleOpponent:
    """Small time-expanded escape search; future enemy moves/bombs are not predicted."""
    def move(self, g):
        me = g.players[1]
        start = me['x'], me['y']
        enemy = g.players[0]['x'], g.players[0]['y']
        n, cfg = g.cfg.size, g.cfg
        horizon = cfg.fuse + cfg.flame_turns
        crates = [(x, y) for y, row in enumerate(g.board) for x, cell in enumerate(row) if cell == '+']
        bomb_cells = {(b['x'], b['y']) for b in g.bombs}
        can_place = start not in bomb_cells and sum(b['owner'] == 1 for b in g.bombs) < cfg.capacity
        # Reward bombs that can break a box or threaten the opponent, not random placement.
        usefulness = 0
        for d in 'UDLR':
            dx, dy = DIRS[d]
            for distance in range(1, cfg.radius + 1):
                x, y = start[0] + dx * distance, start[1] + dy * distance
                if not (0 <= x < n and 0 <= y < n) or g.board[y][x] == '#':
                    break
                if (x, y) == enemy:
                    usefulness += 2
                if g.board[y][x] == '+':
                    usefulness += 1
                    break
                if (x, y) in bomb_cells:
                    break
        best = None
        fallback = None
        for place in (0, 1):
            if place and (not can_place or not usefulness):
                continue
            shadow = g.clone()
            # A hazard forecast must continue after frozen actors die; the live game is untouched.
            shadow.over = lambda: False
            reachable = {start: None}
            for k in range(horizon):
                terrain = [row[:] for row in shadow.board]
                occupied = {(b['x'], b['y']) for b in shadow.bombs}
                if k == 0 and place:
                    occupied.add(start)
                layer = shadow.shrink_layer()
                shadow.step([('S', 0), ('S', place if k == 0 else 0)])
                flames = set(shadow.flames)
                updated = {}
                for (x, y), first in reachable.items():
                    # Shrink precedes movement, so a newly covered cell cannot be escaped this turn.
                    if min(x, y, n - 1 - x, n - 1 - y) <= layer:
                        continue
                    for direction, (dx, dy) in DIRS.items():
                        nx, ny = x + dx, y + dy
                        if not (0 <= nx < n and 0 <= ny < n):
                            continue
                        cell = nx, ny
                        if terrain[ny][nx] != '.' or min(nx, ny, n - 1 - nx, n - 1 - ny) <= layer:
                            continue
                        if cell in occupied and cell != (x, y):
                            continue
                        if cell in flames or cell == enemy:
                            continue
                        updated.setdefault(cell, first or direction)
                reachable = updated
                if k == 0 and not place and reachable:
                    fallback = next(iter(reachable.values()))
                if not reachable:
                    break
            if reachable:
                for (x, y), first in reachable.items():
                    targets = crates or [enemy]
                    distance = min(abs(x - tx) + abs(y - ty) for tx, ty in targets)
                    score = 12 * usefulness * place - distance - .05 * (abs(x - enemy[0]) + abs(y - enemy[1]))
                    if best is None or score > best[0]:
                        best = score, (first, place)
        return best[1] if best else (fallback or 'S', 0)


class Match:
    def __init__(self, opponent, seed):
        self.id = secrets.token_hex(16)
        self.opponent = opponent
        self.seed = seed
        self.last_used = time.monotonic()
        self.game = Game(seed, config_for(2))
        self.bot = None
        self.simple = SimpleOpponent()
        self.failure = None
        if opponent != 'simple':
            exe = executable(SOURCES[opponent])
            if not exe.is_file():
                raise ValueError('这个 bot 尚未编译，请先运行页面提示的编译命令。')
            self.bot = ProcessBot([str(exe)], self.game.header(1))

    def close(self):
        if self.bot:
            self.bot.close()
            self.bot = None

    def snapshot(self):
        g = self.game
        result = g.result()
        done = g.over()
        outcome = None
        if done:
            ranks = result['ranks']
            outcome = '平局' if ranks[0] == ranks[1] else '你获胜' if ranks[0] < ranks[1] else '电脑获胜'
        return dict(g.snapshot(), id=self.id, seed=self.seed, opponent=self.opponent,
                    config=result['config'], done=done, result=outcome, failure=self.failure,
                    points=result['points'], ranks=result['ranks'], kill_credit=result['kill_credit'])

    def step(self, direction, place):
        self.last_used = time.monotonic()
        if self.game.over():
            return self.snapshot()
        forfeits = []
        if self.bot:
            b = self.bot
            b.send(self.game.state_text())
            other, error, _ = b.receive(self.game.turn, INIT_MS if self.game.turn == 0 else MOVE_MS)
            if error:
                self.failure = f'对手程序判负：{error}'
                forfeits.append(1)
                other = ('S', 0)
        else:
            other = self.simple.move(self.game)
        # A bot failure still completes all stages of this turn, as in the official referee.
        self.game.step([(direction, place), other], forfeits)
        if self.game.over() or not self.game.players[1]['alive']:
            self.close()
        return self.snapshot()


class Server(HTTPServer):
    def __init__(self, port):
        super().__init__(('127.0.0.1', port), Handler)
        self.token = secrets.token_hex(32)
        self.match = None
        self.timeout = 1

    def expire(self):
        if self.match and time.monotonic() - self.match.last_used > 600:
            self.match.close()
            self.match = None


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, data, content_type='application/json; charset=utf-8'):
        raw = json.dumps(data, ensure_ascii=False).encode() if content_type.startswith('application/json') else data
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.end_headers()
        self.wfile.write(raw)

    def allowed(self):
        port = self.server.server_address[1]
        hosts = (f'127.0.0.1:{port}', f'localhost:{port}')
        origin = self.headers.get('Origin')
        return self.headers.get('Host') in hosts and (not origin or origin in [f'http://{h}' for h in hosts])

    def do_GET(self):
        if not self.allowed():
            return self.reply(403, {'error': '请通过本地地址访问。'})
        if self.path == '/api/config':
            return self.reply(200, dict(token=self.server.token, opponents=[
                dict(id='simple', name='简单电脑', ready=True),
                *[dict(id=k, name=k, ready=executable(p).is_file()) for k, p in SOURCES.items()]]))
        if self.path in ('/', '/index.html'):
            return self.reply(200, (ROOT / 'play' / 'index.html').read_bytes(), 'text/html; charset=utf-8')
        self.reply(404, {'error': '没有这个页面。'})

    def do_POST(self):
        if not self.allowed() or self.headers.get('X-Game-Token') != self.server.token:
            return self.reply(403, {'error': '访问令牌无效，请刷新页面。'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 4096:
                raise ValueError('请求大小无效。')
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError('请求格式无效。')
            if self.path == '/api/new':
                opponent = data.get('opponent', 'simple')
                if opponent != 'simple' and opponent not in SOURCES:
                    raise ValueError('未知对手。')
                seed = data.get('seed', 1000)
                if type(seed) is not int or not 0 <= seed <= 2147483647:
                    raise ValueError('地图种子应为 0 到 2147483647 的整数。')
                # Construct first, so a missing executable does not destroy the current match.
                match = Match(opponent, seed)
                if self.server.match:
                    self.server.match.close()
                self.server.match = match
                return self.reply(200, match.snapshot())
            if self.path not in ('/api/step', '/api/close'):
                return self.reply(404, {'error': '未知操作。'})
            match = self.server.match
            if not match or data.get('id') != match.id:
                return self.reply(409, {'error': '对局已过期或被另一标签页替换，请开始新对局。'})
            if self.path == '/api/close':
                match.close()
                self.server.match = None
                return self.reply(200, {'ok': True})
            if data.get('turn') != match.game.turn:
                return self.reply(409, {'error': '回合不同步，请开始新对局。'})
            direction = data.get('direction')
            if direction not in DIRS:
                raise ValueError('方向无效。')
            place = data.get('place', 0)
            if type(place) is not int or place not in (0, 1):
                raise ValueError('放弹标记无效。')
            self.reply(200, match.step(direction, place))
        except (ValueError, TypeError) as error:
            self.reply(400, {'error': str(error)})
        except (OSError, RuntimeError) as error:
            self.reply(500, {'error': str(error)})

    def log_message(self, *_):
        pass


def main():
    parser = argparse.ArgumentParser(description='浏览器手动炸弹人对战（无需额外 Python 包）')
    parser.add_argument('--port', type=int, default=8767)
    parser.add_argument('--list-bots', action='store_true')
    parser.add_argument('--prepare-bots', nargs='+', choices=sorted(SOURCES), metavar='BOT_ID',
                        help='显式编译指定原版 bot，完成后退出；启动服务不会自动编译')
    args = parser.parse_args()
    if args.list_bots:
        print('\n'.join(SOURCES))
        return
    if args.prepare_bots:
        for name in args.prepare_bots:
            print(f'编译 {name} …', flush=True)
            print(prepare_bot(SOURCES[name]))
        return
    server = Server(args.port)
    print(f'打开 http://127.0.0.1:{server.server_address[1]} ，Ctrl+C 停止服务。', flush=True)
    try:
        while True:
            server.handle_request()
            server.expire()
    except KeyboardInterrupt:
        print('\n已停止。')
    finally:
        if server.match:
            server.match.close()
        server.server_close()


if __name__ == '__main__':
    main()
