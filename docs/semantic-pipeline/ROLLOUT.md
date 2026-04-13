# Semantic Pipeline Rollout — Design Spec

**Date:** 2026-04-13
**Authors:** krickert + Claude
**Status:** Draft for review
**Supersedes:** `plans/2026-03-28-semantic-pipeline-overhaul.md` (the scatter-gather rewrite — obsoleted by the three-step replacement)
**Technical contract:** `/work/core-services/pipestream-protos/docs/semantic-pipeline/DESIGN.md` (§1–§22; treat §21 as authoritative on hard rules, §22 as the measured pre-refactor baselines)

## 1. Purpose

This document specifies **how** the three-step semantic pipeline refactor gets rolled out. DESIGN.md already specifies **what** the new system looks like (stage contracts, invariants, config records, error semantics, performance gates). This spec defines phases, sequencing, agent work packets, merge gates, and the prerequisite tooling that has to exist before any refactor work begins.

Everything here is subordinate to DESIGN.md. If this spec and DESIGN.md conflict, DESIGN.md wins and this spec gets amended.

## 2. Why this spec exists (and not just the DESIGN.md)

DESIGN.md is a technical contract locked under review. It does not say:

- How to avoid three parallel agents stepping on each other.
- What prerequisite tooling a human-out-of-the-loop workflow actually needs.
- Where the fixtures live, who owns them, when they lock.
- What each agent gets as a self-contained prompt.
- How rollback actually works repo-by-repo.

This spec covers those. After it's approved, the `writing-plans` skill consumes it (plus DESIGN.md) and emits a task-by-task implementation plan for each phase.

## 3. Non-Goals

