import { escapeHtml } from '../utils.js';

function renderServiceRows(service) {
  const rows = [
    ['Control', service.control_mode || 'manual'],
    ['Node', service.node_name || ''],
    ['Tracked', service.tracked ? 'yes' : 'no'],
    ['ROS Graph', service.ros_graph_running ? 'running' : 'not detected'],
    ['Last Update', service.last_update || ''],
  ].filter(([, value]) => value !== undefined && value !== null && value !== '');

  return rows.map(([label, value]) => `
    <div class="detail-row">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
    </div>
  `).join('');
}

export function renderServices(container, services, serviceLogs) {
  if (!services.length) {
    container.innerHTML = '<div class="empty-state">No services configured.</div>';
    return;
  }

  container.innerHTML = services.map((service) => {
    const logs = serviceLogs[service.id];
    const logLines = Array.isArray(logs?.lines) ? logs.lines.join('\n') : '';
    const controllable = service.controllable !== false;

    return `
      <article class="service-card">
        <div class="service-header">
          <div>
            <span class="type-chip">${escapeHtml(service.type)}</span>
            <h2>${escapeHtml(service.name)}</h2>
          </div>
          <span class="status-pill">${escapeHtml(service.status)}</span>
        </div>
        <p>${escapeHtml(service.description)}</p>
        <div class="detail-rows compact-rows">
          ${renderServiceRows(service)}
        </div>
        <div class="service-actions">
          <button type="button" data-service-id="${escapeHtml(service.id)}" data-service-action="start" ${controllable ? '' : 'disabled'}>Start</button>
          <button type="button" data-service-id="${escapeHtml(service.id)}" data-service-action="stop" ${controllable ? '' : 'disabled'}>Stop</button>
          <button type="button" data-service-id="${escapeHtml(service.id)}" data-service-action="restart" ${controllable ? '' : 'disabled'}>Restart</button>
          <button type="button" data-service-id="${escapeHtml(service.id)}" data-service-action="logs">Logs</button>
        </div>
        ${service.message ? `<div class="response-box" data-tone="error">${escapeHtml(service.message)}</div>` : ''}
        ${logLines ? `<pre class="log-box">${escapeHtml(logLines)}</pre>` : ''}
      </article>
    `;
  }).join('');
}
