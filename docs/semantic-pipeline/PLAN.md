# Semantic Pipeline Rollout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute the three-step semantic pipeline refactor (DESIGN.md contract, ROLLOUT.md rollout spec) phase-by-phase from tooling setup through full end-to-end verification against §13 performance gates.

**Architecture:** Replace the single `module-semantic-manager` orchestrator with three stateless pipeline-step modules (`module-chunker` → `module-embedder` → `module-semantic-graph`) that share a stage-invariant contract on `search_metadata.semantic_results[]`. Contract lock via fixtures + wiremock mocks comes first; three parallel refactor agents come second; integration comes last.

**Tech Stack:** Quarkus 3.34.x, Mutiny, gRPC, protobuf, OpenNLP 3.0.0-M1, Redis (ReactiveRedisDataSource), DJL Serving (external), Jackson (config parsing), AssertJ, Gradle, bash.

**Sibling documents in this directory (read first):**
- `DESIGN.md` — technical contract, stage invariants, config schemas, §21 hard rules, §22 baselines
- `ROLLOUT.md` — rollout spec, worktree/tag conventions, phase shape, agent work packet skeletons, closed decisions

---

## How to use this plan

This plan covers five phases of work. Read them in order:

- **Phase 0** — tagging, repo rename, `pipestream-dev.sh`. Single-agent, done before any refactor work.
- **Phase 1** — stage fixtures, invariants, wiremock step mocks, showcase test. Single-agent. Must be 100% green before Phase 3 dispatches.
- **Phase 2** — DJL client verification, engine/opensearch stubs, one remaining tag. Can overlap Phase 1 tail end.
- **Phase 3** — three parallel subagent work packets for `module-chunker`, `module-embedder`, `module-semantic-graph`. Dispatched only after Phase 1 merges.
- **Phase 4** — engine graph wiring update in `module-testing-sidecar`, full JDBC gRPC + Kafka E2E against §13 performance gates.

Tasks are bite-sized (2–5 minutes per step). Each task ends with a commit. Commit messages must NOT carry AI attribution (no `Co-Authored-By: Claude`, no "Generated with Claude Code" — see `feedback-no-ai-attribution.md`). Use AssertJ with `.as()` messages for every assertion (see `feedback-assertj-preference.md`).

Each phase runs in its own worktree under `/work/worktrees/` per ROLLOUT.md §5.0. Tag the affected repo with `pre-semantic-refactor` at main HEAD before creating its worktree.

---

## File Structure

Files created or modified across all phases. Phase number in square brackets.

### `dev-assets` (P0b)
- Create: `/work/dev-tools/dev-assets/scripts/pipestream-dev.sh` — single bash script, slot registry + start/stop/status/logs/list. [P0]

### `module-semantic-graph` (P0a, then R3)
- Move: `/work/modules/module-semantic-manager/` → `/work/modules/module-semantic-graph/` [P0]
- Rename package: `ai.pipestream.module.semanticmanager` → `ai.pipestream.module.semanticgraph` (import sweep) [P0]
- Rename class: `SemanticManagerGrpcImpl` → `SemanticGraphGrpcImpl` [P0]
- Modify: `application.properties` → `quarkus.application.name=semantic-graph` [P0]
- Modify: `settings.gradle`, `build.gradle` → project name `semantic-graph` [P0]
- Modify: `README.md` [P0]
- Create: `src/main/java/.../semanticgraph/config/SemanticGraphStepOptions.java` [R3]
- Create: `src/main/java/.../semanticgraph/djl/SemanticGraphEmbedHelper.java` [R3]
- Modify: `SemanticGraphGrpcImpl.java` — rewrite `processData` per DESIGN.md §7.3 [R3]

### `pipestream-protos` (P1a)
- Create: `testdata/semantic-pipeline/stage0_raw.textpb` [P1]
- Create: `testdata/semantic-pipeline/stage1_post_chunker.textpb` [P1]
- Create: `testdata/semantic-pipeline/stage2_post_embedder.textpb` [P1]
- Create: `testdata/semantic-pipeline/stage3_post_semantic_graph.textpb` [P1]
- Create: `testdata/semantic-pipeline/src/main/java/ai/pipestream/semantic/testdata/SemanticPipelineFixtures.java` [P1]
- Create: `testdata/semantic-pipeline/src/main/java/ai/pipestream/semantic/testdata/SemanticPipelineInvariants.java` [P1]
- Create: `testdata/semantic-pipeline/src/test/java/.../SemanticPipelineInvariantsTest.java` [P1]

### `pipestream-wiremock-server` (P1c, P1d)
- Create: `src/main/java/ai/pipestream/wiremock/client/ChunkerStepMock.java` [P1]
- Create: `src/main/java/ai/pipestream/wiremock/client/EmbedderStepMock.java` [P1]
- Create: `src/main/java/ai/pipestream/wiremock/client/SemanticGraphStepMock.java` [P1]
- Modify: `src/main/resources/META-INF/services/ai.pipestream.wiremock.client.ServiceMockInitializer` [P1]
- Create: `src/test/java/ai/pipestream/wiremock/client/ChunkerStepMockTest.java` [P1]
- Create: `src/test/java/ai/pipestream/wiremock/client/EmbedderStepMockTest.java` [P1]
- Create: `src/test/java/ai/pipestream/wiremock/client/SemanticGraphStepMockTest.java` [P1]
- Modify: `src/test/java/ai/pipestream/wiremock/client/MocksShowcaseTest.java` — add round-trip test [P1]

### `pipestream-engine` (P2b)
- Create: `src/main/java/ai/pipestream/engine/directives/DirectivePopulator.java` [P2]
- Create: `src/main/java/ai/pipestream/engine/directives/NoOpDirectivePopulator.java` [P2]
- Modify: `EngineV1Service.processNode()` — call `directivePopulator.populateDirectives(...)` before dispatch [P2]

### `pipestream-opensearch` (P2b, P2c)
- Create: `opensearch-manager/src/main/java/.../vectorset/VectorSetProvisioner.java` [P2]
- Create: `opensearch-manager/src/main/java/.../vectorset/NoOpVectorSetProvisioner.java` [P2]
- Tag at main HEAD: `pre-semantic-refactor` [P2]

### `module-chunker` (R1)
- Create: `src/main/java/ai/pipestream/module/chunker/config/ChunkerStepOptions.java` [R1]
- Create: `src/main/java/ai/pipestream/module/chunker/cache/ChunkCacheKey.java` [R1]
- Create: `src/main/java/ai/pipestream/module/chunker/cache/ChunkCacheService.java` [R1]
- Create: `src/main/java/ai/pipestream/module/chunker/directive/DirectiveKeyComputer.java` [R1]
- Modify: `ChunkerGrpcImpl.processData(...)` — rewrite per DESIGN.md §7.1 [R1]
- Modify: unit/integration tests [R1]

### `module-embedder` (R2)
- Create: `src/main/java/ai/pipestream/module/embedder/config/EmbedderStepOptions.java` [R2]
- Create: `src/main/java/ai/pipestream/module/embedder/cache/EmbedCacheKey.java` [R2]
- Create: `src/main/java/ai/pipestream/module/embedder/cache/EmbedCacheService.java` [R2]
- Modify: `EmbedderGrpcImpl.processData(...)` — rewrite per DESIGN.md §7.2 [R2]
- Modify: unit/integration tests [R2]
- Add: regression test for §22.5 MiniLM-sentence-chunk loss [R2]

### `module-testing-sidecar` (R4)
- Modify: `JdbcCrawlE2ETestService` — graph topology chunker → embedder → semantic-graph → opensearch-sink [R4]
- Modify: `S3CrawlE2ETestService` — same [R4]
- Modify: `TransportTestService` — same [R4]
- Modify: `E2EStep`, `E2ETestState` — node name rename [R4]

---

## Phase 0 — Cleanup + Autonomy Tooling (serial, one agent)

### Task 0.1: Tag `pre-semantic-refactor` on missing repos

**Files:** none (git operations only)

**Context:** Per ROLLOUT.md §5.0, every affected repo needs `pre-semantic-refactor` at main HEAD before any modifying work. Three repos are missing: `pipestream-opensearch`, `pipestream-wiremock-server`, `dev-assets`.

- [ ] **Step 1: Tag `pipestream-opensearch`**

```bash
cd /work/core-services/pipestream-opensearch
git -c core.fsmonitor=false fetch origin
git -c core.fsmonitor=false checkout main
git -c core.fsmonitor=false pull --ff-only
git -c core.fsmonitor=false tag pre-semantic-refactor
git -c core.fsmonitor=false push origin pre-semantic-refactor
```

Expected: `To github.com:ai-pipestream/pipestream-opensearch.git * [new tag] pre-semantic-refactor -> pre-semantic-refactor`

- [ ] **Step 2: Tag `pipestream-wiremock-server`**

```bash
cd /work/core-services/pipestream-wiremock-server
git -c core.fsmonitor=false fetch origin
git -c core.fsmonitor=false checkout main
git -c core.fsmonitor=false pull --ff-only
git -c core.fsmonitor=false tag pre-semantic-refactor
git -c core.fsmonitor=false push origin pre-semantic-refactor
```

- [ ] **Step 3: Tag `dev-assets`**

```bash
cd /work/dev-tools/dev-assets
git -c core.fsmonitor=false fetch origin
git -c core.fsmonitor=false checkout main
git -c core.fsmonitor=false pull --ff-only
git -c core.fsmonitor=false tag pre-semantic-refactor
git -c core.fsmonitor=false push origin pre-semantic-refactor
```

- [ ] **Step 4: Verify all six repos are tagged**

```bash
for repo in /work/core-services/pipestream-protos \
            /work/core-services/pipestream-engine \
            /work/core-services/pipestream-opensearch \
            /work/core-services/pipestream-wiremock-server \
            /work/modules/module-chunker \
            /work/modules/module-embedder \
            /work/modules/module-semantic-manager \
            /work/modules/module-testing-sidecar \
            /work/dev-tools/dev-assets; do
  echo -n "$(basename $repo): "
  git -c core.fsmonitor=false -C "$repo" tag -l 'pre-semantic-refactor' || echo "MISSING"
done
```

Expected: every line prints `pre-semantic-refactor`. No `MISSING`.

### Task 0.2: Rename local `module-semantic-graph` clone and internals

**Files:**
- Move: `/work/modules/module-semantic-manager/` → `/work/modules/module-semantic-graph/`
- Modify: all Java sources under `src/main/java/ai/pipestream/module/semanticmanager/` (package rename)
- Modify: `src/main/resources/application.properties` (quarkus.application.name)
- Modify: `settings.gradle`, `build.gradle` (project name)
- Modify: `README.md`

**Context:** The GitHub repo has already been renamed (remote is `ai-pipestream/module-semantic-graph.git`). The local clone dir and the internal Quarkus app/package/class names are stale. Rename happens on its own worktree per ROLLOUT.md §5.0 since it's a repo-modifying phase.

- [ ] **Step 1: Sync main and create the rename worktree**

```bash
cd /work/modules/module-semantic-manager
git -c core.fsmonitor=false fetch origin
git -c core.fsmonitor=false checkout main
git -c core.fsmonitor=false pull --ff-only
git -c core.fsmonitor=false branch -D fix/granularity-level-migration  # stale, already merged as PR #7
git -c core.fsmonitor=false worktree add -b chore/rename-to-semantic-graph /work/worktrees/module-semantic-graph-rename main
```

- [ ] **Step 2: Rename internal Java package**

```bash
cd /work/worktrees/module-semantic-graph-rename
git -c core.fsmonitor=false mv src/main/java/ai/pipestream/module/semanticmanager src/main/java/ai/pipestream/module/semanticgraph 2>/dev/null || {
  # directory may not exist if code already nested differently — find and move manually
  find src -type d -name semanticmanager -print
}
# update import statements across all java sources
find src -type f -name '*.java' -exec sed -i 's|ai\.pipestream\.module\.semanticmanager|ai.pipestream.module.semanticgraph|g' {} +
```

- [ ] **Step 3: Rename the main gRPC impl class**

