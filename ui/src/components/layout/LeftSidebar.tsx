import React, { useEffect, useState } from "react";
import { fetchSessions, searchSessions, updateSessionTitle, archiveSession } from "../../api/sessions";

interface Session {
  id: string | number;
  title: string;
  description?: string;
  isFavorite?: boolean;
  isArchived?: boolean;
}

interface Props {
  searchTerm: string;
  setSearchTerm: (value: string) => void;
  reverseSessions: boolean;
}

const loadFavorites = (): number[] => {
  try {
    const raw = localStorage.getItem("labj_favorites");
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.map(Number).filter((n) => !Number.isNaN(n)) : [];
  } catch {
    return [];
  }
};

export const LeftSidebar: React.FC<Props> = ({
  searchTerm,
  setSearchTerm,
  reverseSessions,
}) => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [titleDraft, setTitleDraft] = useState("");
  const [hoverId, setHoverId] = useState<string | null>(null);
  const [favoriteIds, setFavoriteIds] = useState<number[]>(loadFavorites);

  useEffect(() => {
    let mounted = true;

    const refresh = () => {
      const fetcher = searchTerm.trim()
        ? () => searchSessions(searchTerm.trim())
        : fetchSessions;

      fetcher()
        .then((data) => {
          if (!mounted) return;
          setSessions((prev) => {
            const prevMap = new Map(prev.map((p) => [String(p.id), p]));
            return data.map((s: Session) => {
              const existing = prevMap.get(String(s.id));
              return {
                ...s,
                isFavorite:
                  (existing && existing.isFavorite) ||
                  favoriteIds.includes(Number(s.id)),
              };
            });
          });
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
  }, [searchTerm, activeSessionId, editingId, favoriteIds]);

  // Persist favorites locally
  useEffect(() => {
    try {
      localStorage.setItem("labj_favorites", JSON.stringify(favoriteIds));
    } catch {
      /* ignore */
    }
  }, [favoriteIds]);

  const ordered = reverseSessions ? [...sessions].reverse() : sessions;
  const activeSessions = ordered.filter((s) => !s.isArchived);
  const favorites = activeSessions.filter((s) => s.isFavorite);
  const nonFavorites = activeSessions; // show favorites in the main list too
  const archived = ordered.filter((s) => s.isArchived);

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

  const markFavorite = (id: string | number, isFav: boolean) => {
    const numId = Number(id);
    setFavoriteIds((prev) => {
      const next = new Set(prev);
      if (isFav) next.add(numId);
      else next.delete(numId);
      return Array.from(next);
    });
    setSessions((prev) =>
      prev.map((s) =>
        String(s.id) === String(id) ? { ...s, isFavorite: isFav } : s
      )
    );
    if (String(id) === activeSessionId && !isFav && sessions.find((s) => String(s.id) === String(id))?.isArchived) {
      setActiveSessionId(null);
    }
  };

  const setArchiveState = (id: string | number, archivedState: boolean) => {
    setSessions((prev) =>
      prev.map((s) =>
        String(s.id) === String(id) ? { ...s, isArchived: archivedState } : s
      )
    );
    if (archivedState) {
      markFavorite(id, false);
      if (String(id) === activeSessionId) setActiveSessionId(null);
    }
  };

  const handleListKeyDown = async (e: React.KeyboardEvent<HTMLUListElement>) => {
    if (!activeSessionId || editingId) return;
    if (e.key === "Backspace" || e.key === "Delete") {
      try {
        await archiveSession(activeSessionId, true);
        setArchiveState(activeSessionId, true);
      } catch (err) {
        console.error("Failed to archive session", err);
      }
    }
  };

  // Global key listener so “Delete/Backspace” archives the active session even if focus moves.
  useEffect(() => {
    const onKey = async (e: KeyboardEvent) => {
      if (editingId) return;
      if (e.key === "Backspace" || e.key === "Delete") {
        if (!activeSessionId) return;
        try {
          await archiveSession(activeSessionId, true);
          setArchiveState(activeSessionId, true);
        } catch (err) {
          console.error("Failed to archive session", err);
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [activeSessionId, editingId]);

  const handleDragStart = (id: string | number, e: React.DragEvent) => {
    e.dataTransfer.setData("text/plain", String(id));
  };

  const handleDrop = async (
    target: "sessions" | "favorites" | "archived",
    e: React.DragEvent
  ) => {
    e.preventDefault();
    const id = e.dataTransfer.getData("text/plain");
    if (!id) return;
    try {
      if (target === "archived") {
        await archiveSession(id, true);
        setArchiveState(id, true);
      } else {
        await archiveSession(id, false);
        setArchiveState(id, false);
        markFavorite(id, target === "favorites");
      }
    } catch (err) {
      console.error("Failed to move session", err);
    }
  };

  const allowDrop = (e: React.DragEvent) => e.preventDefault();

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
        <ul
          className="session-list"
          tabIndex={0}
          onKeyDown={handleListKeyDown}
          onDragOver={allowDrop}
          onDrop={(e) => handleDrop("sessions", e)}
        >
          {nonFavorites.map((s) => {
            const isActive = String(s.id) === activeSessionId;
            const isEditing = editingId === Number(s.id);
            return (
              <li
                key={s.id}
                className={`session-item ${isActive ? "active" : ""} ${s.isArchived ? "archived" : ""}`}
                onClick={() => handleSelectSession(s.id)}
                onDoubleClick={() => startEditing(s)}
                onMouseEnter={() => setHoverId(String(s.id))}
                onMouseLeave={() => setHoverId(null)}
                draggable
                onDragStart={(e) => handleDragStart(s.id, e)}
              >
                <div className="session-title">
                  {s.isFavorite && (
                    <button
                      className="fav-toggle active"
                      onClick={(e) => {
                        e.stopPropagation();
                        markFavorite(s.id, false);
                      }}
                      title="Remove from favorites"
                    >
                      ★
                    </button>
                  )}
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
        <ul
          className="session-list"
          tabIndex={0}
          onKeyDown={handleListKeyDown}
          onDragOver={allowDrop}
          onDrop={(e) => handleDrop("favorites", e)}
        >
          {favorites.map((s) => {
            const isActive = String(s.id) === activeSessionId;
            const isEditing = editingId === Number(s.id);
            return (
              <li
                key={s.id}
                className={`session-item ${isActive ? "active" : ""} ${s.isArchived ? "archived" : ""}`}
                onClick={() => handleSelectSession(s.id)}
                onDoubleClick={() => startEditing(s)}
                onMouseEnter={() => setHoverId(String(s.id))}
                onMouseLeave={() => setHoverId(null)}
                draggable
                onDragStart={(e) => handleDragStart(s.id, e)}
              >
                <div className="session-title">
                  {s.isFavorite && (
                    <button
                      className="fav-toggle active"
                      onClick={(e) => {
                        e.stopPropagation();
                        markFavorite(s.id, false);
                      }}
                      title="Remove from favorites"
                    >
                      ★
                    </button>
                  )}
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

      <div className="sidebar-section">
        <div className="sidebar-label">Archived</div>
        <ul
          className="session-list"
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => handleDrop("archived", e)}
        >
          {archived.map((s) => (
            <li
              key={s.id}
              className="session-item archived"
              draggable
              onDragStart={(e) => handleDragStart(s.id, e)}
            >
              <div className="session-title">{s.title}</div>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
};
