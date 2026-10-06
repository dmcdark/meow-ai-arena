"""Human vs computer, using the official land rules. Python standard library only."""
import argparse
from collections import deque
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import secrets
import sys
import time

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'workspace' / 'engine'))
from game import Game, config_for, make_start, DIRS, OPPOSITE
from referee import Bot, MOVE_MS, INIT_MS, MAX_ERRORS
import build

CACHE = ROOT / '.build' / 'human-play'
SOURCES = {p.parent.name: p for p in sorted((ROOT / 'bots').glob('*/bot.cpp'))}
SOURCES.update({f'anchor-{p.stem}': p for p in sorted((ROOT / 'workspace' / 'anchors').glob('*.cpp'))})


def executable(source):
    digest = hashlib.sha1(source.read_bytes()).hexdigest()[:12]
    suffix = '.exe' if sys.platform == 'win32' else ''
    return CACHE / f'{source.stem}_{digest}{suffix}'


class SimpleOpponent:
    """Plan small rectangles; if interrupted, search for a safe route home."""
    def __init__(self):
        self.plan = deque()
        self.deaths = 0

    def move(self, g):
        i = 1
        if g.deaths[i] != self.deaths:
            self.plan.clear()
            self.deaths = g.deaths[i]
        x, y = g.pos[i]

        def advance(x, y, direction):
            dx, dy = DIRS[direction]
            nx, ny = x + dx, y + dy
            if not (0 <= nx < g.W and 0 <= ny < g.H):
                return None
            k = ny * g.W + nx
            if g.trail[k] == i or (nx, ny) == g.pos[0]:
                return None
            return nx, ny

        if self.plan:
            d = self.plan[0]
            if d != OPPOSITE[g.dir[i]] and advance(x, y, d):
                return self.plan.popleft()
            self.plan.clear()
        if g.owner[y * g.W + x] == i:
            best = None
            for d in DIRS:
                if d == OPPOSITE[g.dir[i]]:
                    continue
                for e in DIRS:
                    if e in (d, OPPOSITE[d]):
                        continue
                    for size in (3, 5, 7):
                        path = [d] * size + [e] * size + [OPPOSITE[d]] * size + [OPPOSITE[e]] * size
                        px, py = x, y
                        visited = set()
                        valid = True
                        for direction in path:
                            pos = advance(px, py, direction)
                            if pos is None:
                                valid = False
                                break
                            px, py = pos
                            k = py * g.W + px
                            if k in visited or g.protected[k] == 0:
                                valid = False
                                break
                            visited.add(k)
                        if valid:
                            dx, dy = DIRS[d]
                            ex, ey = DIRS[e]
                            score = sum(g.owner[(y + dy * a + ey * b) * g.W + x + dx * a + ex * b] != i
                                        for a in range(size + 1) for b in range(size + 1))
                            if best is None or score > best[0]:
                                best = score, path
            if best and best[0] > 0:
                self.plan.extend(best[1])
                return self.plan.popleft()
        # BFS includes heading because the engine forbids a 180-degree turn.
        queue = deque([(x, y, g.dir[i], None)])
        seen = {(x, y, g.dir[i])}
        fallback = None
        while queue:
            px, py, heading, first = queue.popleft()
            for d in DIRS:
                if d == OPPOSITE[heading]:
                    continue
                pos = advance(px, py, d)
                if pos is None:
                    continue
                nx, ny = pos
                key = nx, ny, d
                if key in seen:
                    continue
                seen.add(key)
                initial = first or d
                fallback = fallback or initial
                if g.owner[ny * g.W + nx] == i:
                    return initial
                queue.append((nx, ny, d, initial))
        return fallback or g.dir[i]


class Match:
    def __init__(self, opponent, seed):
        self.id = secrets.token_hex(16)
        self.opponent = opponent
        self.seed = seed
        self.last_used = time.monotonic()
        cfg = dict(config_for(2))
        spawns, dirs = make_start(seed, cfg)
        self.game = Game(cfg, spawns, dirs)
        self.bot = None
        self.simple = SimpleOpponent()
        self.failure = None
        self.events = []
        if opponent != 'simple':
            exe = executable(SOURCES[opponent])
            if not exe.is_file():
                raise ValueError('这个 bot 尚未编译，请先运行页面提示的编译命令。')
            self.bot = Bot(str(exe))
            try:
                head = 'INIT\n%d %d %d %d %d %d %d\n' % (
                    cfg['width'], cfg['height'], cfg['max_turns'], 2, 1, MOVE_MS, INIT_MS)
                head += ''.join('SPAWN %d %d %d\n' % (j, x, y) for j, (x, y) in enumerate(spawns))
                self.bot.send(head)
            except Exception:
                self.close()
                raise

    def close(self):
        if self.bot:
            self.bot.close()
            self.bot = None

    def snapshot(self):
        g = self.game
        done = g.over() or bool(self.failure)
        areas = g.areas()
        result = None
        if done:
            result = ('你获胜（对手程序判负）' if self.failure else
                      '平局' if areas[0] == areas[1] else '你获胜' if areas[0] > areas[1] else '电脑获胜')
        return dict(id=self.id, seed=self.seed, opponent=self.opponent, width=g.W, height=g.H,
                    max_turns=g.cfg['max_turns'], turn=g.turn, owner=g.owner, trail=g.trail,
                    spawns=g.spawns, pos=g.pos, directions=g.dir, areas=areas, deaths=g.deaths,
                    kills=g.kills, events=self.events, done=done, result=result, failure=self.failure)

    def step(self, direction):
        self.last_used = time.monotonic()
        if self.game.over() or self.failure:
            return self.snapshot()
        if self.bot:
            b = self.bot
            sent_at = time.perf_counter()
            b.send(self.game.state_text(self.game.turn))
            other = b.receive(self.game.turn, sent_at, INIT_MS if self.game.turn == 0 else MOVE_MS)
            if b.crashed or b.errors >= MAX_ERRORS:
                self.events = []
                self.failure = '对手程序崩溃' if b.crashed else '对手超时或无效回复累计达到 10 次'
                self.close()
                return self.snapshot()
        else:
            other = self.simple.move(self.game)
        self.events = self.game.step([direction, other])['events']
        if self.game.over():
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
            self.reply(200, match.step(direction))
        except (ValueError, TypeError) as error:
            self.reply(400, {'error': str(error)})
        except (OSError, RuntimeError) as error:
            self.reply(500, {'error': str(error)})

    def log_message(self, *_):
        pass


def main():
    parser = argparse.ArgumentParser(description='浏览器手动圈地对战（无需额外 Python 包）')
    parser.add_argument('--port', type=int, default=8765)
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
            print(build.compile_bot(str(SOURCES[name]), str(CACHE)))
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