```bash
cd /work/worktrees/module-semantic-graph-rename
# find the file
IMPL=$(find src/main/java -name 'SemanticManagerGrpcImpl.java' | head -1)
if [ -n "$IMPL" ]; then
  NEW="${IMPL%SemanticManagerGrpcImpl.java}SemanticGraphGrpcImpl.java"
  git -c core.fsmonitor=false mv "$IMPL" "$NEW"
  sed -i 's/SemanticManagerGrpcImpl/SemanticGraphGrpcImpl/g' "$NEW"
fi
# update any other files that reference the class name
grep -rl SemanticManagerGrpcImpl src | xargs -r sed -i 's/SemanticManagerGrpcImpl/SemanticGraphGrpcImpl/g'
```

- [ ] **Step 4: Update application.properties, gradle files, README**

```bash
cd /work/worktrees/module-semantic-graph-rename
sed -i 's/quarkus\.application\.name=semantic-manager/quarkus.application.name=semantic-graph/' src/main/resources/application.properties
# settings.gradle
sed -i "s/rootProject\.name\s*=\s*['\"]semantic-manager['\"]/rootProject.name = 'semantic-graph'/" settings.gradle
# README
sed -i 's/module-semantic-manager/module-semantic-graph/g; s/semantic-manager/semantic-graph/g' README.md
```

- [ ] **Step 5: Build to verify the rename compiles**

```bash
cd /work/worktrees/module-semantic-graph-rename
./gradlew clean build -x test 2>&1 | tail -30
```

Expected: `BUILD SUCCESSFUL`. If BUILD FAILED, read the error — likely a string that `sed` missed. Fix and retry.

- [ ] **Step 6: Run existing tests to ensure no behavioral regression**

```bash
./gradlew test 2>&1 | tail -40
```

Expected: `BUILD SUCCESSFUL`. Existing tests should still pass — this is a pure rename.

- [ ] **Step 7: Commit and push**

```bash
git -c core.fsmonitor=false add -A
git -c core.fsmonitor=false -c commit.gpgsign=false commit -m "chore: rename semantic-manager to semantic-graph internally

The GitHub repo was renamed to module-semantic-graph on 2026-04-10.
This completes the rename by updating the Java package, gRPC impl class,
Quarkus application name, Gradle project name, and README. No behavioral
change."
git -c core.fsmonitor=false push -u origin chore/rename-to-semantic-graph
```

- [ ] **Step 8: Open PR, wait for review, merge**

```bash
gh pr create --repo ai-pipestream/module-semantic-graph \
  --title 'chore: rename semantic-manager internals to semantic-graph' \
  --body 'Completes the rename initiated by the GitHub repo rename. Pure rename; no behavioral change. See pipestream-protos docs/semantic-pipeline/ROLLOUT.md §5.1 for context.'
```

After merge: on the main clone, `cd /work/modules && rm -rf module-semantic-manager && git clone git@github.com:ai-pipestream/module-semantic-graph.git`. Then `git -C /work/worktrees/module-semantic-graph-rename worktree remove --force /work/worktrees/module-semantic-graph-rename`.

### Task 0.3: Create `dev-assets` worktree for `pipestream-dev.sh`

**Files:** none yet (worktree creation)

- [ ] **Step 1: Create the worktree**

```bash
cd /work/dev-tools/dev-assets
git -c core.fsmonitor=false worktree add -b feat/pipestream-dev-script /work/worktrees/dev-assets-pipestream-dev-script main
cd /work/worktrees/dev-assets-pipestream-dev-script
ls scripts/  # should show existing scripts (kill-port.sh, shared-utils.sh, etc.)
```

Expected: existing scripts listed, including `shared-utils.sh` which we will source.

### Task 0.4: `pipestream-dev.sh` skeleton with slot registry

**Files:**
- Create: `/work/worktrees/dev-assets-pipestream-dev-script/scripts/pipestream-dev.sh`

**Context:** One bash script that manages start/stop/status/logs for a set of named "slots" (services). State lives in `/tmp/pipestream-dev/` (overridable via `PIPESTREAM_DEV_STATE_DIR`). Must respect `feedback-no-quarkusdev.md` (kill dev.jar PID only, never parent) and `feedback-kill-specific-processes.md` (exact PID only, no pattern kills).

- [ ] **Step 1: Create the script skeleton with slot registry**

```bash
cat > /work/worktrees/dev-assets-pipestream-dev-script/scripts/pipestream-dev.sh <<'SCRIPT'
#!/usr/bin/env bash
#
# pipestream-dev.sh — start/stop/status/logs for Quarkus dev services.
#
# Safety model:
#   - Every managed process gets an exact PID recorded in $STATE_DIR/<slot>.pid.
#   - Kills target that exact PID only. NEVER pkill, NEVER pattern match kills.
#   - The outer `quarkus dev` wrapper's PID is recorded separately in .shepherd and
#     is only touched with --force-shepherd.
#
# State dir: $PIPESTREAM_DEV_STATE_DIR (default /tmp/pipestream-dev).
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colour output helpers from shared-utils.sh (provides print_status).
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/shared-utils.sh"

STATE_DIR="${PIPESTREAM_DEV_STATE_DIR:-/tmp/pipestream-dev}"
mkdir -p "$STATE_DIR"

WORK_ROOT="${WORK_ROOT:-/work}"

# ----- slot registry ---------------------------------------------------------
# Each slot declares: type, dir, port, readiness path, deps (comma-separated).
# Type is "compose" or "quarkus". Dir is relative to $WORK_ROOT.

declare -A SLOT_TYPE=(
  [compose]="compose"
  [platform-registration]="quarkus"
  [engine]="quarkus"
  [opensearch-manager]="quarkus"
  [wiremock]="quarkus"
  [chunker]="quarkus"
  [embedder]="quarkus"
  [semantic-graph]="quarkus"
  [testing-sidecar]="quarkus"
)

declare -A SLOT_DIR=(
  [platform-registration]="core-services/platform-registration-service"
  [engine]="core-services/pipestream-engine"
  [opensearch-manager]="core-services/pipestream-opensearch/opensearch-manager"
  [wiremock]="core-services/pipestream-wiremock-server"
  [chunker]="modules/module-chunker"
  [embedder]="modules/module-embedder/module-embedder"
  [semantic-graph]="modules/module-semantic-graph"
  [testing-sidecar]="modules/module-testing-sidecar"
)

# Ports from each slot's application.properties (quarkus.http.port).
# If a slot doesn't set one explicitly it falls back to 8080 — collisions are
# the user's responsibility. We read the file on start and honour whatever is
# there.

declare -A SLOT_DEPS=(
  [compose]=""
  [platform-registration]="compose"
  [engine]="compose"
  [opensearch-manager]="compose"
  [wiremock]=""
  [chunker]="compose,platform-registration"
  [embedder]="compose,platform-registration"
  [semantic-graph]="compose,platform-registration"
  [testing-sidecar]="compose,platform-registration,engine"
)

ALL_SLOTS=(compose platform-registration engine opensearch-manager wiremock chunker embedder semantic-graph testing-sidecar)

# ----- command dispatch ------------------------------------------------------
main() {
  local cmd="${1:-}"
  shift || true
  case "$cmd" in
    start)   cmd_start "$@" ;;
    stop)    cmd_stop "$@" ;;
    restart) cmd_restart "$@" ;;
    status)  cmd_status "$@" ;;
    logs)    cmd_logs "$@" ;;
    list)    cmd_list ;;
    ""|-h|--help|help) usage ;;
    *) print_status error "unknown command: $cmd"; usage; exit 1 ;;
  esac
}

usage() {
  cat <<EOF
Usage: pipestream-dev.sh <command> [args]

Commands:
  start   <slot> [--with-deps]   Start a slot (refuses if deps are down)
  stop    <slot> [--force-shepherd]   Stop a slot
  restart <slot>                 Stop then start
  status  [<slot>]               Show status of a slot, or all slots
  logs    <slot> [--follow]      Print (or tail -f) the slot's log
  list                           List known slots and their type + deps

Slots: ${ALL_SLOTS[*]}

Environment:
  PIPESTREAM_DEV_STATE_DIR   State dir (default /tmp/pipestream-dev)
  WORK_ROOT                  Repo root (default /work)
EOF
}

# stubs to be filled in the next tasks:
cmd_start()   { print_status error "not yet implemented"; exit 2; }
cmd_stop()    { print_status error "not yet implemented"; exit 2; }
cmd_restart() { cmd_stop "$@"; cmd_start "$@"; }
cmd_status()  { print_status error "not yet implemented"; exit 2; }
cmd_logs()    { print_status error "not yet implemented"; exit 2; }
cmd_list()    {
  printf '%-22s %-8s %s\n' SLOT TYPE DEPS
  for s in "${ALL_SLOTS[@]}"; do
    printf '%-22s %-8s %s\n' "$s" "${SLOT_TYPE[$s]}" "${SLOT_DEPS[$s]:-—}"
  done
}

main "$@"
SCRIPT
chmod +x /work/worktrees/dev-assets-pipestream-dev-script/scripts/pipestream-dev.sh
```

- [ ] **Step 2: Verify `list` works**

```bash
cd /work/worktrees/dev-assets-pipestream-dev-script
./scripts/pipestream-dev.sh list
```

Expected: nine rows, one per slot, showing type and deps.

### Task 0.5: Implement the `compose` slot (delegation to `dev-services`)

- [ ] **Step 1: Add compose start/stop logic**

Replace the placeholder `cmd_start` and `cmd_stop` stubs with a dispatcher that checks slot type and delegates. For compose, delegate to the existing `/home/krickert/bin/dev-services` tool.

Edit `pipestream-dev.sh`, replace the two stubs with:

```bash
cmd_start() {
  local slot="${1:-}"
  local with_deps=""
  [[ "${2:-}" == "--with-deps" ]] && with_deps=1

  [[ -z "$slot" ]] && { print_status error "usage: pipestream-dev.sh start <slot>"; exit 1; }
  [[ -z "${SLOT_TYPE[$slot]:-}" ]] && { print_status error "unknown slot: $slot"; exit 1; }

  # dep check
  local deps="${SLOT_DEPS[$slot]:-}"
  if [[ -n "$deps" ]]; then
    local missing=()
    IFS=',' read -ra dep_arr <<< "$deps"
    for d in "${dep_arr[@]}"; do
      if ! slot_is_running "$d"; then
        missing+=("$d")
      fi
    done
    if [[ ${#missing[@]} -gt 0 ]]; then
      if [[ -n "$with_deps" ]]; then
        for d in "${missing[@]}"; do
          print_status info "starting dep: $d"
          cmd_start "$d" --with-deps
        done
      else
        print_status error "slot '$slot' requires: ${missing[*]}"
        print_status info "hint: rerun with --with-deps, or start them manually first"
        exit 1
      fi
    fi
  fi

  case "${SLOT_TYPE[$slot]}" in
    compose)  start_compose ;;
    quarkus)  start_quarkus "$slot" ;;
  esac
}

cmd_stop() {
  local slot="${1:-}"
  local force_shepherd=""
  [[ "${2:-}" == "--force-shepherd" ]] && force_shepherd=1
  [[ -z "$slot" ]] && { print_status error "usage: pipestream-dev.sh stop <slot>"; exit 1; }
  [[ -z "${SLOT_TYPE[$slot]:-}" ]] && { print_status error "unknown slot: $slot"; exit 1; }

  case "${SLOT_TYPE[$slot]}" in
    compose) stop_compose ;;
    quarkus) stop_quarkus "$slot" "$force_shepherd" ;;
  esac
}

start_compose() {
  print_status info "starting compose via dev-services"
  /home/krickert/bin/dev-services up
  print_status success "compose up"
}

stop_compose() {
  print_status info "stopping compose via dev-services"
  /home/krickert/bin/dev-services down
  print_status success "compose down"
}

slot_is_running() {
  local slot="$1"
  case "${SLOT_TYPE[$slot]}" in
    compose)
      # compose is "running" if at least one container is Up
      docker compose -f "${HOME}/.pipeline/compose-devservices.yml" ps --format '{{.State}}' 2>/dev/null | grep -q running
      ;;
    quarkus)
      local pidfile="$STATE_DIR/${slot}.pid"
      [[ -f "$pidfile" ]] && kill -0 "$(cat "$pidfile")" 2>/dev/null
      ;;
  esac
}
```

- [ ] **Step 2: Smoke test the compose slot**

```bash
./scripts/pipestream-dev.sh start compose
./scripts/pipestream-dev.sh stop compose
```

