from dataclasses import dataclass

@dataclass
class NodeInfo:
    shortId: str = ""
    ip: str = ""
    synced: bool = False
    enabledAPI: bool = False
    accessMana: int = 0
    att: int = 0
    version: str = ""
    indexer: bool = False