from adapter import Adapter
from engine.peer import Peer

class Engine(Adapter):
    def __init__(self):
        self.peers = {}

    def open_peer(self, peer_id: str) -> None:
        if peer_id not in self.peers:
            import sys
            policy = "cascade"
            if "--fk-policy" in sys.argv:
                idx = sys.argv.index("--fk-policy")
                if idx + 1 < len(sys.argv):
                    policy = sys.argv[idx + 1]
            self.peers[peer_id] = Peer(peer_id, fk_policy=policy)

    def apply_schema(self, peer_id: str, stmts: list) -> None:
        for s in stmts:
            self.peers[peer_id].execute(s)

    def execute(self, peer_id: str, sql: str, params: tuple = ()) -> None:
        self.peers[peer_id].execute(sql, params)

    def sync(self, peer_a: str, peer_b: str) -> None:
        self.peers[peer_a].sync_with(self.peers[peer_b])

    def snapshot_hash(self, peer_id: str) -> str:
        return self.peers[peer_id].snapshot_hash()

    def snapshot_state(self, peer_id: str) -> dict:
        return self.peers[peer_id].dump_tables()

    def close(self) -> None:
        for p in self.peers.values():
            p.shutdown()
