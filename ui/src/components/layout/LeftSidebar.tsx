import React, { useEffect, useState } from "react";
import { fetchSessions } from "../../api/sessions";

interface Session {
  id: string;
  title: string;
  description?: string;
  isFavorite?: boolean;
}

export const LeftSidebar: React.FC = () => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  useEffect(() => {
    fetchSessions().then((data) => {
      setSessions(data);
      if (data.length && !activeSessionId) {
        setActiveSessionId(data[0].id);
      }
    });
  }, []);

  const favorites = sessions.filter((s) => s.isFavorite);
  const nonFavorites = sessions.filter((s) => !s.isFavorite);

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
