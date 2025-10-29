# Jarvis AI Monorepo

A top-of-the-line, robust AI assistant system named **Jarvis**. This repo is organized as a clean, extensible monorepo for web, API, desktop assistant, shared packages, infra, and docs.

## Goals

- Clear separation of apps, shared packages, infra, and configuration
- Scalable for realtime AI, skills/plugins, memory, and orchestration
- Easy local development with predictable paths and environment management

## Folder Structure

```
JarvisAi/
├─ apps/
│  ├─ web/                # Web UI (e.g., Next.js)
│  ├─ api/                # Backend API (e.g., FastAPI/Node)
│  └─ assistant/          # Desktop/overlay client (e.g., Electron)
├─ packages/
│  ├─ core/               # Orchestration, pipelines, tools
│  ├─ ai/                 # Model wrappers, inference, embeddings
│  ├─ ui/                 # Reusable UI components
│  └─ common/             # Shared utilities, types, config loaders
├─ infra/
│  ├─ docker/             # Container definitions
│  └─ terraform/          # Cloud infra as code (optional)
├─ config/
│  └─ env/                # Environment templates and loaders
├─ scripts/               # Dev and ops scripts
├─ docs/                  # Architecture and product docs
├─ data/                  # Local datasets (gitignored)
├─ models/                # Model artifacts (gitignored)
└─ .vscode/               # Editor settings for consistency
```

## Python App (JarvisAI)

Alongside the monorepo scaffolding, there is a simple Python application layout for a local desktop GUI assistant:

```
JarvisAi/
├─ main_gui.py                 # Tkinter-based GUI entry
├─ core/
│  ├─ brain.py                 # Core decision logic (stub)
│  ├─ speech.py                # Speech recognition wrapper (optional deps)
│  ├─ tts.py                   # Text-to-speech via pyttsx3
│  └─ memory.py                # JSON-backed memory store
├─ drivers/
│  ├─ __init__.py
│  ├─ open_apps.py             # Launch common apps (Windows)
│  ├─ system_info.py           # System metrics via psutil
│  └─ play_music.py            # Simple audio playback via playsound
├─ memory.json                 # Persistent storage
├─ .env                        # Local environment (gitignored)
└─ requirements.txt            # Python dependencies
```

### Run the GUI

- Create and activate a virtual environment (optional but recommended).
- Install dependencies: `pip install -r requirements.txt`
- Start: `python main_gui.py`

Notes:
- Speech recognition is optional; install microphone drivers and `PyAudio` if needed.
- TTS uses `pyttsx3`, which works offline.

### Wake Word ("Hey Jarvis")

To enable offline wake word detection with Porcupine:
- Install deps: `pip install pvporcupine pyaudio`
- Get a free Picovoice Access Key at `https://console.picovoice.ai/`
- Add to `.env`: `PICOVOICE_KEY=your_picovoice_key_here`

The listener runs in the background and, on detecting “Hey Jarvis”, speaks “Yes?” and triggers voice listening automatically.


## Quick Start (Planning)

- Populate `config/env/.env.example` with required environment variables
- Choose stacks (e.g., Next.js for `apps/web`, FastAPI or Node for `apps/api`)
- Implement core modules in `packages/core` (skills, memory, routing)
- Wire up realtime messaging between `assistant` and `api`

## Docs

- See `docs/architecture.md` for the high-level design
- Each app/package folder includes a local README for scope and responsibilities