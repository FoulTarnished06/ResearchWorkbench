/**
 * AI RESEARCH WORKBENCH - CANVAS & PIPELINE VISUALIZATION MODULE
 * Draggable agent node cards, SVG dynamic Bezier curves, and visual telemetry
 */

import { UIState, elements } from './state.js';

export function activateNode(nodeId) {
  UIState.activeNode = nodeId;
  const card = document.getElementById(`node-agent${nodeId}`);
  const badge = document.getElementById(`badge-agent${nodeId}`);
  
  if (card && badge) {
    card.classList.remove('node-completed');
    card.classList.add('node-active');
    badge.className = 'node-badge badge-active';
    badge.textContent = 'Processing';
  }
}

export function completeNode(nodeId) {
  const card = document.getElementById(`node-agent${nodeId}`);
  const badge = document.getElementById(`badge-agent${nodeId}`);
  
  if (card && badge) {
    card.classList.remove('node-active');
    card.classList.add('node-completed');
    badge.className = 'node-badge badge-done';
    badge.textContent = 'Completed';
  }
}

export function resetNodeStates() {
  const arch = UIState.activeArchitecture || 'system_a';
  for (let i = 1; i <= 4; i++) {
    const card = document.getElementById(`node-agent${i}`);
    const badge = document.getElementById(`badge-agent${i}`);
    const prog = document.getElementById(`prog-agent${i}`);
    
    if (card) card.classList.remove('node-active', 'node-completed');
    if (badge) {
      badge.className = 'node-badge badge-idle';
      if (arch === 'system_c' && i === 2) {
        badge.textContent = 'Ready';
      } else if (arch !== 'system_c' && i === 1) {
        badge.textContent = 'Ready';
      } else {
        badge.textContent = 'Awaiting';
      }
    }
    if (prog) prog.style.width = '0%';
  }

  document.querySelectorAll('.check-item').forEach(chk => {
    chk.classList.remove('done');
    chk.querySelector('.chk-icon').textContent = '○';
  });

  [elements.path12, elements.path23, elements.path34].forEach(p => {
    if (p) p.classList.remove('active', 'completed');
  });

  const a2Tok = document.getElementById('m-agent2-tokens');
  if (a2Tok) a2Tok.textContent = '0 tokens (Call 1)';
  const a4Tok = document.getElementById('m-agent4-tokens');
  if (a4Tok) a4Tok.textContent = '0 tokens (Call 2)';

  // Re-assert active architecture topology
  updateCanvasArchitectureTopology(arch);
}

export function triggerPulse(fromNode) {
  const pathId = fromNode === 1 ? elements.path12 : (fromNode === 2 ? elements.path23 : (fromNode === 3 ? elements.path34 : null));
  const pulseEl = fromNode === 1 ? elements.pulse1 : (fromNode === 2 ? elements.pulse2 : (fromNode === 3 ? elements.pulse3 : null));
  
  if (pathId && pulseEl) {
    pathId.classList.add('active');
    pulseEl.classList.add('pulsing');
    
    const pathLen = pathId.getTotalLength();
    let start = performance.now();
    const duration = 650;
    
    function animate(time) {
      const progress = Math.min((time - start) / duration, 1);
      const point = pathId.getPointAtLength(progress * pathLen);
      pulseEl.setAttribute('cx', point.x);
      pulseEl.setAttribute('cy', point.y);
      
      if (progress < 1) {
        requestAnimationFrame(animate);
      } else {
        pathId.classList.remove('active');
        pathId.classList.add('completed');
        pulseEl.classList.remove('pulsing');
      }
    }
    requestAnimationFrame(animate);
  }
}



