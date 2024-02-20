import time
from twisted.internet import reactor
from piqueserver.map import RotationInfo

# 147ms 623
def apply_script(protocol, connection, config):
    class AimbotDetectProtocol(protocol):

        async def set_map_name(self, rot_info: RotationInfo) -> None:
            rot_info.name = 'lostvalleyarena'
            await protocol.set_map_name(self, rot_info)

        def on_map_change(self, map):
            print("=== AStart benchmark ===")
            sum = 0
            for _ in range(0, 10):
                start = time.monotonic()
                res = map.a_star_start(0, 0, 20, 511, 511, 20, False, False).get()
                end = time.monotonic()-start
                print('%i ms' % (end * 1000))
                sum += end
            print("========================")
            print("AVG TIME: %i ms" % (sum * 100))
            print("PATH COST: %i" % len(res))
            print("========================")
            for b in res:
                map.set_point(b[0], b[1], b[2], (255, 0, 0))
            #reactor.stop()

    return AimbotDetectProtocol, connection