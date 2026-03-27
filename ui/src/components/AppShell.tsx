import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  appendJournalEntry,
  fetchLatestSessionEntry,
  fetchSessionHistory,
  fetchSessionSummaries,
  type JournalEntryRecord,
} from "../api/journalApi";
import { micStart, micStop } from "../api/orchestrationApi";
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
const AUTOSAVE_MAX_ATTEMPTS = 3;

type JournalSource = "ui_manual" | "ui_command";
type VoiceMicState = "idle" | "listening" | "processing";

function createSessionId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function isTransientSaveError(error: unknown): boolean {
  const message = error instanceof Error ? error.message : String(error);
  return (
    message.includes("Failed to fetch") ||
    message.includes("NetworkError") ||
    message.includes("429") ||
    message.includes("502") ||
    message.includes("503") ||
    message.includes("504")
  );
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
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
      headRevisionId: null,
      baseRevisionId: null,
      createdBy: entry.createdBy || "ui_manual",
      entryType: entry.entryType || "general",
      lastSavedAt: entry.lastSavedAt ?? null,
      isDirty: false,
    };
  });
}

function createDraftEntry(title: string): Entry {
  const nowIso = new Date().toISOString();
  const sessionId = createSessionId();
  return {
    id: sessionId,
    sessionId,
    headRevisionId: null,
    baseRevisionId: null,
    title,
    updatedAt: formatUpdatedAt(nowIso),
    lastSavedAt: null,
    isDirty: false,
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

  const [voiceMicState, setVoiceMicState] = useState<VoiceMicState>("idle");
  const [voiceTranscriptPreview, setVoiceTranscriptPreview] = useState<string | null>(null);
  const [voiceErrorMessage, setVoiceErrorMessage] = useState<string | null>(null);

  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [revisionHistory, setRevisionHistory] = useState<JournalEntryRecord[]>([]);
  const [isHistoryLoading, setIsHistoryLoading] = useState<boolean>(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [loadedRevisionId, setLoadedRevisionId] = useState<string | null>(null);

  const editorRef = useRef<JournalEditorHandle | null>(null);
  const saveDebounceRef = useRef<number | null>(null);
  const savedSignatureRef = useRef<Map<string, string>>(new Map());
  const activeEntryRef = useRef<Entry | null>(null);
  const historyRequestRef = useRef<number>(0);

  const activeEntry = useMemo(
    () => entries.find((entry) => entry.id === activeEntryId) ?? null,
    [entries, activeEntryId]
  );
  const isViewingHistoricalRevision = useMemo(() => {
    if (!activeEntry?.headRevisionId || !loadedRevisionId) {
      return false;
    }
    return activeEntry.headRevisionId !== loadedRevisionId;
  }, [activeEntry?.headRevisionId, loadedRevisionId]);

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

  const fetchCurrentHeadRevisionId = useCallback(async (sessionId: string) => {
    try {
      const latest = await fetchLatestSessionEntry(sessionId);
      return latest.entry_id;
    } catch {
      return null;
    }
  }, []);

  const refreshRevisionHistory = useCallback(async (sessionId: string) => {
    const requestId = Date.now();
    historyRequestRef.current = requestId;
    setIsHistoryLoading(true);
    setHistoryError(null);

    try {
      const rows = await fetchSessionHistory(sessionId, 100);
      if (historyRequestRef.current !== requestId) {
        return;
      }
      setRevisionHistory(rows);
      const latestRevisionId = rows[0]?.entry_id ?? null;
      if (latestRevisionId) {
        setEntries((current) =>
          current.map((item) =>
            item.sessionId === sessionId
              ? {
                  ...item,
                  headRevisionId: latestRevisionId,
                }
              : item
          )
        );
      }
    } catch (error) {
      if (historyRequestRef.current !== requestId) {
        return;
      }
      const message =
        error instanceof Error ? error.message : "Failed to load revision history.";
      setHistoryError(message);
      setRevisionHistory([]);
    } finally {
      if (historyRequestRef.current === requestId) {
        setIsHistoryLoading(false);
      }
    }
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
      const baseRevisionId = entry.baseRevisionId ?? entry.headRevisionId;

      if (!options?.force && source === "ui_manual" && lastSavedSignature === signature) {
        setSaveStatus("saved");
        setEntries((current) =>
          current.map((item) =>
            item.sessionId === entry.sessionId
              ? {
                  ...item,
                  isDirty: false,
                }
              : item
          )
        );
        return true;
      }

      try {
        if (baseRevisionId && entry.headRevisionId) {
          const currentHeadRevisionId = await fetchCurrentHeadRevisionId(entry.sessionId);
          if (currentHeadRevisionId && currentHeadRevisionId !== entry.headRevisionId) {
            setSaveStatus("conflict");
            setSaveError(
              "A newer revision was created in this session. Reload latest before saving."
            );
            void refreshRevisionHistory(entry.sessionId);
            return false;
          }
        }

        let response: Awaited<ReturnType<typeof appendJournalEntry>> | null = null;
        let retryAttempt = 0;
        let lastError: unknown = null;

        while (retryAttempt < AUTOSAVE_MAX_ATTEMPTS && !response) {
          try {
            response = await appendJournalEntry(
              {
                session_id: entry.sessionId,
                base_revision_id: baseRevisionId ?? undefined,
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
          } catch (error) {
            lastError = error;
            const canRetry =
              isTransientSaveError(error) && retryAttempt < AUTOSAVE_MAX_ATTEMPTS - 1;
            if (!canRetry) {
              throw error;
            }
            const backoffMs = 500 * 2 ** retryAttempt;
            retryAttempt += 1;
            setSaveError(
              `Autosave retry ${retryAttempt}/${AUTOSAVE_MAX_ATTEMPTS - 1} in ${backoffMs}ms...`
            );
            await delay(backoffMs);
          }
        }

        if (!response) {
          throw lastError ?? new Error("Failed to save journal entry.");
        }

        savedSignatureRef.current.set(entry.sessionId, signature);

        setEntries((current) =>
          current.map((item) =>
            item.sessionId === entry.sessionId
              ? {
                  ...item,
                  title: response.title,
                  content: response.content,
                  headRevisionId: response.entry_id,
                  baseRevisionId: response.entry_id,
                  updatedAt: formatUpdatedAt(response.created_at),
                  lastSavedAt: response.created_at,
                  isDirty: false,
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
        setLoadedRevisionId(response.entry_id);
        void refreshRevisionHistory(entry.sessionId);
        return true;
      } catch (error) {
        const message =
          error instanceof Error
            ? error.message
            : "Failed to save journal entry after retries. Will retry on next autosave trigger.";
        setSaveStatus("error");
        setSaveError(message);
        return false;
      }
    },
    [fetchCurrentHeadRevisionId, refreshRevisionHistory]
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
          headRevisionId:
            latest?.entry_id ?? summary.head_revision_id ?? summary.latest_entry_id ?? null,
          baseRevisionId:
            latest?.entry_id ?? summary.head_revision_id ?? summary.latest_entry_id ?? null,
          title: summary.title,
          updatedAt: formatUpdatedAt(createdAt),
          lastSavedAt: createdAt,
          isDirty: false,
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
      setLoadedRevisionId(hydratedEntries[0].baseRevisionId);
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
      setLoadedRevisionId(fallbackEntries[0].baseRevisionId);
      setSaveStatus("saved");
    } finally {
      setIsHydrating(false);
    }
  }, []);

  useEffect(() => {
    void hydrateEntriesFromApi();
  }, [hydrateEntriesFromApi]);

  useEffect(() => {
    const activeSessionId = activeEntry?.sessionId;
    if (!activeSessionId) {
      setRevisionHistory([]);
      setHistoryError(null);
      setIsHistoryLoading(false);
      return;
    }
    setLoadedRevisionId(activeEntry.baseRevisionId);
    void refreshRevisionHistory(activeSessionId);
  }, [activeEntry?.baseRevisionId, activeEntry?.sessionId, refreshRevisionHistory]);

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
              baseRevisionId: entry.baseRevisionId ?? entry.headRevisionId,
              updatedAt: "Now",
              isDirty: true,
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
    setLoadedRevisionId(null);
    setWorkspaceMode("journal");
    setSaveStatus("saved");
    setSaveError(null);
    savedSignatureRef.current.set(nextEntry.sessionId, entrySignature(nextEntry));
    setRevisionHistory([]);
    setHistoryError(null);
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

  const handleLoadRevision = (revision: JournalEntryRecord) => {
    setEntries((current) =>
      current.map((entry) =>
        entry.id === activeEntryId
          ? {
              ...entry,
              title: revision.title,
              content: revision.content,
              baseRevisionId: revision.entry_id,
              updatedAt: formatUpdatedAt(revision.created_at),
              isDirty: false,
              metadata: normalizeEntryMetadata(revision.metadata, revision.created_at),
              createdBy: revision.created_by,
              entryType: revision.entry_type,
              lastSavedAt: revision.created_at,
            }
          : entry
      )
    );
    setLoadedRevisionId(revision.entry_id);
    setSaveStatus("saved");
    setSaveError(null);
    setWorkspaceMode("journal");
  };

  const handleLoadLatestRevision = useCallback(async () => {
    const current = activeEntryRef.current;
    if (!current?.sessionId || !current.headRevisionId) {
      return;
    }

    const fromHistory =
      revisionHistory.find((item) => item.entry_id === current.headRevisionId) ?? null;

    if (fromHistory) {
      handleLoadRevision(fromHistory);
      return;
    }

    try {
      const latest = await fetchLatestSessionEntry(current.sessionId);
      handleLoadRevision(latest);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to load latest revision.";
      setSaveError(message);
    }
  }, [handleLoadRevision, revisionHistory]);

  const handleToolbarAction = (action: ToolbarAction) => {
    if (workspaceMode !== "journal") {
      return;
    }

    editorRef.current?.runToolbarAction(action);
  };

  const handleToggleVoiceMic = () => {
    if (voiceMicState === "processing") {
      return;
    }

    if (voiceMicState === "listening") {
      setVoiceMicState("processing");
      setVoiceErrorMessage(null);
      void (async () => {
        try {
          const stopResult = await micStop();
          const fullText = stopResult.full_text?.trim() ?? "";
          setVoiceTranscriptPreview(fullText.length ? fullText : null);

          const active = activeEntryRef.current;
          if (active?.sessionId) {
            const latest = await fetchLatestSessionEntry(active.sessionId);
            const updatedEntry: Entry = {
              ...active,
              title: latest.title,
              content: latest.content,
              headRevisionId: latest.entry_id,
              baseRevisionId: latest.entry_id,
              updatedAt: formatUpdatedAt(latest.created_at),
              lastSavedAt: latest.created_at,
              isDirty: false,
              bucket: toEntryBucket(latest.created_at),
              metadata: normalizeEntryMetadata(latest.metadata, latest.created_at),
              createdBy: latest.created_by,
              entryType: latest.entry_type,
            };

            setEntries((current) =>
              current.map((entry) => (entry.id === active.id ? updatedEntry : entry))
            );
            savedSignatureRef.current.set(active.sessionId, entrySignature(updatedEntry));
            setLoadedRevisionId(latest.entry_id);
            setSaveStatus("saved");
            setSaveError(null);
            void refreshRevisionHistory(active.sessionId);
          }
        } catch (error) {
          const message =
            error instanceof Error ? error.message : "Failed to stop mic session.";
          setVoiceErrorMessage(message);
        } finally {
          setVoiceMicState("idle");
        }
      })();
      return;
    }

    setVoiceErrorMessage(null);
    setVoiceTranscriptPreview(null);
    void (async () => {
      try {
        await micStart({
          language: "en",
          stt_api_url: "http://localhost:8001",
          silence_duration: 0.8,
          silence_threshold: 0.01,
        });
        setVoiceMicState("listening");
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Failed to start mic session.";
        setVoiceErrorMessage(message);
        setVoiceMicState("idle");
      }
    })();
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
        voiceMicState={voiceMicState}
        onToggleVoiceMic={handleToggleVoiceMic}
        voiceTranscriptPreview={voiceTranscriptPreview}
        voiceErrorMessage={voiceErrorMessage}
        loadError={loadError}
        saveError={saveError}
        revisionHistory={revisionHistory}
        isHistoryLoading={isHistoryLoading}
        historyError={historyError}
        loadedRevisionId={loadedRevisionId}
        headRevisionId={activeEntry.headRevisionId}
        onLoadRevision={handleLoadRevision}
        onLoadLatestRevision={() => {
          void handleLoadLatestRevision();
        }}
        isViewingHistoricalRevision={isViewingHistoricalRevision}
      />
    </div>
  );
}
