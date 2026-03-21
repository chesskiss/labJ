import type { JournalEntryRecord } from "../../api/journalApi";

interface RevisionHistoryPanelProps {
  revisions: JournalEntryRecord[];
  isLoading: boolean;
  error: string | null;
  loadedRevisionId: string | null;
  headRevisionId: string | null;
  onLoadRevision: (revision: JournalEntryRecord) => void;
}

function formatRevisionTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function stripHtml(value: string): string {
  return value.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
}

export function RevisionHistoryPanel({
  revisions,
  isLoading,
  error,
  loadedRevisionId,
  headRevisionId,
  onLoadRevision,
}: RevisionHistoryPanelProps) {
  return (
    <aside className="revisionPanel" aria-label="Session revision history">
      <div className="revisionPanelHeader">
        <h3>History</h3>
        <span>{revisions.length} revisions</span>
      </div>

      {isLoading && <p className="revisionStatus">Loading revisions...</p>}
      {error && <p className="revisionStatus error">{error}</p>}
      {!isLoading && !revisions.length && !error && (
        <p className="revisionStatus">No revisions yet for this session.</p>
      )}

      {!!revisions.length && (
        <ul className="revisionList">
          {revisions.map((revision) => (
            <li key={revision.entry_id} className="revisionItem">
              <div className="revisionMeta">
                <span>{formatRevisionTimestamp(revision.created_at)}</span>
                <span>{revision.created_by}</span>
              </div>
              <div className="revisionKind">
                {revision.revision_kind} • {revision.entry_type}
              </div>
              <div className="revisionActions">
                {headRevisionId === revision.entry_id && (
                  <span className="revisionBadge">Head</span>
                )}
                {loadedRevisionId === revision.entry_id && (
                  <span className="revisionBadge viewing">Viewing</span>
                )}
                <button
                  type="button"
                  className="secondaryButton"
                  onClick={() => onLoadRevision(revision)}
                  disabled={loadedRevisionId === revision.entry_id}
                >
                  Load
                </button>
              </div>
              <p>{stripHtml(revision.content).slice(0, 140) || "(empty content)"}</p>
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}
