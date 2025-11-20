import React from "react";

interface Props {
  title: string;
}

export const SessionHeader: React.FC<Props> = ({ title }) => {
  return (
    <div className="session-header">
      <h2>{title}</h2>
      <div className="session-divider" />
    </div>
  );
};
