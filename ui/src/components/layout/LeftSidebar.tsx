import React, { useEffect, useState } from "react";
import { fetchSessions, searchSessions, updateSessionTitle } from "../../api/sessions";

interface Session {
  id: string | number;
  title: string;
  description?: string;
  isFavorite?: boolean;
}

interface Props {
  searchTerm: string;
  setSearchTerm: (value: string) => void;
  reverseSessions: boolean;
}

export const LeftSidebar: React.FC<Props> = ({
  searchTerm,
  setSearchTerm,
  reverseSessions,
}) => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [titleDraft, setTitleDraft] = useState("");

  useEffect(() => {
    let mounted = true;

    const refresh = () => {
      const fetcher = searchTerm.trim()
        ? () => searchSessions(searchTerm.trim())
        : fetchSessions;

      fetcher()
        .then((data) => {
          if (!mounted) return;
          setSessions(data);
          if (data.length && !activeSessionId) {
            setActiveSessionId(data[data.length - 1].id);
          }
        })
        .catch((err) => console.error("Failed to fetch sessions", err));
    };

    refresh();
    const interval = window.setInterval(refresh, 2500);

    return () => {
      mounted = false;
      window.clearInterval(interval);
    };
  }, [searchTerm, activeSessionId, editingId]);

  const ordered = reverseSessions ? [...sessions].reverse() : sessions;
  const favorites = ordered.filter((s) => s.isFavorite);
  const nonFavorites = ordered.filter((s) => !s.isFavorite);

  const handleSelectSession = (id: string | number) => {
    setActiveSessionId(String(id));
    const element = document.querySelector(`[data-session-id="${id}"]`);
    if (element) element.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const startEditing = (session: Session) => {
    const sid = Number(session.id);
    setEditingId(sid);
    setTitleDraft(session.title || `Session ${sid}`);
  };

  const commitEditing = async () => {
    if (!editingId) return;
    const newTitle = titleDraft.trim();
    try {
      await updateSessionTitle(editingId, newTitle);
      setSessions((prev) =>
        prev.map((s) =>
          Number(s.id) === editingId ? { ...s, title: newTitle || `Session ${s.id}` } : s
        )
      );
    } catch (err) {
      console.error("Failed to update session title", err);
    } finally {
      setEditingId(null);
    }
  };

  const cancelEditing = () => {
    setEditingId(null);
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      commitEditing();
    } else if (e.key === "Escape") {
      cancelEditing();
    }
  };

  return (
    <aside className="sidebar-left">
      <div className="sidebar-header">
        <span className="logo">Lab Journal</span>
      </div>

      <div className="sidebar-section">
        <input
          type="text"
          placeholder="Search sessions…"
          className="sidebar-search"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />

        <div className="sidebar-label">Sessions</div>
        <ul className="session-list">
          {nonFavorites.map((s) => {
            const isActive = String(s.id) === activeSessionId;
            const isEditing = editingId === Number(s.id);
            return (
              <li
                key={s.id}
                className={`session-item ${isActive ? "active" : ""}`}
                onClick={() => handleSelectSession(s.id)}
                onDoubleClick={() => startEditing(s)}
              >
                <div className="session-title">
                  {isEditing ? (
                    <input
                      className="sidebar-input"
                      autoFocus
                      value={titleDraft}
                      onChange={(e) => setTitleDraft(e.target.value)}
                      onBlur={commitEditing}
                      onKeyDown={onKeyDown}
                    />
                  ) : (
                    s.title
                  )}
                </div>
                {s.description && (
                  <div className="session-desc">{s.description}</div>
                )}
              </li>
            );
          })}
        </ul>
      </div>

      <div className="sidebar-section">
        <div className="sidebar-label">Favorites</div>
        <ul className="session-list">
          {favorites.map((s) => {
            const isActive = String(s.id) === activeSessionId;
            const isEditing = editingId === Number(s.id);
            return (
              <li
                key={s.id}
                className={`session-item ${isActive ? "active" : ""}`}
                onClick={() => handleSelectSession(s.id)}
                onDoubleClick={() => startEditing(s)}
              >
                <div className="session-title">
                  {isEditing ? (
                    <input
                      className="sidebar-input"
                      autoFocus
                      value={titleDraft}
                      onChange={(e) => setTitleDraft(e.target.value)}
                      onBlur={commitEditing}
                      onKeyDown={onKeyDown}
                    />
                  ) : (
                    s.title
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      </div>
    </aside>
  );
};
