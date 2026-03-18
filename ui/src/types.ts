export type AppSection = "projects" | "search" | "recent" | "settings";

export type EntryBucket = "today" | "week" | "older";

export type WorkspaceMode = "journal" | "metadata" | "files";

export type VoiceCaptureState = "idle" | "listening" | "processing";

export type VoiceCaptureMode = "dictation" | "command" | "note";

export type SaveStatus = "saved" | "saving" | "error";

export type ToolbarAction =
  | "bold"
  | "italic"
  | "bullet"
  | "heading"
  | "checkbox"
  | "table"
  | "attach";

export interface EntryMetadata {
  date: string;
  tags: string[];
  notes: string;
}

export interface Entry {
  id: string;
  sessionId: string;
  title: string;
  updatedAt: string;
  bucket: EntryBucket;
  content: string;
  metadata: EntryMetadata;
  createdBy: string;
  entryType: string;
}