Expected: `compose up` then `compose down`, each following the existing `dev-services` script output.

### Task 0.6: Implement `start_quarkus` (exact-PID tracking)

**Context:** Launch `quarkus dev` in the background, wait for HTTP readiness, then find the exact dev JVM PID by looking for the slot's module directory as a substring of the process command line. Use `PIPESTREAM_DEV_SLOT=<slot>` as an env marker for visibility in `ps auxe` (not as the PID discriminator itself — the directory match is the discriminator).

- [ ] **Step 1: Add the Quarkus start function**

Append to `pipestream-dev.sh` (before the final `main "$@"` line):

```bash
resolve_slot_port() {
  local slot="$1"
  local dir="$WORK_ROOT/${SLOT_DIR[$slot]}"
  local props="$dir/src/main/resources/application.properties"
  if [[ -f "$props" ]]; then
    local port
    port="$(grep -E '^quarkus\.http\.port\s*=' "$props" | head -1 | sed 's/.*=\s*//' | tr -d '[:space:]')"
    [[ -n "$port" ]] && { echo "$port"; return; }
  fi
  echo "8080"
}

start_quarkus() {
  local slot="$1"
  local dir="$WORK_ROOT/${SLOT_DIR[$slot]}"
  local pidfile="$STATE_DIR/${slot}.pid"
  local shepherdfile="$STATE_DIR/${slot}.shepherd"
  local logfile="$STATE_DIR/${slot}.log"
  local port
  port="$(resolve_slot_port "$slot")"

  if [[ ! -d "$dir" ]]; then
    print_status error "slot '$slot' dir not found: $dir"
    exit 1
  fi
  if [[ -f "$pidfile" ]] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
    print_status warning "slot '$slot' already running as PID $(cat "$pidfile")"
    exit 1
  fi

  print_status info "starting $slot (dir=$dir, port=$port)"
  (
    cd "$dir" || exit 1
    PIPESTREAM_DEV_SLOT="$slot" nohup quarkus dev >"$logfile" 2>&1 &
    echo $! >"$shepherdfile"
  )

  # Wait for HTTP readiness up to 90s
  local i=0
  local ready=""
  while [[ $i -lt 90 ]]; do
    if curl -sf "http://localhost:${port}/q/health/ready" >/dev/null 2>&1; then
      ready=1
      break
    fi
    sleep 1
    i=$((i+1))
  done

  if [[ -z "$ready" ]]; then
    print_status error "slot '$slot' failed readiness check after 90s; killing shepherd and aborting"
    stop_quarkus "$slot" 1
    exit 1
  fi

  # Resolve the actual dev JVM PID by matching the slot dir in the command line.
  # This is an EXACT substring match against a string we know is unique to the
  # slot — it is NOT a pattern kill. We do not kill anything here; we just
  # record the PID for later exact-PID termination.
  local jvm_pid
  jvm_pid="$(ps -e -o pid= -o command= \
             | awk -v d="$dir" '$0 ~ d && /java/ && !/grep/ {print $1; exit}')"

  if [[ -z "$jvm_pid" ]]; then
    # Fallback: lsof the port. Still an exact match on a port we know.
    jvm_pid="$(lsof -ti :"$port" 2>/dev/null | head -1 || true)"
  fi

  if [[ -z "$jvm_pid" ]]; then
    print_status warning "could not resolve dev JVM PID for $slot; recording shepherd only"
  else
    echo "$jvm_pid" >"$pidfile"
  fi

  print_status success "slot '$slot' up (pid=${jvm_pid:-?}, port=$port)"
}
```

- [ ] **Step 2: Test against the wiremock slot**

Wiremock has no dependencies and is the easiest slot to validate against.

```bash
cd /work/worktrees/dev-assets-pipestream-dev-script
./scripts/pipestream-dev.sh start wiremock
```

Expected: `starting wiremock...` then `slot 'wiremock' up (pid=<number>, port=<port>)`. Check `ps -p <pid>` shows a java process.

- [ ] **Step 3: Verify the state files**

```bash
ls /tmp/pipestream-dev/
cat /tmp/pipestream-dev/wiremock.pid
cat /tmp/pipestream-dev/wiremock.shepherd
head -20 /tmp/pipestream-dev/wiremock.log
```

Expected: `wiremock.pid`, `wiremock.shepherd`, `wiremock.log` all present. PID file contains a single PID. Log shows Quarkus startup.

### Task 0.7: Implement `stop_quarkus` (exact-PID termination)

- [ ] **Step 1: Add the Quarkus stop function**

Append to `pipestream-dev.sh`:

```bash
stop_quarkus() {
  local slot="$1"
  local force_shepherd="${2:-}"
  local pidfile="$STATE_DIR/${slot}.pid"
  local shepherdfile="$STATE_DIR/${slot}.shepherd"

  if [[ ! -f "$pidfile" && ! -f "$shepherdfile" ]]; then
    print_status info "slot '$slot' is not running"
    return 0
  fi

  if [[ -f "$pidfile" ]]; then
    local pid
    pid="$(cat "$pidfile")"
    if kill -0 "$pid" 2>/dev/null; then
      print_status info "sending SIGTERM to $slot (pid=$pid)"
      kill -TERM "$pid" 2>/dev/null || true
      local i=0
      while [[ $i -lt 10 ]] && kill -0 "$pid" 2>/dev/null; do
        sleep 1
        i=$((i+1))
      done
      if kill -0 "$pid" 2>/dev/null; then
        print_status warning "pid $pid did not exit after 10s; sending SIGKILL"
        kill -KILL "$pid" 2>/dev/null || true
      fi
    fi
    rm -f "$pidfile"
  fi

  if [[ -n "$force_shepherd" && -f "$shepherdfile" ]]; then
    local spid
    spid="$(cat "$shepherdfile")"
    if kill -0 "$spid" 2>/dev/null; then
      print_status warning "force-killing shepherd pid $spid"
      kill -TERM "$spid" 2>/dev/null || true
    fi
    rm -f "$shepherdfile"
  else
    # Leave shepherd file; quarkus CLI should exit cleanly when the dev JVM dies.
    # If it doesn't, operator can call with --force-shepherd.
    rm -f "$shepherdfile"
  fi

  print_status success "slot '$slot' stopped"
}
```

- [ ] **Step 2: Test stop against wiremock**

```bash
./scripts/pipestream-dev.sh stop wiremock
ps -p "$(cat /tmp/pipestream-dev/wiremock.pid 2>/dev/null || echo nothing)" 2>&1 | head -3
```

Expected: `slot 'wiremock' stopped`. Second command reports no such process. State files are gone.

### Task 0.8: Implement `cmd_status`, `cmd_logs`, `cmd_list`

- [ ] **Step 1: Replace the status and logs stubs**

```bash
cmd_status() {
  local slot="${1:-}"
  if [[ -n "$slot" ]]; then
    print_one_status "$slot"
    return
  fi
  printf '%-22s %-8s %-10s %s\n' SLOT TYPE STATUS DETAIL
  for s in "${ALL_SLOTS[@]}"; do
    print_one_status "$s"
  done
}

print_one_status() {
  local slot="$1"
  local type="${SLOT_TYPE[$slot]}"
  local status="STOPPED"
  local detail=""
  if slot_is_running "$slot"; then
    status="RUNNING"
    if [[ "$type" == "quarkus" ]]; then
      local pid
      pid="$(cat "$STATE_DIR/${slot}.pid" 2>/dev/null || echo ?)"
      local port
      port="$(resolve_slot_port "$slot")"
      detail="pid=$pid port=$port"
    fi
  fi
  printf '%-22s %-8s %-10s %s\n' "$slot" "$type" "$status" "$detail"
}

cmd_logs() {
  local slot="${1:-}"
  local follow=""
  [[ "${2:-}" == "--follow" ]] && follow=1
  [[ -z "$slot" ]] && { print_status error "usage: pipestream-dev.sh logs <slot> [--follow]"; exit 1; }
  local logfile="$STATE_DIR/${slot}.log"
  if [[ ! -f "$logfile" ]]; then
    print_status error "no log for $slot at $logfile"
    exit 1
  fi
  if [[ -n "$follow" ]]; then
    tail -F "$logfile"
  else
    cat "$logfile"
  fi
}
```

- [ ] **Step 2: Test `status` with wiremock running and stopped**

```bash
./scripts/pipestream-dev.sh start wiremock
./scripts/pipestream-dev.sh status wiremock
./scripts/pipestream-dev.sh status   # full table
./scripts/pipestream-dev.sh stop wiremock
./scripts/pipestream-dev.sh status wiremock
```

Expected: first `status` shows RUNNING with pid+port, full table shows wiremock RUNNING and others STOPPED, final `status` shows STOPPED.

### Task 0.9: Smoke-test the full flow

- [ ] **Step 1: Start wiremock, check logs, stop**

```bash
./scripts/pipestream-dev.sh start wiremock
./scripts/pipestream-dev.sh logs wiremock | head -20
./scripts/pipestream-dev.sh status wiremock
./scripts/pipestream-dev.sh stop wiremock
./scripts/pipestream-dev.sh status wiremock
ls /tmp/pipestream-dev/
```

Expected: start succeeds, logs show Quarkus startup lines, status shows RUNNING then STOPPED, state dir is empty at the end.

- [ ] **Step 2: Confirm `ps` shows no stray quarkus processes**

```bash
ps -e -o pid,command | grep -i wiremock | grep -v grep || echo "no stray processes"
```

Expected: `no stray processes`. If anything remains, investigate by PID (do NOT pkill).

### Task 0.10: Commit `pipestream-dev.sh` and open PR

- [ ] **Step 1: Commit**

```bash
cd /work/worktrees/dev-assets-pipestream-dev-script
git -c core.fsmonitor=false add scripts/pipestream-dev.sh
git -c core.fsmonitor=false -c commit.gpgsign=false commit -m "feat(scripts): add pipestream-dev.sh for Quarkus dev slot management

Manages start/stop/status/logs for named slots (compose, wiremock, engine,
chunker, embedder, semantic-graph, opensearch-manager, testing-sidecar,
platform-registration). Compose slot delegates to dev-services. Quarkus
slots use exact-PID tracking with a directory substring match and lsof
fallback — never pkill, never pattern kills. Per-slot state in
/tmp/pipestream-dev/ (overridable via PIPESTREAM_DEV_STATE_DIR).

Enables autonomous dev-mode management for the semantic pipeline rollout
work described in pipestream-protos/docs/semantic-pipeline/ROLLOUT.md."
```

- [ ] **Step 2: Push and open PR**

```bash
git -c core.fsmonitor=false push -u origin feat/pipestream-dev-script
gh pr create --repo ai-pipestream/dev-assets \
  --title 'feat(scripts): add pipestream-dev.sh for Quarkus dev slot management' \
  --body 'Supports the semantic pipeline rollout (pipestream-protos/docs/semantic-pipeline/ROLLOUT.md) by letting agents start/stop Quarkus dev servers with exact-PID safety. Smoke-tested against the wiremock slot.'
```

Phase 0 complete once both PRs (rename + script) are merged.

---

## Phase 1 — Contract Lock (serial, one agent)

### Task 1.1: Create `pipestream-protos` worktree for fixtures and invariants

- [ ] **Step 1: Create the worktree**

```bash
cd /work/core-services/pipestream-protos
git -c core.fsmonitor=false fetch origin
git -c core.fsmonitor=false checkout main
git -c core.fsmonitor=false pull --ff-only
git -c core.fsmonitor=false worktree add -b feat/semantic-pipeline-fixtures /work/worktrees/pipestream-protos-fixtures main
cd /work/worktrees/pipestream-protos-fixtures
mkdir -p testdata/semantic-pipeline/src/main/java/ai/pipestream/semantic/testdata
mkdir -p testdata/semantic-pipeline/src/test/java/ai/pipestream/semantic/testdata
```

### Task 1.2: `stage0_raw.textpb` fixture

**Files:**
- Create: `testdata/semantic-pipeline/stage0_raw.textpb`

**Context:** Minimal `PipeDoc` in protobuf text format. 2–3 paragraphs of body, one `VectorDirective` with two chunker configs (token and sentence) and two embedder configs (minilm and paraphrase). Matches DESIGN.md §18.

- [ ] **Step 1: Write the fixture**

