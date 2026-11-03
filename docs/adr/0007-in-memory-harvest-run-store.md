# ADR 0007: In-memory harvest run and session state

## Status

Accepted

## Context

Harvest validation is **long-running** (three sequential phases, many HTTP requests to the target registry). The legacy servlet model used **server sessions** (`JSESSIONID`, `runid` query parameters) to hold partial results and poll status.

Benson exposes both the legacy-compatible harvest API and a newer **job** API (`POST /validator/jobs`, status/result URLs). Runs accumulate large XML trees and optional harvested resource bytes before the client fetches results.

## Decision

Store active harvest runs in a **process-local in-memory store** (`benson.session.store`: `HarvestRun` dataclass, global `store` with asyncio locks). Background work uses **`asyncio.Task`** via `benson.service.validation_job` and `harvest_runner`.

There is no Redis, database, or shared filesystem session backend in the default deployment.

## Consequences

- **Positive:** Simple deployment (single container, no extra infrastructure); matches “one validator instance” usage for RoFR operations.
- **Positive:** Async locks protect progress updates while phases run concurrently with status polling.
- **Negative:** **Restarts drop in-flight runs**; horizontal scaling requires sticky sessions or a future ADR for external run storage.
- **Negative:** Memory use grows with phase 3 harvested resources; limits such as `maxVORInclude` behaviour are parity-sensitive ([regvalidate-parity-notes.md](../regvalidate-parity-notes.md)).
- **Neutral:** Clients should treat `run_id` as valid only on the instance that created it unless a shared store is introduced later.
