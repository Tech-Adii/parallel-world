import { useEffect, useState } from "react";
import { Bot, Send, Sparkles } from "lucide-react";
import { api } from "../api/client";
import type { AIAdviceResponse, UniverseSnapshot } from "../types/simulation";

interface AIAdvisorPanelProps {
  snapshot: UniverseSnapshot;
  onExecuteAction: (actionKey: string) => void;
}

export function AIAdvisorPanel({ snapshot, onExecuteAction }: AIAdvisorPanelProps) {
  const [advice, setAdvice] = useState<AIAdviceResponse | null>(null);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);

  const refreshAdvice = async (customQ?: string) => {
    setLoading(true);
    try {
      const res = await api.getAIAdvice(snapshot.universe_id, customQ);
      setAdvice(res);
    } catch {
      // Ignore transient error
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshAdvice();
  }, [
    snapshot.universe_id,
    Math.floor(snapshot.tick / 4),
    snapshot.interventions.emergency_response_active,
    snapshot.interventions.alternative_routes_active,
    snapshot.interventions.load_shedding_active,
  ]);

  const handleAsk = (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;
    refreshAdvice(question.trim());
    setQuestion("");
  };

  return (
    <section className="panel" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <div className="panel-header" style={{ marginBottom: 0 }}>
        <h2 className="panel-title">
          <Bot size={15} color="#a78bfa" />
          AI City Administrator
        </h2>
        <span
          className="mono"
          style={{
            fontSize: 10,
            padding: "2px 7px",
            borderRadius: 6,
            background: "rgba(167, 139, 250, 0.16)",
            color: "#ddd6fe",
          }}
        >
          {advice?.source === "ollama+engine" ? `Ollama (${advice.ollama_model})` : "Tactical AI Engine"}
        </span>
      </div>

      {advice && (
        <>
          <div
            style={{
              fontSize: 12,
              lineHeight: 1.45,
              padding: "8px 10px",
              borderRadius: 9,
              background: "rgba(15, 23, 42, 0.85)",
              border: "1px solid rgba(167, 139, 250, 0.25)",
              color: "#e2e8f0",
            }}
          >
            {advice.answer ?? advice.summary}
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {advice.recommendations.slice(0, 3).map((rec) => (
              <div
                key={rec.id}
                style={{
                  padding: "9px 10px",
                  borderRadius: 10,
                  background: "rgba(6, 10, 19, 0.72)",
                  border: "1px solid rgba(148, 163, 184, 0.14)",
                  display: "flex",
                  flexDirection: "column",
                  gap: 5,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 6 }}>
                  <strong style={{ fontSize: 12.5 }}>{rec.title}</strong>
                  <span className={`badge badge-${rec.priority.toLowerCase()}`}>{rec.priority}</span>
                </div>
                <div style={{ fontSize: 11.5, color: "#94a3b8", lineHeight: 1.4 }}>{rec.rationale}</div>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 6, marginTop: 2 }}>
                  <span className="mono" style={{ fontSize: 10.5, color: "#6ee7b7" }}>
                    +{rec.projected_stability_gain}% stab · {rec.projected_citizens_saved} saved
                  </span>
                  {rec.action_key && (
                    <button
                      type="button"
                      className="pill-btn active"
                      onClick={() => onExecuteAction(rec.action_key!)}
                    >
                      <Sparkles size={11} style={{ marginRight: 4, verticalAlign: "middle" }} />
                      Apply
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      <form onSubmit={handleAsk} style={{ display: "flex", gap: 6 }}>
        <input
          type="text"
          className="input-dark"
          style={{ flex: 1 }}
          placeholder="Ask AI about grid, routes, or evacuation..."
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
        />
        <button type="submit" className="btn btn-primary" disabled={loading}>
          <Send size={13} />
        </button>
      </form>
    </section>
  );
}