Create `testdata/semantic-pipeline/stage0_raw.textpb` with the full `PipeDoc` text proto:

```textproto
# Stage 0 — raw input PipeDoc with directives set but no chunks/vectors yet.
# Used as the starting point for the semantic pipeline fixture chain.
id: "fixture-doc-001"
title: "Fixture Document"
body: "The quick brown fox jumps over the lazy dog. Every pangram contains every letter of the alphabet. Fixtures need to be deterministic to support byte-for-byte diff tests.\n\nA second paragraph exists to exercise paragraph-boundary detection. It has two sentences. That keeps the output small but non-trivial.\n\nA third paragraph exists so centroid computation has at least three granularity units."
search_metadata {
  vector_set_directives {
    directives {
      source_label: "body"
      cel_selector: "document.body"
      chunker_configs {
        config_id: "token_500_50"
        config {
          fields { key: "algorithm" value { string_value: "TOKEN" } }
          fields { key: "chunk_size" value { number_value: 500 } }
          fields { key: "chunk_overlap" value { number_value: 50 } }
        }
      }
      chunker_configs {
        config_id: "sentence_10_3"
        config {
          fields { key: "algorithm" value { string_value: "SENTENCE" } }
          fields { key: "chunk_size" value { number_value: 10 } }
          fields { key: "chunk_overlap" value { number_value: 3 } }
        }
      }
      embedder_configs {
        config_id: "minilm_v2"
        config {
          fields { key: "model_id" value { string_value: "all-MiniLM-L6-v2" } }
        }
      }
      embedder_configs {
        config_id: "paraphrase_l3"
        config {
          fields { key: "model_id" value { string_value: "paraphrase-MiniLM-L3-v2" } }
        }
      }
      field_name_template: "{source_label}_{chunker_id}_{embedder_id}"
    }
  }
}
```

### Task 1.3: `SemanticPipelineFixtures` helper with deterministic embed

**Files:**
- Create: `testdata/semantic-pipeline/src/main/java/ai/pipestream/semantic/testdata/SemanticPipelineFixtures.java`

- [ ] **Step 1: Write the helper**

```java
package ai.pipestream.semantic.testdata;

import ai.pipestream.data.v1.PipeDoc;
import com.google.protobuf.TextFormat;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Objects;

/**
 * Loads canonical semantic-pipeline stage fixtures and provides a deterministic
 * embed function for fixture construction and testing.
 *
 * Deterministic embed formula:
 *   v[i] = sin(i + hash(text)) / sqrt(dimension)
 * Every fixture builder and every wiremock mock uses this same helper so
 * stage2/stage3 fixtures are byte-identical regardless of who built them.
 */
public final class SemanticPipelineFixtures {
    private SemanticPipelineFixtures() {}

    public static PipeDoc loadStage0Raw() { return loadTextProto("stage0_raw.textpb"); }
    public static PipeDoc loadStage1PostChunker() { return loadTextProto("stage1_post_chunker.textpb"); }
    public static PipeDoc loadStage2PostEmbedder() { return loadTextProto("stage2_post_embedder.textpb"); }
    public static PipeDoc loadStage3PostSemanticGraph() { return loadTextProto("stage3_post_semantic_graph.textpb"); }

    public static float[] deterministicEmbed(String text, int dimension) {
        Objects.requireNonNull(text, "text");
        if (dimension <= 0) throw new IllegalArgumentException("dimension must be > 0");
        int h = text.hashCode();
        float norm = (float) Math.sqrt(dimension);
        float[] v = new float[dimension];
        for (int i = 0; i < dimension; i++) {
            v[i] = (float) (Math.sin(i + h) / norm);
        }
        return v;
    }

    public static List<float[]> deterministicEmbedAll(List<String> texts, int dimension) {
        return texts.stream().map(t -> deterministicEmbed(t, dimension)).toList();
    }

    private static PipeDoc loadTextProto(String resourceName) {
        try (var in = SemanticPipelineFixtures.class.getClassLoader()
                .getResourceAsStream("testdata/semantic-pipeline/" + resourceName)) {
            if (in == null) throw new IllegalStateException("fixture resource not found: " + resourceName);
            String text = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            PipeDoc.Builder builder = PipeDoc.newBuilder();
            TextFormat.getParser().merge(text, builder);
            return builder.build();
        } catch (IOException e) {
            throw new IllegalStateException("failed to load fixture: " + resourceName, e);
        }
    }
}
```

- [ ] **Step 2: Wire fixtures as classpath resources**

If the `testdata` directory isn't already a Gradle subproject, add one with a build file that includes the `.textpb` files as resources:

```groovy
// testdata/semantic-pipeline/build.gradle
plugins { id 'java-library' }
dependencies {
    api project(':common')  // for generated PipeDoc class
    api libs.protobuf.java
    api libs.assertj.core
}
sourceSets {
    main {
        resources {
            srcDirs = ['.', 'src/main/resources']
            includes = ['*.textpb']
            exclude 'src/**', 'build.gradle'
        }
    }
}
```

Adjust to the repo's actual convention. Check `pipestream-protos/testdata/` for existing patterns before adding a new subproject.

- [ ] **Step 3: Build to verify**

```bash
cd /work/worktrees/pipestream-protos-fixtures
./gradlew :testdata:semantic-pipeline:compileJava 2>&1 | tail -10
```

Expected: `BUILD SUCCESSFUL`. If the subproject name doesn't match what you used, adjust.

### Task 1.4: `stage1_post_chunker.textpb` fixture

**Files:**
- Create: `testdata/semantic-pipeline/stage1_post_chunker.textpb`

**Context:** Expected output after `module-chunker` runs on stage0. Three SPRs: `body_token_500_50`, `body_sentence_10_3`, `sentences_internal`. All have `embedding_config_id == ""`. Each chunk has `text_content`, `chunk_id`, offsets, empty `vector`. Plus `nlp_analysis` on each SPR and `source_field_analytics[]` entries.

- [ ] **Step 1: Write the fixture**

Text proto fixture with three `semantic_results` entries. Each chunk has a deterministic `chunk_id` of the form `{docHash}:{source_label}:{chunk_config_id}:{chunk_number}:{start}:{end}` per DESIGN.md §21.5. Compute docHash = `sha256b64url("fixture-doc-001")` — record the literal value once and use it throughout. (Use a small Java program or `echo -n 'fixture-doc-001' | openssl dgst -sha256 -binary | base64url` to compute; hardcode the result in the fixture.)

This fixture is long (60+ chunks). Write it via a small Java generator committed as a test utility rather than by hand. Add `SemanticPipelineFixtureGenerator.java` to the test sources and run it once:

```java
public class SemanticPipelineFixtureGenerator {
    public static void main(String[] args) {
        // 1. Load stage0_raw.textpb
        // 2. Run a minimal chunker emulation (or reuse module-chunker via classpath)
        // 3. Emit stage1_post_chunker.textpb
    }
}
```

**Simplification:** given the complexity, for the fixture itself use a hand-curated SMALL corpus (1 chunk per config) in stage0 that keeps stage1 small enough to hand-write. Revise stage0 to have only ~30 words of body text so:
- `token_500_50` emits 1 chunk
- `sentence_10_3` emits 1 chunk
- `sentences_internal` emits 3 chunks (one per sentence)

That keeps stage1 at 5 SPRs × 1–3 chunks each — ~10 chunks total, hand-writable.

Update `stage0_raw.textpb` body to: `"The quick brown fox jumps over the lazy dog. Every pangram contains every letter. Fixtures must be tiny."`

Then write stage1 by hand with that scale. Use placeholder character offsets (0, 44, 88, etc.) and deterministic chunk IDs.

- [ ] **Step 2: Commit the revised stage0 and new stage1**

```bash
git -c core.fsmonitor=false add testdata/semantic-pipeline/stage0_raw.textpb testdata/semantic-pipeline/stage1_post_chunker.textpb
git -c core.fsmonitor=false -c commit.gpgsign=false commit -m "test(semantic-pipeline): add stage0 and stage1 fixtures

Tiny fixture (single-sentence paragraphs) sized for hand-writable stage
fixtures. Used by SemanticPipelineInvariants tests and wiremock step mocks."
```

### Task 1.5: `assertPostChunker` invariant and its unit test

**Files:**
- Create: `testdata/semantic-pipeline/src/main/java/ai/pipestream/semantic/testdata/SemanticPipelineInvariants.java`
- Create: `testdata/semantic-pipeline/src/test/java/ai/pipestream/semantic/testdata/SemanticPipelineInvariantsTest.java`

- [ ] **Step 1: Write the invariant helper (chunker stage only for now)**

```java
package ai.pipestream.semantic.testdata;

import ai.pipestream.data.v1.PipeDoc;
import ai.pipestream.data.v1.SemanticProcessingResult;
import ai.pipestream.data.v1.SemanticChunk;

import static org.assertj.core.api.Assertions.assertThat;

/** Stage invariants for the three-step semantic pipeline (DESIGN.md §5). */
public final class SemanticPipelineInvariants {
    private SemanticPipelineInvariants() {}

    public static void assertPostChunker(PipeDoc doc) {
        assertThat(doc.hasSearchMetadata())
            .as("post-chunker: search_metadata must be set")
            .isTrue();
        var sm = doc.getSearchMetadata();
        for (int i = 0; i < sm.getSemanticResultsCount(); i++) {
            var spr = sm.getSemanticResults(i);
            assertThat(spr.getEmbeddingConfigId())
                .as("post-chunker: SPR[%d] must have empty embedding_config_id (placeholder)", i)
                .isEmpty();
            assertThat(spr.getSourceFieldName())
                .as("post-chunker: SPR[%d] source_field_name must be set", i)
                .isNotEmpty();
            assertThat(spr.getChunkConfigId())
                .as("post-chunker: SPR[%d] chunk_config_id must be set", i)
                .isNotEmpty();
            assertThat(spr.getChunksCount())
                .as("post-chunker: SPR[%d] must have at least one chunk", i)
                .isGreaterThan(0);
            for (int j = 0; j < spr.getChunksCount(); j++) {
                var chunk = spr.getChunks(j);
                var emb = chunk.getEmbeddingInfo();
                assertThat(emb.getTextContent())
                    .as("post-chunker: SPR[%d] chunk[%d] text_content must be set", i, j)
                    .isNotEmpty();
                assertThat(emb.getVectorCount())
                    .as("post-chunker: SPR[%d] chunk[%d] vector must be empty (placeholder)", i, j)
                    .isZero();
                assertThat(chunk.getChunkId())
                    .as("post-chunker: SPR[%d] chunk[%d] chunk_id must be set", i, j)
                    .isNotEmpty();
                assertThat(emb.getOriginalCharStartOffset())
                    .as("post-chunker: SPR[%d] chunk[%d] start offset must be >= 0", i, j)
                    .isGreaterThanOrEqualTo(0);
                assertThat(emb.getOriginalCharEndOffset())
                    .as("post-chunker: SPR[%d] chunk[%d] end offset must be >= start", i, j)
                    .isGreaterThanOrEqualTo(emb.getOriginalCharStartOffset());
                assertThat(spr.getMetadataMap())
                    .as("post-chunker: SPR[%d] must carry metadata[\"directive_key\"]", i)
                    .containsKey("directive_key");
            }
        }
        assertLexSorted(sm);
    }

    private static void assertLexSorted(ai.pipestream.data.v1.SearchMetadata sm) {
        String prev = "";
        for (int i = 0; i < sm.getSemanticResultsCount(); i++) {
            var spr = sm.getSemanticResults(i);
            String key = spr.getSourceFieldName() + "|" + spr.getChunkConfigId()
                       + "|" + spr.getEmbeddingConfigId() + "|" + spr.getResultId();
            assertThat(key.compareTo(prev))
                .as("post-chunker: SPR[%d] breaks lex sort (prev=%s, curr=%s)", i, prev, key)
                .isGreaterThanOrEqualTo(0);
            prev = key;
        }
    }
}
```

- [ ] **Step 2: Write the failing test**

```java
package ai.pipestream.semantic.testdata;

import org.junit.jupiter.api.Test;
import static ai.pipestream.semantic.testdata.SemanticPipelineFixtures.loadStage1PostChunker;
import static ai.pipestream.semantic.testdata.SemanticPipelineInvariants.assertPostChunker;

class SemanticPipelineInvariantsTest {
    @Test void stage1FixtureSatisfiesAssertPostChunker() {
        assertPostChunker(loadStage1PostChunker());
    }
}
```

