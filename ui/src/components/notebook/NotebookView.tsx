import React, { useEffect, useState } from "react";
import { fetchNotebook } from "../../api/sessions";
import { SessionHeader } from "./SessionHeader";
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

export const NotebookView: React.FC = () => {
  const [sessions, setSessions] = useState<Session[]>([]);

  useEffect(() => {
    fetchNotebook().then(setSessions);
  }, []);

  return (
    <main className="notebook-main">
      {sessions.map((session) => (
        <section
          key={session.id}
          className="notebook-session"
          data-session-id={session.id}
        >
          <SessionHeader title={session.title} />
          <TiptapEditor session={session} />
        </section>
      ))}
    </main>
  );
};
