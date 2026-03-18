import React, { useState, useEffect } from "react";
import { LeftSidebar } from "./LeftSidebar";
import { RightPanel } from "./RightPanel";
import { NotebookView } from "../notebook/NotebookView";
import { CommandConsole } from "../console/CommandConsole";
import { SubWindow as SubWindowComponent } from "../subwindow/SubWindow";
import type { SubWindow } from "../../types";
import {
  fetchSubWindows,
  updateSubWindow,
  closeSubWindow,
} from "../../api/subwindows";

export const Layout: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState("");
  const [reverseSessions, setReverseSessions] = useState(false);
  const [subWindows, setSubWindows] = useState<SubWindow[]>([]);

  // Poll for sub-windows every 500ms
  useEffect(() => {
    const loadSubWindows = async () => {
      try {
        const windows = await fetchSubWindows();
        setSubWindows(windows);
      } catch (err) {
        console.error("Failed to fetch sub-windows:", err);
      }
    };

    loadSubWindows();
    const interval = setInterval(loadSubWindows, 500);
    return () => clearInterval(interval);
  }, []);

  const handleUpdateSubWindow = async (
    id: string,
    updates: Partial<SubWindow>
  ) => {
    // Optimistic update
    setSubWindows((prev) =>
      prev.map((w) => (w.id === id ? { ...w, ...updates } : w))
    );

    try {
      await updateSubWindow(id, updates);
    } catch (err) {
      console.error("Failed to update sub-window:", err);
      // Revert on error by refetching
      const windows = await fetchSubWindows();
      setSubWindows(windows);
    }
  };

  const handleCloseSubWindow = async (id: string) => {
    // Optimistic remove
    setSubWindows((prev) => prev.filter((w) => w.id !== id));

    try {
      await closeSubWindow(id);
    } catch (err) {
      console.error("Failed to close sub-window:", err);
      // Revert on error by refetching
      const windows = await fetchSubWindows();
      setSubWindows(windows);
    }
  };

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

      {/* Render all sub-windows */}
      {subWindows.map((window) => (
        <SubWindowComponent
          key={window.id}
          window={window}
          onUpdate={handleUpdateSubWindow}
          onClose={handleCloseSubWindow}
        />
      ))}
    </div>
  );
};
