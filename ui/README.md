# LabJ ELN UI Plan (Inspired by Benchling)

## Overview
LabJ is a **voice-first Electronic Lab Notebook (ELN)** designed for wet labs.  
Unlike traditional ELNs (e.g., Benchling), which are document-first, LabJ is **capture-first**, with speech-to-text (STT) as the primary input modality.

This document defines the **UI architecture, component breakdown, and MVP scope**.

---

## Core Design Principle

Benchling:
> Document-first + structured scientific data

LabJ:
> Capture-first + voice-native interaction

Key questions the UI must always answer:
1. Is the mic on or off?
2. What is being transcribed?
3. What did the system understand?
4. Where will it be inserted?
5. Can the user edit before committing?

---

## High-Level Architecture
App
├── Projects
│ ├── Project list
│ └── Project detail
│ ├── Journal entries
│ ├── Templates
│ └── Attachments
├── Search
├── Recent
└── Settings


---

## Project-Level Layout


Project Shell
├── Left Sidebar
│ ├── Search
│ ├── Filters
│ ├── New Entry
│ └── Entry List
├── Top Tabs (open entries)
└── Active Entry View
├── Entry Header
├── Mode Tabs (Journal / Metadata / Files)
├── Toolbar
├── Main Canvas
└── Voice Capture Dock


---

## Component Breakdown

### 1. Global Rail
- App navigation (Projects, Search, Recent, Settings)
- Icon-only vertical bar

### 2. Project Sidebar
- Project selector
- Search input
- Filters
- New Entry button
- Entry list (title, last edited, active state)

### 3. Workspace Tabs
- Multiple open entries
- Active tab highlight
- Close buttons

### 4. Entry Header
- Title
- Save state
- Share/export
- Overflow menu

### 5. Mode Tabs
- Journal (default)
- Metadata
- Files

### 6. Toolbar (MVP)
- Bold / Italic / Underline
- Lists (bullet, numbered)
- Headings
- Checkbox
- Table insert
- File/image attach
- Timestamp

### 7. Main Journal Canvas
- Rich-text or block editor
- Sections
- Tables
- Attachments
- Voice-inserted content blocks

### 8. Voice Capture Dock (CORE FEATURE)
- Persistent mic button
- States: idle / listening / processing / error
- Live transcript preview
- Actions:
  - Insert
  - Insert as structured step
  - Edit
  - Discard
- Modes:
  - Dictation
  - Command
  - Note

### 9. Metadata Panel
- Title
- Date/time
- Tags
- Samples/reagents (free text)
- Protocol reference
- Attachments

---

## Layout (Desktop)


┌──────┬────────────────────┬──────────────────────────────────────────────┐
│ Rail │ Project Sidebar │ Workspace │
│ │ │ ┌──────────────────────────────────────────┐ │
│ │ │ │ Tabs │ │
│ │ │ ├──────────────────────────────────────────┤ │
│ │ │ │ Header │ │
│ │ │ ├──────────────────────────────────────────┤ │
│ │ │ │ Mode Tabs │ │
│ │ │ ├──────────────────────────────────────────┤ │
│ │ │ │ Toolbar │ │
│ │ │ ├──────────────────────────────────────────┤ │
│ │ │ │ Main Canvas │ │
│ │ │ ├──────────────────────────────────────────┤ │
│ │ │ │ Voice Dock │ │
│ │ │ └──────────────────────────────────────────┘ │
└──────┴────────────────────┴──────────────────────────────────────────────┘


---

## Voice Interaction Modes

### Dictation
- Speak → transcript → insert as text block

### Command
- Speak → parse → structured step → confirm → insert

### Note
- Quick voice → timestamped note block

---

## Design Guidelines

### Keep from Benchling
- Clean enterprise UI
- White canvas + gray background
- Blue as primary action color
- High density, low clutter

### Adapt for LabJ
- Prominent mic control
- Strong recording state feedback
- Simpler UI
- Fewer simultaneous controls

---

## Design Tokens

- Background: light gray
- Canvas: white
- Primary: blue
- Success: green
- Error: red
- Radius: small-medium
- Spacing: 4 / 8 / 12 / 16 / 24

---

## MVP Scope

### Build Now
- App shell
- Sidebar + entry list
- Tabs
- Editor
- Toolbar
- Voice dock
- Metadata

### Next
- Attachments
- Search
- Templates
- Structured step insertion

### Later
- Protocols
- Inventory
- Review workflows

---

## Product Decisions

1. Voice must be **persistent and visible**
2. Metadata must be **lightweight**
3. Journal + transcription must feel like **one surface**

---

## Next Steps

1. Finalize layout
2. Choose voice dock design (bottom vs floating)
3. Build React skeleton
4. Integrate STT states later