export function positionNodeCards() {
  const container = document.getElementById('view-canvas');
  if (!container) return;
  const w = container.clientWidth;
  const h = container.clientHeight;
  const arch = UIState.activeArchitecture || 'system_a';

  const n1H = elements.node1?.offsetHeight || 245;
  const n2H = elements.node2?.offsetHeight || 285;
  const n3H = elements.node3?.offsetHeight || 245;
  const n4H = elements.node4?.offsetHeight || 245;
  const cardW = elements.node2?.offsetWidth || 345;

  const isMobile = w < 1080;
  if (isMobile) {
    const cardX = Math.max(16, Math.round((w - cardW) * 0.5));
    const mobGap = 35;
    const mobTop = 30;

    if (arch === 'system_c') {
      UIState.nodePositions = {
        agent1: { x: -9999, y: -9999 },
        agent2: { x: cardX, y: mobTop },
        agent3: { x: -9999, y: -9999 },
        agent4: { x: -9999, y: -9999 }
      };
    } else if (arch === 'system_b') {
      const a1Y = mobTop;
      const a2Y = a1Y + n1H + mobGap;
      UIState.nodePositions = {
        agent1: { x: cardX, y: a1Y },
        agent2: { x: cardX, y: a2Y },
        agent3: { x: -9999, y: -9999 },
        agent4: { x: -9999, y: -9999 }
      };
    } else {
      // System A Mobile: Vertical stack with dynamic clearance
      const a1Y = mobTop;
      const a2Y = a1Y + n1H + mobGap;
      const a3Y = a2Y + n2H + mobGap;
      const a4Y = a3Y + n3H + mobGap;
      UIState.nodePositions = {
        agent1: { x: cardX, y: a1Y },
        agent2: { x: cardX, y: a2Y },
        agent3: { x: cardX, y: a3Y },
        agent4: { x: cardX, y: a4Y }
      };
    }
  } else {
    // Desktop Layouts per architecture
    if (arch === 'system_c') {
      // System C: Centered single LLM Call
      UIState.nodePositions = {
        agent1: { x: -9999, y: -9999 },
        agent2: { x: Math.max(30, Math.round((w - cardW) * 0.5)), y: Math.max(80, Math.round((h - n2H) * 0.35)) },
        agent3: { x: -9999, y: -9999 },
        agent4: { x: -9999, y: -9999 }
      };
    } else if (arch === 'system_b') {
      // System B: Two-node Conventional RAG (Node 1 -> Node 2)
      const centerY = Math.max(80, Math.round((h - Math.max(n1H, n2H)) * 0.35));
      UIState.nodePositions = {
        agent1: { x: Math.max(40, Math.round(w * 0.18)), y: centerY },
        agent2: { x: Math.min(w - cardW - 40, Math.round(w * 0.56)), y: centerY },
        agent3: { x: -9999, y: -9999 },
        agent4: { x: -9999, y: -9999 }
      };
    } else {
      // System A: Full 4-Agent Pipeline
      // Column 1: Agent 1 (Left)
      // Column 2: Agent 2 (Middle Top) and Agent 3 (Middle Bottom, strictly below Agent 2)
      // Column 3: Agent 4 (Right)
      const col1X = Math.max(30, Math.min(Math.round(w * 0.05), 70));
      const col2X = Math.max(col1X + cardW + 35, Math.min(Math.round(w * 0.38), w - (cardW * 2) - 65));
      const col3X = Math.min(w - cardW - 30, Math.max(col2X + cardW + 35, Math.round(w * 0.70)));

      const topOffset = Math.max(45, Math.min(70, Math.round(h * 0.06)));
      const agent2Y = topOffset;
      const verticalGap = Math.max(45, Math.min(75, Math.round(h * 0.07)));
      const agent3Y = agent2Y + n2H + verticalGap; // GUARANTEED ZERO OVERLAP

      // Agent 1 vertically center-aligned with Agent 2
      const agent1Y = Math.max(45, agent2Y + Math.round((n2H - n1H) * 0.5));

      // Agent 4 vertically centered across the Column 2 stack
      const col2CenterY = (agent2Y + (agent3Y + n3H)) * 0.5;
      const agent4Y = Math.max(50, Math.round(col2CenterY - (n4H * 0.5)));

      UIState.nodePositions = {
        agent1: { x: col1X, y: agent1Y },
        agent2: { x: col2X, y: agent2Y },
        agent3: { x: col2X, y: agent3Y },
        agent4: { x: col3X, y: agent4Y }
      };
    }
  }

  // Update canvas wrapper min-height to prevent vertical clipping on smaller viewports
  let maxBottom = 0;
  if (arch === 'system_a') {
    maxBottom = Math.max(
      UIState.nodePositions.agent1.y + n1H,
      UIState.nodePositions.agent2.y + n2H,
      UIState.nodePositions.agent3.y + n3H,
      UIState.nodePositions.agent4.y + n4H
    );
  } else if (arch === 'system_b') {
    maxBottom = Math.max(
      UIState.nodePositions.agent1.y + n1H,
      UIState.nodePositions.agent2.y + n2H
    );
  } else {
    maxBottom = UIState.nodePositions.agent2.y + n2H;
  }

  const wrapper = document.querySelector('.canvas-wrapper');
  if (wrapper && maxBottom > 0) {
    const requiredHeight = Math.max(h, maxBottom + 60);
    wrapper.style.minHeight = `${requiredHeight}px`;
  }

  setNodeTransform(elements.node1, UIState.nodePositions.agent1);
  setNodeTransform(elements.node2, UIState.nodePositions.agent2);
  setNodeTransform(elements.node3, UIState.nodePositions.agent3);
  setNodeTransform(elements.node4, UIState.nodePositions.agent4);
}

