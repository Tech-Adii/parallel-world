import { useState } from "react";
import {
  Building2,
  Eraser,
  Flame,
  GraduationCap,
  Hammer,
  Hospital,
  MousePointer,
  Save,
  Shield,
  TrafficCone,
  Trees,
  Waves,
  Zap,
} from "lucide-react";
import type { BuilderTool } from "../types/simulation";

interface CityBuilderToolbarProps {
  activeTool: BuilderTool;
  onSelectTool: (tool: BuilderTool) => void;
  onSaveCity: (name: string, description: string) => Promise<void>;
}

export function CityBuilderToolbar({
  activeTool,
  onSelectTool,
  onSaveCity,
}: CityBuilderToolbarProps) {
  const [cityName, setCityName] = useState("");
  const [saving, setSaving] = useState(false);
  const [savedNotice, setSavedNotice] = useState("");

  const tools: { id: BuilderTool; label: string; icon: JSX.Element }[] = [
    { id: "inspect", label: "Inspect / Pan", icon: <MousePointer size={14} /> },
    { id: "road", label: "Road Segment", icon: <TrafficCone size={14} /> },
    { id: "residential", label: "Residential", icon: <Building2 size={14} /> },
    { id: "hospital", label: "Hospital", icon: <Hospital size={14} /> },
    { id: "school", label: "School", icon: <GraduationCap size={14} /> },
    { id: "industry", label: "Industry", icon: <Hammer size={14} /> },
    { id: "power_station", label: "Power Station", icon: <Zap size={14} /> },
    { id: "shelter", label: "Evac Shelter", icon: <Shield size={14} /> },
    { id: "park", label: "Green Park", icon: <Trees size={14} /> },
    { id: "water", label: "Water Channel", icon: <Waves size={14} /> },
    { id: "empty", label: "Bulldoze", icon: <Eraser size={14} /> },
    { id: "block_road", label: "Block/Unblock Road", icon: <TrafficCone size={14} /> },
    { id: "ignite_fire", label: "Ignite Fire", icon: <Flame size={14} /> },
    { id: "trigger_flood", label: "Inject Flood", icon: <Waves size={14} /> },
  ];

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!cityName.trim()) return;
    setSaving(true);
    try {
      await onSaveCity(cityName.trim(), "Custom city created in Parallel World City Creation Engine");
      setSavedNotice(`Saved "${cityName.trim()}" to SQLite!`);
      setCityName("");
      setTimeout(() => setSavedNotice(""), 3500);
    } finally {
      setSaving(false);
    }
  };

  return (
    <aside className="panel" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div className="panel-header" style={{ marginBottom: 0 }}>
        <h2 className="panel-title">
          <Hammer size={15} color="#38bdf8" />
          City Creation Engine
        </h2>
      </div>

      <p style={{ margin: 0, fontSize: 12, color: "#94a3b8", lineHeight: 1.45 }}>
        Select a blueprint tool and click any tile on the PixiJS map to construct roads, hospitals,
        schools, power plants, shelters, or trigger localized hazards.
      </p>

      <div className="builder-palette">
        {tools.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`tool-btn ${activeTool === t.id ? "active" : ""}`}
            onClick={() => onSelectTool(t.id)}
          >
            {t.icon}
            <span>{t.label}</span>
          </button>
        ))}
      </div>

      <form
        onSubmit={handleSave}
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 8,
          paddingTop: 10,
          borderTop: "1px solid rgba(148,163,184,0.14)",
        }}
      >
        <label style={{ fontSize: 11.5, color: "#cbd5e1", fontWeight: 600 }}>
          Save City Blueprint to SQLite
        </label>
        <div style={{ display: "flex", gap: 6 }}>
          <input
            type="text"
            className="input-dark"
            style={{ flex: 1 }}
            placeholder="e.g., Neo Bengaluru"
            value={cityName}
            onChange={(e) => setCityName(e.target.value)}
          />
          <button type="submit" className="btn btn-primary" disabled={saving || !cityName.trim()}>
            <Save size={13} />
            <span>Save</span>
          </button>
        </div>
        {savedNotice && <span style={{ fontSize: 11.5, color: "#6ee7b7" }}>{savedNotice}</span>}
      </form>
    </aside>
  );
}
