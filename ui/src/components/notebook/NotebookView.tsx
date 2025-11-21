import React, { useEffect, useState } from "react";
import { fetchNotebook } from "../../api/sessions";
import { TiptapEditor, blocksToHtml } from "./TiptapEditor";

interface NotebookBlock {
  id: string;
  type: "paragraph" | "chart" | "graph" | "table" | "log";
  content: any;
}

interface Session {
  id: string;
  title: string;
  blocks: NotebookBlock[];
  isArchived?: boolean;
}

interface Props {
  searchTerm: string;
  reverseSessions: boolean;
}

export const NotebookView: React.FC<Props> = ({ searchTerm, reverseSessions }) => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [sessionState, setSessionState] = useState<Record<string, { html: string; dirty: boolean }>>({});
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    const refresh = () => {
      fetchNotebook()
        .then((data) => {
          if (!mounted) return;
          setSessions(data);

          setSessionState((prev) => {
            const next = { ...prev };
            for (const session of data) {
              const key = String(session.id);
              const existing = prev[key];
              if (!existing || !existing.dirty) {
                next[key] = {
                  html: blocksToHtml(session.blocks, searchTerm),
                  dirty: false,
                };
              }
            }
            return next;
          });
        })
        .catch((err) => console.error("Failed to fetch notebook", err));
    };

    refresh();
    const interval = window.setInterval(refresh, 2500);

    return () => {
      mounted = false;
      window.clearInterval(interval);
    };
  }, []);

  // Recompute non-dirty HTML when sessions or search term change
  useEffect(() => {
    setSessionState((prev) => {
      const next = { ...prev };
      for (const session of sessions) {
        const key = String(session.id);
        const existing = prev[key];
        if (!existing || !existing.dirty) {
          const html = blocksToHtml(session.blocks, searchTerm);
          if (!existing || existing.html !== html) {
            next[key] = { html, dirty: false };
          }
        }
      }
      return next;
    });
  }, [sessions, searchTerm]);

  return (
    <main className="notebook-main">
      {(reverseSessions ? [...sessions].reverse() : sessions)
        .filter((s) => !s.isArchived)
        .map((session) => {
          const blocks = session.blocks.filter((b) => b.type !== "log");
          return (
            <section
              key={session.id}
              className="notebook-session"
              data-session-id={session.id}
            >
              {/* Title intentionally hidden for a clean, continuous notebook */}
              <TiptapEditor
                session={{ ...session, blocks }}
                searchTerm={searchTerm}
                html={sessionState[String(session.id)]?.html ?? blocksToHtml(blocks, searchTerm)}
                isDirty={Boolean(sessionState[String(session.id)]?.dirty)}
                onChange={(html) =>
                  setSessionState((prev) => ({
                    ...prev,
                    [String(session.id)]: { html, dirty: true },
                  }))
                }
              />
            </section>
          );
        })}
    </main>
  );
};