export function setNodeTransform(el, pos) {
  if (el) {
    el.style.left = `${pos.x}px`;
    el.style.top = `${pos.y}px`;
  }
}

export function drawBezierConnectors() {
  const arch = UIState.activeArchitecture || 'system_a';
  const container = document.getElementById('view-canvas');
  const w = container ? container.clientWidth : window.innerWidth;
  const isMobile = w < 1080;

  const n1H = elements.node1?.offsetHeight || 245;
  const n2H = elements.node2?.offsetHeight || 285;
  const n3H = elements.node3?.offsetHeight || 245;
  const n4H = elements.node4?.offsetHeight || 245;
  const cardW = elements.node2?.offsetWidth || 345;

  if (arch === 'system_c') {
    // No connectors in single API call
    elements.path12?.setAttribute('d', '');
    elements.path23?.setAttribute('d', '');
    elements.path34?.setAttribute('d', '');
    return;
  }

  const p1 = UIState.nodePositions.agent1;
  const p2 = UIState.nodePositions.agent2;

  if (isMobile) {
    // Mobile / Narrow stack: vertical connectors from bottom of card N to top of card N+1
    if (arch === 'system_b') {
      const start1 = { x: p1.x + (cardW * 0.5), y: p1.y + n1H };
      const end2 = { x: p2.x + (cardW * 0.5), y: p2.y };
      elements.path12?.setAttribute('d', calculateVerticalBezier(start1, end2));
      elements.path23?.setAttribute('d', '');
      elements.path34?.setAttribute('d', '');
      return;
    }

    // System A Mobile
    const p3 = UIState.nodePositions.agent3;
    const p4 = UIState.nodePositions.agent4;

    const start1 = { x: p1.x + (cardW * 0.5), y: p1.y + n1H };
    const end2 = { x: p2.x + (cardW * 0.5), y: p2.y };
    elements.path12?.setAttribute('d', calculateVerticalBezier(start1, end2));

    const start2 = { x: p2.x + (cardW * 0.5), y: p2.y + n2H };
    const end3 = { x: p3.x + (cardW * 0.5), y: p3.y };
    elements.path23?.setAttribute('d', calculateVerticalBezier(start2, end3));

    const start3 = { x: p3.x + (cardW * 0.5), y: p3.y + n3H };
    const end4 = { x: p4.x + (cardW * 0.5), y: p4.y };
    elements.path34?.setAttribute('d', calculateVerticalBezier(start3, end4));
    return;
  }

  // Desktop
  if (arch === 'system_b') {
    // Only Node 1 -> Node 2 connector
    const start1 = { x: p1.x + cardW, y: p1.y + (n1H * 0.5) };
    const end2 = { x: p2.x, y: p2.y + (n2H * 0.5) };
    elements.path12?.setAttribute('d', calculateBezier(start1, end2));
    elements.path23?.setAttribute('d', '');
    elements.path34?.setAttribute('d', '');
    return;
  }

  // System A Desktop: Node 1 (left) -> Node 2 (mid-top) -> Node 3 (mid-bot) -> Node 4 (right)
  const p3 = UIState.nodePositions.agent3;
  const p4 = UIState.nodePositions.agent4;

  const start1 = { x: p1.x + cardW, y: p1.y + (n1H * 0.5) };
  const end2 = { x: p2.x, y: p2.y + (n2H * 0.5) };
  elements.path12?.setAttribute('d', calculateBezier(start1, end2));

  const start2 = { x: p2.x + (cardW * 0.5), y: p2.y + n2H };
  const end3 = { x: p3.x + (cardW * 0.5), y: p3.y };
  elements.path23?.setAttribute('d', calculateVerticalBezier(start2, end3));

  const start3 = { x: p3.x + cardW, y: p3.y + (n3H * 0.45) };
  const end4 = { x: p4.x, y: p4.y + (n4H * 0.5) };
  elements.path34?.setAttribute('d', calculateBezier(start3, end4));
}

