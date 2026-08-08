# T1D Companion App — Architecture & Implementation Guide

> **Wellness Disclaimer Philosophy:** This app is a companion tool, not a regulated medical device.
> Every dosing output is framed as a suggestion. Clinical decisions remain with the patient and their care team.
> The architecture is built regulation-ready (audit logs, versioned algorithms, data export) for a future
> FDA 510(k) or CE marking path without a rewrite.

---

## 1. Product Overview

A cross-platform mobile-first companion app for adult Type 1 diabetic patients. It unifies daily
diabetes management — glucose logging, bolus calculation, meal tracking, and AI-assisted education —
into a single interface accessible via both touch/text and voice.

### Core Design Tenets
- **Offline-first:** Every safety-critical feature (logging, bolus calc) works with zero connectivity
- **Module-federated:** Each feature is an independently deployable module; new modules plug in without touching the app shell
- **Voice-native:** Push-to-talk is a first-class input modality, not a bolt-on
- **India-first:** Indian food data, Hinglish voice support, OTP auth, and low-bandwidth resilience are defaults, not afterthoughts
- **Privacy by default:** Health audio and data never leave the device unless the user explicitly syncs

---

## 2. V1 Scope

| Module | Type | Notes |
|---|---|---|
| Glucose Tracker & Logger | Core (owned) | Manual entry, history, threshold alerts |
| Bolus Calculator | Core (owned) | TDD-based, IOB-aware, gated on profile completion |
| Carb Counter | Integration (black-box) | Photo + text/voice input, Indian food DB |
| General T1D RAGbot | Integration (black-box) | External pre-built service, interface-agnostic |
| Push-to-Talk Voice + TTS | Cross-cutting layer | Local Whisper.cpp, Hindi/English/Hinglish |
| Agentic Intent Router | Cross-cutting layer | Classifies voice/text → module commands |
| Auth & Onboarding | Core (owned) | Phone OTP + Google, structured profile gate |
| Local Notifications | Core (owned) | 3 alert types, all opt-in |

