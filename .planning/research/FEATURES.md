---
project: basketball-stats-api
doc: research/FEATURES
created: 2026-05-19
updated: 2026-05-19
owner: Roger Llinares
status: draft
source: scrape de www.basquethero.cat + PROJECT.md
---

# FEATURES — Basketball Stats API

Domini: REST API per a stats de bàsquet amateur/semi-pro català. Inspiració: `basquethero.cat`. Estil: NO copiar NBA, modelar el bàsquet territorial FCBQ.

---

## 1. Scrape findings — basquethero.cat (verified 2026-05-18)

### 1.1. Stack del referent
- **Next.js sobre Vercel** (`X-Powered-By: Next.js`, `Server: Vercel`, `X-Nextjs-Prerender: 1`).
- Pre-render estàtic + revalidate (`max-age=0, must-revalidate`, `X-Nextjs-Stale-Time: 300`). Bona pista: les dades es pre-rendritzen, NO és live.
- Sitemap públic gegant: **17.015 URLs**. Robots permissive (`Allow: /`).
- **Disclaimer al footer:** "Datos de la Federació Catalana de Basquetbol · Proyecto independiente, sin vinculación oficial." → escraping de la FCBQ, no API oficial. Botó "Feedback" per retirada de dades (privacy). **Cap API pública pròpia ni dades obertes anunciades.**

### 1.2. Taxonomia d'URLs (única i neta)
```
/                                       homepage (lligues disponibles)
/clubs                                  índex de clubs (325)
/clubs/<slug-club>                      pàgina de club (estàtica, mostly CSR)
/fichajes                               Beta — "trobar el teu pròxim jugador" (mercat)
/liga/<slug-lliga>                      resumen de jornada actual de la lliga
/liga/<slug>/calendario                 calendari per jornades
/liga/<slug>/equipos                    classificació + tots els equips
/liga/<slug>/jugadores                  lleaderboard de jugadors (paginat 20/pàg)
/liga/<slug>/equipo/<id>                pàgina d'equip dins una lliga
/liga/<slug>/jugador/<id>|<#>|<NOM>     pàgina de jugador dins una lliga
/liga/<slug>/partido/<mongoid>          box-score d'un partit
```

Observacions importants:
- **El "club" i la "lliga/equip" són entitats separades**. Un club té múltiples equips, cada equip juga en una lliga concreta.
- **L'ID de jugador és compost**: `<licenseId>|#<dorsal>|<NOM>` (e.g. `80121|#5|RAFAEL_PINTO`). Apunta a tracking per llicència federativa, no per identitat global del jugador.
- **L'ID de partit és un Mongo ObjectId** (24-hex, e.g. `68c5a7db2c40a80001172281`). Pista que el referent usa MongoDB; per Roger irrellevant (Postgres locked), només deixa traça que els partits es modelen com a document gran amb sub-documents.

### 1.3. Lligues observades (sample 10/44)
- `super-copa-m`, `copa-catalunya-m`, `cc-1a-m-grup-03`, `cc-2a-m-grup-03`
- `1a-territorial-m-bcn-grup-02/04/06`
- `3a-territorial-m-bcn-grup-03/04`, `3a-territorial-m-gir-grup-01/02`

**Patró clau:** `<categoria-de-competició>-<gènere>-<territori>-<grup>`.
- Categories observades: `super-copa`, `copa-catalunya`, `cc-1a` (Catalunya Categoria 1a), `cc-2a`, `1a-territorial`, `3a-territorial`.
- Gènere: `m` masculí (el scrape no ha trobat femení a la primera pàgina, però el `fichajes` parla de 9.459 jugadors total → existeix `f`).
- Territori: `bcn` (Barcelona), `gir` (Girona). Probable: `tar` (Tarragona), `lle` (Lleida).
- Grup: subdivisió per proximitat geogràfica dins el mateix territori (e.g. `grup-02`, `grup-04`).
- **No hi ha categories d'edat (sub-12, cadet, junior, sub-22)** al sample que hem vist — basquethero.cat sembla focalitzar-se en **sèniors masculins**. Roger ha de decidir si el seu API les inclou (probable SÍ — la seva lliga és sub-22 o sèniors).

