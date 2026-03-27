import type { RefObject } from "react";
import type { JournalEntryRecord } from "../../api/journalApi";
import type {
  Entry,
  EntryMetadata,
  SaveStatus,
  ToolbarAction,
  WorkspaceMode,
} from "../../types";
import { EntryHeader } from "./EntryHeader";
import { JournalEditor, type JournalEditorHandle } from "./JournalEditor";
import { MetadataPanel } from "./MetadataPanel";
import { ModeTabs } from "./ModeTabs";
import { RevisionHistoryPanel } from "./RevisionHistoryPanel";
import { Toolbar } from "./Toolbar";
import { VoiceCaptureDock } from "./VoiceCaptureDock";

interface WorkspaceProps {
  entry: Entry;
  workspaceMode: WorkspaceMode;
  saveStatus: SaveStatus;
  editorRef: RefObject<JournalEditorHandle | null>;
  onTitleChange: (value: string) => void;
  onModeChange: (mode: WorkspaceMode) => void;
  onToolbarAction: (action: ToolbarAction) => void;
  onEditorContentChange: (html: string) => void;
  onEditorBlur: () => void;
  onMetadataChange: (metadata: EntryMetadata) => void;
  voiceMicState: "idle" | "listening" | "processing";
  onToggleVoiceMic: () => void;
  voiceTranscriptPreview: string | null;
  voiceErrorMessage: string | null;
  loadError: string | null;
  saveError: string | null;
  revisionHistory: JournalEntryRecord[];
  isHistoryLoading: boolean;
  historyError: string | null;
  loadedRevisionId: string | null;
  headRevisionId: string | null;
  onLoadRevision: (revision: JournalEntryRecord) => void;
  onLoadLatestRevision: () => void;
  isViewingHistoricalRevision: boolean;
}

export function Workspace({
  entry,
  workspaceMode,
  saveStatus,
  editorRef,
  onTitleChange,
  onModeChange,
  onToolbarAction,
  onEditorContentChange,
  onEditorBlur,
  onMetadataChange,
  voiceMicState,
  onToggleVoiceMic,
  voiceTranscriptPreview,
  voiceErrorMessage,
  loadError,
  saveError,
  revisionHistory,
  isHistoryLoading,
  historyError,
  loadedRevisionId,
  headRevisionId,
  onLoadRevision,
  onLoadLatestRevision,
  isViewingHistoricalRevision,
}: WorkspaceProps) {
  return (
    <section className="workspace" aria-label="Notebook workspace">
      <div className="workspaceMain">
        <EntryHeader
          title={entry.title}
          saveStatus={saveStatus}
          isDirty={entry.isDirty}
          lastSavedAt={entry.lastSavedAt}
          onTitleChange={onTitleChange}
        />

        <ModeTabs activeMode={workspaceMode} onModeChange={onModeChange} />

        <Toolbar onAction={onToolbarAction} disabled={workspaceMode !== "journal"} />

        <div className="workspaceCanvas">
          {loadError && (
            <div className="workspaceNotice error" role="status" aria-live="polite">
              Loading DB-backed journal data failed. Showing fallback data. {loadError}
            </div>
          )}
          {saveError && (
            <div className="workspaceNotice warning" role="status" aria-live="polite">
              {saveStatus === "conflict"
                ? `Save paused. ${saveError}`
                : `Latest save failed. It will retry on the next autosave trigger. ${saveError}`}
            </div>
          )}
          {isViewingHistoricalRevision && (
            <div className="workspaceNotice warning" role="status" aria-live="polite">
              You are editing an older revision, not the current head.
              <button type="button" className="secondaryButton noticeAction" onClick={onLoadLatestRevision}>
                Load latest
              </button>
            </div>
          )}

          {workspaceMode === "journal" && (
            <div className="journalModeLayout">
              <JournalEditor
                key={`${entry.id}:${loadedRevisionId ?? "latest"}`}
                ref={editorRef}
                entryId={entry.id}
                initialContent={entry.content}
                onContentChange={onEditorContentChange}
                onBlur={onEditorBlur}
              />
              <RevisionHistoryPanel
                revisions={revisionHistory}
                isLoading={isHistoryLoading}
                error={historyError}
                loadedRevisionId={loadedRevisionId}
                headRevisionId={headRevisionId}
                onLoadRevision={onLoadRevision}
                onLoadLatestRevision={onLoadLatestRevision}
                isViewingHistoricalRevision={isViewingHistoricalRevision}
              />
            </div>
          )}

          {workspaceMode === "metadata" && (
            <MetadataPanel
              title={entry.title}
              metadata={entry.metadata}
              onTitleChange={onTitleChange}
              onMetadataChange={onMetadataChange}
            />
          )}

          {workspaceMode === "files" && (
            <section className="filesPanel" aria-label="Attached files">
              <h2>Files</h2>
              <p>Attachment integration is mocked in this phase.</p>
              <ul>
                <li>raw_plate_image_03.png</li>
                <li>growth_curve_export.csv</li>
                <li>protocol_revision_notes.pdf</li>
              </ul>
            </section>
          )}
        </div>
      </div>

      <VoiceCaptureDock
        micState={voiceMicState}
        onToggleMic={onToggleVoiceMic}
        transcriptPreview={voiceTranscriptPreview}
        errorMessage={voiceErrorMessage}
      />
    </section>
  );
}
