const agents = [
  ["Scout", "Scanning 24 sources", "active"],
  ["Researcher", "Corroborating 7 claims", "active"],
  ["Skeptic", "Challenging timeline", "review"],
  ["Editor", "Waiting for evidence", "waiting"],
];

export default function Home() {
  return (
    <main>
      <header className="masthead">
        <div>
          <p className="eyebrow">The Signal Desk</p>
          <h1>Multi-Agent Newsroom</h1>
        </div>
        <div className="status"><span /> Systems operational</div>
      </header>

      <section className="hero">
        <p className="eyebrow">Developing investigation · 14:32 IST</p>
        <h2>Every claim challenged.<br />Every source visible.</h2>
        <p className="lede">An autonomous editorial team is tracing conflicting reports into one accountable story.</p>
        <Link className="button" href="/investigations/demo">Open investigation <span>→</span></Link>
      </section>

      <section className="grid">
        <article className="panel lead-story">
          <div className="panel-heading"><span>Lead story</span><strong>LIVE</strong></div>
          <h3>Conflicting reports emerge as events continue to develop</h3>
          <p>Eight independent sources · 19 extracted claims · 3 contradictions under review</p>
          <div className="confidence"><span style={{ width: "78%" }} /></div>
          <small>Overall evidence confidence <b>78%</b></small>
        </article>

        <article className="panel agents">
          <div className="panel-heading"><span>Agent desk</span><em>4 assigned</em></div>
          {agents.map(([name, task, state]) => (
            <div className="agent" key={name}>
              <i className={state} />
              <div><b>{name}</b><small>{task}</small></div>
            </div>
          ))}
        </article>

        <article className="panel evidence">
          <div className="panel-heading"><span>Evidence pulse</span><em>Updated now</em></div>
          <div className="metric"><b>19</b><span>Claims mapped</span></div>
          <div className="metric"><b>31</b><span>Citations linked</span></div>
          <div className="metric warning"><b>3</b><span>Contradictions</span></div>
        </article>
      </section>
    </main>
  );
}
import Link from "next/link";