- No proto changes. Locked in DESIGN.md §19.
- No changes to `opensearch-sink`, `schemamanager`, or the lazy `ensureFlatKnnField` path. Locked in DESIGN.md §2.
- No real `DirectivePopulator` or `VectorSetProvisioner` implementation (tasks #78/#79, out of scope).
- No Apicurio schema versioning for OpenSearch mappings (task #80, out of scope).
- No per-worktree port isolation for `pipestream-dev.sh` until an agent actually needs it.

## 4. Phase Overview

| Phase | Serial/Parallel | Exit criterion |
|---|---|---|
| P0 — cleanup + autonomy tooling | serial | `pipestream-dev.sh` can start/stop every slot; `module-semantic-graph` rename is clean |
| P1 — contract lock | serial | `MocksShowcaseTest` round-trip proves stage0 → stage3 passes all invariants; wiremock PR merged |
| P2 — supporting work | parallel with P1c/d | DJL provider extracted; stub interfaces in place; rollback tags complete |
| P3 — refactor (R1/R2/R3) | parallel, three agents | Each module passes its invariants + wiremock upstream/downstream tests |
| P4 — integration (R4/R5) | serial, one agent | JDBC gRPC + Kafka E2E meet §13 gates; §22.5 regression does not recur |

Fixtures are LOCKED from the moment P1 merges. Any fixture change after that point is a contract break that stops all parallel work and requires a DESIGN.md amendment.

## 5. Phase 0 — Cleanup + Autonomy Tooling (serial)

### 5.0 Worktree and tag conventions (applies to every phase)

**Worktree rule:** every phase that modifies a repo runs in a dedicated worktree, not on the main clone's checkout of `main`. Single-agent phases (P0, P1, P2, P4) use `git worktree add /work/worktrees/<repo>-<branch-slug> -b <branch-slug> main` against the `/work/worktrees/` directory that already hosts other project worktrees (`opennlp-debug`, `quarkus-grpc-zero-dedup`, etc.). Parallel R-phase agents use the `Agent` tool's `isolation: "worktree"` parameter so each subagent gets an auto-managed worktree that is cleaned up on success and left behind only if there are uncommitted changes.

**Tag rule:** every affected repo must carry a `pre-semantic-refactor` tag at its current `main` HEAD before any modifying work starts. This is the rollback anchor per §10. The tag is authoritative for rollback regardless of whether the refactor branch is merged; `git checkout pre-semantic-refactor` always returns a clean pre-refactor state.

**Currently tagged:** `module-chunker`, `module-embedder`, `module-semantic-graph` (on the stale local clone still named `module-semantic-manager`), `pipestream-protos`, `pipestream-engine`, `module-testing-sidecar`.

**Missing and owed before its phase starts:** `pipestream-opensearch` (P2b — tag at main HEAD), `pipestream-wiremock-server` (P1 — tag at main HEAD), `dev-assets` (P0b — tag at main HEAD).

**Commit attribution:** no AI attribution in any commit in any affected repo per `feedback-no-ai-attribution.md`. No `Co-Authored-By: Claude`, no "Generated with Claude Code," no footer emoji block.

### 5.1 P0a — Local `module-semantic-graph` rename

**Scope:** the GitHub rename is already done (`ai-pipestream/module-semantic-graph` exists, remote points there). The local working copy and the internal Quarkus app name are stale.

**Work:**

1. Rename `/work/modules/module-semantic-manager` → `/work/modules/module-semantic-graph` (filesystem `mv`; git remote is already correct).
2. Internal package rename: `ai.pipestream.module.semanticmanager` → `ai.pipestream.module.semanticgraph`. Import sweep across the repo.
3. Class rename: `SemanticManagerGrpcImpl` → `SemanticGraphGrpcImpl`; `SemanticManagerApplication` (or equivalent) → `SemanticGraphApplication`; any `*SemanticManager*` test class.
4. Quarkus app name in `application.properties`: `quarkus.application.name=semantic-graph`.
5. Gradle project name in `settings.gradle` and `build.gradle`: `semantic-graph`.
6. README update.
7. The `pre-semantic-refactor` tag on the current branch is preserved (not rewritten). If the repo's current branch is `fix/granularity-level-migration`, decide separately (P0a.7) whether R3 branches off that or off main.

**Exit criterion:** `./gradlew build` green, `quarkus dev` starts cleanly, no `semantic-manager` string remains in source outside of history / migration notes / the README's "formerly known as" paragraph.

**P0a.7 — R3 branch base:** open decision. `fix/granularity-level-migration` has in-flight work. Either (a) R3 starts fresh from main and that branch is discarded, or (b) R3 rebases on top of that branch. This spec does not choose; the writing-plans output will.

### 5.2 P0b — `pipestream-dev.sh` (autonomy unblock)

**Rationale:** Phase 1–4 are meant to run with minimal human intervention. Today, `quarkus dev` restarts require human attention and carry a shared-session risk (killing the wrong PID cascades into the Claude session — see `feedback-no-quarkusdev.md`, `feedback-kill-specific-processes.md`). This script exists so start/stop/status/logs are a single command with exact-PID safety guarantees, and so an agent can bring up exactly the slots it needs before starting work.

**Location:** `/work/dev-tools/dev-assets/scripts/pipestream-dev.sh`

**Worktree:** `/work/worktrees/dev-assets-pipestream-dev-script` on branch `feat/pipestream-dev-script`. `dev-assets` is tracked at `ai-pipestream/dev-assets`. Commit the script there; open a PR once the wiremock smoke test in the exit criterion passes. `dev-assets` gets a `pre-semantic-refactor` tag at current main HEAD before the worktree is created.

**State directory:** `/tmp/pipestream-dev/` (overridable via `PIPESTREAM_DEV_STATE_DIR` env var). One `.pid`, one `.shepherd`, and one `.log` file per slot.

**Commands:**

```
pipestream-dev.sh start   <slot> [--with-deps]
pipestream-dev.sh stop    <slot>
pipestream-dev.sh restart <slot>
pipestream-dev.sh status  [<slot>]
pipestream-dev.sh logs    <slot>  [--follow]
pipestream-dev.sh list
```

**Slot registry (inline bash associative array, grows as needed):**

| Slot | Type | Dir (under /work) | Readiness | Deps |
|---|---|---|---|---|
| `compose` | docker | — | `dev-services` tool reports up | — |
| `platform-registration` | quarkus | `core-services/platform-registration-service` | HTTP `/q/health/ready` | `compose` |
| `engine` | quarkus | `core-services/pipestream-engine` | HTTP `/q/health/ready` | `compose` |
| `opensearch-manager` | quarkus | `core-services/pipestream-opensearch/opensearch-manager` | HTTP `/q/health/ready` | `compose` |
| `wiremock` | quarkus | `core-services/pipestream-wiremock-server` | HTTP `/q/health/ready` | — |
| `chunker` | quarkus | `modules/module-chunker` | HTTP `/q/health/ready` | `compose`, `platform-registration` |
| `embedder` | quarkus | `modules/module-embedder/module-embedder` | HTTP `/q/health/ready` | `compose`, `platform-registration` |
| `semantic-graph` | quarkus | `modules/module-semantic-graph` | HTTP `/q/health/ready` | `compose`, `platform-registration` |
| `testing-sidecar` | quarkus | `modules/module-testing-sidecar` | HTTP `/q/health/ready` | `compose`, `platform-registration`, `engine` |

Ports are read from each slot's `application.properties` at `start` time.

**`compose` slot behavior:** delegates to the existing `/home/krickert/bin/dev-services up | down` tool (which is a symlink to `/work/dev-tools/scripts/dev-services.sh`). No duplication of that script's logic. `status` for the `compose` slot runs `docker compose -f ~/.pipeline/compose-devservices.yml ps` and reports a summary.

**`quarkus` slot start flow:**

1. Refuse if any dep is not running (check via `status`). `--with-deps` walks the dep graph and starts missing pieces.
2. `mkdir -p $STATE_DIR`. If an existing `.pid` for the slot points at a live process, refuse with "already running as PID X".
3. `cd <slot-dir>`; launch with `nohup env PIPESTREAM_DEV_SLOT=<slot> quarkus dev > $STATE_DIR/<slot>.log 2>&1 &`.
4. Write the shell `$!` to `$STATE_DIR/<slot>.shepherd` (that's the quarkus CLI wrapper, not the dev JVM — kept for cleanup only).
5. Poll the readiness URL up to 90 s (configurable per slot). If readiness fails, `stop` the slot and exit non-zero.
6. On readiness, resolve the real dev JVM PID by either `ps -e -o pid,command | grep` for the slot's module directory as an **exact substring match** (not a pattern match on `quarkus` or `java`), or `lsof -ti :<port>` as a fallback. Write the result to `$STATE_DIR/<slot>.pid`.

**`quarkus` slot stop flow:**

1. Read `$STATE_DIR/<slot>.pid`. If absent, report "not running" and exit 0.
2. `kill -TERM <exact_pid>`. Poll up to 10 s.
3. If still alive, `kill -KILL <exact_pid>`.
4. Only touch the shepherd PID if `--force-shepherd` is passed, OR if the dev JVM PID was never captured (readiness-failed start).
5. Never `pkill`, never pattern-match kills, never kill a PID that isn't in the state files.
6. Remove `.pid` and `.shepherd` files on clean shutdown.

**`status` command:** for each slot, print `RUNNING <pid> <port>` or `STOPPED`. `status` with no arg prints the whole table.

**`logs <slot> --follow`:** `tail -f` on `$STATE_DIR/<slot>.log`.

**Safety constraints (per saved feedback):**

- Exact-PID kills only. Zero pattern-kill operations.
- Shepherd PID is captured but never killed unless the dev JVM PID couldn't be resolved or the operator passes `--force-shepherd`.
- No `sudo`, no `systemctl`, no touching other users' processes.
- No operations on anything outside `$STATE_DIR` and the target slot's repo directory.
- Sources `shared-utils.sh` (already in `dev-assets/scripts/`) for coloured `print_status` output, so it matches existing convention.

**Verification items to resolve while writing it:**

- Whether `quarkus dev` propagates the `PIPESTREAM_DEV_SLOT` env var to the forked dev JVM. If it does, that's the cleanest PID discriminator. If not, fall back to substring match on the slot's module directory in the command line (still exact, still not a pattern match).
- Whether `compose-devservices.yml` has path-relative volumes; if so, the `compose` slot must `cd` appropriately (likely already handled inside `dev-services`).

**Exit criterion:** `pipestream-dev.sh start wiremock` brings up `pipestream-wiremock-server` cleanly; `stop wiremock` leaves no stray processes; `status` reports state accurately; PID files are consistent with `ps`. This is the test target, because wiremock has no dependencies and is the simplest slot.

## 6. Phase 1 — Contract Lock (serial, must be 100%)

### 6.1 P1a — Stage fixtures + invariants

**Location:** `pipestream-protos/testdata/semantic-pipeline/`

**Deliverables:**

- `stage0_raw.textpb` — a minimal input doc with 2–3 paragraphs of body text, an upstream parser having set `search_metadata`, and a `vector_set_directives` block with **one** directive that has **two** `NamedChunkerConfig`s (`token_500_50`, `sentence_10_3`) and **two** `NamedEmbedderConfig`s (`minilm_v2`, `paraphrase_l3`). Matches DESIGN.md §18.
- `stage1_post_chunker.textpb` — the expected output after the chunker step: 2 placeholder SPRs (one per chunker config) + 1 `sentences_internal` SPR + `source_field_analytics[]` + `nlp_analysis` attached.
- `stage2_post_embedder.textpb` — the expected output after embedder: 4 populated SPRs (2 chunkers × 2 embedders) + 2 embedded `sentences_internal` SPRs (one per embedder). Fake but deterministic vectors (see below).
- `stage3_post_semantic_graph.textpb` — Stage 2 + appended centroid SPRs + semantic-boundary SPRs. Final lex sort applied.
- `SemanticPipelineInvariants.java` — `assertPostChunker(PipeDoc)`, `assertPostEmbedder(PipeDoc)`, `assertPostSemanticGraph(PipeDoc)` per DESIGN.md §5. Uses AssertJ with `.as()` messages (per `feedback-assertj-preference.md`).
- `SemanticPipelineFixtures.java` — helper that loads the `.textpb` files via Java resources, plus programmatic builders for test-specific variants.

**Deterministic fake vectors:** for fixtures to be reproducible without DJL running, Stage 2 and Stage 3 vectors are generated by a deterministic stub: `float[i] = sin(i + hash(text)) / sqrt(dimension)`. This is only used in fixtures; production code always calls DJL. The stub formula is captured in `SemanticPipelineFixtures.deterministicEmbed(String text, int dim)` and every wiremock mock + every unit test uses the same helper.

**Corpus choice:** tiny synthetic 2–3 paragraph doc for fast unit tests. The sidecar's `JdbcCrawlE2ETestService` covers scale. This matches DESIGN.md §14.1/§14.2 and is what the user agreed to.

**Exit criterion:** `SemanticPipelineInvariants.assertPostChunker(load("stage1_post_chunker.textpb"))` passes; same for stage2/stage3. Unit test `SemanticPipelineInvariantsTest` committed.

### 6.2 P1b — Step-option records (per DESIGN.md §6)

The three step-option records (`ChunkerStepOptions`, `EmbedderStepOptions`, `SemanticGraphStepOptions`) **live in their owning module**, per DESIGN.md §6.1 / §6.2 / §6.3. No shared location. No duplication. No shared library.

An earlier pass of this spec reopened this as a location question because wiremock mocks were thought to need access to the records for config validation. Re-reading the mock scenarios in §6.3 below (SUCCESS / FAIL_PRECONDITION / FAIL_INVALID_ARG / FAIL_INTERNAL / PARTIAL / SLOW): none of them parse config — every scenario is driven by the `x-mock-scenario` gRPC metadata header. The mocks never touch the records. DESIGN.md §6 is the answer: one record per module, owned by that module, no sharing.

Each record is a Java record annotated `@JsonIgnoreProperties(ignoreUnknown = true)`, Jackson-parsed from `ProcessConfiguration.json_config` (a `google.protobuf.Struct`) at step entry, with `effective*()` helpers for defaults. On parse failure the step returns `INVALID_ARGUMENT` per §21.1 — no default-on-parse-failure behavior.

**Exit criterion:** each record lands alongside its `*GrpcImpl` refactor in R1/R2/R3. No P1b deliverable exists in isolation outside the R-phase worktrees.

### 6.3 P1c — Three wiremock step mocks

**Location:** `pipestream-wiremock-server`

**Classes:** `ChunkerStepMock`, `EmbedderStepMock`, `SemanticGraphStepMock`. All three implement `ai.pipestream.wiremock.client.ServiceMockInitializer` so they're discovered by `ServiceMockRegistry` via ServiceLoader.

**Pattern:** extends the existing `PipeStepProcessorMock` approach (header-based discrimination via `x-module-name` metadata, `WireMockGrpcService` for stub registration, no Quarkus CDI in the mock classes themselves per wiremock's "no `@GrpcService`" rule).

**Scenarios each mock must expose:**

| Scenario | Trigger | Response |
|---|---|---|
| SUCCESS | default / `x-mock-scenario: success` | Deterministic stage-N+1 fixture output |
| FAIL_PRECONDITION | `x-mock-scenario: fail-precondition` | `Status.FAILED_PRECONDITION` |
| FAIL_INVALID_ARG | `x-mock-scenario: fail-invalid-arg` | `Status.INVALID_ARGUMENT` |
| FAIL_INTERNAL | `x-mock-scenario: fail-internal` | `Status.INTERNAL`, retryable |
| PARTIAL | `x-mock-scenario: partial` | Some SPRs populated, some missing — exercises downstream resilience |
| SLOW | `x-mock-scenario: slow` | Success but delayed 2–5 seconds — exercises timeout paths |

Front-end devs and E2E tests flip scenarios via the header, not via rebuilds. Matches DESIGN.md §14.3 "deterministic, configurable scenarios."

**Constraints reaffirmed from the wiremock project's own rules:**

- NOT a Quarkus `@GrpcService` consumer. Uses `org.wiremock.grpc.dsl.WireMockGrpcService`.
- `generateMutiny = false` — uses plain gRPC stubs / raw protobuf.
- Depends on `pipestream-protos` only (plus WireMock, Jackson, SLF4J).
- Does NOT consume `pipestream-bom`.
- ServiceLoader registration through `META-INF/services/ai.pipestream.wiremock.client.ServiceMockInitializer`.

**Exit criterion:** `quarkus dev` on `pipestream-wiremock-server` comes up; a gRPC client can hit the PipeStepProcessor endpoint with `x-module-name: chunker` and get back a Stage 1 fixture.

### 6.4 P1d — `MocksShowcaseTest` round-trip

**Purpose:** prove the mock wiring is correct and the fixtures are self-consistent. Specifically: each mock returns its canned fixture for the SUCCESS scenario, `x-module-name` header dispatch works, every fixture satisfies its corresponding invariant, and the four fixtures form a coherent shape chain (stage0 → stage1 → stage2 → stage3).

**What it does NOT prove:** that the real `module-chunker`, `module-embedder`, or `module-semantic-graph` produce those fixtures. Each module's own unit tests (R1/R2/R3) prove that. The real end-to-end pipeline test lives in R5, via `module-testing-sidecar`'s `JdbcCrawlE2ETestService`.

Why bother with the showcase test at all: it's the cheapest contract-lock signal available. If `stage2_post_embedder.textpb` is internally inconsistent with `stage1_post_chunker.textpb` on chunk IDs or offsets, this test catches it before any R-phase agent has built anything against the bad fixture. It's a fixture-level regression gate that runs inside the wiremock-server's own CI so it can't drift.

**Test shape:**

```
stage0 = load("stage0_raw.textpb")
stage1 = grpcCall(pipeStepProcessor, stage0, header("x-module-name", "chunker"))
assertPostChunker(stage1)  // from P1a invariants

stage2 = grpcCall(pipeStepProcessor, stage1, header("x-module-name", "embedder"))
assertPostEmbedder(stage2)

stage3 = grpcCall(pipeStepProcessor, stage2, header("x-module-name", "semantic-graph"))
assertPostSemanticGraph(stage3)

assertThat(stage3).isEqualTo(load("stage3_post_semantic_graph.textpb"))
```

This is the contract lock. It runs inside the wiremock-server repo's own test suite so it can't regress silently. The same assertions also live in `pipestream-protos/testdata` so the module repos can link against them during R1–R3.

**Exit criterion:** `MocksShowcaseTest` green on a clean build. Wiremock PR reviewed and merged. Fixtures are now LOCKED.

## 7. Phase 2 — Supporting Work (can overlap P1c/d)

### 7.1 P2a — DJL extension usage (no provider extraction)

**The picture:** `quarkus-djl-embeddings/runtime/` today contains a JAX-RS REST client `DjlServingClient` that speaks to an external DJL Serving process (the extension is a REST client, not an in-JVM DJL library). `module-embedder` has its own high-level wrapper — `DjlServingEmbeddingProvider` + `DjlServingVectorizer` — that handles big-batch hydration, model discovery, retries, and the concerns specific to its workload (arbitrary N-chunk hydration across many directives). `module-semantic-graph` also needs DJL, but for a very different workload: ≤ 50 sentence-group texts re-embedded once per doc with a single model ID (`boundary_embedding_model_id`), no cache, no fan-out.

**Decision:** do NOT extract the high-level provider. The two workloads are different enough that a shared high-level abstraction either carries dead code or leaks so much configuration surface that both sides write glue anyway. The thing worth sharing is the **low-level REST client**, which already exists and is already a public `@RegisterRestClient` interface in the extension.

**Work (reduced):**

1. Verify `ai.pipestream.quarkus.djl.serving.runtime.client.DjlServingClient` is a public, injectable interface in `quarkus-djl-embeddings-runtime`. It already is (`@Path("/") @RegisterRestClient(configKey = "djl-serving")`). No change needed unless the package or annotation is currently restricted.
2. `module-embedder` is **not touched** in P2a. It keeps `DjlServingEmbeddingProvider` / `DjlServingVectorizer` exactly as they are. R2's refactor modifies them only for its own reasons (§21.6 `ReactiveRedisDataSource` batch path, fan-out, retry bounds).
3. `module-semantic-graph` adds a dependency on `quarkus-djl-embeddings-runtime` during R3 and writes its own small helper `SemanticGraphEmbedHelper` (~50 lines) that does exactly one thing: given a `List<String>` and a model ID, pack all texts into **one** DJL Serving `predict` call (DJL Serving's `/predictions/{model}` accepts batch input natively), return `List<float[]>`. No cache, no model registry, no fan-out, at most one retry on transient error.

**No custom thread pool.** Three reasons:

1. The 50-text batch is a single HTTP request via Quarkus rest-client-reactive's Mutiny bindings — non-blocking by default, runs on the Vert.x event loop. At ~20–40 ms warm-path latency per batch, it hits the §13 500 ms p95 budget with room to spare. No parallelism needed at all.
2. If batching turns out impossible (e.g. the model's DJL Serving handler rejects lists), the Mutiny-native fallback is `Multi.createFrom().iterable(texts).onItem().transformToUniAndMerge(concurrency, text -> djlClient.predict(...))` with `concurrency` ≈ 8. Bounded parallelism without a custom executor — Quarkus rest-client-reactive already handles I/O on tuned event-loop threads.
3. The real concurrency limit is external: DJL Serving decides how many inflight requests it accepts and how fast its GPU consumes them. A client-side thread pool in semantic-graph doesn't help — it just adds a queue in front of a queue. Cross-doc concurrency comes from the engine's slot config per §3, not from per-module executors.

**When a dedicated pool WOULD make sense:** if the DJL REST calls were blocking (they're not — Mutiny chain, non-blocking), or if semantic-graph had CPU-heavy work on the event loop competing with I/O (it doesn't — centroids are cheap CPU math, boundary detection is fast). Neither applies.

**"In-process" clarification preserved from earlier drafts:** "in-process" in DESIGN.md §8 means "inside the module's own JVM, no gRPC round-trip through `module-embedder`." It does NOT mean "DJL Java library running inside the JVM." Both modules still speak REST to external DJL Serving via `DjlServingClient`. This distinction was discovered during rollout planning and is captured here so a future DESIGN.md edit can inline it if useful.

**Worktree:** P2a is a read-only verification in the common case. If the `DjlServingClient` interface turns out to need an annotation change or a package move, P2a gets a worktree `/work/worktrees/module-embedder-djl-client-verify` on branch `chore/djl-client-public-api`.

**Exit criterion:** confirmed that `DjlServingClient` can be `@Inject`-ed from any module depending on `quarkus-djl-embeddings-runtime`. `module-semantic-graph`'s R3 branch can add the dependency and build without additional refactor work to `module-embedder`.

### 7.2 P2b — Stub `DirectivePopulator` and `VectorSetProvisioner`

**Per DESIGN.md §12:**

- `DirectivePopulator` interface + `NoOpDirectivePopulator` implementation in `pipestream-engine`. Wired into `EngineV1Service.processNode` before dispatch. TODO comment references task #78.
- `VectorSetProvisioner` interface + `NoOpVectorSetProvisioner` implementation in `pipestream-opensearch/opensearch-manager`. Injected where eager field creation would go. TODO comment references task #79.

**Exit criterion:** both stubs compile, are wired via CDI, and do not affect current E2E behavior (they're no-ops).

### 7.3 P2c — Missing `pre-semantic-refactor` tag on `pipestream-opensearch`

**Observation:** the tag exists on chunker, embedder, semantic-graph (as semantic-manager), pipestream-protos, pipestream-engine, and testing-sidecar. It does NOT exist on `pipestream-opensearch`, which will receive a real (even if no-op) edit from P2b.

**Action:** tag `pipestream-opensearch` at main HEAD as `pre-semantic-refactor` so rollback remains symmetric across all affected repos. Decision locked per §11.

**Worktree for the P2b edit:** `/work/worktrees/pipestream-opensearch-vector-set-provisioner-stub` on branch `feat/vector-set-provisioner-stub`. Even though the stub is a no-op, the edit runs in a worktree per §5.0 — every modification lives in its own branch.

**Exit criterion:** tag exists and `git checkout pre-semantic-refactor` in that repo returns a clean working tree; the stub builds cleanly in the worktree and the worktree's test suite passes.

## 8. Phase 3 — Parallel Refactor (R1/R2/R3)

**Constraint:** P1 must be merged before any R-phase starts. P2 should be merged in parallel with P1c/d so that R2/R3 can depend on the extracted DJL provider from day 1.

### 8.1 Agent work packet template

Each of R1/R2/R3 is a self-contained agent prompt. Every agent's prompt includes:

1. **Pointer to DESIGN.md** (specifically §4/§5 stage contracts, §6 config records, §7 step-behavior spec for the agent's module, §10 error semantics, §21 amendments).
2. **Pointer to this spec's §8.Rn** section for module-specific scope.
3. **Pointer to `SemanticPipelineInvariants`** in `pipestream-protos/testdata/semantic-pipeline/` for input/output assertions.
4. **Pointer to the wiremock step mocks** for upstream/downstream simulation so integration tests don't require the other two real modules.
5. **Explicit scope fence:** "you may NOT change any `.textpb` fixture, any `SemanticPipelineInvariants` assertion, or any wiremock step mock. If you believe a fixture or invariant is wrong, STOP and raise it to the human operator as a spec amendment — do not patch around it. You CAN and should create your own step-option record (`ChunkerStepOptions` / `EmbedderStepOptions` / `SemanticGraphStepOptions`) inside your own module; that's part of your scope per §6.2."
6. **Isolation:** each R-phase agent is dispatched via the `Agent` tool with `isolation: "worktree"` so the subagent runs in its own auto-managed git worktree. No two agents touch the same clone. On completion the worktree cleans up if there are no uncommitted changes; on failure the worktree + branch are preserved for human inspection.
7. **Merge gate:** module's test suite passes; `assertPost*` invariants hold on real output; wiremock-backed integration tests pass; no `pkill` / broad-kill operations in any script the agent touches; no commits carry AI attribution.

### 8.2 R1 — `module-chunker`

**Branch:** `refactor/semantic-pipeline-three-step` off current main.

**Scope per DESIGN.md §7.1:**

- Parse `ChunkerStepOptions`.
- Resolve directives from `search_metadata.vector_set_directives`; fail `FAILED_PRECONDITION` if absent (§21.1).
- Validate `source_label` uniqueness; compute and stamp `directive_key` on every output SPR (§21.2).
- For each `VectorDirective`, for each `NamedChunkerConfig`: check `chunk:{sha256b64url(text)}:{chunker_config_id}` in Redis via chunker's chosen API (`@CacheResult` or `ReactiveRedisDataSource` per §21.6 — implementer's choice). Compute on miss, writeback.
- Always emit the `sentences_internal` SPR (§21.9) when `always_emit_sentences` is true and no directive already requested sentence chunking.
- Use deterministic `result_id` / `chunk_id` (§21.5). Remove any UUID generation.
- RTBF policy gate (§21.7): read `RtbfPolicy.isSuppressed(doc)` before cache writes; reads stay enabled.
- Output lex-sorted per §21.8.

**Test gates:**

- Unit tests that consume `stage0_raw.textpb` and assert the output passes `assertPostChunker`.
- Integration test against `EmbedderStepMock` (wiremock) to prove chunker output hydrates through the embedder mock without assertion failure.
- The `module-chunker` existing test suite (Bible KJV, court opinions — §22.2) stays green.

**Exit criterion:** branch passes its own CI and all P1 invariants; PR ready to merge pending the R4 graph-wiring dependency.

### 8.3 R2 — `module-embedder`

**Branch:** `refactor/semantic-pipeline-three-step` off current main.

**Scope per DESIGN.md §7.2:**

- Parse `EmbedderStepOptions`.
- Call `assertPostChunker` on input; fail `FAILED_PRECONDITION` on violation.
- Partition SPRs into placeholders (`embedding_config_id == ""`) and pass-throughs.
- For each placeholder, match its directive by `directive_key` first and `source_label` second (§21.2).
- For each `NamedEmbedderConfig`: batch `MGET` via `ReactiveRedisDataSource.value(String.class, byte[].class).mget(keys)` (§21.6). Hit/miss partition. DJL call for misses via `@Inject DjlEmbeddingProvider` from the extension (P2a).
- Bounded retry (`maxRetryAttempts`, `retryBackoffMs`) on transient DJL errors only. Permanent errors fail immediately.
- Batch `MSET` writeback with per-key expiry.
- Fan-out: one placeholder Stage-1 SPR → N Stage-2 SPRs (one per embedder config on the matching directive).
- RTBF gate on cache writes.
- Deterministic IDs, lex sort.

**MANDATORY regression test:** the §22.5 MiniLM-sentence-chunk-loss failure mode. R2 must reproduce it against the mocks (partial-scenario) and prove the new retry/fan-out path cannot leave any chunk with a null vector. A unit test of the form:

```
given: an embedder-step input with 312 sentence chunks × minilm_v2 model
when: DJL returns 400 on 144 of them (mock partial failure)
then: after retry, every chunk has a populated vector OR the whole doc fails explicitly — never a silent hole
```

This is the one gate that DESIGN.md calls out by name (§22.5). Merging R2 without this test is a rollback trigger.

**Test gates:**

- Unit tests consume `stage1_post_chunker.textpb` and assert output passes `assertPostEmbedder`.
- Integration tests against `ChunkerStepMock` (upstream) and `SemanticGraphStepMock` (downstream).
- Existing embedder test suite stays green.

**Exit criterion:** branch passes CI, invariants, §22.5 regression test. PR ready to merge.

### 8.4 R3 — `module-semantic-graph`

**Branch base decision:** P0a.7 (open).

**Scope per DESIGN.md §7.3:**

- Parse `SemanticGraphStepOptions`.
- Call `assertPostEmbedder` on input.
- Group SPRs by `(source_field, chunker_config, embedder_config)`; for each group emit document / paragraph / section centroids per enabled flags, delegating averaging to the existing `CentroidComputer`.
- Semantic boundary detection: require explicit `boundary_embedding_model_id` (§21.3). Resolve against loaded DJL models via `@Inject DjlEmbeddingProvider`. Fail `FAILED_PRECONDITION` if not loaded. No "first available model" fallback.
- Run `SemanticBoundaryDetector` on `sentences_internal` SPR vectors. Enforce `max_semantic_chunks_per_doc` as a hard cap — fail `INTERNAL` if exceeded, never silently truncate.
- Re-embed boundary group text via local DJL (≤ 50 calls per doc, by contract).
- Append new SPRs; do NOT touch the Stage 2 SPRs that are carried forward. `assertPostSemanticGraph` verifies this with a deep-equal check on the pre-append portion.
- Lex sort.

**Test gates:**

- Unit tests consume `stage2_post_embedder.textpb` and assert output passes `assertPostSemanticGraph`.
- Integration test against `EmbedderStepMock` (upstream).
- Deep-equal check: the Stage 2 prefix of `semantic_results[]` is untouched.

**Exit criterion:** branch passes CI, invariants, deep-equal check. PR ready to merge.

### 8.5 Coordination rules for the three parallel agents

- All three work against the same P1 fixtures. Any fixture change requires all three agents to stop. A fixture bug is a design amendment, not a patch.
- Agents do NOT read each other's branches. Cross-module coupling happens only through the wiremock mocks and the shared invariants file.
- Agents run tests sequentially within their own worktree (`feedback-test-sequential.md`). Across agents, tests are parallel by virtue of running in three worktrees.
- Agent commits have zero AI attribution per `feedback-no-ai-attribution.md`.
- Each agent reports back a single PR URL + a passing-tests summary. The reviewing human (or a reviewer agent) validates the PR against `pr-review-toolkit:silent-failure-hunter` and `pr-review-toolkit:code-reviewer`.

## 9. Phase 4 — Integration (R4/R5)

### 9.1 R4 — Engine graph wiring in `module-testing-sidecar`

**Per DESIGN.md §14.4 and §17:**

1. Update `JdbcCrawlE2ETestService` to build the graph as `parser → chunker → embedder → semantic-graph → opensearch-sink` (was `parser → chunker → semantic-manager → opensearch-sink`).
2. Update `S3CrawlE2ETestService` and `TransportTestService` the same way.
3. Update the frontend / E2E step list (`E2EStep`, `E2ETestState`) to reflect the new node topology.
4. Any remaining references to `semantic-manager` in test code, YAML, or step names get renamed to `semantic-graph`.

**Exit criterion:** `quarkus dev` on testing-sidecar reports the new topology; a 3-doc JDBC gRPC run completes; semantic SPR output shape is identical to the pre-refactor output.

### 9.2 R5 — Full E2E verification against the gates

**Instrumentation required (DESIGN.md §22.7):**

- Wall clock for 3-doc, 20-doc, 100-doc JDBC gRPC + semantic.
- Wall clock for 3-doc and 20-doc JDBC Kafka + semantic (for the §13 "within 10% of gRPC" gate).
- Per-step p95 latency for chunker / embedder / semantic-graph, read from the existing pipeline-events audit trail.
- Cache hit rate on `chunk:*` and `embed:*` for a cold crawl followed immediately by an identical re-crawl.
- MiniLM sentence-chunk vector coverage across both transports (§22.5 regression check).
- opensearch-sink heap headroom on the 100-doc semantic run.

**Merge gates from DESIGN.md §13:**

| Gate | Target |
|---|---|
| 3-doc JDBC gRPC wall clock | ≤ 5 s |
| 20-doc JDBC gRPC wall clock | ≤ 15 s |
| 100-doc JDBC gRPC wall clock | ≤ 60 s |
| Per-doc embedder p95 | ≤ 1 s |
| Per-doc semantic-graph p95 | ≤ 500 ms |
| Chunker cache hit rate on identical re-crawl | ≥ 95 % |
| Embedder cache hit rate on identical re-crawl | ≥ 90 % |
| Kafka transport wall clock | within 10 % of gRPC |
| §22.5 MiniLM sentence coverage | 100 % on both transports |

**Exit criterion:** every gate above is green on a clean run. The R5 run's captured numbers become the new `pre-semantic-refactor` baseline for the next cycle. If any gate fails, R5 does not merge — the failing module goes back to its R-phase for revision, and its `pre-semantic-refactor` tag becomes the rollback target.

## 10. Rollback

Per DESIGN.md §16, every affected repo has (or will have) a `pre-semantic-refactor` tag at the pre-refactor HEAD. Because protos are untouched and output shape is preserved at every stage, per-module rollback is safe and non-cascading. Rollback procedure per repo:

```
git -C <repo> checkout pre-semantic-refactor
# or: git revert <refactor merge commit>
```

The stub `DirectivePopulator` + `VectorSetProvisioner` stay as no-ops regardless of which module is rolled back. The wiremock mocks remain in place so integration tests for the un-rolled-back modules still run.

## 11. Decisions Closed During Spec Review

All decisions below were resolved during the 2026-04-13 spec review pass. No open items remain in this spec. If any of these need to be reopened during implementation, do NOT patch around them — raise a spec amendment to this document and re-run §11 sign-off.

1. **R3 branch base — CLOSED.** `fix/granularity-level-migration` is fully merged on GitHub (PR #7 merged 2026-04-10). The local `module-semantic-manager` clone is just stale. R3 branches from a freshly pulled `main` on `module-semantic-graph`; the local stale branch is deleted.
2. **Step-option record location — CLOSED.** Per-module, per DESIGN.md §6. See §6.2 for the rationale (wiremock mocks are header-driven and never parse config, so no sharing is needed).
3. **Tag `pipestream-opensearch` — CLOSED.** Tag at main HEAD as `pre-semantic-refactor` before P2b work starts. See §7.3.
4. **Agent dispatch style — CLOSED.** Three parallel `Agent` tool subagents with `isolation: "worktree"`, one per module, dispatched concurrently as soon as P1 merges. Sequential canary is NOT the plan. See §8.1 item 6.
5. **Worktree rule (general) — CLOSED.** Broad: every phase that modifies any repo runs in its own worktree on its own branch, tagged with `pre-semantic-refactor` at main HEAD before work starts. See §5.0.
6. **DJL provider extraction (P2a) — CLOSED.** No extraction. Both modules consume `DjlServingClient` directly from the extension; `module-semantic-graph` writes its own thin `SemanticGraphEmbedHelper`. No custom thread pools. See §7.1.

## 12. Definition of Done

The rollout is complete when:

1. `pipestream-dev.sh` exists and can manage every slot in §5.2's table.
2. Wiremock server has the three step mocks + `MocksShowcaseTest` green.
3. `SemanticPipelineInvariants` + four stage fixtures are committed to `pipestream-protos/testdata/semantic-pipeline/`.
4. `quarkus-djl-embeddings/runtime/` exposes `DjlEmbeddingProvider` and both `module-embedder` and `module-semantic-graph` consume it via `@Inject`.
5. `DirectivePopulator` / `VectorSetProvisioner` no-op stubs are wired.
6. `module-chunker`, `module-embedder`, `module-semantic-graph` each pass their own CI plus the wiremock integration tests plus the shared invariants.
7. `module-testing-sidecar` E2E uses the new topology and meets every §13 gate.
8. The §22.5 MiniLM sentence-loss failure does not recur on either transport.
9. No commits in any affected repo carry AI attribution.
10. Every affected repo has a clean `pre-semantic-refactor` rollback tag.

## 13. What This Spec Does NOT Specify (by intent)

- Real `DirectivePopulator` / `VectorSetProvisioner` implementations. Tasks #78/#79.
- Apicurio schema versioning for OpenSearch mapping changes. Task #80.
- Sink-side sentence indexing opt-out. DESIGN.md §21.9 leaves this as a future sink-side toggle.
- Parallel worktree port isolation for `pipestream-dev.sh`. Added only if an agent hits the pain.
- Any change to the engine slot config / concurrency tuning. Engine changes are out of scope; cross-doc concurrency comes from whatever slot config the graph already uses.

---

**End of rollout spec.**
