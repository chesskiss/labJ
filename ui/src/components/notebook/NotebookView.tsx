import React, { useEffect, useState } from "react";
import { fetchNotebook } from "../../api/sessions";
import { TiptapEditor } from "./TiptapEditor";

interface NotebookBlock {
  id: string;
  type: "paragraph" | "chart" | "graph" | "table";
  content: any;
}

interface Session {
  id: string;
  title: string;
  blocks: NotebookBlock[];
}

interface Props {
  searchTerm: string;
  reverseSessions: boolean;
}

export const NotebookView: React.FC<Props> = ({ searchTerm, reverseSessions }) => {
  const [sessions, setSessions] = useState<Session[]>([]);

  useEffect(() => {
    let mounted = true;

    const refresh = () => {
      fetchNotebook()
        .then((data) => {
          if (mounted) setSessions(data);
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

  return (
    <main className="notebook-main">
      {(reverseSessions ? [...sessions].reverse() : sessions).map((session) => (
        <section
          key={session.id}
          className="notebook-session"
          data-session-id={session.id}
        >
          {/* Title intentionally hidden for a clean, continuous notebook */}
          <TiptapEditor session={session} searchTerm={searchTerm} />
        </section>
      ))}
    </main>
  );
};