export function calculateBezier(p1, p2) {
  const dx = (p2.x - p1.x) * 0.5;
  return `M ${p1.x} ${p1.y} C ${p1.x + dx} ${p1.y}, ${p2.x - dx} ${p2.y}, ${p2.x} ${p2.y}`;
}

export function calculateVerticalBezier(p1, p2) {
  const dy = (p2.y - p1.y) * 0.5;
  return `M ${p1.x} ${p1.y} C ${p1.x} ${p1.y + dy}, ${p2.x} ${p2.y - dy}, ${p2.x} ${p2.y}`;
}

export function zoomCanvas(factor) {
  UIState.scale = Math.min(Math.max(UIState.scale * factor, 0.6), 1.5);
  document.getElementById('agent-nodes-container').style.transform = `scale(${UIState.scale})`;
  elements.svgLayer.style.transform = `scale(${UIState.scale})`;
}

export function resetCanvasZoom() {
  UIState.scale = 1.0;
  document.getElementById('agent-nodes-container').style.transform = 'scale(1)';
  elements.svgLayer.style.transform = 'scale(1)';
}

// Background Grid (FE-04 FIX: single resize listener registration)
let bgCanvasInitialized = false;

export function initBackgroundCanvas() {
  const canvas = document.getElementById('bg-grid-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  function drawGrid() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const gridSize = 40;
    ctx.fillStyle = document.body.classList.contains('theme-beige') 
      ? 'rgba(120, 95, 70, 0.08)' 
      : 'rgba(255, 255, 255, 0.035)';
    
    for (let x = 0; x < canvas.width; x += gridSize) {
      for (let y = 0; y < canvas.height; y += gridSize) {
        ctx.beginPath();
        ctx.arc(x, y, 1, 0, Math.PI * 2);
        ctx.fill();
      }
    }
  }

  function resize() {
    if (canvas.parentElement) {
      canvas.width = canvas.parentElement.clientWidth;
      canvas.height = canvas.parentElement.clientHeight;
      drawGrid();
    }
  }

  if (!bgCanvasInitialized) {
    window.addEventListener('resize', resize);
    bgCanvasInitialized = true;
  }
  resize();
}

export function logToCanvas(text) {
  const line = document.createElement('div');
  line.className = 'log-line';
  if (text.includes('SUCCESS') || text.includes('DONE')) line.className += ' success';
  if (text.includes('AGENT') || text.includes('QUERY')) line.className += ' active';
  line.textContent = text;
  
  elements.canvasLogContainer.appendChild(line);
  elements.canvasLogContainer.scrollTop = elements.canvasLogContainer.scrollHeight;
}

