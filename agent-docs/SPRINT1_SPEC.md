# Sprint 1 Specification — Trust Interrogation + Deduction Board

**Sprint:** 1
**Status:** READY FOR DEVELOPMENT
**Features:** F1 (Trust-Gated Interrogation), F2 (Visual Deduction Board)
**Primary Agent:** Bolt (full-stack dev)
**Support:** Pixel (UX mockups), Scout (QA)

---

## F1: Trust-Gated Interrogation System

### Overview
Add trust and pressure mechanics to NPC interrogations. Players earn information by building rapport or applying pressure — NPCs don't freely reveal everything.

### Backend Changes

**New module: `trust-scoring.js` (or equivalent)**

1. **Trust/Pressure Evaluator**
   - After each player message, call `claude-sonnet` with a scoring prompt:
     ```
     Given the NPC's personality and the conversation so far,
     evaluate the player's last message:
     - trust_delta: float (-1.0 to +1.0) — how much this builds/breaks trust
     - pressure_delta: float (-1.0 to +1.0) — how much pressure this applies
     - reasoning: string — brief explanation
     ```
   - Accumulate trust/pressure scores per NPC per session (start at 0.0, cap at 1.0)

2. **NPC Response Modifier**
   - Inject trust/pressure context into the NPC's system prompt:
     ```
     Current trust level: 0.6/1.0 (the player has been empathetic)
     Current pressure level: 0.3/1.0 (mild pressure applied)

     BEHAVIOR RULES:
     - Below 0.3 trust: Give evasive, guarded responses. Refuse to share key details.
     - 0.3-0.6 trust: Share surface-level info. Hint at deeper knowledge.
     - Above 0.6 trust: Open up. Share personal details and key evidence.
     - Above 0.7 pressure with low trust: Become hostile, clam up.
     - Above 0.7 pressure with high trust: Break down, confess details.
     ```

3. **Dialogue Gate System**
   - Define per-NPC "gated reveals" — specific clues that unlock only at certain trust/pressure thresholds
   - Store gates in the chapter data (e.g., `"reveal_murder_weapon": {"min_trust": 0.6, "min_pressure": 0.0}`)
   - When a gate unlocks, the NPC's system prompt gets the unlocked info appended

### Frontend Changes

1. **TrustMeter Component**
   - Two horizontal bars below the NPC portrait during conversation:
     - Trust bar (blue/green gradient, left-to-right fill)
     - Pressure bar (red/orange gradient, left-to-right fill)
   - Animate on change (smooth transition, ~300ms)
   - Show subtle pulse when a gate unlocks ("New info available" indicator)

2. **Evidence Presentation UI**
   - Button in conversation UI: "Present Evidence"
   - Opens casebook overlay where player selects a clue to show the NPC
   - Presenting evidence should increase pressure score and trigger NPC reaction

### API Endpoints

```
POST /api/npc/evaluate-message
  Body: { npc_id, message, conversation_history, trust, pressure }
  Returns: { trust_delta, pressure_delta, unlocked_gates[] }

GET /api/npc/:npc_id/trust-state
  Returns: { trust: float, pressure: float, unlocked_gates: string[] }
```

### Integration Points — Existing Game API (from live build analysis)

The live game at `https://ninja-games-detective-story-production.up.railway.app/play` uses these endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/game/start` | POST | Start a new game session |
| `/api/game/timeline` | POST | Get chapter timeline |
| `/api/npc/${npcId}/talk/stream` | POST | SSE streaming NPC conversation (PRIMARY) |
| `/api/npc/${npcId}/talk` | POST | Non-streaming fallback |
| `/api/npc/${npcId}/hint` | POST | Get hint from NPC |
| `/api/game/accuse` | POST | Make accusation |
| `/api/tts` | POST | Text-to-speech |

**F1 hooks into `/api/npc/${npcId}/talk/stream`:**
- Trust/pressure evaluation should run in parallel with NPC response generation
- Return trust/pressure deltas as additional SSE events alongside the text stream
- Store trust state in the existing game session (the frontend already tracks `gameState.cluesFound`)

**Existing frontend structure (from HTML analysis):**
- NPC portrait: `#npc-portrait`, name: `#npc-name`, emotion: `#npc-emotion`
- Casebook panel: `#detective-tools` with clue list at `#tools-clue-list`
- Clue counter: `#clue-count` / `#clue-total` (8 clues per chapter)
- The game has 5 difficulty levels (Rookie→Impossible) with varying question/hint limits
- Accusation requires 4+ clues (`#accuse-btn` disabled until threshold)

