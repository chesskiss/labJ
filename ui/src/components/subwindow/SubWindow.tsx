import React, { useState, useRef, useEffect } from "react";
import type { SubWindow as SubWindowType } from "../../types";
import { Calculator } from "./Calculator";
import "./SubWindow.css";

interface SubWindowProps {
  window: SubWindowType;
  onUpdate: (id: string, updates: Partial<SubWindowType>) => void;
  onClose: (id: string) => void;
}

export const SubWindow: React.FC<SubWindowProps> = ({
  window,
  onUpdate,
  onClose,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const windowRef = useRef<HTMLDivElement>(null);

  const handleMouseDown = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).classList.contains("subwindow-header")) {
      setIsDragging(true);
      const rect = windowRef.current?.getBoundingClientRect();
      if (rect) {
        setDragOffset({
          x: e.clientX - rect.left,
          y: e.clientY - rect.top,
        });
      }
    }
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isDragging && windowRef.current) {
        const newX = e.clientX - dragOffset.x;
        const newY = e.clientY - dragOffset.y;
        onUpdate(window.id, {
          position: { x: newX, y: newY },
        });
      }
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    if (isDragging) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
    }

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDragging, dragOffset, window.id, onUpdate]);

  const handleContentChange = (
    e: React.ChangeEvent<HTMLTextAreaElement | HTMLInputElement>
  ) => {
    onUpdate(window.id, { content: e.target.value });
  };

  return (
    <div
      ref={windowRef}
      className="subwindow"
      style={{
        left: `${window.position.x}px`,
        top: `${window.position.y}px`,
        width: `${window.size.width}px`,
        height: `${window.size.height}px`,
      }}
      onMouseDown={handleMouseDown}
    >
      <div className="subwindow-header">
        <span className="subwindow-title">{window.title}</span>
        <button
          className="subwindow-close"
          onClick={() => onClose(window.id)}
        >
          ✕
        </button>
      </div>
      <div className="subwindow-content">
        {window.type === "note" && (
          <textarea
            className="note-textarea"
            value={window.content}
            onChange={handleContentChange}
            placeholder="Type your note here..."
          />
        )}
        {window.type === "calculator" && (
          <Calculator
            initialContent={window.content}
            onStateChange={(state) => {
              onUpdate(window.id, { content: JSON.stringify(state) });
            }}
          />
        )}
      </div>
    </div>
  );
};
