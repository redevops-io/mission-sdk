"""Adapter SPIs for the local single-node profile (design §7).

Three seams let a mission run with zero infrastructure locally and swap to real backends later. M1
wires the **event-ledger** seam concretely (in-memory, or an append-only file); the **policy** and
**RAG** seams are declared here with their intended shape and default to the runtime's native behavior
(built-in approval gates; no retrieval). Real backends fill them in M2+.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class EventLedgerBackend(Protocol):
    """Supplies the append-only event store a mission run records to (and replay reads back)."""
    def store(self): ...


class LocalEventLedger:
    """The default event ledger: in-memory, or an append-only NDJSON file when a path is given."""

    def __init__(self, path: str | None = None) -> None:
        self.path = path

    def store(self):
        from ._bootstrap import ensure_runtime
        ensure_runtime()
        from agentic_os.mission.store import EventStore
        return EventStore(self.path) if self.path else EventStore()


@runtime_checkable
class PolicyAdapter(Protocol):
    """Seam (M2): decide whether a consequential node may proceed. The local profile uses the runtime's
    native approval gates instead of an external policy backend."""
    def decide(self, request: dict) -> str: ...   # ALLOW · DENY · REQUIRE_REVIEW


@runtime_checkable
class RagAdapter(Protocol):
    """Seam (M2): reference-first retrieval — returns handles, never raw text. The local profile does
    no retrieval by default."""
    def retrieve(self, query: str) -> list: ...
