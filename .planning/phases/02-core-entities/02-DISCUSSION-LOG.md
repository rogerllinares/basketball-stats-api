# Phase 2: Core entities + public read - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-20
**Phase:** 2-core-entities
**Areas discussed:** Entity relationships, VAL GENERATED COLUMN, Standings + leaderboards grain, Pagination + seed fidelity

---

## A. Entity relationships shape

### A.1 — Player primary key shape

| Option | Description | Selected |
|--------|-------------|----------|
| Surrogate INT PK + UNIQUE composite | `player.id` INT PK + UNIQUE(license_id, dorsal, normalized_name). FKs simples. Industry-standard. | |
| Composite natural key as PK | PK = (license_id, dorsal, normalized_name). Fidelitat federativa literal. FKs 3-col arreu. | ✓ (inicial) |
| Surrogate INT + sense unique constraint | Permet duplicats temporals, dedup manual al servei. | |

**User's choice (inicial):** Composite natural key com PK.
**Notes:** Claude va flaggear costos no òbvis: cascada UPDATE al canviar nom, migracions verboses, JOIN performance lleugerament pitjor.

### A.2 — Normalització de noms

| Option | Description | Selected |
|--------|-------------|----------|
| UPPER + sense accents + trim | "Rafael Pintó" → "RAFAEL PINTO". Aplica a Player, Team, Club. Alineat amb FCBQ. | ✓ |

**User's choice:** "Els accents ho fem tot sense accents, diria que ja és així a la federació".
**Notes:** Mitiga risc de cascada UPDATE per typos d'accent. Roger ho va proposar com domain knowledge real (acta FCBQ usa majúscules sense accents).

### A.3 — Player PK reconsiderat (post-normalització)

| Option | Description | Selected |
|--------|-------------|----------|
| Híbrid: surrogate INT PK + UNIQUE composite + URL composite a l'API | `id INT PK + UNIQUE(license_id, dorsal, normalized_name)`. URL exposa composite (`/players/80121-5-rafael-pinto`). | ✓ |
| Manté composite PK pur | PK literal `(license_id, dorsal, normalized_name)`. FKs 3-col. | |

**User's choice:** Opció B híbrid segur.
**Notes:** Claude va explicar concisament per a principiant: Opció A = identitat = les 3 dades, copia a totes les taules; Opció B = id intern numèric + 3 dades amb UNIQUE, FKs simples, API exposa composite externament. Roger va triar híbrid després de la explicació pros/contras.

### A.4 — Team shape

| Option | Description | Selected |
|--------|-------------|----------|
| Team permanent + Roster M:N | `teams (id, club_id, name)` etern. `rosters (player_id, team_id, season_id, dorsal)` M:N temporal. | ✓ |
| Team season-scoped (basquethero pattern) | Cada season nou Team row. FK directe player.team_id. | |
| Team permanent + Player.current_team_id directe | Sense Roster table. Historial perdut. | |

**User's choice:** Team permanent + Roster table separat (RECOMANAT).

### A.5 — Coach + Phase (tàcit, no preguntat explícitament)

| Option | Description | Selected |
|--------|-------------|----------|
| Coach ↔ Team M:N join table | `coaching_assignments (coach_id, team_id, season_id, role, dates)`. | ✓ (default) |
| Phase = enum column a Competition | Valors fase_previa / segona_fase / playoff. Cada combinació té competition_id distint. | ✓ (default) |

**User's choice:** "Passem a B — VAL GENERATED COLUMN" (tots els defaults acceptats).

---

## B. VAL GENERATED COLUMN

### B.1 — Variant PIR

| Option | Description | Selected |
|--------|-------------|----------|
| PIR-amateur (sense fouls_drawn/blocks_received) | Fórmula adaptada als camps acta FCBQ reals. | |
| PIR FIBA literal amb fouls_drawn=0 + blocks_received=0 sempre | Fórmula completa amb camps inexistents marcats 0. Easier upgrade future. | ✓ |
| Re-obrir ROADMAP: basquethero ponderat (scope change) | Coeficients basquethero. Trenca LOCKED ROADMAP. | |

**User's choice:** PIR FIBA literal amb fouls_drawn=0 + blocks_received=0 sempre.

### B.2 — Total REB com a 2n GENERATED column?

| Option | Description | Selected |
|--------|-------------|----------|
| SÍ — 2n GENERATED column `reb` | `reb GENERATED ALWAYS AS (reb_of + reb_def) STORED`. | ✓ |
| NO — calculat read-side | `SELECT reb_of+reb_def AS reb`. | |

**User's choice:** SÍ — 2n GENERATED column `reb`.

### B.3 — Asimetria Supercopa↔Territorial (revealed mid-discussion)

Roger interrumpeix amb domain knowledge: "A Supercopa SÍ hi ha totes les dades, a altres lligues n'hi ha algunes sí i algunes no."