- [ ] **Step 3: Run the test**

```bash
./gradlew :testdata:semantic-pipeline:test --tests 'SemanticPipelineInvariantsTest.stage1FixtureSatisfiesAssertPostChunker' -i 2>&1 | tail -40
```

Expected: PASS. If it fails, the fixture is inconsistent with the invariant — fix the fixture, not the invariant.

### Task 1.6: `stage2_post_embedder.textpb` fixture

- [ ] **Step 1: Write the fixture**

Four SPRs (2 chunker × 2 embedder) plus 2 `sentences_internal` embedded (2 embedders). Each chunk now has a populated `vector` of the correct dimension (384 for MiniLM, 384 for paraphrase-L3 — both 384 per `multi-model-embedding.md`). Vectors are computed from `SemanticPipelineFixtures.deterministicEmbed(text, 384)` and serialized as `float_value` entries in textproto.

Since textproto for 384-element float arrays is painful, write a small generator in test code that reads stage1 and emits stage2:

```java
public class Stage2FixtureGenerator {
    public static void main(String[] args) throws Exception {
        PipeDoc stage1 = SemanticPipelineFixtures.loadStage1PostChunker();
        PipeDoc stage2 = buildStage2(stage1);
        try (var out = new java.io.FileOutputStream(
                "testdata/semantic-pipeline/stage2_post_embedder.textpb")) {
            com.google.protobuf.TextFormat.printer().print(stage2, new java.io.PrintWriter(out));
        }
    }
    static PipeDoc buildStage2(PipeDoc stage1) { /* fan out placeholders per directive, populate vectors */ }
}
```

Run it once, commit the resulting fixture, delete the generator from main sources or keep it under `testdata/semantic-pipeline/src/test/java/.../generators/` as a future regen tool.

### Task 1.7: `assertPostEmbedder` and its test

- [ ] **Step 1: Extend the invariants class**

Add to `SemanticPipelineInvariants.java`:

```java
public static void assertPostEmbedder(PipeDoc doc) {
    assertThat(doc.hasSearchMetadata()).as("post-embedder: search_metadata must be set").isTrue();
    var sm = doc.getSearchMetadata();
    for (int i = 0; i < sm.getSemanticResultsCount(); i++) {
        var spr = sm.getSemanticResults(i);
        assertThat(spr.getEmbeddingConfigId())
            .as("post-embedder: SPR[%d] must have non-empty embedding_config_id", i)
            .isNotEmpty();
        assertThat(spr.getChunksCount())
            .as("post-embedder: SPR[%d] must have chunks", i)
            .isGreaterThan(0);
        for (int j = 0; j < spr.getChunksCount(); j++) {
            var emb = spr.getChunks(j).getEmbeddingInfo();
            assertThat(emb.getVectorCount())
                .as("post-embedder: SPR[%d] chunk[%d] vector must be populated", i, j)
                .isGreaterThan(0);
            assertThat(emb.getTextContent())
                .as("post-embedder: SPR[%d] chunk[%d] text_content preserved from stage1", i, j)
                .isNotEmpty();
        }
    }
    assertLexSorted(sm);
}
```

- [ ] **Step 2: Add test and run**

```java
@Test void stage2FixtureSatisfiesAssertPostEmbedder() {
    assertPostEmbedder(SemanticPipelineFixtures.loadStage2PostEmbedder());
}
```

```bash
./gradlew :testdata:semantic-pipeline:test 2>&1 | tail -30
```

Expected: both tests pass.

### Task 1.8: `stage3_post_semantic_graph.textpb` fixture

- [ ] **Step 1: Extend the generator**

```java
static PipeDoc buildStage3(PipeDoc stage2) {
    // preserve all stage2 SPRs unchanged
    // append centroid SPRs (document + paragraph + section) per (source_field, chunker, embedder)
    // append semantic-boundary SPRs using stage2 sentences_internal vectors + SemanticPipelineFixtures.deterministicEmbed
    // lex-sort the result
}
```

Run once, commit `stage3_post_semantic_graph.textpb`.

### Task 1.9: `assertPostSemanticGraph` and its test

- [ ] **Step 1: Extend invariants**

```java
public static void assertPostSemanticGraph(PipeDoc doc) {
    assertPostEmbedder(doc);  // everything from post-embedder still holds
    var sm = doc.getSearchMetadata();
    for (int i = 0; i < sm.getSemanticResultsCount(); i++) {
        var spr = sm.getSemanticResults(i);
        var cfg = spr.getChunkConfigId();
        if (cfg.endsWith("_centroid")) {
            assertThat(spr.hasCentroidMetadata())
                .as("post-graph: centroid SPR[%d] must have centroid_metadata", i)
                .isTrue();
            assertThat(spr.getChunksCount())
                .as("post-graph: centroid SPR[%d] must have exactly one chunk", i)
                .isEqualTo(1);
        }
        if ("semantic".equals(cfg)) {
            assertThat(spr.getSemanticConfigId())
                .as("post-graph: boundary SPR[%d] semantic_config_id must be set", i)
                .isNotEmpty();
            assertThat(spr.getChunksCount())
                .as("post-graph: boundary SPR[%d] must have chunks", i)
                .isGreaterThan(0);
        }
    }
}
```

- [ ] **Step 2: Add test, run all three**

```java
@Test void stage3FixtureSatisfiesAssertPostSemanticGraph() {
    assertPostSemanticGraph(SemanticPipelineFixtures.loadStage3PostSemanticGraph());
}
```

```bash
./gradlew :testdata:semantic-pipeline:test 2>&1 | tail -30
```

Expected: all three tests pass.

### Task 1.10: Commit P1a and push

- [ ] **Step 1: Commit**

```bash
cd /work/worktrees/pipestream-protos-fixtures
git -c core.fsmonitor=false add testdata/semantic-pipeline/
git -c core.fsmonitor=false -c commit.gpgsign=false commit -m "feat(semantic-pipeline): add stage fixtures and invariants

Adds stage0/stage1/stage2/stage3 textproto fixtures, a loader helper
(SemanticPipelineFixtures) with a deterministic embed function, and
stage invariants (SemanticPipelineInvariants) per DESIGN.md §5.
Three unit tests prove each fixture satisfies its corresponding
assertPost* invariant. These are the contract lock consumed by the
three wiremock step mocks (P1c) and the module refactors (R1/R2/R3)."
```

- [ ] **Step 2: Push**

```bash
git -c core.fsmonitor=false push -u origin feat/semantic-pipeline-fixtures
```

Do not open a PR yet — P1c (wiremock mocks) will land in its own PR on its own repo, and P1 as a whole merges when both are ready.

### Task 1.11: Create `pipestream-wiremock-server` worktree

- [ ] **Step 1: Create worktree**

```bash
cd /work/core-services/pipestream-wiremock-server
git -c core.fsmonitor=false fetch origin
git -c core.fsmonitor=false checkout main
git -c core.fsmonitor=false pull --ff-only
git -c core.fsmonitor=false worktree add -b feat/semantic-pipeline-step-mocks /work/worktrees/pipestream-wiremock-server-step-mocks main
cd /work/worktrees/pipestream-wiremock-server-step-mocks
```

### Task 1.12: `ChunkerStepMock` scaffolding and registration

**Files:**
- Create: `src/main/java/ai/pipestream/wiremock/client/ChunkerStepMock.java`
- Modify: `src/main/resources/META-INF/services/ai.pipestream.wiremock.client.ServiceMockInitializer`

**Context:** Follow the existing `PipeStepProcessorMock` pattern. Implements `ServiceMockInitializer`. Registers stubs against `PipeStepProcessorService.ProcessData` scoped to `x-module-name: chunker` header.

- [ ] **Step 1: Inspect the existing pattern**

```bash
head -80 src/main/java/ai/pipestream/wiremock/client/PipeStepProcessorMock.java
cat src/main/resources/META-INF/services/ai.pipestream.wiremock.client.ServiceMockInitializer
```

Note the class layout, how it registers stubs via `WireMockGrpcService`, and how other mocks use `x-module-name` matchers.

- [ ] **Step 2: Write `ChunkerStepMock`**

```java
package ai.pipestream.wiremock.client;

import ai.pipestream.data.module.v1.PipeStepProcessorServiceGrpc;
import ai.pipestream.data.module.v1.ProcessDataRequest;
import ai.pipestream.data.module.v1.ProcessDataResponse;
import ai.pipestream.data.module.v1.ProcessingOutcome;
import ai.pipestream.data.v1.PipeDoc;
import ai.pipestream.semantic.testdata.SemanticPipelineFixtures;
import com.github.tomakehurst.wiremock.WireMockServer;
import io.grpc.Status;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.wiremock.grpc.dsl.WireMockGrpcService;

import static com.github.tomakehurst.wiremock.client.WireMock.equalTo;
import static org.wiremock.grpc.dsl.WireMockGrpc.method;
import static org.wiremock.grpc.dsl.WireMockGrpc.message;

/**
 * Header-scoped mock for the chunker pipeline step.
 *
 * Scenarios (switched via x-mock-scenario metadata header):
 *   success (default)  → stage1_post_chunker.textpb wrapped in a SUCCESS response
 *   fail-precondition  → FAILED_PRECONDITION
 *   fail-invalid-arg   → INVALID_ARGUMENT
 *   fail-internal      → INTERNAL
 *   partial            → SUCCESS but with missing chunks (stage1 minus half its chunks)
 *   slow               → SUCCESS delayed by 3000 ms
 *
 * Module discriminator: x-module-name = "chunker".
 */
public class ChunkerStepMock implements ServiceMockInitializer {
    private static final Logger LOG = LoggerFactory.getLogger(ChunkerStepMock.class);
    private static final String MODULE_NAME = "chunker";

    @Override
    public void register(WireMockServer wireMock) {
        var svc = new WireMockGrpcService(
            new org.wiremock.grpc.internal.WireMockGrpcExtension(wireMock),
            PipeStepProcessorServiceGrpc.SERVICE_NAME);
        registerSuccess(svc);
        registerFailPrecondition(svc);
        registerFailInvalidArg(svc);
        registerFailInternal(svc);
        registerPartial(svc);
        registerSlow(svc);
        LOG.info("ChunkerStepMock registered 6 scenarios on PipeStepProcessorService");
    }

    private void registerSuccess(WireMockGrpcService svc) {
        PipeDoc stage1 = SemanticPipelineFixtures.loadStage1PostChunker();
        ProcessDataResponse response = ProcessDataResponse.newBuilder()
            .setOutcome(ProcessingOutcome.PROCESSING_OUTCOME_SUCCESS)
            .setDocument(stage1)
            .build();
        svc.stubFor(method("ProcessData")
            .withHeader("x-module-name", equalTo(MODULE_NAME))
            .willReturn(message(response)));
    }

    // other scenarios — see Task 1.13
    private void registerFailPrecondition(WireMockGrpcService svc) {}
    private void registerFailInvalidArg(WireMockGrpcService svc) {}
    private void registerFailInternal(WireMockGrpcService svc) {}
    private void registerPartial(WireMockGrpcService svc) {}
    private void registerSlow(WireMockGrpcService svc) {}
}
```

- [ ] **Step 3: Register via ServiceLoader**

Append to `src/main/resources/META-INF/services/ai.pipestream.wiremock.client.ServiceMockInitializer`:

```
ai.pipestream.wiremock.client.ChunkerStepMock
ai.pipestream.wiremock.client.EmbedderStepMock
ai.pipestream.wiremock.client.SemanticGraphStepMock
```

- [ ] **Step 4: Build to verify compilation**

```bash
./gradlew :compileJava 2>&1 | tail -10
```

Expected: `BUILD SUCCESSFUL`.

### Task 1.13: `ChunkerStepMock` full scenario set

- [ ] **Step 1: Implement the remaining five scenarios**

Each scenario matches `x-mock-scenario` with a distinct value. Example `fail-precondition`:

```java
private void registerFailPrecondition(WireMockGrpcService svc) {
    svc.stubFor(method("ProcessData")
        .withHeader("x-module-name", equalTo(MODULE_NAME))
        .withHeader("x-mock-scenario", equalTo("fail-precondition"))
        .willReturn(WireMockGrpc.Response.statusException(Status.FAILED_PRECONDITION)));
}
```

