import type { EntryMetadata } from "../../types";

interface MetadataPanelProps {
  title: string;
  metadata: EntryMetadata;
  onTitleChange: (value: string) => void;
  onMetadataChange: (metadata: EntryMetadata) => void;
}

export function MetadataPanel({ title, metadata, onTitleChange, onMetadataChange }: MetadataPanelProps) {
  return (
    <section className="metadataPanel" aria-label="Entry metadata">
      <label className="metadataField">
        <span>Title</span>
        <input
          value={title}
          onChange={(event) => onTitleChange(event.target.value)}
          className="metadataInput"
        />
      </label>

      <label className="metadataField">
        <span>Date</span>
        <input
          type="date"
          value={metadata.date}
          onChange={(event) =>
            onMetadataChange({
              ...metadata,
              date: event.target.value,
            })
          }
          className="metadataInput"
        />
      </label>

      <label className="metadataField">
        <span>Tags</span>
        <input
          value={metadata.tags.join(", ")}
          onChange={(event) =>
            onMetadataChange({
              ...metadata,
              tags: event.target.value
                .split(",")
                .map((tag) => tag.trim())
                .filter(Boolean),
            })
          }
          className="metadataInput"
          placeholder="e.g. pcr, optimization"
        />
      </label>

      <label className="metadataField">
        <span>Notes</span>
        <textarea
          value={metadata.notes}
          onChange={(event) =>
            onMetadataChange({
              ...metadata,
              notes: event.target.value,
            })
          }
          className="metadataTextarea"
          rows={6}
        />
      </label>
    </section>
  );
}
