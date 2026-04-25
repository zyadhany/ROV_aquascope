import { escapeHtml } from '../utils.js';

export function renderServices(container, services, serviceLogs) {
  if (!services.length) {
    container.innerHTML = '<div class="empty-state">No services configured.</div>';
    return;
  }

  container.innerHTML = services.map((service) => {
    const logs = serviceLogs[service.id];
    const logLines = Array.isArray(logs?.lines) ? logs.lines.join('\n') : '';

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
        <div class="service-actions">
          <button type="button" data-service-id="${escapeHtml(service.id)}" data-service-action="start">Start</button>
          <button type="button" data-service-id="${escapeHtml(service.id)}" data-service-action="stop">Stop</button>
          <button type="button" data-service-id="${escapeHtml(service.id)}" data-service-action="restart">Restart</button>
          <button type="button" data-service-id="${escapeHtml(service.id)}" data-service-action="logs">Logs</button>
        </div>
        ${logLines ? `<pre class="log-box">${escapeHtml(logLines)}</pre>` : ''}
      </article>
    `;
  }).join('');
}