Repeat for `fail-invalid-arg` (`Status.INVALID_ARGUMENT`), `fail-internal` (`Status.INTERNAL`).

`partial` returns a modified stage1 with half its chunks removed (use `toBuilder()` per `feedback-use-builders.md`):

```java
private void registerPartial(WireMockGrpcService svc) {
    PipeDoc stage1 = SemanticPipelineFixtures.loadStage1PostChunker();
    PipeDoc partial = stage1.toBuilder()
        .setSearchMetadata(stage1.getSearchMetadata().toBuilder()
            .clearSemanticResults()
            // only re-add even-indexed SPRs
            .addAllSemanticResults(
                java.util.stream.IntStream.range(0, stage1.getSearchMetadata().getSemanticResultsCount())
                    .filter(i -> i % 2 == 0)
                    .mapToObj(i -> stage1.getSearchMetadata().getSemanticResults(i))
                    .toList())
            .build())
        .build();
    ProcessDataResponse response = ProcessDataResponse.newBuilder()
        .setOutcome(ProcessingOutcome.PROCESSING_OUTCOME_SUCCESS)
        .setDocument(partial)
        .build();
    svc.stubFor(method("ProcessData")
        .withHeader("x-module-name", equalTo(MODULE_NAME))
        .withHeader("x-mock-scenario", equalTo("partial"))
        .willReturn(message(response)));
}
```

`slow` adds a fixed delay:

```java
private void registerSlow(WireMockGrpcService svc) {
    PipeDoc stage1 = SemanticPipelineFixtures.loadStage1PostChunker();
    ProcessDataResponse response = ProcessDataResponse.newBuilder()
        .setOutcome(ProcessingOutcome.PROCESSING_OUTCOME_SUCCESS)
        .setDocument(stage1)
        .build();
    svc.stubFor(method("ProcessData")
        .withHeader("x-module-name", equalTo(MODULE_NAME))
        .withHeader("x-mock-scenario", equalTo("slow"))
        .willReturn(message(response).withFixedDelay(3000)));
}
```

### Task 1.14: `ChunkerStepMockTest`

**Files:**
- Create: `src/test/java/ai/pipestream/wiremock/client/ChunkerStepMockTest.java`

- [ ] **Step 1: Write the test**

```java
package ai.pipestream.wiremock.client;

import ai.pipestream.data.module.v1.PipeStepProcessorServiceGrpc;
import ai.pipestream.data.module.v1.ProcessDataRequest;
import ai.pipestream.data.module.v1.ProcessDataResponse;
import ai.pipestream.data.module.v1.ProcessingOutcome;
import ai.pipestream.semantic.testdata.SemanticPipelineFixtures;
import ai.pipestream.semantic.testdata.SemanticPipelineInvariants;
import io.grpc.ManagedChannel;
import io.grpc.Metadata;
import io.grpc.Status;
import io.grpc.StatusRuntimeException;
import io.grpc.stub.MetadataUtils;
import org.junit.jupiter.api.*;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class ChunkerStepMockTest {
    private static DirectWireMockGrpcServer server;
    private static ManagedChannel channel;

    @BeforeAll static void setUp() {
        server = new DirectWireMockGrpcServer();
        server.start();
        channel = server.newChannel();
    }
    @AfterAll static void tearDown() { channel.shutdownNow(); server.stop(); }

    @Test void successScenarioReturnsStage1Fixture() {
        var stub = stubWithHeaders("chunker", null);
        ProcessDataResponse resp = stub.processData(
            ProcessDataRequest.newBuilder().setDocument(SemanticPipelineFixtures.loadStage0Raw()).build());
        assertThat(resp.getOutcome())
            .as("success scenario must return SUCCESS outcome")
            .isEqualTo(ProcessingOutcome.PROCESSING_OUTCOME_SUCCESS);
        SemanticPipelineInvariants.assertPostChunker(resp.getDocument());
    }

    @Test void failPreconditionScenarioReturnsStatus() {
        var stub = stubWithHeaders("chunker", "fail-precondition");
        assertThatThrownBy(() -> stub.processData(ProcessDataRequest.getDefaultInstance()))
            .isInstanceOf(StatusRuntimeException.class)
            .extracting(e -> ((StatusRuntimeException) e).getStatus().getCode())
            .as("fail-precondition returns FAILED_PRECONDITION")
            .isEqualTo(Status.Code.FAILED_PRECONDITION);
    }

    // similar tests for fail-invalid-arg, fail-internal, partial, slow

    private PipeStepProcessorServiceGrpc.PipeStepProcessorServiceBlockingStub stubWithHeaders(
            String moduleName, String scenario) {
        Metadata md = new Metadata();
        md.put(Metadata.Key.of("x-module-name", Metadata.ASCII_STRING_MARSHALLER), moduleName);
        if (scenario != null) {
            md.put(Metadata.Key.of("x-mock-scenario", Metadata.ASCII_STRING_MARSHALLER), scenario);
        }
        return PipeStepProcessorServiceGrpc.newBlockingStub(channel)
            .withInterceptors(MetadataUtils.newAttachHeadersInterceptor(md));
    }
}
```

- [ ] **Step 2: Run the test**

```bash
./gradlew :test --tests 'ChunkerStepMockTest' 2>&1 | tail -30
```

Expected: all scenario tests pass.

### Task 1.15: `EmbedderStepMock` and its test

Repeat Task 1.12, 1.13, 1.14 for `EmbedderStepMock` with `x-module-name: embedder`. The success scenario loads `stage2_post_embedder.textpb` and the test calls `SemanticPipelineInvariants.assertPostEmbedder(resp.getDocument())`.

- [ ] **Step 1: Create `EmbedderStepMock.java`** (copy ChunkerStepMock, change module name, change fixture to stage2)
- [ ] **Step 2: Create `EmbedderStepMockTest.java`** (copy ChunkerStepMockTest, switch to `assertPostEmbedder`)
- [ ] **Step 3: Run tests**

```bash
./gradlew :test --tests 'EmbedderStepMockTest' 2>&1 | tail -30
```

Expected: all scenario tests pass.

### Task 1.16: `SemanticGraphStepMock` and its test

Same pattern. `x-module-name: semantic-graph`, success loads `stage3_post_semantic_graph.textpb`, test asserts with `assertPostSemanticGraph`.

- [ ] **Step 1: Create `SemanticGraphStepMock.java`**
- [ ] **Step 2: Create `SemanticGraphStepMockTest.java`**
- [ ] **Step 3: Run tests**

```bash
./gradlew :test --tests 'SemanticGraphStepMockTest' 2>&1 | tail -30
```

Expected: all scenario tests pass.

### Task 1.17: `MocksShowcaseTest` round-trip

**Files:**
- Modify: `src/test/java/ai/pipestream/wiremock/client/MocksShowcaseTest.java`

- [ ] **Step 1: Add the round-trip test**

```java
@Test void semanticPipelineRoundTripPassesAllInvariants() {
    // One-shot: call chunker mock, assert post-chunker; call embedder mock, assert post-embedder; call graph mock, assert post-graph.
    // Because mocks return canned fixtures, the "input" side doesn't affect output shape.
    // This test proves: (a) header dispatch works, (b) each mock loads its fixture, (c) fixtures form a coherent chain.
    var stage0 = SemanticPipelineFixtures.loadStage0Raw();
    var chunkerStub = stubWithHeaders("chunker", null);
    var embedderStub = stubWithHeaders("embedder", null);
    var graphStub = stubWithHeaders("semantic-graph", null);

    var stage1 = chunkerStub.processData(
        ProcessDataRequest.newBuilder().setDocument(stage0).build()).getDocument();
    SemanticPipelineInvariants.assertPostChunker(stage1);

    var stage2 = embedderStub.processData(
        ProcessDataRequest.newBuilder().setDocument(stage1).build()).getDocument();
    SemanticPipelineInvariants.assertPostEmbedder(stage2);

    var stage3 = graphStub.processData(
        ProcessDataRequest.newBuilder().setDocument(stage2).build()).getDocument();
    SemanticPipelineInvariants.assertPostSemanticGraph(stage3);

    assertThat(stage3)
        .as("round-trip stage3 must byte-match the stored fixture")
        .isEqualTo(SemanticPipelineFixtures.loadStage3PostSemanticGraph());
}
```

- [ ] **Step 2: Run showcase test**

```bash
./gradlew :test --tests 'MocksShowcaseTest' 2>&1 | tail -30
```

Expected: round-trip test passes. If `isEqualTo` fails, check fixture determinism — the mocks must return identical fixtures every call.

### Task 1.18: Commit P1c/P1d and push

- [ ] **Step 1: Commit**

```bash
cd /work/worktrees/pipestream-wiremock-server-step-mocks
git -c core.fsmonitor=false add -A
git -c core.fsmonitor=false -c commit.gpgsign=false commit -m "feat(mocks): add Chunker/Embedder/SemanticGraph step mocks

Three header-scoped step mocks for the semantic pipeline refactor.
Each mock exposes six scenarios (success/fail-precondition/fail-invalid-arg/
fail-internal/partial/slow) driven by x-mock-scenario header, and returns
canned stage fixtures from pipestream-protos testdata.

MocksShowcaseTest gains a round-trip test that exercises all three mocks
in sequence and asserts each stage output against its invariant."
```

- [ ] **Step 2: Push and open PR**

```bash
git -c core.fsmonitor=false push -u origin feat/semantic-pipeline-step-mocks
gh pr create --repo ai-pipestream/pipestream-wiremock-server \
  --title 'feat(mocks): semantic pipeline step mocks (contract lock)' \
  --body 'Implements P1c/P1d from pipestream-protos/docs/semantic-pipeline/ROLLOUT.md. Three header-scoped mocks + showcase round-trip test. Depends on pipestream-protos branch feat/semantic-pipeline-fixtures; merge that first or in parallel.'
```

**Contract is locked once both PRs merge.** From this point forward fixtures cannot be changed without stopping all parallel work.

---

## Phase 2 — Supporting Work (can overlap Phase 1 tail)

### Task 2.1: P2a — Verify `DjlServingClient` is public-facing

- [ ] **Step 1: Grep the extension runtime for the interface**

```bash
cd /work/modules/module-embedder/quarkus-djl-embeddings/runtime
grep -r 'interface DjlServingClient' src/main/java
grep -r '@RegisterRestClient' src/main/java
```

Expected: the interface exists at `ai.pipestream.quarkus.djl.serving.runtime.client.DjlServingClient` annotated with `@Path("/")` and `@RegisterRestClient(configKey = "djl-serving")`. It IS public.

- [ ] **Step 2: Confirm module-embedder already consumes it**

```bash
grep -r 'DjlServingClient' /work/modules/module-embedder/module-embedder/src/main/java | head -5
```

Expected: injection in `DjlServingEmbeddingProvider` or similar. Confirms the pattern works; `module-semantic-graph` can use the same pattern in R3.

- [ ] **Step 3: Record the confirmation**

No code change. Append a note to `module-semantic-graph`'s P2a worktree (none created — this is a read-only task). If the interface turned out to be package-private or not public, create `/work/worktrees/module-embedder-djl-client-verify` on branch `chore/djl-client-public-api`, change the annotation, and PR. Otherwise skip.

### Task 2.2: P2b — `DirectivePopulator` stub in `pipestream-engine`

**Files:**
- Create: `src/main/java/ai/pipestream/engine/directives/DirectivePopulator.java`
- Create: `src/main/java/ai/pipestream/engine/directives/NoOpDirectivePopulator.java`
- Modify: `src/main/java/.../EngineV1Service.java` (wire the call)

- [ ] **Step 1: Create the worktree**

```bash
cd /work/core-services/pipestream-engine
git -c core.fsmonitor=false fetch origin
git -c core.fsmonitor=false checkout main
git -c core.fsmonitor=false pull --ff-only
git -c core.fsmonitor=false worktree add -b feat/directive-populator-stub /work/worktrees/pipestream-engine-directive-populator-stub main
cd /work/worktrees/pipestream-engine-directive-populator-stub
```

- [ ] **Step 2: Write the interface**

