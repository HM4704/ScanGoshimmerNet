from dataclasses import dataclass

@dataclass
class NodeInfo:
    shortId: str = ""
    ip: str = ""
    synced: bool = False
    enabledAPI: bool = False
    att: int = 0
    version: str = ""
    indexer: bool = False