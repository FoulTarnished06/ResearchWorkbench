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
  for (let i = 1; i <= 4; i++) {
    const card = document.getElementById(`node-agent${i}`);
    const badge = document.getElementById(`badge-agent${i}`);
    const prog = document.getElementById(`prog-agent${i}`);
    
    if (card) card.classList.remove('node-active', 'node-completed');
    if (badge) {
      badge.className = 'node-badge badge-idle';
      badge.textContent = 'Awaiting';
    }
    if (prog) prog.style.width = '0%';
  }

  document.querySelectorAll('.check-item').forEach(chk => {
    chk.classList.remove('done');
    chk.querySelector('.chk-icon').textContent = '○';
  });

  [elements.path12, elements.path23, elements.path34].forEach(p => {
    p.classList.remove('active', 'completed');
  });

  const a2Tok = document.getElementById('m-agent2-tokens');
  if (a2Tok) a2Tok.textContent = '0 tokens (Call 1)';
  const a4Tok = document.getElementById('m-agent4-tokens');
  if (a4Tok) a4Tok.textContent = '0 tokens (Call 2)';
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

  const isMobile = w < 1000;
  if (isMobile) {
    UIState.nodePositions = {
      agent1: { x: 20, y: 30 },
      agent2: { x: 20, y: 300 },
      agent3: { x: 20, y: 570 },
      agent4: { x: 20, y: 840 }
    };
  } else {
    UIState.nodePositions = {
      agent1: { x: Math.max(40, w * 0.05), y: h * 0.22 },
      agent2: { x: w * 0.36, y: h * 0.12 },
      agent3: { x: w * 0.36, y: h * 0.52 },
      agent4: { x: Math.min(w - 350, w * 0.68), y: h * 0.30 }
    };
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
  const cardW = 310;
  const cardH = 200;

  const p1 = UIState.nodePositions.agent1;
  const p2 = UIState.nodePositions.agent2;
  const p3 = UIState.nodePositions.agent3;
  const p4 = UIState.nodePositions.agent4;

  const start1 = { x: p1.x + cardW, y: p1.y + (cardH * 0.45) };
  const end2 = { x: p2.x, y: p2.y + (cardH * 0.45) };
  elements.path12.setAttribute('d', calculateBezier(start1, end2));

  const start2 = { x: p2.x + (cardW * 0.5), y: p2.y + cardH };
  const end3 = { x: p3.x + (cardW * 0.5), y: p3.y };
  elements.path23.setAttribute('d', calculateVerticalBezier(start2, end3));

  const start3 = { x: p3.x + cardW, y: p3.y + (cardH * 0.45) };
  const end4 = { x: p4.x, y: p4.y + (cardH * 0.45) };
  elements.path34.setAttribute('d', calculateBezier(start3, end4));
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