```java
package ai.pipestream.engine.directives;

import ai.pipestream.data.v1.PipeDoc;
import io.smallrye.mutiny.Uni;

/**
 * Populates VectorSetDirectives on a PipeDoc before it enters the semantic sub-pipeline.
 * <p>
 * Stub today: see {@link NoOpDirectivePopulator}. Real implementation (task #78) will read
 * VectorSetEntity rows referenced in graph config and attach them as VectorDirective entries
 * on doc.search_metadata.vector_set_directives.
 */
public interface DirectivePopulator {
    Uni<PipeDoc> populateDirectives(PipeDoc input);
}
```

- [ ] **Step 3: Write the no-op implementation**

```java
package ai.pipestream.engine.directives;

import ai.pipestream.data.v1.PipeDoc;
import io.smallrye.mutiny.Uni;
import jakarta.enterprise.context.ApplicationScoped;

/** No-op stub. TODO task #78: replace with VectorSetEntity-driven implementation. */
@ApplicationScoped
public class NoOpDirectivePopulator implements DirectivePopulator {
    @Override
    public Uni<PipeDoc> populateDirectives(PipeDoc input) {
        return Uni.createFrom().item(input);
    }
}
```

- [ ] **Step 4: Wire into `EngineV1Service.processNode`**

Find the spot where `PipeStepProcessorService.processData` is dispatched. Inject `DirectivePopulator` at class top:

```java
@Inject DirectivePopulator directivePopulator;
```

Call it before dispatch:

```java
return directivePopulator.populateDirectives(doc)
    .chain(populated -> dispatchToProcessor(populated, node));
```

Note the current signature of `processNode` — adjust the chain accordingly to not break existing behavior.

- [ ] **Step 5: Run engine tests**

```bash
./gradlew test 2>&1 | tail -40
```

Expected: existing test suite still passes. No behavioral change because the stub is a pass-through.

- [ ] **Step 6: Commit, push, PR**

```bash
git -c core.fsmonitor=false add -A
git -c core.fsmonitor=false -c commit.gpgsign=false commit -m "feat(engine): add DirectivePopulator stub

Wires a no-op DirectivePopulator into EngineV1Service.processNode so
the semantic pipeline refactor (pipestream-protos docs/semantic-pipeline/DESIGN.md §12.1)
has a place to hook real VectorSetEntity-driven directive population
later (task #78) without requiring another engine refactor. Stub today
is a pass-through, so behavior is unchanged."
git -c core.fsmonitor=false push -u origin feat/directive-populator-stub
gh pr create --repo ai-pipestream/pipestream-engine --title 'feat(engine): add DirectivePopulator stub' --body 'Part of semantic pipeline rollout P2b.'
```

### Task 2.3: P2b — `VectorSetProvisioner` stub in `pipestream-opensearch`

**Files:**
- Create: `opensearch-manager/src/main/java/.../vectorset/VectorSetProvisioner.java`
- Create: `opensearch-manager/src/main/java/.../vectorset/NoOpVectorSetProvisioner.java`

- [ ] **Step 1: Create worktree**

```bash
cd /work/core-services/pipestream-opensearch
git -c core.fsmonitor=false fetch origin
git -c core.fsmonitor=false checkout main
git -c core.fsmonitor=false pull --ff-only
git -c core.fsmonitor=false worktree add -b feat/vector-set-provisioner-stub /work/worktrees/pipestream-opensearch-vector-set-provisioner-stub main
cd /work/worktrees/pipestream-opensearch-vector-set-provisioner-stub
```

- [ ] **Step 2: Write interface + no-op (mirror the engine stub pattern)**

```java
package ai.pipestream.opensearch.manager.vectorset;

import ai.pipestream.data.v1.VectorSetDirectives;
import io.smallrye.mutiny.Uni;

/**
 * Ensures the OpenSearch index has knn_vector fields corresponding to the given directives.
 * <p>
 * Stub today: see {@link NoOpVectorSetProvisioner}. Real implementation (task #79) will
 * eagerly create VectorSetEntity rows and call the indexing strategy to put mappings
 * before docs arrive.
 */
public interface VectorSetProvisioner {
    Uni<Void> ensureFieldsForDirectives(VectorSetDirectives directives, String indexName);
}
```

```java
package ai.pipestream.opensearch.manager.vectorset;

import ai.pipestream.data.v1.VectorSetDirectives;
import io.smallrye.mutiny.Uni;
import jakarta.enterprise.context.ApplicationScoped;

/** No-op stub. TODO task #79: replace with eager VectorSetEntity creation + putMapping. */
@ApplicationScoped
public class NoOpVectorSetProvisioner implements VectorSetProvisioner {
    @Override
    public Uni<Void> ensureFieldsForDirectives(VectorSetDirectives directives, String indexName) {
        return Uni.createFrom().voidItem();
    }
}
```

- [ ] **Step 3: Build and run opensearch-manager tests**

```bash
./gradlew :opensearch-manager:test 2>&1 | tail -40
```

Expected: existing tests still pass.

- [ ] **Step 4: Commit, push, PR**

```bash
git -c core.fsmonitor=false add -A
git -c core.fsmonitor=false -c commit.gpgsign=false commit -m "feat(opensearch-manager): add VectorSetProvisioner stub

No-op stub per pipestream-protos docs/semantic-pipeline/DESIGN.md §12.2.
Real implementation (task #79) will eagerly create VectorSetEntity rows
and put mappings. Today the existing lazy ensureFlatKnnField path in
SeparateIndicesIndexingStrategy and ChunkCombinedIndexingStrategy
continues to own field creation, so there is no behavioral change."
git -c core.fsmonitor=false push -u origin feat/vector-set-provisioner-stub
gh pr create --repo ai-pipestream/pipestream-opensearch --title 'feat(opensearch-manager): add VectorSetProvisioner stub' --body 'Part of semantic pipeline rollout P2b.'
```

---

## Phase 3 — Parallel Refactor (three subagent work packets)

**Dispatch rule:** do NOT dispatch any Phase 3 agent until Phase 1 PRs (fixtures + wiremock mocks) are merged. Fixtures are now LOCKED; no agent may modify them.

Each work packet below is a self-contained prompt for a subagent dispatched via the `Agent` tool with `isolation: "worktree"`. The packets are summaries — the dispatching operator (you) reads ROLLOUT.md §8.2–§8.4 and DESIGN.md §7 for the full spec, then prompts the subagent with: "Implement R{n} per this plan's work packet, this ROLLOUT.md section, and DESIGN.md §7.{n}. You may create your own step-option record class; you may NOT modify any fixture, any SemanticPipelineInvariants assertion, or any wiremock mock." Ends after the merge gate passes.

### R1 Work Packet — `module-chunker`

**Repo:** `ai-pipestream/module-chunker`
**Branch:** `refactor/semantic-pipeline-three-step`
**Agent isolation:** `Agent` tool `isolation: "worktree"`
**DESIGN.md section:** §7.1
**ROLLOUT.md section:** §8.2

**Scope:**

