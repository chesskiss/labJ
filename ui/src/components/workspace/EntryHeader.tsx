import type { SaveStatus } from "../../types";

interface EntryHeaderProps {
  title: string;
  saveStatus: SaveStatus;
  onTitleChange: (value: string) => void;
}

export function EntryHeader({ title, saveStatus, onTitleChange }: EntryHeaderProps) {
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
        <button type="button" className="secondaryButton">
          Share
        </button>
      </div>
    </header>
  );
}
