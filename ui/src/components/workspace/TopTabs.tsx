import type { Entry } from "../../types";

interface TopTabsProps {
  openEntries: Entry[];
  activeEntryId: string;
  onSelectTab: (entryId: string) => void;
  onCloseTab: (entryId: string) => void;
}

export function TopTabs({ openEntries, activeEntryId, onSelectTab, onCloseTab }: TopTabsProps) {
  return (
    <div className="topTabs" role="tablist" aria-label="Open notebook entries">
      {openEntries.map((entry) => {
        const isActive = entry.id === activeEntryId;

        return (
          <div key={entry.id} className={`topTab ${isActive ? "active" : ""}`} role="presentation">
            <button
              type="button"
              role="tab"
              aria-selected={isActive}
              className="topTabTrigger"
              onClick={() => onSelectTab(entry.id)}
            >
              {entry.title}
            </button>
            {openEntries.length > 1 && (
              <button
                type="button"
                className="topTabClose"
                onClick={() => onCloseTab(entry.id)}
                aria-label={`Close ${entry.title}`}
              >
                x
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}
