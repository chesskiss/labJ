import React, { useState } from "react";

export const RightPanel: React.FC = () => {
  const [showTimestamps, setShowTimestamps] = useState(false);
  const [showTags, setShowTags] = useState(true);

  return (
    <aside className="sidebar-right">
      <div className="sidebar-right-header">
        <h3>View & Filters</h3>
      </div>

      <div className="sidebar-right-section">
        <label>
          <input
            type="checkbox"
            checked={showTimestamps}
            onChange={(e) => setShowTimestamps(e.target.checked)}
          />
          Show timestamps
        </label>
        <label>
          <input
            type="checkbox"
            checked={showTags}
            onChange={(e) => setShowTags(e.target.checked)}
          />
          Show tags
        </label>
      </div>

      <div className="sidebar-right-section">
        <div className="sidebar-label">Tags</div>
        <div className="tag-chips">
          <button className="tag-chip selected">Results</button>
          <button className="tag-chip">Reagents</button>
          <button className="tag-chip">Protocol</button>
        </div>
      </div>

      <div className="sidebar-right-section">
        <div className="sidebar-label">Ask assistant</div>
        <textarea
          rows={3}
          placeholder="Hide all timestamps, highlight anomalies…"
          className="assistant-input"
        />
        <button className="btn-primary">Apply</button>
      </div>
    </aside>
  );
};