// Database Modal
export async function openDatabaseModal() {
  elements.dbInspectorModal.classList.add('open');
  elements.dbTableBody.innerHTML = `<tr><td colspan="7" class="text-center text-subtle">Querying SQLite cache.db...</td></tr>`;
  
  try {
    const resp = await fetch('/api/cache/papers');
    if (resp.ok) {
      const data = await resp.json();
      if (data.papers && data.papers.length > 0) {
        elements.dbTableBody.innerHTML = '';
        data.papers.forEach(p => {
          const tr = document.createElement('tr');
          tr.innerHTML = `
            <td class="mono">${(p.id || '').substring(0, 10)}...</td>
            <td>${p.query || '--'}</td>
            <td><strong>${p.title || 'Untitled'}</strong></td>
            <td>${p.authors || '--'}</td>
            <td>${p.year || '--'}</td>
            <td>${p.venue || '--'}</td>
            <td class="mono">${p.citation_count || 0}</td>
          `;
          elements.dbTableBody.appendChild(tr);
        });
        return;
      }
    }
  } catch (e) {
    // console.log("DB fallback to static view", e);
  }

  // Fallback demo papers
  elements.dbTableBody.innerHTML = `
    <tr>
      <td class="mono">quant_01</td>
      <td>Quantum Qubits</td>
      <td><strong>Quantum Error Mitigation in Rydberg Atom Arrays</strong></td>
      <td>M. Endres, H. Levine et al.</td>
      <td>2024</td>
      <td>Nature Quantum</td>
      <td class="mono">142</td>
    </tr>
    <tr>
      <td class="mono">crispr_01</td>
      <td>CRISPR Cas12f</td>
      <td><strong>Engineered Cas12f Nucleases for Compact In Vivo Viral Delivery</strong></td>
      <td>K. Tsuchida, F. Zhang et al.</td>
      <td>2024</td>
      <td>Nature Biotech</td>
      <td class="mono">178</td>
    </tr>
  `;
}

