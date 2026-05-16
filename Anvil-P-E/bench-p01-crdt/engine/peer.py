from engine.crdt_store import CRDTStore
from engine.uniqueness import EscrowLog
from engine.fk_enforcer import FKEnforcer
from engine.sql_executor import SQLExecutor

class Peer:
    def __init__(self, peer_id: str, fk_policy: str = "cascade"):
        self.store = CRDTStore(peer_id, fk_policy=fk_policy)
        self.store.escrow = EscrowLog()
        self.fk_enforcer = FKEnforcer()
        self.executor = SQLExecutor(self.store, self.fk_enforcer)
        self.store.known_peers.add(peer_id)

    def execute(self, sql: str, params: tuple = ()) -> None:
        self.executor.execute(sql, params)

    def sync_with(self, other: 'Peer') -> None:
        from engine.sync import sync
        sync(self, other)

    def snapshot_hash(self) -> str:
        return self.store.snapshot_hash()

    def dump_tables(self) -> dict:
        return self.store.snapshot_state()

    def shutdown(self) -> None:
        pass

    @property
    def state_hash(self) -> str:
        return self.snapshot_hash()
