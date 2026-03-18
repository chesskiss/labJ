import type { Entry, EntryBucket } from "../../types";

interface ProjectSidebarProps {
  entries: Entry[];
  activeEntryId: string;
  searchTerm: string;
  activeFilter: EntryBucket | "all";
  onSelectEntry: (entryId: string) => void;
  onCreateEntry: () => void;
  onSearchTermChange: (value: string) => void;
  onFilterChange: (value: EntryBucket | "all") => void;
}

const filters: Array<{ id: EntryBucket | "all"; label: string }> = [
  { id: "all", label: "All" },
  { id: "today", label: "Today" },
  { id: "week", label: "This Week" },
  { id: "older", label: "Older" },
];

export function ProjectSidebar({
  entries,
  activeEntryId,
  searchTerm,
  activeFilter,
  onSelectEntry,
  onCreateEntry,
  onSearchTermChange,
  onFilterChange,
}: ProjectSidebarProps) {
  const normalizedSearch = searchTerm.trim().toLowerCase();

  const visibleEntries = entries.filter((entry) => {
    const matchesFilter = activeFilter === "all" ? true : entry.bucket === activeFilter;
    const matchesSearch = normalizedSearch.length
      ? entry.title.toLowerCase().includes(normalizedSearch)
      : true;

    return matchesFilter && matchesSearch;
  });

  return (
    <aside className="projectSidebar" aria-label="Project entries">
      <header className="projectSidebarHeader">
        <div>
          <p className="sidebarOverline">Lab Project</p>
          <h1 className="sidebarTitle">Fermentation Assays</h1>
        </div>
        <button type="button" className="newEntryButton" onClick={onCreateEntry}>
          + New Entry
        </button>
      </header>

      <div className="sidebarSearchBlock">
        <input
          value={searchTerm}
          onChange={(event) => onSearchTermChange(event.target.value)}
          className="sidebarSearch"
          placeholder="Search entries"
          aria-label="Search entries"
        />
        <div className="filterRow" role="tablist" aria-label="Entry filters">
          {filters.map((filter) => (
            <button
              key={filter.id}
              type="button"
              className={`filterChip ${filter.id === activeFilter ? "active" : ""}`}
              onClick={() => onFilterChange(filter.id)}
            >
              {filter.label}
            </button>
          ))}
        </div>
      </div>

      <ul className="entryList" aria-label="Notebook entries">
        {visibleEntries.map((entry) => (
          <li key={entry.id}>
            <button
              type="button"
              className={`entryItem ${entry.id === activeEntryId ? "active" : ""}`}
              onClick={() => onSelectEntry(entry.id)}
            >
              <span className="entryTitle">{entry.title}</span>
              <span className="entryMeta">Updated {entry.updatedAt}</span>
            </button>
          </li>
        ))}

        {!visibleEntries.length && <li className="entryEmpty">No entries match the current filter.</li>}
      </ul>
    </aside>
  );
}