### 1.4. Estadístiques tracked (verified — Super Copa Masculina J28, 2025-26)

**Stats per jugador (box-score + lleaderboard):**
- `VAL` (Valoración) ← **mètrica primària** del referent. Lleaderboard ordenat per defecte per VAL.
- `MIN`, `PTS`, `+/-`
- `2P`, `2PM`, `2PA` (tirs de 2 fets/intentats)
- `3P`, `3PM`, `3PA` (triples)
- `TL`, `TL%` (tirs lliures fets/intentats + %)
- `REB` (total) — pàgina jugador desglossa `REB_DEF` / `REB_OF`
- `AST`, `REC` (recuperacions = steals), `TAP` (taps = blocks), `PER` (pèrdues = TO), `FC` (faltes comeses)
- `PJ` (partits jugats), `%V` (% victòries personal)

**Composició de "Valoración" (revelada a la pàgina de jugador):**
```
VAL = +1.0·PTS +0.8·REB_DEF +1.2·REB_OF +1.0·AST +1.2·REC +1.0·TAP −0.4·FAL
      −0.8·PER −0.4·TL_FALLATS +0.2·TRIPLES −0.x·TIROS_FALLATS
```
Aquesta és la **fórmula FIBA Valuation/PIR** (Performance Index Rating) ajustada. **Concretament:** PIR oficial = (PTS+REB+AST+STL+BLK+FOULS_DRAWN) − (MISSED_FG+MISSED_FT+TO+FOULS_COMM). El referent usa una variant ponderada però la idea és la mateixa.

→ **Decisió:** l'API de Roger HA DE calcular i exposar VAL/PIR. Aquesta és LA mètrica del bàsquet català, no PPG sol.

**Stats per equip (classificació):**
- `J` (jugats), `V`, `D` (vict/derr), `%V`
- `PF` (punts a favor), `PC` (punts en contra), `+/-` diferencial
- `Local 13-1`, `Visitante 11-3` (rècord casa/fora)
- `Racha` (streak) — fletxes ▲3/▼3 indiquen tendència

**Stats per partit (box-score complet):**
- Marcador final + parcials per quart (`Q1 Q2 Q3 Q4`).
- Per cada equip: comparativa de tirs `28/74 (37.84%)` — FG, 2P, 3P, FT amb fets/intentats + %.
- Equip: REB defensius vs ofensius, AST, REC, TAP, PER, FC totals.
- Per cada jugador: la fila box-score completa.
- MVP del partit (jugador amb VAL més alta).
- Líders del partit per categoria (PTS, REB, AST, 3P, +/-).
- Link a "acta oficial FCBQ" → els partits venen del PDF de l'acta federativa.

**No s'observa play-by-play textual ni shot chart.** Només quart-per-quart + box-score final. Pista: el referent treballa amb el PDF d'acta, no amb event-stream.

### 1.5. Pàgina d'inici (UX principal)
Frase clau: "**¿Quién es el MVP de tu liga? Rankings, récords, rachas y los números que no ves en el acta. Todo el basket territorial catalán, desglosado.**"

→ El **valor real** del referent és **el que no és a l'acta**: rankings, ràtios, ratxes, MVP de la jornada, quintet ideal, líders agregats. L'acta PDF ja té el box-score; el valor afegit és **l'agregació + el rànquing**.

### 1.6. Diferenciador del referent: `/fichajes` ("trobar el teu pròxim fitxatge")
Beta. "9.459 jugadors · 44 grups". Permet filtrar jugadors disponibles per estadístiques. **Pels clubs amateur que volen reforçar plantilla.** Forta inspiració pel hook d'entrevista de Roger ("el vaig fer per al meu equip"): el coach del seu equip podria fer servir l'API per scout intern.

