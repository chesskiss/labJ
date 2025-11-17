import React from "react";
import { LeftSidebar } from "./LeftSidebar";
import { RightPanel } from "./RightPanel";
import { NotebookView } from "../notebook/NotebookView";
import { CommandConsole } from "../console/CommandConsole";

export const Layout: React.FC = () => {
  return (
    <div className="app-root">
      <LeftSidebar />

      <div className="app-main">
        <NotebookView />
        <CommandConsole />
      </div>

      <RightPanel />
    </div>
  );
};
