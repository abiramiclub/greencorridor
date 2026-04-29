import React, { useState } from 'react';
import parcels from '../data/parcels.json';
import guardrails from '../data/guardrails.json';

const SEVERITY_COLORS = {
  BLOCK: { bg: '#FFEBEE', border: '#C41E3A', text: '#C41E3A', badge: '#C41E3A' },
  CONDITIONAL: { bg: '#FFF3E0', border: '#E65100', text: '#E65100', badge: '#E65100' },
  REVIEW: { bg: '#FFF9C4', border: '#F57C00', text: '#F57C00', badge: '#F57C00' },
  CONSULT: { bg: '#E3F2FD', border: '#1565C0', text: '#1565C0', badge: '#1565C0' },
};

const SEVERITY_ICONS = { BLOCK: '🚫', CONDITIONAL: '⚠️', REVIEW: '🔍', CONSULT: '📋' };

function evaluateRules(parcel) {
  const f = parcel.features;
  const triggered = [];

  guardrails.rules.forEach(rule => {
    let fired = false;
    if (rule.id === 'RIPARIAN_BUFFER')      fired = f.riparian_distance_ft < 100;
    if (rule.id === 'FOREST_CANOPY')        fired = f.core_forest_acres > 1.0;
    if (rule.id === 'EAGLE_HABITAT')        fired = f.bald_eagle_sightings_miles < 2.0;
    if (rule.id === 'HABITAT_CONNECTIVITY') fired = f.habitat_connectivity_priority === 'high';
    if (rule.id === 'WETLAND_IMPACT')       fired = f.wetland_percent > 5;
    if (fired) triggered.push(rule);
  });

  const blocks = triggered.filter(r => r.severity === 'BLOCK');
  return {
    triggered,
    blocks,
    decision: blocks.length > 0 ? 'BLOCKED' : 'PASS',
    timestamp: new Date().toLocaleString(),
  };
}

function RuleCard({ rule }) {
  const [open, setOpen] = useState(false);
  const c = SEVERITY_COLORS[rule.severity] || SEVERITY_COLORS.REVIEW;
  return (
    <div style={{ marginBottom: 12, borderRadius: 6, border: `1px solid ${c.border}`, overflow: 'hidden' }}>
      <div
        onClick={() => setOpen(o => !o)}
        style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px',
          backgroundColor: c.bg, cursor: 'pointer', userSelect: 'none' }}
      >
        <span style={{ fontSize: 18 }}>{SEVERITY_ICONS[rule.severity]}</span>
        <div style={{ flex: 1 }}>
          <strong style={{ color: c.text }}>{rule.name}</strong>
          <div style={{ fontSize: 12, color: '#555', marginTop: 2 }}>{rule.regulation}</div>
        </div>
        <span style={{
          fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 12,
          backgroundColor: c.badge, color: 'white', letterSpacing: 1
        }}>{rule.severity}</span>
        <span style={{ color: '#999', fontSize: 12 }}>{open ? '▲' : '▼'}</span>
      </div>
      {open && (
        <div style={{ padding: '12px 14px', backgroundColor: 'white', borderTop: `1px solid ${c.border}` }}>
          <p style={{ margin: '0 0 8px', color: '#333' }}><strong>Impact:</strong> {rule.impact_if_violated}</p>
          <p style={{ margin: '0 0 4px', fontWeight: 600, color: '#444' }}>Mitigation options:</p>
          <ul style={{ margin: '0 0 10px', paddingLeft: 20, color: '#555' }}>
            {rule.mitigation_options.map((opt, i) => <li key={i} style={{ marginBottom: 4 }}>{opt}</li>)}
          </ul>
          <p style={{ margin: 0, fontSize: 12, color: '#777', fontStyle: 'italic' }}>
            <strong>Approval path:</strong> {rule.approval_path}
          </p>
        </div>
      )}
    </div>
  );
}

