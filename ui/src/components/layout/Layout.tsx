import React, { useState } from "react";
import { LeftSidebar } from "./LeftSidebar";
import { RightPanel } from "./RightPanel";
import { NotebookView } from "../notebook/NotebookView";
import { CommandConsole } from "../console/CommandConsole";

export const Layout: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState("");
  const [reverseSessions, setReverseSessions] = useState(false);

  return (
    <div className="app-root">
      <LeftSidebar
        searchTerm={searchTerm}
        setSearchTerm={setSearchTerm}
        reverseSessions={reverseSessions}
      />

      <div className="app-main">
        <NotebookView searchTerm={searchTerm} reverseSessions={reverseSessions} />
        <CommandConsole />
      </div>

      <RightPanel
        reverseSessions={reverseSessions}
        setReverseSessions={setReverseSessions}
      />
    </div>
  );
};