| Option | Description | Selected |
|--------|-------------|----------|
| Default 0 uniforme + ADR documentant l'asimetria | `NOT NULL DEFAULT 0`. Formula PIR FIBA funciona sense COALESCE. ADR-0003 explica. | ✓ |
| NULL per defecte + COALESCE a la formula | Schema nullable. Formula amb COALESCE. | |
| Flag competition.has_detailed_fouls | Trenca STAT-04 LOCKED (no Python compute). DESCARTAT tècnicament. | |

**User's choice:** Default 0 uniforme + ADR documentant l'asimetria (RECOMANAT).

---

## C. Standings + leaderboards grain

### C.1 — Tie-breakers FCBQ

| Option | Description | Selected |
|--------|-------------|----------|
| Simple FEB-style | `RANK() OVER (ORDER BY wins DESC, (PF-PC) DESC, PF DESC)`. | |
| Head-to-head amb CTE complex | Sub-CTE per empats 2-3 equips. Fidel normativa FCBQ. | |
| Simple ara + ADR documentant gap normatiu | Implementació simple + ADR-0004. Honest defense. | ✓ |

**User's choice:** Simple ara + ADR documentant gap normatiu.

### C.2 — Season averages: on-the-fly vs materialized

| Option | Description | Selected |
|--------|-------------|----------|
| On-the-fly amb window functions cada request | Cap taula materialitzada. Window function visible. | ✓ |
| Materialized table `player_season_averages` | Recompute hook P3 BackgroundTask. | |

**User's choice:** On-the-fly amb window functions (RECOMANAT).

### C.3 — Per-season vs per-phase scoping (tàcit, derivat de A.5)

Decisió Phase enum a Competition (A.5) implica que cada (category, gender, territory, group, season, phase) = competition_id distint. Standings/leaderboards naturalment per-phase. Cross-phase agregat fora MVP.

---

## D. Pagination + seed fidelity

### D.1 — Pagination shape

| Option | Description | Selected |
|--------|-------------|----------|
| Offset/limit simple | `?offset=0&limit=20`, default 20, max 100, `X-Total-Count` header. | ✓ |
| Page-based amb metadata | `?page=1&page_size=20`, response amb total_pages. | |
| Cursor-based (RFC 5988 Link header) | Robust a inserts mid-pagination. Over-engineering. | |

**User's choice:** Offset/limit simple (RECOMANAT MVP).

### D.2 — Seed minimal names

| Option | Description | Selected |
|--------|-------------|----------|
| Fictius realistes en català | CB GRANOLLERS, CB ARTES, noms catalans fictius, dorsals 4-15, llicències 99001-99012. | ✓ |
| Reals Roger + 11 companys Sènior A | Privacy risk al repo públic. | |
| Hybrid: Roger real + 11 fictius | Compromise. | |

**User's choice:** Fictius realistes en català (RECOMANAT).

### D.3 — Seed scope (tàcit, ROADMAP LOCKED)

INFRA-06 LOCKED literal: 1 competition + 2 teams + 1 game + 12 box-scores. Mantenim sense canvi. Demo final amb dades reals via CLI FCBQ Phase 2.5.

---

## Claude's Discretion

Roger ha delegat (igual que P1) detail-level amb la consigna "documenta lo que haces y porque". Decisions internes de Claude (totes amb rationale defensable a CONTEXT.md):
- **D2-15:** Pure-read phase → no Service layer fins P3 quan apareguin transactions.
- **D2-16:** Fitxers de repository per concepte de query, no per entitat ORM.
- **D2-17:** Schemas Create/Update existeixen com a drafts a P2 (POST/PUT endpoints són P3).
- **D2-18:** ResponseModel obligatori a totes les rutes (no `dict`).
- **D2-19:** Tests específics enumerats per a integration (window functions + pagination + GENERATED COLUMNS).
- **D2-20:** Una migration cohesiva per phase (`0002_core_entities.py`).

## Scope change durant discussió

Roger va proposar mid-discussió afegir **FCBQ Ingest CLI** per scrapejar dades reals (originalment OUT-of-scope a PROJECT.md). Claude va flaggear el conflicte amb LOCKED constraint i va presentar 4 opcions:
- A. Phase nova 2.5 separada ✓ **(Roger trià)**
- B. Modificar INFRA-06 a P2 (escope creep risc)
- C. Repo separat
- D. Defer a v2

**Conseqüència:** Phase 2 ship en temps amb seed minimal manual fictiu. Phase 2.5 a crear via `/gsd-insert-phase` post-P2-ship. Apuntat a TODO.md raíz §Basketball Stats API com a [P2].

Roger també va demanar apuntar com a [P3] al TODO: web frontend UI amb eines de disseny especialitzades (basketball-stats-web repo separat o landing custom).

## Deferred Ideas (transcrites a CONTEXT.md §deferred)

- FCBQ Ingest CLI (Phase 2.5)
- Web frontend UI (P3 TODO)
- Materialized table `player_season_averages`
- Cross-phase aggregate endpoint
- Head-to-head tie-breaker CTE
- Service layer per a reads (defer a P3)
- Materialized view per a standings
- JSONB play-by-play column
- Streak detection (Racha)
- /matchday/{date}/mvp endpoint
- Player development trend (LAG)