export function updateCanvasArchitectureTopology(arch = 'system_a') {
  const n1 = document.getElementById('node-agent1');
  const n2 = document.getElementById('node-agent2');
  const n3 = document.getElementById('node-agent3');
  const n4 = document.getElementById('node-agent4');

  const b1 = document.getElementById('badge-agent1');
  const b2 = document.getElementById('badge-agent2');
  const b3 = document.getElementById('badge-agent3');
  const b4 = document.getElementById('badge-agent4');

  const p12 = document.getElementById('path-1-2');
  const p23 = document.getElementById('path-2-3');
  const p34 = document.getElementById('path-3-4');

  // Reset bypassed classes
  [n1, n2, n3, n4].forEach(n => {
    if (n) {
      n.classList.remove('node-bypassed');
    }
  });
  [p12, p23, p34].forEach(p => {
    if (p) {
      p.classList.remove('path-bypassed');
    }
  });

  if (arch === 'system_a') {
    // System A: All 4 nodes visible and active
    if (n1) {
      n1.style.display = '';
      n1.removeAttribute('aria-hidden');
      const nameEl = n1.querySelector('.node-name');
      const subEl = n1.querySelector('.node-sub');
      if (nameEl) nameEl.textContent = 'Agent 1: Academic Scraper';
      if (subEl) subEl.textContent = 'Crossref, DOAJ & OpenAlex APIs';
      if (b1 && (b1.textContent === 'Bypassed' || !b1.textContent)) {
        b1.className = 'node-badge badge-idle';
        b1.textContent = 'Ready';
      }
    }
    if (n2) {
      n2.style.display = '';
      n2.removeAttribute('aria-hidden');
      const nameEl = n2.querySelector('.node-name');
      const subEl = n2.querySelector('.node-sub');
      if (nameEl) nameEl.textContent = 'Agent 2: Research Drafter';
      if (subEl) subEl.textContent = 'Synthesizes literature & embeds claims';
      if (b2 && (b2.textContent === 'Bypassed' || !b2.textContent)) {
        b2.className = 'node-badge badge-idle';
        b2.textContent = 'Awaiting';
      }
    }
    if (n3) {
      n3.style.display = '';
      n3.removeAttribute('aria-hidden');
      const nameEl = n3.querySelector('.node-name');
      const subEl = n3.querySelector('.node-sub');
      if (nameEl) nameEl.textContent = 'Agent 3: SQLite Evidence Cacher';
      if (subEl) subEl.textContent = 'Local Cosine Pre-Filter (≥ 0.80)';
      if (b3 && (b3.textContent === 'Bypassed' || !b3.textContent)) {
        b3.className = 'node-badge badge-idle';
        b3.textContent = 'Awaiting';
      }
    }
    if (n4) {
      n4.style.display = '';
      n4.removeAttribute('aria-hidden');
      const nameEl = n4.querySelector('.node-name');
      const subEl = n4.querySelector('.node-sub');
      if (nameEl) nameEl.textContent = 'Agent 4: Fact-Checker & Synthesizer';
      if (subEl) subEl.textContent = 'Adversarial Claim Verification';
      if (b4 && (b4.textContent === 'Bypassed' || !b4.textContent)) {
        b4.className = 'node-badge badge-idle';
        b4.textContent = 'Awaiting';
      }
    }
    if (p12) p12.style.display = '';
    if (p23) p23.style.display = '';
    if (p34) p34.style.display = '';
    logToCanvas("[TOPOLOGY] System A Active: 4-Agent Full Pipeline connected.");
  } else if (arch === 'system_b') {
    // Conventional RAG: Node 1 (Retriever) -> Node 2 (Augmented Call). Hide Node 3 & 4!
    if (n1) {
      n1.style.display = '';
      n1.removeAttribute('aria-hidden');
      const nameEl = n1.querySelector('.node-name');
      const subEl = n1.querySelector('.node-sub');
      if (nameEl) nameEl.textContent = 'Vector DB Retriever';
      if (subEl) subEl.textContent = 'FastEmbed ONNX Top-K Retrieval';
      if (b1 && (b1.textContent === 'Bypassed' || !b1.textContent)) {
        b1.className = 'node-badge badge-idle';
        b1.textContent = 'Ready';
      }
    }
    if (n2) {
      n2.style.display = '';
      n2.removeAttribute('aria-hidden');
      const nameEl = n2.querySelector('.node-name');
      const subEl = n2.querySelector('.node-sub');
      if (nameEl) nameEl.textContent = 'Augmented LLM Generation';
      if (subEl) subEl.textContent = 'Single-Pass Context Generation';
      if (b2 && (b2.textContent === 'Bypassed' || !b2.textContent)) {
        b2.className = 'node-badge badge-idle';
        b2.textContent = 'Awaiting';
      }
    }
    if (n3) {
      n3.style.display = 'none';
      n3.setAttribute('aria-hidden', 'true');
    }
    if (n4) {
      n4.style.display = 'none';
      n4.setAttribute('aria-hidden', 'true');
    }
    if (p12) p12.style.display = '';
    if (p23) p23.style.display = 'none';
    if (p34) p34.style.display = 'none';
    logToCanvas("[TOPOLOGY] System B Active: Conventional RAG (Vector Top-K -> 1 Call). Agent 3 & 4 Hidden.");
  } else if (arch === 'system_c') {
    // Direct Single API: Only Node 2 active! Hide Node 1, 3, 4!
    if (n1) {
      n1.style.display = 'none';
      n1.setAttribute('aria-hidden', 'true');
    }
    if (n2) {
      n2.style.display = '';
      n2.removeAttribute('aria-hidden');
      const nameEl = n2.querySelector('.node-name');
      const subEl = n2.querySelector('.node-sub');
      if (nameEl) nameEl.textContent = 'Direct Single API Call';
      if (subEl) subEl.textContent = 'Zero-Shot Parametric Memory';
      if (b2 && (b2.textContent === 'Bypassed' || !b2.textContent)) {
        b2.className = 'node-badge badge-idle';
        b2.textContent = 'Ready';
      }
    }
    if (n3) {
      n3.style.display = 'none';
      n3.setAttribute('aria-hidden', 'true');
    }
    if (n4) {
      n4.style.display = 'none';
      n4.setAttribute('aria-hidden', 'true');
    }
    if (p12) p12.style.display = 'none';
    if (p23) p23.style.display = 'none';
    if (p34) p34.style.display = 'none';
    logToCanvas("[TOPOLOGY] System C Active: Direct Single API (Zero-Shot). Nodes 1, 3, 4 Hidden.");
  }

  // Instantly re-calculate layout and update SVG connectors
  positionNodeCards();
  drawBezierConnectors();
}



