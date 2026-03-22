import type { SaveStatus } from "../../types";

interface EntryHeaderProps {
  title: string;
  saveStatus: SaveStatus;
  isDirty: boolean;
  lastSavedAt: string | null;
  onTitleChange: (value: string) => void;
}

function formatLastSaved(value: string | null): string {
  if (!value) {
    return "Not yet saved";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Saved";
  }
  return `Last saved ${date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
}

export function EntryHeader({
  title,
  saveStatus,
  isDirty,
  lastSavedAt,
  onTitleChange,
}: EntryHeaderProps) {
  let statusLabel = "All changes saved";
  if (saveStatus === "saving") {
    statusLabel = "Saving...";
  }
  if (saveStatus === "error") {
    statusLabel = "Save failed - will retry";
  }
  if (saveStatus === "conflict") {
    statusLabel = "Newer revision exists - reload latest";
  }
  if (isDirty && saveStatus !== "saving") {
    statusLabel = "Unsaved changes";
  }

  return (
    <header className="entryHeader">
      <input
        className="entryTitleInput"
        value={title}
        onChange={(event) => onTitleChange(event.target.value)}
        aria-label="Entry title"
      />
      <div className="entryHeaderActions">
        <span className={`saveStatus ${saveStatus}`}>{statusLabel}</span>
        <span className="saveMeta">{isDirty ? "Pending autosave..." : formatLastSaved(lastSavedAt)}</span>
        <button type="button" className="secondaryButton">
          Share
        </button>
      </div>
    </header>
  );
}
