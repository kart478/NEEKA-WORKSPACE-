import { useEffect, useState, type ReactElement } from "react";
import { apiClient } from "../services/api/client";
import type { ConnectionState } from "./connection";
import "./app.css";

export function App(): ReactElement {
  const [state, setState] = useState<ConnectionState>("STARTING");
  const [message, setMessage] = useState("Connecting to the local engine...");
  useEffect(() => {
    let active = true;
    const check = async () => {
      try {
        const result = await apiClient.health();
        if (!active) return;
        setState(result.health?.status === "ok" ? "READY" : "DEGRADED");
        setMessage(result.health?.status === "ok" ? "NEEKA Work Engine is running." : result.error || "Engine is responding unexpectedly.");
      } catch { if (active) { setState("ERROR"); setMessage("The local engine is unavailable."); } }
    };
    void check();
    const timer = window.setInterval(check, 5000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);
  return <main className="shell">
    <header className="topbar"><div className="brand"><span className="brand-mark">N</span><span>NEEKA</span></div><span className="version">Work Engine v0.2.0</span></header>
    <section className="welcome"><p className="eyebrow">DESKTOP FOUNDATION</p><h1>Your work engine, close at hand.</h1><p className="message">{message}</p><div className={`status status-${state.toLowerCase()}`}><span className="status-dot" />{state}</div></section>
    <nav className="navigation" aria-label="Application navigation"><button className="nav-item active" type="button">Overview</button><button className="nav-item" type="button" disabled>Projects</button><button className="nav-item" type="button" disabled>Knowledge</button><button className="nav-item" type="button" disabled>Artifacts</button></nav>
    <footer>Local-first workspace · Secure desktop bridge</footer>
  </main>;
}