import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  appendJournalEntry,
  fetchLatestSessionEntry,
  fetchSessionSummaries,
} from "../api/journalApi";
import { initialEntries } from "../data/mockData";
import type {
  AppSection,
  Entry,
  EntryBucket,
  EntryMetadata,
  SaveStatus,
  ToolbarAction,
  WorkspaceMode,
} from "../types";
import { GlobalRail } from "./layout/GlobalRail";
import { ProjectSidebar } from "./layout/ProjectSidebar";
import { Workspace } from "./workspace/Workspace";
import type { JournalEditorHandle } from "./workspace/JournalEditor";

const AUTOSAVE_DELAY_MS = 2000;

type JournalSource = "ui_manual" | "ui_command";

function createSessionId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function toEntryBucket(isoTimestamp: string): EntryBucket {
  const createdAt = new Date(isoTimestamp);
  const now = new Date();
  const dayMs = 24 * 60 * 60 * 1000;
  const daysDiff = Math.floor((now.getTime() - createdAt.getTime()) / dayMs);

  if (daysDiff <= 0) {
    return "today";
  }
  if (daysDiff <= 7) {
    return "week";
  }
  return "older";
}

function formatUpdatedAt(isoTimestamp: string): string {
  const date = new Date(isoTimestamp);
  const now = new Date();

  const sameDay = date.toDateString() === now.toDateString();
  if (sameDay) {
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (date.toDateString() === yesterday.toDateString()) {
    return "Yesterday";
  }

  return date.toLocaleDateString([], { month: "short", day: "numeric" });
}

function normalizeEntryMetadata(raw: unknown, createdAtIso: string): EntryMetadata {
  const metadata = typeof raw === "object" && raw !== null ? (raw as Record<string, unknown>) : {};

  const tags = Array.isArray(metadata.tags)
    ? metadata.tags.filter((item): item is string => typeof item === "string")
    : [];

  const notes = typeof metadata.notes === "string" ? metadata.notes : "";
  const date =
    typeof metadata.date === "string" && metadata.date.length > 0
      ? metadata.date
      : createdAtIso.slice(0, 10);

  return {
    date,
    tags,
    notes,
  };
}

function entrySignature(entry: Entry): string {
  return JSON.stringify({
    title: entry.title,
    content: entry.content,
    metadata: entry.metadata,
  });
}

function fallbackEntriesFromMockData(): Entry[] {
  return initialEntries.map((entry, index) => {
    const sessionId = entry.sessionId || `mock-session-${index}`;
    return {
      ...entry,
      id: sessionId,
      sessionId,
      createdBy: entry.createdBy || "ui_manual",
      entryType: entry.entryType || "general",
    };
  });
}

function createDraftEntry(title: string): Entry {
  const nowIso = new Date().toISOString();
  const sessionId = createSessionId();
  return {
    id: sessionId,
    sessionId,
    title,
    updatedAt: formatUpdatedAt(nowIso),
    bucket: "today",
    content: "<p>Start documenting this experiment...</p>",
    metadata: {
      date: nowIso.slice(0, 10),
      tags: [],
      notes: "",
    },
    createdBy: "ui_manual",
    entryType: "general",
  };
}

export function AppShell() {
  const [activeSection, setActiveSection] = useState<AppSection>("projects");
  const [entries, setEntries] = useState<Entry[]>([]);
  const [activeEntryId, setActiveEntryId] = useState<string>("");
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [activeFilter, setActiveFilter] = useState<EntryBucket | "all">("all");
  const [workspaceMode, setWorkspaceMode] = useState<WorkspaceMode>("journal");
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("saved");
  const [isHydrating, setIsHydrating] = useState<boolean>(true);

  const [isVoicePanelOpen, setIsVoicePanelOpen] = useState<boolean>(false);
  const [voicePromptDraft, setVoicePromptDraft] = useState<string>("");
  const [isVoiceSending, setIsVoiceSending] = useState<boolean>(false);

  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  const editorRef = useRef<JournalEditorHandle | null>(null);
  const saveDebounceRef = useRef<number | null>(null);
  const savedSignatureRef = useRef<Map<string, string>>(new Map());
  const activeEntryRef = useRef<Entry | null>(null);

  const activeEntry = useMemo(
    () => entries.find((entry) => entry.id === activeEntryId) ?? null,
    [entries, activeEntryId]
  );

  useEffect(() => {
    activeEntryRef.current = activeEntry;
  }, [activeEntry]);

  useEffect(() => {
    return () => {
      if (saveDebounceRef.current) {
        window.clearTimeout(saveDebounceRef.current);
      }
    };
  }, []);

  const persistEntry = useCallback(
    async (
      entry: Entry,
      source: JournalSource,
      options?: {
        keepalive?: boolean;
        force?: boolean;
      }
    ): Promise<boolean> => {
      const signature = entrySignature(entry);
      const lastSavedSignature = savedSignatureRef.current.get(entry.sessionId);

      if (!options?.force && source === "ui_manual" && lastSavedSignature === signature) {
        setSaveStatus("saved");
        return true;
      }

      try {
        const response = await appendJournalEntry(
          {
            session_id: entry.sessionId,
            title: entry.title,
            content: entry.content,
            entry_type: "general",
            source,
            metadata: {
              date: entry.metadata.date,
              tags: entry.metadata.tags,
              notes: entry.metadata.notes,
            },
          },
          { keepalive: options?.keepalive }
        );

        savedSignatureRef.current.set(entry.sessionId, signature);

        setEntries((current) =>
          current.map((item) =>
            item.sessionId === entry.sessionId
              ? {
                  ...item,
                  title: response.title,
                  content: response.content,
                  updatedAt: formatUpdatedAt(response.created_at),
                  bucket: toEntryBucket(response.created_at),
                  metadata: normalizeEntryMetadata(response.metadata, response.created_at),
                  createdBy: response.created_by,
                  entryType: response.entry_type,
                }
              : item
          )
        );

        setSaveStatus("saved");
        setSaveError(null);
        return true;
      } catch (error) {
        const message =
          error instanceof Error
            ? error.message
            : "Failed to save journal entry. Retrying on next autosave trigger.";
        setSaveStatus("error");
        setSaveError(message);
        return false;
      }
    },
    []
  );

  const flushActiveAutosave = useCallback(
    async (options?: { keepalive?: boolean }) => {
      if (saveDebounceRef.current) {
        window.clearTimeout(saveDebounceRef.current);
        saveDebounceRef.current = null;
      }

      const current = activeEntryRef.current;
      if (!current) {
        return;
      }

      await persistEntry(current, "ui_manual", { keepalive: options?.keepalive });
    },
    [persistEntry]
  );

  const scheduleAutosave = useCallback(() => {
    if (isHydrating) {
      return;
    }

    if (saveDebounceRef.current) {
      window.clearTimeout(saveDebounceRef.current);
    }

    saveDebounceRef.current = window.setTimeout(() => {
      void flushActiveAutosave();
    }, AUTOSAVE_DELAY_MS);
  }, [flushActiveAutosave, isHydrating]);

  const hydrateEntriesFromApi = useCallback(async () => {
    setIsHydrating(true);
    setLoadError(null);

    try {
      const summaries = await fetchSessionSummaries();

      if (!summaries.length) {
        const draft = createDraftEntry("Untitled Session");
        savedSignatureRef.current = new Map([[draft.sessionId, entrySignature(draft)]]);
        setEntries([draft]);
        setActiveEntryId(draft.id);
        setSaveStatus("saved");
        setIsHydrating(false);
        return;
      }

      const latestRecords = await Promise.all(
        summaries.map(async (summary) => {
          try {
            return await fetchLatestSessionEntry(summary.session_id);
          } catch {
            return null;
          }
        })
      );

      const hydratedEntries: Entry[] = summaries.map((summary, index) => {
        const latest = latestRecords[index];
        const createdAt = latest?.created_at ?? summary.latest_created_at;
        const metadata = normalizeEntryMetadata(latest?.metadata, createdAt);

        return {
          id: summary.session_id,
          sessionId: summary.session_id,
          title: summary.title,
          updatedAt: formatUpdatedAt(createdAt),
          bucket: toEntryBucket(createdAt),
          content: latest?.content ?? "<p>Start documenting this experiment...</p>",
          metadata,
          createdBy: latest?.created_by ?? "ui_manual",
          entryType: latest?.entry_type ?? summary.latest_entry_type,
        };
      });

      hydratedEntries.sort((left, right) => {
        const leftDate = new Date(summaries.find((item) => item.session_id === left.sessionId)?.latest_created_at ?? 0);
        const rightDate = new Date(
          summaries.find((item) => item.session_id === right.sessionId)?.latest_created_at ?? 0
        );
        return rightDate.getTime() - leftDate.getTime();
      });

      savedSignatureRef.current = new Map(
        hydratedEntries.map((entry) => [entry.sessionId, entrySignature(entry)])
      );

      setEntries(hydratedEntries);
      setActiveEntryId(hydratedEntries[0].id);
      setSaveStatus("saved");
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Failed to load journal data from DB-backed API.";
      setLoadError(message);

      const fallbackEntries = fallbackEntriesFromMockData();
      savedSignatureRef.current = new Map(
        fallbackEntries.map((entry) => [entry.sessionId, entrySignature(entry)])
      );
      setEntries(fallbackEntries);
      setActiveEntryId(fallbackEntries[0].id);
      setSaveStatus("saved");
    } finally {
      setIsHydrating(false);
    }
  }, []);

  useEffect(() => {
    void hydrateEntriesFromApi();
  }, [hydrateEntriesFromApi]);

  useEffect(() => {
    const handleBeforeUnload = () => {
      void flushActiveAutosave({ keepalive: true });
    };

    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
    };
  }, [flushActiveAutosave]);

  useEffect(() => {
    if (!entries.length) {
      return;
    }

    const hasActive = entries.some((entry) => entry.id === activeEntryId);
    if (!hasActive) {
      setActiveEntryId(entries[0].id);
    }
  }, [entries, activeEntryId]);

  const updateActiveEntryFromUser = (updater: (entry: Entry) => Entry) => {
    const currentActive = activeEntryRef.current;
    if (!currentActive) {
      return;
    }

    setEntries((current) =>
      current.map((entry) =>
        entry.id === currentActive.id
          ? {
              ...updater(entry),
              updatedAt: "Now",
            }
          : entry
      )
    );

    setSaveStatus("saving");
    setSaveError(null);
    scheduleAutosave();
  };

  const handleSelectEntry = (entryId: string) => {
    void flushActiveAutosave();
    setActiveEntryId(entryId);
    setWorkspaceMode("journal");
  };

  const handleCreateEntry = () => {
    void flushActiveAutosave();

    const nextEntry = createDraftEntry(`Untitled Session ${entries.length + 1}`);
    setEntries((current) => [nextEntry, ...current]);
    setActiveEntryId(nextEntry.id);
    setWorkspaceMode("journal");
    setSaveStatus("saved");
    setSaveError(null);
    savedSignatureRef.current.set(nextEntry.sessionId, entrySignature(nextEntry));
  };

  const handleTitleChange = (title: string) => {
    updateActiveEntryFromUser((entry) => ({
      ...entry,
      title: title.trim().length ? title : "Untitled Session",
    }));
  };

  const handleEditorContentChange = (content: string) => {
    updateActiveEntryFromUser((entry) => ({
      ...entry,
      content,
    }));
  };

  const handleMetadataChange = (metadata: EntryMetadata) => {
    updateActiveEntryFromUser((entry) => ({
      ...entry,
      metadata,
    }));
  };

  const handleEditorBlur = () => {
    void flushActiveAutosave();
  };

  const handleModeChange = (mode: WorkspaceMode) => {
    if (workspaceMode === "journal" && mode !== "journal") {
      void flushActiveAutosave();
    }
    setWorkspaceMode(mode);
  };

  const handleToolbarAction = (action: ToolbarAction) => {
    if (workspaceMode !== "journal") {
      return;
    }

    editorRef.current?.runToolbarAction(action);
  };

  const handleToggleVoicePanel = () => {
    setIsVoicePanelOpen((current) => !current);
  };

  const handleCloseVoicePanel = () => {
    setIsVoicePanelOpen(false);
  };

  const handleSendVoicePrompt = async () => {
    const prompt = voicePromptDraft.trim();
    if (!prompt.length || isVoiceSending) {
      return;
    }

    const current = activeEntryRef.current;
    if (!current) {
      return;
    }

    setIsVoiceSending(true);
    setVoicePromptDraft("");

    const commandBlock = `<p><strong>Command:</strong> ${escapeHtml(prompt)}</p>`;
    const updatedEntry: Entry = {
      ...current,
      content: `${current.content}${commandBlock}`,
      updatedAt: "Now",
    };

    setEntries((entriesList) =>
      entriesList.map((entry) => (entry.id === current.id ? updatedEntry : entry))
    );
    setSaveStatus("saving");
    setSaveError(null);

    if (saveDebounceRef.current) {
      window.clearTimeout(saveDebounceRef.current);
      saveDebounceRef.current = null;
    }

    await persistEntry(updatedEntry, "ui_command", { force: true });
    setIsVoiceSending(false);
  };

  if (!activeEntry) {
    return (
      <div className="appShell">
        <GlobalRail activeSection={activeSection} onSectionChange={setActiveSection} />
        <ProjectSidebar
          entries={entries}
          activeEntryId={activeEntryId}
          searchTerm={searchTerm}
          activeFilter={activeFilter}
          onSelectEntry={handleSelectEntry}
          onCreateEntry={handleCreateEntry}
          onSearchTermChange={setSearchTerm}
          onFilterChange={setActiveFilter}
        />
        <section className="workspace" aria-label="Notebook workspace">
          <div className="workspaceMain">
            <div className="workspaceCanvas">
              <div className="filesPanel">
                <h2>{isHydrating ? "Loading journal entries..." : "No entries available"}</h2>
                {loadError && <p>{loadError}</p>}
              </div>
            </div>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="appShell">
      <GlobalRail activeSection={activeSection} onSectionChange={setActiveSection} />

      <ProjectSidebar
        entries={entries}
        activeEntryId={activeEntry.id}
        searchTerm={searchTerm}
        activeFilter={activeFilter}
        onSelectEntry={handleSelectEntry}
        onCreateEntry={handleCreateEntry}
        onSearchTermChange={setSearchTerm}
        onFilterChange={setActiveFilter}
      />

      <Workspace
        entry={activeEntry}
        workspaceMode={workspaceMode}
        saveStatus={saveStatus}
        editorRef={editorRef}
        onTitleChange={handleTitleChange}
        onModeChange={handleModeChange}
        onToolbarAction={handleToolbarAction}
        onEditorContentChange={handleEditorContentChange}
        onEditorBlur={handleEditorBlur}
        onMetadataChange={handleMetadataChange}
        isVoicePanelOpen={isVoicePanelOpen}
        voicePromptDraft={voicePromptDraft}
        isVoiceSending={isVoiceSending}
        onToggleVoicePanel={handleToggleVoicePanel}
        onVoicePromptChange={setVoicePromptDraft}
        onSendVoicePrompt={() => {
          void handleSendVoicePrompt();
        }}
        onCloseVoicePanel={handleCloseVoicePanel}
        loadError={loadError}
        saveError={saveError}
      />
    </div>
  );
}