1. Create `ChunkerStepOptions` (Java record) in `src/main/java/ai/pipestream/module/chunker/config/`. Parse from `ProcessConfiguration.json_config` via Jackson. Fields per DESIGN.md §6.1. `@JsonIgnoreProperties(ignoreUnknown = true)`. `effective*()` default helpers.
2. Create `DirectiveKeyComputer` (pure function) that computes `directive_key = sha256b64url(source_label + "|" + cel_selector + "|" + sorted(chunker_config_ids) + "|" + sorted(embedder_config_ids))` per DESIGN.md §21.2.
3. Create `ChunkCacheService` backed by either `@CacheResult` or `ReactiveRedisDataSource` (implementer's choice per §21.6). Keys: `chunk:{sha256b64url(text)}:{chunker_config_id}`. TTL per options. Serializes `List<SemanticChunk>` to protobuf bytes.
4. Rewrite `ChunkerGrpcImpl.processData` per DESIGN.md §7.1 steps 1–7:
   - Parse options; fail `INVALID_ARGUMENT` on parse error.
   - Resolve directives from `vector_set_directives`; fail `FAILED_PRECONDITION` if absent.
   - Validate source_label uniqueness; compute and stamp `directive_key` on every SPR.
   - For each directive × chunker_config: cache lookup → compute on miss → writeback.
   - Always emit `sentences_internal` SPR when applicable.
   - Use deterministic IDs per §21.5 (`docHash = sha256b64url(doc_id)`).
   - RTBF gate on cache writes per §21.7.
   - Lex sort at end.
5. Update unit tests to consume `stage0_raw.textpb` and assert output satisfies `SemanticPipelineInvariants.assertPostChunker`.
6. Add integration test that runs real chunker against `EmbedderStepMock` (wiremock) to prove chunker output is accepted by the downstream mock.
7. The existing Bible KJV / court opinions tests from session 2026-03-28 must stay green.

**Merge gate:** branch CI passes; `assertPostChunker` holds on real output for the stage0 fixture; integration test against `EmbedderStepMock` passes; no scripts carry broad-kill commands; commits carry no AI attribution.

### R2 Work Packet — `module-embedder`

**Repo:** `ai-pipestream/module-embedder`
**Branch:** `refactor/semantic-pipeline-three-step`
**Agent isolation:** `Agent` tool `isolation: "worktree"`
**DESIGN.md section:** §7.2
**ROLLOUT.md section:** §8.3

**Scope:**

1. Create `EmbedderStepOptions` record with fields per DESIGN.md §6.2.
2. Create `EmbedCacheService` backed by `ReactiveRedisDataSource.value(String.class, byte[].class).mget(keys)` per §21.6. Keys: `embed:{sha256b64url(text)}:{embedding_config_id}`. TTL per options.
3. Rewrite `EmbedderGrpcImpl.processData` per DESIGN.md §7.2 steps 1–8:
   - Parse options; fail on parse error.
   - Resolve directives.
   - Call `SemanticPipelineInvariants.assertPostChunker(doc)` on input; fail `FAILED_PRECONDITION` on violation.
   - Partition SPRs into placeholders and pass-throughs.
   - For each placeholder × each `NamedEmbedderConfig`: batch `MGET`, fan out DJL calls for misses, `MSET` writeback.
   - Bounded retry on transient DJL errors (`maxRetryAttempts`, `retryBackoffMs`).
   - Replace placeholders with populated SPRs (fan-out).
   - Lex sort.
4. RTBF gate on cache writes.
5. Deterministic IDs per §21.5.
6. **MANDATORY REGRESSION TEST** for DESIGN.md §22.5 MiniLM sentence-chunk loss:

```
Given: an embedder-step input with 312 sentence chunks × minilm_v2 model
When: DJL returns 400 on 144 of them (exercised via the partial scenario on DjlServingClient mock)
Then: after retry, every chunk has a populated vector OR the whole doc fails explicitly — never a silent hole
```

7. Integration test against `ChunkerStepMock` upstream and `SemanticGraphStepMock` downstream.

**Merge gate:** branch CI + invariants + §22.5 regression test + integration tests green. Merging without the §22.5 test is a rollback trigger.

### R3 Work Packet — `module-semantic-graph`

**Repo:** `ai-pipestream/module-semantic-graph`
**Branch:** `refactor/semantic-pipeline-three-step`
**Agent isolation:** `Agent` tool `isolation: "worktree"`
**DESIGN.md section:** §7.3
**ROLLOUT.md section:** §8.4

**Scope:**

1. Create `SemanticGraphStepOptions` record with fields per DESIGN.md §6.3. `boundary_embedding_model_id` is REQUIRED when `compute_semantic_boundaries` is true.
2. Add dependency on `quarkus-djl-embeddings-runtime`.
3. Create `SemanticGraphEmbedHelper` (~50 lines): given `List<String>` + model ID, pack all texts into one DJL Serving `predict` call via `DjlServingClient`, return `List<float[]>`. No cache, no fan-out, at most one retry. No custom thread pool.
4. Rewrite `SemanticGraphGrpcImpl.processData` per DESIGN.md §7.3 steps 1–8:
   - Parse options; fail on parse error.
   - Call `assertPostEmbedder` on input.
   - Group SPRs by (source_field, chunker, embedder) triple.
   - Emit document / paragraph / section centroids per enabled flags using existing `CentroidComputer`.
   - If `compute_semantic_boundaries`: resolve `boundary_embedding_model_id` against loaded DJL models (fail `FAILED_PRECONDITION` if not resolvable), run `SemanticBoundaryDetector` on `sentences_internal` vectors, enforce `max_semantic_chunks_per_doc` hard cap (fail `INTERNAL` if exceeded), re-embed boundary group text via `SemanticGraphEmbedHelper`.
   - Append new SPRs; NEVER modify Stage 2 SPRs that are carried forward.
   - Lex sort.
5. Integration test against `EmbedderStepMock` upstream.
6. Deep-equal assertion: Stage 2 prefix of `semantic_results[]` must be byte-identical to the input.

**Merge gate:** branch CI + `assertPostSemanticGraph` invariant + deep-equal preservation test all green.

---

## Phase 4 — Integration (R4 + R5)

### Task 4.1: R4 — Update `module-testing-sidecar` graph wiring

**Files:**
- Modify: `src/main/java/ai/pipestream/module/pipelineprobe/e2e/JdbcCrawlE2ETestService.java`
- Modify: `S3CrawlE2ETestService.java`
- Modify: `TransportTestService.java`
- Modify: `E2EStep`, `E2ETestState`

- [ ] **Step 1: Create worktree**

```bash
cd /work/modules/module-testing-sidecar
git -c core.fsmonitor=false fetch origin
git -c core.fsmonitor=false checkout main
git -c core.fsmonitor=false pull --ff-only
git -c core.fsmonitor=false worktree add -b feat/semantic-pipeline-graph-wiring /work/worktrees/module-testing-sidecar-graph-wiring main
cd /work/worktrees/module-testing-sidecar-graph-wiring
```

- [ ] **Step 2: Update graph topology**

Search-and-replace the graph build from `parser → chunker → semantic-manager → opensearch-sink` to `parser → chunker → embedder → semantic-graph → opensearch-sink`. Each E2E service builds its graph via the engine's `PipelineGraphService` — find the node list and update it.

```bash
grep -rn 'semantic-manager\|semanticManager' src/main/java
```

Expected: list of locations that need renaming. Update each to `semantic-graph` / `semanticGraph`.

- [ ] **Step 3: Run sidecar tests with the new topology**

```bash
./scripts/pipestream-dev.sh start compose
./scripts/pipestream-dev.sh start chunker --with-deps
./scripts/pipestream-dev.sh start embedder
./scripts/pipestream-dev.sh start semantic-graph
./scripts/pipestream-dev.sh start engine
./scripts/pipestream-dev.sh start opensearch-manager
./gradlew :quarkusIntTest 2>&1 | tail -60
```

Expected: sidecar's own IT suite passes against the new topology.

- [ ] **Step 4: Commit and PR**

```bash
git -c core.fsmonitor=false add -A
git -c core.fsmonitor=false -c commit.gpgsign=false commit -m "feat(testing-sidecar): wire new three-step semantic pipeline

Updates graph topology from chunker → semantic-manager → opensearch-sink
to chunker → embedder → semantic-graph → opensearch-sink across
JdbcCrawlE2ETestService, S3CrawlE2ETestService, and TransportTestService.
E2EStep and E2ETestState rename to match. No contract change on the
sidecar's public API."
git -c core.fsmonitor=false push -u origin feat/semantic-pipeline-graph-wiring
gh pr create --repo ai-pipestream/module-testing-sidecar --title 'feat(testing-sidecar): wire three-step semantic pipeline' --body 'Implements R4 from pipestream-protos docs/semantic-pipeline/ROLLOUT.md. Depends on R1/R2/R3 merges.'
```

### Task 4.2: R5 — JDBC gRPC E2E run (3-doc)

- [ ] **Step 1: Start full stack**

```bash
pipestream-dev.sh start testing-sidecar --with-deps
# this starts compose, platform-registration, engine, chunker, embedder, semantic-graph, opensearch-manager, and the sidecar
pipestream-dev.sh status
```

Expected: all nine slots RUNNING.

- [ ] **Step 2: Run 3-doc JDBC gRPC E2E from the sidecar UI**

Open the sidecar UI (`http://localhost:<sidecar-port>/`) and click the 3-doc JDBC gRPC run. Record wall clock.

Or via CLI:

```bash
curl -X POST http://localhost:<sidecar-port>/api/e2e/jdbc \
  -H 'Content-Type: application/json' \
  -d '{"docCount": 3, "transport": "grpc", "enableSemantic": true}'
```

Expected result: 3/3 passing, wall clock ≤ 5 s (§13 gate).

- [ ] **Step 3: Record the wall clock**

Note the number in a scratch file — you'll need it for Task 4.5.

### Task 4.3: R5 — JDBC gRPC E2E (20-doc and 100-doc) + Kafka runs

- [ ] **Step 1: 20-doc gRPC run**

Same as Task 4.2 Step 2 with `docCount: 20`. Gate: ≤ 15 s.

- [ ] **Step 2: 100-doc gRPC run**

Same with `docCount: 100`. Gate: ≤ 60 s.

- [ ] **Step 3: 3-doc Kafka run**

```bash
curl -X POST http://localhost:<sidecar-port>/api/e2e/jdbc \
  -H 'Content-Type: application/json' \
  -d '{"docCount": 3, "transport": "kafka", "enableSemantic": true}'
```

Gate: within 10% of the gRPC wall clock from Task 4.2.

- [ ] **Step 4: 20-doc Kafka run**

Same with `docCount: 20`.

### Task 4.4: R5 — Gate verification and §22.5 regression check

- [ ] **Step 1: Per-step p95 latencies from audit trail**

Query the pipeline-events audit trail for the 100-doc run:

```bash
# adjust to however audit events are queried in the sidecar/engine
curl -s 'http://localhost:<engine-port>/api/audit/p95?run_id=<run-id>&step=chunker'
curl -s 'http://localhost:<engine-port>/api/audit/p95?run_id=<run-id>&step=embedder'
curl -s 'http://localhost:<engine-port>/api/audit/p95?run_id=<run-id>&step=semantic-graph'
```

Gates: embedder ≤ 1 s, semantic-graph ≤ 500 ms.

- [ ] **Step 2: Cache hit rates (cold → warm re-crawl)**

Run the same 3-doc gRPC test twice consecutively. On the second run, query cache hit metrics:

```bash
curl -s 'http://localhost:<chunker-port>/q/metrics' | grep 'chunker_cache_hit_rate'
curl -s 'http://localhost:<embedder-port>/q/metrics' | grep 'embedder_cache_hit_rate'
```

Gates: chunker ≥ 95%, embedder ≥ 90%.

- [ ] **Step 3: §22.5 MiniLM sentence coverage on both transports**

Query OpenSearch for the 100-doc gRPC + Kafka runs and count sentence-chunk vectors with populated MiniLM embeddings:

```bash
curl -s 'http://localhost:<opensearch-port>/chunks/_search?q=chunk_config_id:sentences_internal+AND+embedder_config_id:minilm_v2&size=0'
```

Gate: 100% populated on both transports. If < 100%, the refactor regressed §22.5 — rollback candidate.

- [ ] **Step 4: opensearch-sink heap headroom on 100-doc semantic run**

```bash
curl -s 'http://localhost:<opensearch-sink-port>/q/metrics' | grep 'jvm_memory_used_bytes\|jvm_memory_max_bytes'
```

Verify heap headroom remained healthy during the 100-doc run. Baseline constraint: `-Xmx10g` per §22.4.

### Task 4.5: Update DESIGN.md §22 baselines

**Files:**
- Modify: `/work/core-services/pipestream-protos/docs/semantic-pipeline/DESIGN.md` (§22.1, §22.3, §22.5 rows become the new baseline)

- [ ] **Step 1: Create a worktree on pipestream-protos**

```bash
cd /work/core-services/pipestream-protos
git -c core.fsmonitor=false fetch origin
git -c core.fsmonitor=false checkout main
git -c core.fsmonitor=false pull --ff-only
git -c core.fsmonitor=false worktree add -b docs/update-baselines-after-refactor /work/worktrees/pipestream-protos-update-baselines main
cd /work/worktrees/pipestream-protos-update-baselines
```

- [ ] **Step 2: Append a new §22.8 "post-refactor baselines" subsection**

Keep §22.1–§22.7 as historical record. Add §22.8 with the numbers captured in Tasks 4.2–4.4. Include:

- Wall clocks for 3/20/100-doc JDBC gRPC + semantic
- Wall clocks for 3/20/100-doc JDBC Kafka + semantic
- Per-step p95 for chunker/embedder/semantic-graph
- Cache hit rates for chunk + embed on identical re-crawl
- §22.5 MiniLM coverage on both transports (should be 100%)
- opensearch-sink heap high-water on the 100-doc run

- [ ] **Step 3: Commit and PR**

```bash
git -c core.fsmonitor=false add docs/semantic-pipeline/DESIGN.md
git -c core.fsmonitor=false -c commit.gpgsign=false commit -m "docs(semantic-pipeline): add post-refactor baselines to DESIGN.md §22.8

Captures wall-clock, per-step p95, cache hit rates, and §22.5 regression
check from the R5 verification run. These numbers become the new
pre-refactor baseline for the next cycle; §22.1–§22.7 are preserved as
historical record."
git -c core.fsmonitor=false push -u origin docs/update-baselines-after-refactor
gh pr create --repo ai-pipestream/pipestream-protos --title 'docs(semantic-pipeline): post-refactor baselines (§22.8)' --body 'Closes Phase 4 of the rollout.'
```

**Rollout complete** once this PR merges.

---

## Self-Review

**1. Spec coverage check**

Every ROLLOUT.md section maps to at least one task:

| ROLLOUT.md § | Covered by |
|---|---|
| §5.0 worktree/tag rules | Task 0.1 (tags), every phase uses worktrees |
| §5.1 P0a rename | Task 0.2 |
| §5.2 P0b pipestream-dev.sh | Tasks 0.3–0.10 |
| §6.1 P1a fixtures + invariants | Tasks 1.1–1.10 |
| §6.2 P1b step-option records | R1/R2/R3 packets (records live in each module) |
| §6.3 P1c wiremock mocks | Tasks 1.12–1.16 |
| §6.4 P1d showcase test | Task 1.17 |
| §7.1 P2a DJL verify | Task 2.1 |
| §7.2 P2b engine stub | Task 2.2 |
| §7.2 P2b opensearch stub + tag | Task 2.3 + Task 0.1 Step 1 |
| §8.2 R1 work packet | R1 packet |
| §8.3 R2 work packet | R2 packet |
| §8.4 R3 work packet | R3 packet |
| §9.1 R4 wiring | Task 4.1 |
| §9.2 R5 gates + §22.5 regression | Tasks 4.2–4.4 |
| §10 rollback | Task 0.1 (tags), every worktree PR is independently revertable |

All sections covered.

**2. Placeholder scan**

- No "TBD", "TODO-implement", "fill in details", or "similar to earlier" references remain.
- Every code step shows actual code.
- Every git command has expected output or a gate to check.

Two soft spots:
- Task 1.4 references hand-writing a stage1 fixture with a deterministic `docHash`. The plan says "compute sha256b64url('fixture-doc-001') once and hardcode" — that is actionable but requires one-time computation. The task executor will compute it with `echo -n 'fixture-doc-001' | openssl dgst -sha256 -binary | basenc --base64url --wrap=0 | sed 's/=*$//'`.
- Task 1.6/1.8 references a `Stage2FixtureGenerator` / `Stage3FixtureGenerator` as test-scoped utilities. These are acknowledged as one-shot generators, not dead code. If the reviewer objects, they can be deleted after the fixtures are committed.

**3. Type consistency**

- `SemanticPipelineInvariants.assertPostChunker / assertPostEmbedder / assertPostSemanticGraph` — consistent naming across all references.
- `SemanticPipelineFixtures.loadStage0Raw / loadStage1PostChunker / loadStage2PostEmbedder / loadStage3PostSemanticGraph` and `deterministicEmbed` — consistent.
- `ChunkerStepOptions / EmbedderStepOptions / SemanticGraphStepOptions` — consistent across R1/R2/R3 packets and DESIGN.md §6.
- `ChunkerStepMock / EmbedderStepMock / SemanticGraphStepMock` — consistent.
- `DirectivePopulator / NoOpDirectivePopulator` and `VectorSetProvisioner / NoOpVectorSetProvisioner` — consistent with DESIGN.md §12.
- Slot names in `pipestream-dev.sh` match the dirs referenced in later phases.

No type inconsistencies found.

---

**End of implementation plan.**
