import React, { useState } from "react";
import { sendCommand } from "../../api/commands";

export const CommandConsole: React.FC = () => {
  const [value, setValue] = useState("");

  const onSubmit = async () => {
    if (!value.trim()) return;
    await sendCommand(value.trim());
    setValue("");
  };

  return (
    <div className="command-console">
      <div className="command-label">Command / Manual Input</div>
      <textarea
        className="command-input"
        rows={2}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder='e.g. "new section: results at 37°C"'
      />
      <div className="command-actions">
        <button className="btn-primary" onClick={onSubmit}>
          Send
        </button>
      </div>
    </div>
  );
};