**Personal RAGbot (user's own health data queries) → V2**
**Health API CGM bridge, caregiver sharing, wake word → V2**

---

## 3. Overall Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FLUTTER APP SHELL                        │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Glucose  │  │  Bolus   │  │  Carb    │  │ RAGbot   │  │
│  │ Tracker  │  │  Calc    │  │ Counter  │  │   UI     │  │
│  │ Module   │  │ Module   │  │  Proxy   │  │  Proxy   │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
│       │              │              │              │         │
│  ─────┴──────────────┴──────────────┴──────────────┴──────  │
│                    MODULE REGISTRY                           │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              VOICE / AGENT LAYER                     │   │
│  │  PTT Button → Whisper.cpp → Intent Classifier       │   │
│  │  → Module Router → Handler → TTS Response           │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                 DATA LAYER                           │   │
│  │   Isar (local, offline-first, source of truth)      │   │
│  │   Supabase Sync Adapter (background, on connectivity)│   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTPS / WSS
          ┌───────────────┴───────────────┐
          │                               │
   ┌──────▼──────┐                ┌───────▼────────┐
   │  SUPABASE   │                │  FASTAPI       │
   │  (Postgres) │                │  ORCHESTRATION │
   │  Auth       │                │  SERVICE       │
   │  RLS        │                │                │
   │  Realtime   │                │  Intent resolve│
   │  Storage    │                │  RAGbot router │
   └─────────────┘                │  Carb API proxy│
                                  └───────┬────────┘
                                          │
                     ┌────────────────────┴──────────────────┐
                     │                                       │
              ┌──────▼──────┐                      ┌────────▼───────┐
              │  GENERAL    │                      │  CARB COUNTER  │
              │  T1D RAGBOT │                      │  SERVICE       │
              │  (External) │                      │  (External)    │
              └─────────────┘                      └────────────────┘
```

---

## 4. Full Tech Stack

### Frontend (Mobile)
| Concern | Choice | Rationale |
|---|---|---|
| Framework | Flutter (Dart) | Single codebase for iOS + Android, high-performance UI, excellent for data-dense health UIs |
| Local DB | Isar | Same author as Hive, full query engine (Hive is key-value only — insufficient for time-series health queries like "readings > 180 in last 30 days") |
| State Management | Riverpod | Compile-safe, scales cleanly with module-federated architecture |
| Navigation | GoRouter | Deep linking, nested routes, module-level route registration |
| STT | Whisper.cpp (via FFI) | On-device, no audio leaves phone, multilingual Hindi/English/Hinglish |
| TTS | flutter_tts | On-device, offline, supports Hindi |
| Notifications | flutter_local_notifications | Background isolate, no server needed for v1 alert types |
| HTTP Client | Dio | Interceptors for auth token injection, retry logic, offline queue |
| Sync | Supabase Flutter SDK | Realtime subscriptions, auth, storage |
| Charts | fl_chart | Glucose trend graphs, bolus history visualizations |

### Web Companion (V1.5)
| Concern | Choice |
|---|---|
| Framework | Next.js 14 (App Router) |
| Styling | Tailwind CSS |
| Auth | Supabase Auth (shared session) |
| Deployment | Vercel |

### Backend — Data & Auth
| Concern | Choice | Rationale |
|---|---|---|
| Platform | Supabase | Postgres (real queries), Auth, RLS, Realtime, Storage — open-source, self-hostable |
| Database | Postgres (via Supabase) | Time-series queries, JSONB for flexible module data, full SQL |
| Auth | Supabase Auth | Phone OTP (MSG91 for India) + Google OAuth |
| Security | Row-Level Security | Users can only read/write their own rows — enforced at DB level, not app code |
| File Storage | Supabase Storage | Meal photos before carb counter API call |

### Backend — AI Orchestration
| Concern | Choice | Rationale |
|---|---|---|
| Framework | FastAPI (Python) | Natural home for ML/AI orchestration, async, fast |
| Agent Orchestration | LangChain | Tool-based routing between RAGbot, carb counter, and personal data layer |
| Deployment | Railway / Fly.io | Low-cost, auto-scaling, Indian region available |
| Auth | Supabase JWT verification | FastAPI validates the same JWT the Flutter app receives |

---

## 5. Module Architecture — The Registry Pattern

Every module (current and future) conforms to a single interface. This is what makes the system
infinitely scalable to new modules without touching the app shell.

```dart
abstract class AppModule {
  // Unique identifier — used for routing and intent mapping
  String get moduleId;

  // The Flutter widget rendered in the module's tab/screen
  Widget get entryWidget;

  // Navigation routes this module owns
  List<GoRoute> get routes;

  // Voice intents this module handles
  List<IntentHandler> get intentHandlers;

  // Isar schemas this module needs registered
  List<CollectionSchema> get dataSchemas;

  // Supabase tables this module syncs to
  List<SyncAdapter> get syncAdapters;
}
```

**Module Registration at app startup:**
```dart
final registry = ModuleRegistry();
registry.register(GlucoseTrackerModule());
registry.register(BolusCalculatorModule());
registry.register(CarbCounterProxyModule());
registry.register(RAGbotProxyModule());

// Adding a new module in V2 = one line here. Nothing else changes.
// registry.register(ActivityTrackerModule());
```

The `ModuleRegistry` auto-builds navigation, voice intent routing, and the bottom nav bar from
whatever modules are registered. The app shell is unaware of module internals.

---

## 6. Data Model

### Isar (Local) + Supabase (Cloud) — Mirrored Schema

#### `users` (Supabase only)
```sql
id          uuid primary key
phone       text unique
created_at  timestamptz
insulin_type text  -- 'rapid' | 'regular' (determines 500/1800 vs 400/1500 constants)
```

#### `user_profiles`
```sql
user_id           uuid references users
tdd               float      -- Total Daily Dose (units/day)
icr               float      -- Insulin-to-Carb Ratio (auto-calculated, user-confirmed)
isf               float      -- Insulin Sensitivity Factor (auto-calculated, user-confirmed)
target_bg_low     float      -- mmol/L or mg/dL
target_bg_high    float
action_duration   float      -- Hours insulin remains active (3.0–5.0)
profile_complete  boolean    -- Gates bolus module access
updated_at        timestamptz
```

#### `glucose_readings`
```sql
id          uuid
user_id     uuid
value       float
unit        text    -- 'mmol' | 'mgdl'
source      text    -- 'manual' | 'cgm' | 'health_api' (future-proofed)
notes       text
recorded_at timestamptz
synced_at   timestamptz
```

#### `bolus_entries`
```sql
id               uuid
user_id          uuid
carbs_g          float
current_bg       float
target_bg        float
food_bolus       float    -- carbs_g / ICR
correction_bolus float    -- (current_bg - target_bg) / ISF
iob              float    -- Insulin on Board at time of calculation
total_suggested  float    -- food_bolus + correction_bolus - iob
user_confirmed   boolean
insulin_taken    float    -- User can edit the actual units they took
calculated_at    timestamptz
meal_entry_id    uuid     -- nullable, links to meal if carbs came from carb counter
```

#### `meal_entries`
```sql
id              uuid
user_id         uuid
carbs_g         float
food_items      jsonb   -- [{name, carbs_g, portion}] from carb counter
input_mode      text    -- 'photo' | 'text' | 'voice'
raw_input       text    -- original voice transcript or text query
photo_url       text    -- nullable, Supabase Storage URL
logged_at       timestamptz
```

#### `notification_settings`
```sql
user_id                  uuid
logging_reminder_enabled boolean
logging_reminder_hours   int     -- trigger if no log in X hours
meal_bolus_reminder_min  int     -- trigger X min after meal with no bolus
threshold_low_alert      float
threshold_high_alert     float
threshold_alerts_enabled boolean
```

### Sync Strategy
- Isar is the **write-first** layer — all writes go local immediately, then sync
- A `sync_queue` table in Isar holds pending operations when offline
- On connectivity restored → background isolate drains the queue to Supabase
- Conflict resolution: **last-write-wins by `recorded_at` timestamp**
- Supabase Realtime subscription handles multi-device sync (future)

---

## 7. Voice & Agent Layer

This is the cross-cutting system that routes voice (and typed) commands to the right module.

### Full Pipeline

```
User holds PTT button
        │
        ▼
Audio Buffer (flutter_sound)
        │
        ▼
Whisper.cpp FFI (on-device)
  Model: whisper-small-multilingual
  Languages: Hindi, English, Hinglish (code-switch handled natively)
        │
        ▼
Transcript String (e.g. "mera sugar 180 tha abhi, bolus calculate karo")
        │
        ▼
Intent Classifier
  Lightweight: keyword trees + regex for structured commands
  LLM fallback (FastAPI) for ambiguous/complex queries only
        │
        ▼
Classified Intent + Entities
  { intent: "CALCULATE_BOLUS", entities: { current_bg: 180 } }
        │
        ▼
Module Router (consults ModuleRegistry intent handlers)
        │
        ▼
Module Handler Executes
  (BolusCal module runs calculation, returns structured result)
        │
        ▼
Response Builder
  Structured result → natural language response string
        │
        ▼
TTS Output (flutter_tts, on-device)
  + UI update (module screen reflects the action)
```

### Intent Registry

| Intent | Entities | Handled By |
|---|---|---|
| `LOG_GLUCOSE` | `value`, `unit` | GlucoseTrackerModule |
| `QUERY_LAST_GLUCOSE` | — | GlucoseTrackerModule |
| `CALCULATE_BOLUS` | `carbs_g?`, `current_bg?` | BolusCalculatorModule |
| `LOG_MEAL` | `description` | CarbCounterProxyModule |
| `ASK_RAGBOT` | `query` | RAGbotProxyModule |
| `QUERY_HISTORY` | `metric`, `timeframe` | GlucoseTrackerModule |
| `WHAT_IS_MY_IOB` | — | BolusCalculatorModule |

New modules register new intent handlers. The router is unaware of module internals.

### Intent Classification Strategy

```
Transcript
    │
    ├─► Structured command patterns (fast, no network, no LLM)
    │     "log X [mg/dl | mmol]"        → LOG_GLUCOSE
    │     "sugar [tha|hai|was|is] X"    → LOG_GLUCOSE  
    │     "bolus [calc|calculate|karo]" → CALCULATE_BOLUS
    │     "X gram carbs khaya/khaya"    → LOG_MEAL
    │     "IOB kya hai"                 → WHAT_IS_MY_IOB
    │
    └─► Falls through → FastAPI LLM intent classifier
          (only for RAGbot queries and complex natural language)
```

**Critical:** Structured commands (logging, bolus calc) NEVER go through the LLM.
Fast, deterministic, offline-capable. The LLM is only invoked for open-ended queries.

---

## 8. Bolus Calculator — Implementation Detail

### Formula Pipeline

```
INPUT: TDD (from profile), insulin_type, carbs_g, current_bg, target_bg

STEP 1 — Constants (set at profile creation, based on insulin type)
  Rapid-acting (Humalog, NovoLog, Apidra):
    ICR = 500 / TDD
    ISF = 1800 / TDD
  Regular insulin:
    ICR = 400 / TDD
    ISF = 1500 / TDD

STEP 2 — Food Bolus
  food_bolus = carbs_g / ICR

STEP 3 — Correction Bolus
  correction_bolus = (current_bg - target_bg) / ISF
  # negative correction_bolus (BG below target) reduces total dose

STEP 4 — Insulin on Board (IOB)
  Linear decay model over action_duration (user-set, 3–5 hrs):
  
  iob = Σ ( dose_i × max(0, 1 - (now - time_i) / action_duration) )
         for all bolus_entries in last action_duration hours
  
  # This prevents insulin stacking — the most dangerous bolus calc error

STEP 5 — Total Suggested Dose
  total = food_bolus + correction_bolus - iob
  total = max(0, total)  # never suggest negative insulin

OUTPUT: Displayed as "Estimated bolus: X.X U — confirm with your care team"
```

### Module Access Gate

```dart
// In BolusCalculatorModule.entryWidget:
if (!userProfile.profileComplete) {
  return BolusLockedCard(
    onSetupTap: () => context.push('/onboarding/insulin-profile'),
  );
}
return BolusCalculatorScreen();
```

---

## 9. External Module Integration — Interface Contract

Both the General RAGbot and Carb Counter are **black-box integrations**. The FastAPI orchestration
layer is the sole point of contact. If either service changes provider, protocol, or implementation,
only the FastAPI adapter changes — the Flutter app is unaffected.

### FastAPI Proxy Endpoints

```
POST /api/ragbot/query
  Body:  { query: string, user_id: string, session_id: string }
  Returns: { answer: string, sources: [], disclaimer: string }
  Adapts to: REST | WebSocket | gRPC | LangChain chain — whichever the external bot exposes

POST /api/carb-counter/analyze
  Body:  { mode: 'photo'|'text'|'voice', content: base64|string }
  Returns: { items: [{name, carbs_g, confidence}], total_carbs_g, needs_confirmation: bool }
  Adapts to: External vision API | internal model endpoint
```

### Flutter Proxy Modules

```dart
// CarbCounterProxyModule — Flutter never calls the carb API directly
class CarbCounterProxyModule implements AppModule {
  Future<MealAnalysis> analyzePhoto(File photo) async {
    // Uploads photo to Supabase Storage → sends URL to FastAPI
    final url = await storageService.upload(photo);
    return fastApiClient.post('/carb-counter/analyze', { mode: 'photo', content: url });
  }
  
  Future<MealAnalysis> analyzeText(String description) async {
    return fastApiClient.post('/carb-counter/analyze', { mode: 'text', content: description });
  }
}
```

---

## 10. Authentication & Onboarding Flow

```
SCREEN 1 — Auth
  Phone number entry → OTP via MSG91 (India) / Twilio
  OR: "Sign in with Google"

SCREEN 2 — Basic Profile
  Name, Year of diagnosis
  Insulin type: [Rapid-acting ▼] [Regular ▼]
  (This sets ICR/ISF constants — cannot be skipped)

SCREEN 3 — Insulin Profile (skippable, gates bolus module)
  "What is your Total Daily Dose?"
  [   ] units/day
  → Shows auto-calculated: ICR = X g/U, ISF = X mg/dL per U
  → "These are estimates. Confirm with your endocrinologist."
  → User can adjust ICR/ISF manually before confirming
  [Set my ratios] [Skip for now — Bolus module will be locked]

SCREEN 4 — Glucose Targets
  Low: [70] mg/dL    High: [180] mg/dL
  Insulin action duration: [4] hours
  [Skip — use defaults]

→ HOME SCREEN
```

**Supabase RLS Policy (example):**
```sql
-- Users can only access their own health data
CREATE POLICY "user_own_data" ON glucose_readings
  FOR ALL USING (auth.uid() = user_id);
```

---

## 11. Local Notifications Architecture

All three alert types run in a **Flutter background isolate** — no server, no FCM, no network needed.

```
Background Isolate (runs every 15 min via WorkManager)
    │
    ├─► CHECK: Last glucose reading > reminder_hours ago?
    │     → Local notification: "Time to check your glucose 🩸"
    │
    ├─► CHECK: Meal logged in last reminder_minutes with no bolus_entry linked?
    │     → Local notification: "Did you take your bolus after your last meal?"
    │
    └─► CHECK: Last manual reading outside [threshold_low, threshold_high]?
          → Local notification: "Your last reading was X — check again"

All notifications: opt-in, user-configurable intervals, dismissible.
```

---

## 12. Security & Compliance

| Concern | Implementation |
|---|---|
| Data at rest (device) | Isar AES-256 encryption (Isar Encryption package) |
| Data in transit | TLS 1.3 (Supabase + FastAPI enforce this) |
| Auth tokens | Supabase JWT, stored in Flutter Secure Storage (Keychain/Keystore) |
| Row-level isolation | Supabase RLS — no user can read another user's data at DB level |
| Audio privacy | Whisper.cpp runs fully on-device — no audio transmitted |
| India DPDP Act 2023 | User data stored in Supabase India region (Mumbai), explicit consent at onboarding, data deletion endpoint in profile settings |
| Audit trail | Every bolus_entry timestamped, formula version logged (for future regulatory path) |
| Bolus algorithm versioning | `formula_version` column in bolus_entries — if formula changes, historical entries remain interpretable |

---

## 13. Scalability — Adding New Modules

This is the payoff of the registry pattern. Adding a **new module** (e.g., Activity Tracker, HbA1c Predictor, Sleep Logger) requires:

1. Create a new Flutter package under `packages/modules/activity_tracker/`
2. Implement the `AppModule` interface
3. Define Isar schemas and Supabase sync adapters
4. Register voice intent handlers
5. Add one line to the module registry in `main.dart`

**Nothing in the app shell changes.** Navigation auto-updates. Voice router auto-updates.
The new module is isolated, testable, and deployable independently.

### Module Folder Structure
```
lib/
├── core/
│   ├── module_registry.dart
│   ├── voice/
│   │   ├── whisper_service.dart
│   │   ├── intent_classifier.dart
│   │   └── tts_service.dart
│   ├── data/
│   │   ├── isar_service.dart
│   │   └── supabase_sync.dart
│   └── navigation/
│       └── app_router.dart
│
packages/
└── modules/
    ├── glucose_tracker/
    │   ├── lib/glucose_tracker_module.dart
    │   ├── lib/screens/
    │   ├── lib/data/
    │   └── lib/intents/
    ├── bolus_calculator/
    ├── carb_counter_proxy/
    └── ragbot_proxy/
```

---

## 14. V2 Roadmap (Post-V1)

| Feature | Dependency |
|---|---|
| Personal RAGbot layer | Sufficient user health data in Supabase, vector embedding pipeline |
| Wake word detection | Porcupine SDK (on-device), replaces PTT |
| Health API bridge (HealthKit/Health Connect) | Platform-specific plugin, replaces/supplements manual entry |
| Caregiver sharing | Multi-user data relationships, Supabase Realtime, FCM push |
| Direct CGM integration (Dexcom Share / LibreLinkUp) | Partner API agreements |
| HbA1c trend predictor | 90-day glucose data, regression model in FastAPI |
| Web companion (PWA) | Next.js frontend on shared Supabase backend |
| Regulatory pathway (wellness → SaMD) | Audit trail already built; needs clinical validation study |

---

## 15. Decision Log

| Decision | Choice | Rationale |
|---|---|---|
| Regulation | Wellness companion | Faster to market; architecture is regulation-ready for future 510(k) |
| Platform | Flutter cross-platform | Single codebase, near-native performance, excellent data UI |
| Local DB | Isar (not Hive) | Full query engine required for time-series health data |
| Cloud backend | Supabase | Open-source, self-hostable, real SQL, no vendor lock-in |
| AI orchestration | FastAPI | Python-native for ML/AI, external modules isolated behind HTTP |
| STT | Whisper.cpp (on-device) | Privacy, offline, Hinglish multilingual support |
| Voice modality | Push-to-talk | No accidental triggers, no background mic, trust-critical for health app |
| Bolus constant | 500/1800 (rapid) or 400/1500 (regular) | Insulin type captured at onboarding; constants differ by insulin class |
| Carb counter | Black-box proxy | Owned by separate team; integration point only |
| RAGbot general | Black-box proxy | Pre-built external service; interface-agnostic adapter in FastAPI |
| RAGbot personal | V2 | Needs data history to be useful; ship after users have 3+ weeks of logs |
| Notifications | Local isolate only | No server infrastructure for v1; FCM enters in v2 for caregiver alerts |
