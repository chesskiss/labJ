import type { WorkspaceMode } from "../../types";

interface ModeTabsProps {
  activeMode: WorkspaceMode;
  onModeChange: (mode: WorkspaceMode) => void;
}

const modes: Array<{ id: WorkspaceMode; label: string }> = [
  { id: "journal", label: "Journal" },
  { id: "metadata", label: "Metadata" },
  { id: "files", label: "Files" },
];

export function ModeTabs({ activeMode, onModeChange }: ModeTabsProps) {
  return (
    <div className="modeTabs" role="tablist" aria-label="Entry view modes">
      {modes.map((mode) => (
        <button
          key={mode.id}
          type="button"
          role="tab"
          aria-selected={mode.id === activeMode}
          className={`modeTab ${mode.id === activeMode ? "active" : ""}`}
          onClick={() => onModeChange(mode.id)}
        >
          {mode.label}
        </button>
      ))}
    </div>
  );
}