function ParcelInfo({ parcel }) {
  const f = parcel.features;
  const rows = [
    ['Corridor zone', f.green_corridor_name || f.green_corridor_zone],
    ['Riparian distance', `${f.riparian_distance_ft} ft from ${f.riparian_feature}`],
    ['Wetland coverage', `${f.wetland_percent}% — ${f.wetland_type}`],
    ['Core forest', `${f.core_forest_acres} ac (${f.core_forest_type})`],
    ['Bald eagle sightings', `${f.bald_eagle_sightings_miles} mi — ${f.eagle_sightings_count} sightings`],
    ['Connectivity priority', f.habitat_connectivity_priority.toUpperCase()],
    ['Spotted salamander habitat', f.spotted_salamander_habitat ? 'Yes' : 'No'],
    ['American eel access', f.american_eel_access ? 'Yes' : 'No'],
  ];
  return (
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
      <tbody>
        {rows.map(([label, val]) => (
          <tr key={label} style={{ borderBottom: '1px solid #eee' }}>
            <td style={{ padding: '5px 8px', color: '#555', fontWeight: 600, whiteSpace: 'nowrap' }}>{label}</td>
            <td style={{ padding: '5px 8px', color: '#222' }}>{val}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function CorridorGuardianDemo() {
  const [selectedId, setSelectedId] = useState('PH-001');
  const [expansionAcres, setExpansionAcres] = useState(0.2);
  const [results, setResults] = useState(null);
  const [evaluated, setEvaluated] = useState(false);

  const parcel = parcels.parcels.find(p => p.id === selectedId);

  const handleEvaluate = () => {
    setResults(evaluateRules(parcel));
    setEvaluated(true);
  };

  const handleParcelChange = (id) => {
    setSelectedId(id);
    setResults(null);
    setEvaluated(false);
  };

  const decisionColor = results?.decision === 'PASS' ? '#2C5F2D' : '#C41E3A';
  const decisionBg = results?.decision === 'PASS' ? '#E8F5E9' : '#FFEBEE';

  const blocks = results?.triggered.filter(r => r.severity === 'BLOCK') || [];
  const others = results?.triggered.filter(r => r.severity !== 'BLOCK') || [];

  return (
    <div style={{ fontFamily: 'Calibri, Segoe UI, sans-serif', maxWidth: 860, margin: '0 auto', padding: 24, color: '#222' }}>

      {/* Header */}
      <div style={{ borderBottom: '3px solid #2C5F2D', paddingBottom: 12, marginBottom: 24 }}>
        <h1 style={{ margin: 0, fontSize: 26, color: '#2C5F2D' }}>CorridorGuardian</h1>
        <p style={{ margin: '4px 0 0', color: '#555', fontSize: 14 }}>
          Town of Philipstown — Permit Scenario Evaluator &nbsp;|&nbsp; Hudson Highlands Green Corridors Initiative
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>

        {/* Left: inputs */}
        <div>
          <div style={{ marginBottom: 20, padding: 16, background: '#f8f8f8', borderRadius: 8 }}>
            <h3 style={{ margin: '0 0 12px', fontSize: 15 }}>Step 1 — Select Parcel</h3>
            {parcels.parcels.map(p => (
              <label key={p.id} style={{ display: 'flex', alignItems: 'flex-start', gap: 8,
                marginBottom: 10, cursor: 'pointer' }}>
                <input type="radio" name="parcel" value={p.id}
                  checked={selectedId === p.id}
                  onChange={() => handleParcelChange(p.id)}
                  style={{ marginTop: 3 }} />
                <div>
                  <div style={{ fontWeight: 600 }}>{p.id} — {p.address}</div>
                  <div style={{ fontSize: 12, color: '#666' }}>{p.owner} · {p.zoning} · {p.acres} ac</div>
                  <div style={{ fontSize: 12, color: '#888', fontStyle: 'italic' }}>{p.description}</div>
                </div>
              </label>
            ))}
          </div>

          <div style={{ marginBottom: 20, padding: 16, background: '#f8f8f8', borderRadius: 8 }}>
            <h3 style={{ margin: '0 0 12px', fontSize: 15 }}>Step 2 — Propose Expansion</h3>
            <label style={{ fontSize: 14 }}>
              Expansion size (acres):&nbsp;
              <input type="number" value={expansionAcres}
                onChange={e => setExpansionAcres(parseFloat(e.target.value))}
                min="0.1" max="5" step="0.1"
                style={{ padding: '5px 8px', width: 80, borderRadius: 4, border: '1px solid #ccc', fontSize: 14 }} />
            </label>
          </div>

          <button onClick={handleEvaluate} style={{
            width: '100%', padding: '13px 0', fontSize: 15, fontWeight: 700,
            backgroundColor: '#2C5F2D', color: 'white', border: 'none',
            borderRadius: 6, cursor: 'pointer', letterSpacing: 0.5
          }}>
            Evaluate Against Town Guardrails →
          </button>

          {/* Parcel feature table */}
          {parcel && (
            <div style={{ marginTop: 20, padding: 16, background: '#f8f8f8', borderRadius: 8 }}>
              <h3 style={{ margin: '0 0 10px', fontSize: 14, color: '#444' }}>Parcel Environmental Data</h3>
              <ParcelInfo parcel={parcel} />
            </div>
          )}
        </div>

        {/* Right: results */}
        <div>
          {!evaluated && (
            <div style={{ padding: 24, background: '#f0f4f0', borderRadius: 8, textAlign: 'center', color: '#666' }}>
              <div style={{ fontSize: 40, marginBottom: 12 }}>🌿</div>
              <p style={{ margin: 0, fontSize: 14 }}>Select a parcel and click <strong>Evaluate</strong> to check against Philipstown's green guardrails.</p>
            </div>
          )}

          {evaluated && results && (
            <div>
              {/* Decision banner */}
              <div style={{ padding: '14px 18px', borderRadius: 8, backgroundColor: decisionBg,
                border: `2px solid ${decisionColor}`, marginBottom: 16 }}>
                <div style={{ fontSize: 22, fontWeight: 800, color: decisionColor }}>
                  {results.decision === 'PASS' ? '✓ PASSES GUARDRAILS' : '🚫 BLOCKED'}
                </div>
                <div style={{ fontSize: 13, color: '#555', marginTop: 4 }}>
                  {parcel.address} · {expansionAcres} ac expansion · {results.timestamp}
                </div>
                <div style={{ fontSize: 13, marginTop: 6, color: '#333' }}>
                  {results.triggered.length === 0
                    ? 'No guardrails triggered. Expansion may proceed subject to standard review.'
                    : `${blocks.length} blocking violation${blocks.length !== 1 ? 's' : ''}, ${others.length} condition${others.length !== 1 ? 's' : ''} to address.`}
                </div>
              </div>

              {/* Blocking violations */}
              {blocks.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                  <h3 style={{ fontSize: 14, color: '#C41E3A', margin: '0 0 8px' }}>
                    🚫 Critical Violations — Expansion Blocked
                  </h3>
                  {blocks.map(r => <RuleCard key={r.id} rule={r} />)}
                </div>
              )}

              {/* Conditions & consultations */}
              {others.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                  <h3 style={{ fontSize: 14, color: '#E65100', margin: '0 0 8px' }}>
                    ⚠️ Conditions & Consultations Required
                  </h3>
                  {others.map(r => <RuleCard key={r.id} rule={r} />)}
                </div>
              )}

              {/* All clear */}
              {results.triggered.length === 0 && (
                <div style={{ padding: 16, backgroundColor: '#E8F5E9', borderRadius: 6,
                  borderLeft: '4px solid #2C5F2D' }}>
                  <p style={{ margin: 0, fontWeight: 600, color: '#2C5F2D' }}>
                    ✓ All 5 guardrails evaluated — no violations detected.
                  </p>
                  <p style={{ margin: '8px 0 0', fontSize: 13, color: '#444' }}>
                    Proceed to standard planning board review. All decisions are logged and auditable.
                  </p>
                </div>
              )}

              {/* Footer note */}
              <p style={{ fontSize: 11, color: '#888', marginTop: 16, fontStyle: 'italic' }}>
                Source: Hudson Highlands Green Corridors Plan (2022), NYS Environmental Conservation Law.
                AI-assisted. Field verification by a qualified ecologist is recommended before any land use decision.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
