import React, { useEffect, useState } from "react";
import { fetchSessions, searchSessions } from "../../api/sessions";

interface Session {
  id: string;
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
  }, [searchTerm]);

  const ordered = reverseSessions ? [...sessions].reverse() : sessions;
  const favorites = ordered.filter((s) => s.isFavorite);
  const nonFavorites = ordered.filter((s) => !s.isFavorite);

  const handleSelectSession = (id: string) => {
    setActiveSessionId(id);
    const element = document.querySelector(`[data-session-id="${id}"]`);
    if (element) element.scrollIntoView({ behavior: "smooth", block: "start" });
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
          {nonFavorites.map((s) => (
            <li
              key={s.id}
              className={`session-item ${s.id === activeSessionId ? "active" : ""}`}
              onClick={() => handleSelectSession(s.id)}
            >
              <div className="session-title">{s.title}</div>
              {s.description && (
                <div className="session-desc">{s.description}</div>
              )}
            </li>
          ))}
        </ul>
      </div>

      <div className="sidebar-section">
        <div className="sidebar-label">Favorites</div>
        <ul className="session-list">
          {favorites.map((s) => (
            <li
              key={s.id}
              className={`session-item ${s.id === activeSessionId ? "active" : ""}`}
              onClick={() => handleSelectSession(s.id)}
            >
              <div className="session-title">{s.title}</div>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
};