**TrustMeter placement:** Add below `#npc-portrait` / `.npc-panel` — this is where NPC name/role/emotion are displayed during interrogation.

**Evidence Presentation:** Extend the existing casebook (`#detective-tools`) with a "Present to NPC" action per clue item.

---

## F2: Visual Deduction Board

### Overview
A drag-and-drop evidence board where players connect clues, form hypotheses, and get AI feedback on their deduction logic.

### Frontend Changes

1. **DeductionBoard Component** (new top-level view, accessible from game nav)
   - Canvas/SVG-based board using native HTML5 drag-and-drop or lightweight `interact.js` (no React — game is vanilla JS)
   - Clue nodes: draggable cards showing clue name + icon
   - Connection lines: click one clue, click another to draw a line
   - Suspect zones: designated areas for each suspect where clues can be grouped
   - "Check Deduction" button: sends current board state to backend for AI evaluation

2. **Clue Import from Casebook**
   - Sidebar panel showing all collected clues (pulled from existing casebook data)
   - Drag clues from sidebar onto the board
   - Clues on board show expanded detail on hover/click

3. **Hypothesis Formation**
   - Player can create labeled connections: "motive", "alibi", "contradiction", "supports"
   - Player can write a short hypothesis text for each connection
   - Connection types color-coded (green=supports, red=contradicts, yellow=unclear)

4. **Board Persistence**
   - Board state saved to game session (node positions, connections, labels)
   - Persists across chapters — player builds their board throughout the game

### Backend Changes

1. **Deduction Validator**
   - Endpoint that receives the board state and evaluates it:
     ```
     POST /api/deduction/evaluate
     Body: {
       nodes: [{ clue_id, position, zone }],
       connections: [{ from_clue, to_clue, type, hypothesis }],
       suspect_assignments: [{ suspect_id, clue_ids }]
     }
     Returns: {
       accuracy: float (0-1),
       feedback: string (AI-generated hint about what's right/wrong),
       correct_connections: number,
       total_possible: number
     }
     ```
   - Use `claude-sonnet` with chapter's solution data to evaluate

2. **Board State Storage**
   ```
   GET /api/deduction/board — load saved board
   PUT /api/deduction/board — save board state
   ```

### Integration with Existing Game
- Clue data comes from `gameState.cluesFound` (array of clue strings already tracked by frontend)
- Access the board via a new button in the suspect selection screen (alongside existing CASEBOOK and MAKE ACCUSATION buttons)
- The suspect grid (`#suspects-grid`) dynamically renders NPC cards — use the same NPC data for suspect zones on the board
- Each chapter has 8 clues total (`#clue-total`)

### UX Guidelines (for Pixel)
- Board should feel like a detective's cork board — warm tones, pin/string aesthetic
- Clue cards should look like index cards or polaroids
- Connection lines should look like colored string/yarn
- Dark background to make the board pop
- Responsive: Full board on desktop, simplified list view on mobile

---

## Sprint 1 Definition of Done

- [ ] Trust/pressure meters visible during NPC conversations
- [ ] NPC behavior changes based on trust/pressure levels
- [ ] At least 2 gated reveals per NPC in Chapter 1
- [ ] Evidence presentation triggers pressure increase
- [ ] Deduction board accessible from game navigation
- [ ] Clues can be dragged from casebook to board
- [ ] Connections can be drawn between clues
- [ ] "Check Deduction" returns AI feedback
- [ ] Board state persists across page reloads
- [ ] No new JS errors, console errors, or CORS issues
- [ ] Works on desktop (1280px) and tablet (768px)

---

## Dependencies & Risks

| Risk | Mitigation |
|------|-----------|
| Trust evaluation adds latency to NPC responses | Run evaluation in parallel, not in series |
| Deduction board complex on mobile | Start desktop-first, mobile can be simplified list |
| Chapter data needs trust gates defined | Start with Chapter 1 only, add gates to existing data |
| Canvas/SVG library adds complexity | Use native HTML5 Canvas with interact.js; keep it lightweight |

---

*Sprint 1 spec authored by Nova (PM). Bolt: start with F1 backend (trust scoring module), then F1 frontend (meters), then F2.*