### 1.7. Quirks Catalans capturats
| Quirk | Què implica per l'schema | Què cal modelar |
|---|---|---|
| **Categoria + territori + grup** | `competition` no és una taula plana, és jeràrquica | `competition (id, name, category, gender, territory, group_no, season)` |
| **Temporada com a entitat pròpia** | `2025-26` apareix arreu | `season (id, start_year, label)`; cada equip "ressuscita" cada temporada |
| **Club ≠ equip** | "CB ARTÉS" club té múltiples equips (A, B, sub-22) | `club (id, slug, name) ──< team (id, club_id, name, season_id, competition_id)` |
| **Fase Prèvia / Fase Final / Playoff** | Breadcrumb mostra "Fase Prèvia" | `competition.phase (regular_phase, second_phase, playoff)` o taula `phase` separada |
| **Jornada** = matchday | "J 28 de 30" | `game.matchday_no` (INT) |
| **PIR/Valoración és la mètrica** | No PPG sol | Computar VAL com a `GENERATED COLUMN` o vista materialitzada |
| **MVP de jornada** | "Mejor jugador de la jornada 10" | Endpoint dedicat — window function `RANK() OVER (PARTITION BY matchday_no ORDER BY val DESC)` |
| **Quintet ideal** | Top-5 jugadors per VAL | Mateix patró, `LIMIT 5` |
| **Acta oficial FCBQ** | Font autoritzada = PDF | El referent és ingest manual; Roger també (ingest = POST de coach, igual que l'API oficial demana) |
| **Privacy opt-out** | "Eres jugador i vols que retiri les teves dades?" | `player.deleted_at` / `player.public_consent` BOOL |
| **Logos d'equip i fotos de jugador** | Es mostren | `team.logo_url`, `player.photo_url` (no obligatori MVP) |

### 1.8. Disponibilitat d'API oficial
**Cap.** El referent escrapa el web/PDFs de la FCBQ. La FCBQ NO té API pública documentada (Roger ho ha de confirmar al seu cantó, però sitemap+disclaimer+ID-mongo del referent suggereixen que tothom fa scrape). → **L'API de Roger funciona amb dades pujades pel coach (manual / CSV upload), NO consumir FCBQ live.** Coincideix amb decisió locked al PROJECT.md (sense live ingest).

---

## 2. Table-stakes features (MVP — obligatòries)

Sense aquestes, l'API no és creïble com a peça de portfolio.

| REQ-ID | Feature | Complexitat | Depèn de | Endpoints |
|---|---|---|---|---|
| `[DOM-01]` | Schema base: club / team / player / season / competition | M | — | (migracions) |
| `[DOM-02]` | CRUD lligues (competicions) | S | DOM-01 | `GET /competitions`, `GET /competitions/{id}` |
| `[DOM-03]` | CRUD equips per lliga | S | DOM-02 | `GET /competitions/{id}/teams`, `GET /teams/{id}` |
| `[DOM-04]` | CRUD jugadors per equip + temporada | M | DOM-03 | `GET /teams/{id}/players`, `GET /players/{id}` |
| `[DOM-05]` | Schema de partit (game + game_player_stats) | M | DOM-04 | (migracions + endpoints DOM-07) |
| `[DOM-06]` | Calendari per jornada de lliga | S | DOM-05 | `GET /competitions/{id}/schedule?matchday=N` |
| `[DOM-07]` | Box-score públic d'un partit | M | DOM-05 | `GET /games/{id}` (retorna stats per equip + per jugador + parcials per quart) |
| `[DOM-08]` | Standings de lliga (classificació) | M | DOM-05 | `GET /competitions/{id}/standings` (J, V, D, %V, PF, PC, +/-, casa/fora, ratxa) |
| `[DOM-09]` | Perfil de jugador (stats agregats temporada + game log) | M | DOM-05 | `GET /players/{id}/season-stats?competition_id=X`, `GET /players/{id}/games` |
| `[DOM-10]` | Càlcul automàtic de Valoración (PIR) | M | DOM-05 | Fórmula com a `GENERATED COLUMN` o vista; exposat a tots els endpoints |
| `[DOM-11]` | Upload box-score (coach autenticat) | M | DOM-05, AUTH | `POST /games` + `POST /games/{id}/box-score` |
| `[DOM-12]` | Correcció de box-score (idempotent update) | S | DOM-11 | `PATCH /games/{id}/box-score` |
| `[AUTH-01]` | OAuth2 + JWT, roles `public` / `coach` / `admin` | M | — | `POST /auth/token`, `GET /me` |
| `[AUTH-02]` | Coach només pot escriure dels SEUS equips | S | AUTH-01, DOM-04 | (regla a `Depends()` FastAPI) |
| `[OBS-01]` | OpenAPI `/docs` complet amb exemples per endpoint | S | tot l'anterior | (auto + decoradors `responses=` + `Field(example=)`) |
| `[OBS-02]` | Health/readiness `/health`, `/ready` | S | — | `GET /health`, `GET /ready` |

**Total estimat:** ~12-14 dies júnior amb GSD → cap dins el budget 1-2 setmanes si Roger no s'embolica amb advanced metrics.

---

## 3. Differentiators (showcase tech jr Postgres + FastAPI)

Aquests són els que els recruiters miraran a `/docs` i diran "ah, aquest sap el que fa".

| REQ-ID | Feature | Complex | Tech demostrada | Endpoint(s) |
|---|---|---|---|---|
| `[DIFF-01]` | **Leaderboard de lliga ordenat per VAL/PTS/REB/AST/3P/+/-** amb `RANK() OVER (PARTITION BY competition_id ORDER BY stat DESC)` | M | **Postgres window functions** | `GET /competitions/{id}/leaderboards?stat=val&limit=20&min_games=14` |
| `[DIFF-02]` | **MVP de jornada** + **quintet ideal** de jornada | M | Window functions amb `DENSE_RANK() OVER (PARTITION BY matchday_no)` | `GET /competitions/{id}/matchdays/{n}/mvp`, `GET /competitions/{id}/matchdays/{n}/best-five` |
| `[DIFF-03]` | **Full-text search de jugadors i equips** per nom | M | **Postgres `tsvector` + `tsquery` + GIN index** | `GET /search?q=melgarejo&type=player\|team` |
| `[DIFF-04]` | **Play-by-play JSONB** per partit (opcional al box-score, però l'schema ho suporta) | M | **Postgres JSONB + `jsonb_path_query`** | `POST /games/{id}/events` (afegir esdeveniments), `GET /games/{id}/events?quarter=3` |
| `[DIFF-05]` | **Tendència del jugador** (rolling avg últims 5 partits) | M | Window functions `AVG() OVER (PARTITION BY player_id ORDER BY game_date ROWS BETWEEN 4 PRECEDING AND CURRENT)` | `GET /players/{id}/trend?stat=val&window=5` |
| `[DIFF-06]` | **Recompute automàtic de standings/leaderboards en `POST /games`** | M | **FastAPI BackgroundTasks** + cache invalidation (Redis si hi és) | (post-acció implícita a DOM-11) |
| `[DIFF-07]` | **Composite index** sobre `game(date DESC, competition_id)` per calendari | S | **Postgres composite indexes** (visible a `EXPLAIN ANALYZE`, ADR justificant elecció) | (suport intern, demostrat al README + ADR) |
| `[DIFF-08]` | **Head-to-head equip A vs equip B** (històric partits) | S | CTE `WITH` + `UNION ALL` | `GET /teams/{a}/h2h/{b}` |
| `[DIFF-09]` | **Streaks / ratxes** (V/D consecutives) | M | Window functions amb `LAG()` + gaps-and-islands pattern | `GET /teams/{id}/streak` (inclou-ho dins standings DOM-08) |
| `[DIFF-10]` | **Rate limit + ETag/`If-None-Match`** als endpoints públics | M | FastAPI middleware + headers HTTP correctes | (transversal) |
| `[DIFF-11]` | **`docs/adr/`** amb 5+ ADRs (auth, sync vs background, cache, deploy target, why-Postgres-pur) | S | Engineering rigor visible | (docs) |
| `[DIFF-12]` | **Testcontainers Postgres** als tests d'integració (no mocks) | M | Tests d'integració realistes | (CI) |
| `[DIFF-13]` | **GitHub Actions full pipeline** (ruff → mypy → pytest → docker build → deploy tag) | M | CI/CD demostrat | (`.github/workflows/`) |

**Showcase mapping resumit (per al recruiter al README "Stack walkthrough"):**

| Tech | On es veu | Feature concreta |
|---|---|---|
| Postgres window functions | `DIFF-01` leaderboards, `DIFF-02` MVP/quintet, `DIFF-05` trend, `DIFF-09` streaks | 4 features distintes |
| Postgres JSONB | `DIFF-04` play-by-play | 1 feature (low pressure al MVP, sí post-MVP) |
| Postgres full-text search | `DIFF-03` search | 1 feature |
| Postgres composite indexes | `DIFF-07` calendari | suport intern + ADR |
| Postgres GENERATED COLUMN | `DOM-10` VAL/PIR | calculat al motor, no a Python |
| FastAPI async + Pydantic v2 | tot | OpenAPI `/docs` |
| FastAPI BackgroundTasks | `DIFF-06` recompute | invalidació de cache |
| FastAPI Security (OAuth2 + JWT) | `AUTH-01`, `AUTH-02` | rols `coach` vs `public` |
| Docker Compose | local dev | `docker compose up` |
| Testcontainers | `DIFF-12` | tests d'integració amb Postgres real |
| GitHub Actions | `DIFF-13` | pipeline complet |

---

## 4. Anti-features (DELIBERAT no construir)

Cadascuna amb 1-línia de raó. Roger ha de saber dir "no" a l'entrevista.

| Anti-feature | Per què NO |
|---|---|
| **UI web / dashboard / mobile app** | API-only locked al PROJECT.md; un UI seria un altre repo |
| **Live ingest des d'scoreboard físic / FCBQ scrape automàtic** | Out-of-scope locked; legal greyzone + estabilitat fragil; coach POST manual és suficient i creïble |
| **WebSockets / SSE live game updates** | Locked deferred a post-MVP; complica el deploy a Fly.io free |
| **Push notifications (FCM, APNS)** | Locked out-of-scope total — domini API, no app |
| **Mètriques NBA-style (PER, TS%, BPM, eFG%, USG%, ORTG/DRTG, VORP, RAPM)** | MVP = bàsics + VAL/PIR (que ÉS la mètrica catalana real). NBA stats deferred a milestone v2. Si Roger les vol mostrar, n'hi ha prou amb 1 (eFG% que costa 1h) com a "easter egg" |
| **Shot charts / heatmaps / posicions de tir** | Requereix posició (x,y) de cada tir — NO és a l'acta FCBQ. Inventaríem dades. NO. |
| **Multi-tenant SaaS (cada club gestiona els seus permisos)** | Locked: single-league focus. Multi-lliga emergeix de l'schema, no és feature dedicada amb tenancy real |
| **Integració amb betting / odds / pronòstics** | Anti-pattern flagrant per a un portfolio de feina — confondria l'entrevistador; bloquejat |
| **Social features (comentaris, likes, follow jugador, chat)** | Fora del core "stats"; afegiria 3-5 dies sense valor de portfolio |
| **Sistema de fitxatges/mercat (com `/fichajes` del referent)** | Tot i ser interessant, és un altre subdomini sencer (rules, ofertes, candidatures). Aparcar a v3 |
| **Predicció amb ML (qui guanyarà el següent partit?)** | Spurious; cap recruiter compraria un model entrenat amb 28 partits. Demaga al rev |
| **Mobile responsive / PWA / etc.** | API-only, no apliquen |
| **Vercel/Render/Supabase als serveis o build steps** | Locked anti-overlap amb SST/Apostes |
| **Real-time leaderboard updates en menys de 5s** | Per cache + recompute on POST n'hi ha prou; sub-segon és vanity |
| **Suport multi-idioma de l'API** (l10n de missatges d'error) | YAGNI; els missatges en anglès són estàndard d'API |
| **GraphQL endpoint en paral·lel al REST** | REST + OpenAPI ja és el showcase; GraphQL duplicaria feina i confondria el pitch |
| **Categories d'edat infantil completes (sub-12, sub-14, sub-16)** | El bàsquet de Roger és sub-22/sèniors; modelar `category` ENUM amb totes les categories al schema però seedar només les que té → "expandible sense feina" sense gastar dies seedant |

---

## 5. MVP recomanat — ordre de construcció

Ordre per minimitzar dependència circular i poder fer demo a cada gate.

**Setmana 1 — domini + lectura:**

1. `[DOM-01]` Schema base (club / team / player / season / competition / matchday)
2. `[DOM-02]` `GET /competitions[/{id}]`
3. `[DOM-03]` `GET /teams[/{id}]`
4. `[DOM-04]` `GET /players[/{id}]`
5. `[DOM-05]` Schema de partit (game + game_player_stats + game_quarter_score)
6. `[DOM-10]` VAL/PIR com a GENERATED COLUMN (early — tots els endpoints futurs el necessiten)
7. `[DOM-07]` `GET /games/{id}` (box-score públic)
8. `[DOM-06]` `GET /competitions/{id}/schedule`
9. `[DOM-08]` `GET /competitions/{id}/standings` (amb window functions per `Racha`/streak → DIFF-09 ja integrat)
10. `[DOM-09]` `GET /players/{id}/season-stats`, `GET /players/{id}/games`
11. `[OBS-01]` Polish OpenAPI `/docs` (exemples a cada ruta)
12. `[OBS-02]` `GET /health`, `GET /ready`
13. **GATE 1 (D7-D8):** demo de lectura completa amb seed de l'equip real de Roger.

**Setmana 2 — escriptura + showcase + ship:**

14. `[AUTH-01]` OAuth2 + JWT, rols
15. `[AUTH-02]` Coach només pot escriure els seus equips
16. `[DOM-11]` `POST /games` + `POST /games/{id}/box-score` (recompute via DIFF-06 BackgroundTasks)
17. `[DOM-12]` `PATCH /games/{id}/box-score`
18. `[DIFF-01]` `GET /competitions/{id}/leaderboards?stat=...&limit=...&min_games=...`
19. `[DIFF-02]` `GET /competitions/{id}/matchdays/{n}/mvp` + `/best-five`
20. `[DIFF-03]` `GET /search?q=...&type=...` (tsvector + GIN)
21. `[DIFF-05]` `GET /players/{id}/trend?window=5`
22. `[DIFF-08]` `GET /teams/{a}/h2h/{b}`
23. `[DIFF-07]` Composite index + EXPLAIN ANALYZE al README
24. `[DIFF-10]` Rate limit + ETag (transversal)
25. `[DIFF-12]` Testcontainers a tests d'integració
26. `[DIFF-13]` GitHub Actions complet
27. `[DIFF-11]` 5 ADRs a `docs/adr/`
28. `[DIFF-04]` JSONB play-by-play **(optional MVP, sí milestone v2)**
29. **GATE 2 (D14):** ship a Fly.io, `/docs` públic, README pro, portfolio-defense.md.

**Si overrun a D17-D18:** retallar `DIFF-04` (JSONB) i `DIFF-08` (H2H) → mou a milestone v2. Tot lo demés és core demo.

---

## Quality gate self-check
- [x] basquethero.cat actually scraped — 6 pàgines (home, league, jugadores, equipo, partido, jugador) + sitemap + fichajes + clubs
- [x] Cada feature té complexity (S/M/L) + dependència
- [x] Showcase ↔ tech mapping explícit (taula §3)
- [x] Catalan basketball specifics capturats (§1.7 quirks, no NBA-default)
- [x] Anti-features amb rationale d'una línia
- [x] Hook "ho vaig fer per al meu equip" coherent — features cobreixen ús real del coach (upload box-score, llegir standings i leaderboards de la seva lliga)
