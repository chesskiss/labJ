import type { RefObject } from "react";
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
  isVoicePanelOpen: boolean;
  voicePromptDraft: string;
  isVoiceSending: boolean;
  onToggleVoicePanel: () => void;
  onVoicePromptChange: (value: string) => void;
  onSendVoicePrompt: () => void;
  onCloseVoicePanel: () => void;
  loadError: string | null;
  saveError: string | null;
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
  isVoicePanelOpen,
  voicePromptDraft,
  isVoiceSending,
  onToggleVoicePanel,
  onVoicePromptChange,
  onSendVoicePrompt,
  onCloseVoicePanel,
  loadError,
  saveError,
}: WorkspaceProps) {
  return (
    <section className="workspace" aria-label="Notebook workspace">
      <div className="workspaceMain">
        <EntryHeader title={entry.title} saveStatus={saveStatus} onTitleChange={onTitleChange} />

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
              Latest save failed. It will retry on the next autosave trigger. {saveError}
            </div>
          )}

          {workspaceMode === "journal" && (
            <JournalEditor
              ref={editorRef}
              entryId={entry.id}
              initialContent={entry.content}
              onContentChange={onEditorContentChange}
              onBlur={onEditorBlur}
            />
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
        isOpen={isVoicePanelOpen}
        promptDraft={voicePromptDraft}
        isSending={isVoiceSending}
        onToggleOpen={onToggleVoicePanel}
        onPromptChange={onVoicePromptChange}
        onSendPrompt={onSendVoicePrompt}
        onClose={onCloseVoicePanel}
      />
    </section>
  );
}
