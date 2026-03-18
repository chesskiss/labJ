import type { ToolbarAction } from "../../types";

interface ToolbarProps {
  onAction: (action: ToolbarAction) => void;
  disabled?: boolean;
}

const controls: Array<{ id: ToolbarAction; label: string }> = [
  { id: "bold", label: "B" },
  { id: "italic", label: "I" },
  { id: "bullet", label: "List" },
  { id: "heading", label: "H2" },
  { id: "checkbox", label: "Check" },
  { id: "table", label: "Table" },
  { id: "attach", label: "Attach" },
];

export function Toolbar({ onAction, disabled = false }: ToolbarProps) {
  return (
    <div className="toolbar" aria-label="Journal toolbar">
      {controls.map((control) => (
        <button
          key={control.id}
          type="button"
          className="toolbarButton"
          onClick={() => onAction(control.id)}
          disabled={disabled}
        >
          {control.label}
        </button>
      ))}
    </div>
  );
}
