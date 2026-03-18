import type { AppSection } from "../../types";

interface GlobalRailProps {
  activeSection: AppSection;
  onSectionChange: (section: AppSection) => void;
}

const railItems: Array<{ id: AppSection; icon: string; label: string }> = [
  { id: "projects", icon: "PR", label: "Projects" },
  { id: "search", icon: "SR", label: "Search" },
  { id: "recent", icon: "RC", label: "Recent" },
  { id: "settings", icon: "ST", label: "Settings" },
];

export function GlobalRail({ activeSection, onSectionChange }: GlobalRailProps) {
  return (
    <aside className="globalRail" aria-label="Global navigation">
      <div className="railLogo">LJ</div>
      <nav className="railNav">
        {railItems.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`railButton ${item.id === activeSection ? "active" : ""}`}
            onClick={() => onSectionChange(item.id)}
            title={item.label}
            aria-label={item.label}
          >
            <span className="railIcon" aria-hidden="true">
              {item.icon}
            </span>
          </button>
        ))}
      </nav>
      <div className="railAvatar" title="Researcher">
        AC
      </div>
    </aside>
  );
}
