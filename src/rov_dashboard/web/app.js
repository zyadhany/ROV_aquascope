const DEFAULT_FLOWCHART = {
  config: {
    project_name: 'ROV Dashboard',
    refresh_rate_ms: 1000,
    edit_mode_enabled: true,
    allow_drag: true,
    allow_save_layout: true,
    show_connection_labels: true,
    theme: {
      background: '#0f172a',
      panel_background: '#111827',
      text: '#f8fafc',
      muted_text: '#94a3b8',
    },
    colors: {
      thruster: '#ef4444',
      pump: '#f97316',
      light: '#facc15',
      camera: '#8b5cf6',
      sensor: '#06b6d4',
      topic: '#22c55e',
      node: '#3b82f6',
      service: '#a855f7',
      interface: '#ec4899',
      software: '#f97316',
      subsystem: '#64748b',
    },
    font_sizes: {
      block_title: 14,
      block_type: 11,
      panel_title: 18,
      normal_text: 14,
    },
  },
  blocks: [],
  connections: [],
  layout: {
    version: 1,
    viewport: {
      zoom: 1,
      pan_x: 0,
      pan_y: 0,
    },
    positions: {},
    groups: [],
  },
};

let cy = null;
let flowchartState = cloneValue(DEFAULT_FLOWCHART);
let selectedBlockId = null;
let selectedBlock = null;
let selectedState = null;
let selectedLogs = null;
let selectedTopicData = null;
let commandResponse = null;
let topicPublishResponse = null;
let services = [];
let serviceLogs = {};
let editMode = true;
let refreshTimer = null;
let topicPollTimer = null;
let topicPollInFlight = false;
let topicDataStatus = 'idle';
let topicDataError = '';
let activePanel = 'block';
let topicPublishDraft = {
  topic: '',
  messageType: '',
  value: '',
  advanced: false,
  jsonValue: '{\n  "linear": {\n    "x": 1.0,\n    "y": 0.0,\n    "z": 0.0\n  },\n  "angular": {\n    "x": 0.0,\n    "y": 0.0,\n    "z": 0.5\n  }\n}',
};

const projectNameElement = document.getElementById('projectName');
const editModeToggle = document.getElementById('editModeToggle');
const saveLayoutButton = document.getElementById('saveLayoutButton');
const reloadButton = document.getElementById('reloadButton');
const selectionDetailsElement = document.getElementById('selectionDetails');
const servicesListElement = document.getElementById('servicesList');
const saveStatusElement = document.getElementById('saveStatus');
const blockCountElement = document.getElementById('blockCount');
const connectionCountElement = document.getElementById('connectionCount');
const selectedBlockLabelElement = document.getElementById('selectedBlockLabel');
const blockPanel = document.getElementById('blockPanel');
const servicesPanel = document.getElementById('servicesPanel');

function cloneValue(value) {
  return JSON.parse(JSON.stringify(value));
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function formatType(value) {
  return String(value || 'unknown')
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function prettyJson(value) {
  return escapeHtml(JSON.stringify(value ?? {}, null, 2));
}

function normalizeMessageType(messageType) {
  return String(messageType || '').replace('/msg/', '/');
}

function isTopicBlock(block) {
  return block?.type === 'topic';
}

function isSimpleStdMessage(messageType) {
  return [
    'std_msgs/Float64',
    'std_msgs/Float32',
    'std_msgs/Int32',
    'std_msgs/Int64',
    'std_msgs/Bool',
    'std_msgs/String',
  ].includes(normalizeMessageType(messageType));
}

function parseBool(value) {
  const normalized = String(value).trim().toLowerCase();
  if (['true', '1', 'yes', 'on'].includes(normalized)) {
    return true;
  }
  if (['false', '0', 'no', 'off'].includes(normalized)) {
    return false;
  }
  throw new Error('Bool value must be true or false.');
}

function parsePublishValue(messageType, valueText, advanced) {
  if (advanced) {
    return JSON.parse(valueText || 'null');
  }

  const normalizedType = normalizeMessageType(messageType);
  if (['std_msgs/Float64', 'std_msgs/Float32'].includes(normalizedType)) {
    const value = Number(valueText);
    if (!Number.isFinite(value)) {
      throw new Error('Value must be a number.');
    }
    return value;
  }

  if (['std_msgs/Int32', 'std_msgs/Int64'].includes(normalizedType)) {
    const value = Number(valueText);
    if (!Number.isInteger(value)) {
      throw new Error('Value must be an integer.');
    }
    return value;
  }

  if (normalizedType === 'std_msgs/Bool') {
    return parseBool(valueText);
  }

  if (normalizedType === 'std_msgs/String') {
    return String(valueText ?? '');
  }

  try {
    return JSON.parse(valueText);
  } catch (error) {
    return String(valueText ?? '');
  }
}

function mergedFlowchart(payload) {
  const incomingConfig = payload.config || {};
  const incomingLayout = payload.layout || {};

  return {
    config: {
      ...cloneValue(DEFAULT_FLOWCHART.config),
      ...incomingConfig,
      theme: {
        ...DEFAULT_FLOWCHART.config.theme,
        ...(incomingConfig.theme || {}),
      },
      colors: {
        ...DEFAULT_FLOWCHART.config.colors,
        ...(incomingConfig.colors || {}),
      },
      font_sizes: {
        ...DEFAULT_FLOWCHART.config.font_sizes,
        ...(incomingConfig.font_sizes || {}),
      },
    },
    blocks: Array.isArray(payload.blocks) ? payload.blocks : [],
    connections: Array.isArray(payload.connections) ? payload.connections : [],
    layout: {
      ...cloneValue(DEFAULT_FLOWCHART.layout),
      ...incomingLayout,
      viewport: {
        ...DEFAULT_FLOWCHART.layout.viewport,
        ...(incomingLayout.viewport || {}),
      },
      positions: {
        ...DEFAULT_FLOWCHART.layout.positions,
        ...(incomingLayout.positions || {}),
      },
      groups: Array.isArray(incomingLayout.groups) ? incomingLayout.groups : [],
    },
  };
}

function blockApiPath(blockId) {
  const cleanId = String(blockId || '').replace(/^\/+/, '');
  const encoded = cleanId.split('/').map(encodeURIComponent).join('/');
  return `/api/block/${encoded}`;
}

function setPanel(panelName) {
  activePanel = panelName;
  document.querySelectorAll('.tab-button').forEach((button) => {
    button.classList.toggle('active', button.dataset.panel === panelName);
  });
  blockPanel.classList.toggle('active', panelName === 'block');
  servicesPanel.classList.toggle('active', panelName === 'services');
  syncTopicPolling();
}

function setSaveStatus(message, tone = 'neutral') {
  saveStatusElement.textContent = message;
  saveStatusElement.dataset.tone = tone;
}

function updateStatusBar() {
  blockCountElement.textContent = String(flowchartState.blocks.length);
  connectionCountElement.textContent = String(flowchartState.connections.length);
  selectedBlockLabelElement.textContent = selectedBlock ? selectedBlock.name : 'None';
}

function applyTheme() {
  const rootStyle = document.documentElement.style;
  const theme = flowchartState.config.theme;
  rootStyle.setProperty('--app-bg', theme.background);
  rootStyle.setProperty('--panel-bg', theme.panel_background);
  rootStyle.setProperty('--text-main', theme.text);
  rootStyle.setProperty('--text-muted', theme.muted_text);
  rootStyle.setProperty('--accent', flowchartState.config.colors.interface);
}

function blockColor(blockType) {
  return flowchartState.config.colors[blockType] || flowchartState.config.colors.subsystem;
}

function fallbackPosition(index) {
  const column = index % 4;
  const row = Math.floor(index / 4);
  return {
    x: 140 + column * 260,
    y: 130 + row * 170,
  };
}

function graphElements() {
  const nodes = flowchartState.blocks.map((block, index) => ({
    data: {
      ...block,
      label: `${block.name}\n${formatType(block.type)}`,
      color: blockColor(block.type),
    },
    position: flowchartState.layout.positions[block.id] || fallbackPosition(index),
  }));

  const edges = flowchartState.connections.map((connection, index) => ({
    data: {
      ...connection,
      id: connection.id || `${connection.from}-${connection.to}-${index}`,
      source: connection.from,
      target: connection.to,
      color: flowchartState.config.colors.interface,
    },
  }));

  return [...nodes, ...edges];
}

function currentPositions() {
  const positions = {};
  if (!cy) {
    return positions;
  }

  cy.nodes().forEach((node) => {
    positions[node.id()] = {
      x: node.position('x'),
      y: node.position('y'),
    };
  });

  return positions;
}

function currentViewport() {
  if (!cy) {
    return cloneValue(DEFAULT_FLOWCHART.layout.viewport);
  }

  return {
    zoom: cy.zoom(),
    pan_x: cy.pan().x,
    pan_y: cy.pan().y,
  };
}

function applyViewport() {
  const viewport = flowchartState.layout.viewport;
  cy.zoom(viewport.zoom ?? 1);
  cy.pan({
    x: viewport.pan_x ?? 0,
    y: viewport.pan_y ?? 0,
  });
}

function setEditMode(nextValue) {
  editMode = Boolean(nextValue && flowchartState.config.allow_drag);
  editModeToggle.checked = editMode;
  editModeToggle.disabled = !flowchartState.config.allow_drag;

  if (!cy) {
    return;
  }

  cy.autoungrabify(!editMode);
  cy.nodes().forEach((node) => {
    if (editMode) {
      node.unlock();
      node.grabify();
    } else {
      node.ungrabify();
      node.lock();
    }
  });
}

function applyGraphStyle() {
  cy.style([
    {
      selector: 'node',
      style: {
        'background-color': 'data(color)',
        'border-color': '#dbeafe',
        'border-width': 2,
        'color': '#f8fafc',
        'font-size': flowchartState.config.font_sizes.block_title,
        'font-weight': 700,
        'height': 62,
        'label': 'data(label)',
        'shape': 'round-rectangle',
        'text-halign': 'center',
        'text-max-width': 148,
        'text-valign': 'center',
        'text-wrap': 'wrap',
        'width': 168,
      },
    },
    {
      selector: 'edge',
      style: {
        'arrow-scale': 1,
        'color': '#cbd5e1',
        'curve-style': 'bezier',
        'font-size': 10,
        'label': flowchartState.config.show_connection_labels ? 'data(label)' : '',
        'line-color': 'data(color)',
        'target-arrow-color': 'data(color)',
        'target-arrow-shape': 'triangle',
        'text-background-color': '#0f172a',
        'text-background-opacity': 0.9,
        'text-background-padding': 3,
        'text-rotation': 'autorotate',
        'width': 2,
      },
    },
    {
      selector: 'node:selected',
      style: {
        'border-color': '#f8fafc',
        'border-width': 4,
      },
    },
    {
      selector: 'edge:selected',
      style: {
        'line-color': '#f8fafc',
        'target-arrow-color': '#f8fafc',
        'width': 3,
      },
    },
  ]).update();
}

function renderGraph() {
  cy.elements().remove();
  cy.add(graphElements());
  cy.layout({
    name: 'preset',
    fit: false,
  }).run();
  applyGraphStyle();
  applyViewport();
  setEditMode(flowchartState.config.edit_mode_enabled);
  updateStatusBar();
}

function renderEmptyDetails(message = 'No block selected.') {
  selectionDetailsElement.className = 'empty-state';
  selectionDetailsElement.innerHTML = escapeHtml(message);
}

function detailRows(block) {
  const rows = [
    ['Name', block.name],
    ['Type', formatType(block.type)],
    ['ID', block.id],
    ['Category', block.category],
    ['Enabled', block.enabled ? 'true' : 'false'],
    ['Description', block.description],
  ];

  if (block.ros_topic) {
    rows.push(['ROS Topic', block.ros_topic]);
  }
  if (block.message_type) {
    rows.push(['Message Type', block.message_type]);
  }
  if (block.ros_node) {
    rows.push(['ROS Node', block.ros_node]);
  }

  return rows.filter(([, value]) => value !== undefined && value !== null && value !== '');
}

function renderRows(rows) {
  return rows.map(([label, value]) => `
    <div class="detail-row">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
    </div>
  `).join('');
}

function renderControls(controls) {
  if (!Array.isArray(controls) || controls.length === 0) {
    return '<div class="subtle-text">No commands configured.</div>';
  }

  return controls.map((control, index) => {
    const commandName = escapeHtml(control.name || '');
    const label = escapeHtml(control.label || control.name || `Command ${index + 1}`);

    if (control.type === 'number') {
      const value = control.default ?? control.min ?? 0;
      return `
        <div class="command-row">
          <label for="commandInput${index}">${label}</label>
          <div class="command-inline">
            <input
              id="commandInput${index}"
              type="number"
              value="${escapeHtml(value)}"
              min="${escapeHtml(control.min ?? '')}"
              max="${escapeHtml(control.max ?? '')}"
              step="${escapeHtml(control.step ?? 1)}"
              data-command-input="${index}"
            >
            <button type="button" data-command-index="${index}" data-command-type="number">
              Send
            </button>
          </div>
        </div>
      `;
    }

    return `
      <button
        class="command-button"
        type="button"
        data-command-index="${index}"
        data-command-type="button"
        title="${commandName}"
      >
        ${label}
      </button>
    `;
  }).join('');
}

function renderMedia(block, state) {
  if (!block || block.type !== 'camera') {
    return '';
  }

  const media = state?.data?.media || block.media || {};
  return `
    <section class="detail-section">
      <h3>Media</h3>
      <div class="media-placeholder">
        <span>Camera Placeholder</span>
        <strong>${escapeHtml(media.topic || 'No topic')}</strong>
      </div>
    </section>
  `;
}

function renderLogs(logs) {
  if (!logs) {
    return '';
  }

  const lines = Array.isArray(logs.lines) ? logs.lines : [];
  return `
    <section class="detail-section">
      <h3>Logs</h3>
      <pre class="log-box">${escapeHtml(lines.join('\n'))}</pre>
    </section>
  `;
}

function renderCommandResponse(response) {
  if (!response) {
    return '';
  }

  const tone = response.success ? 'success' : 'error';
  return `
    <div class="response-box" data-tone="${tone}">
      ${escapeHtml(response.message || 'Command response received.')}
    </div>
  `;
}

function renderEndpointList(items) {
  if (!Array.isArray(items) || items.length === 0) {
    return '<div class="subtle-text">None detected.</div>';
  }

  return `
    <pre class="data-box compact-box">${prettyJson(items)}</pre>
  `;
}

function renderTopicLatestMessage(topicData) {
  const latestMessage = topicData?.latest_message;
  if (!latestMessage || latestMessage.data === null || latestMessage.data === undefined) {
    return '<div class="subtle-text">No message received yet</div>';
  }

  return `
    <div class="detail-row">
      <span>Received</span>
      <strong>${escapeHtml(latestMessage.received_at || 'unknown')}</strong>
    </div>
    <pre class="data-box">${prettyJson(latestMessage)}</pre>
  `;
}

function renderTopicLiveData() {
  const topicData = selectedTopicData || selectedState?.data || {};
  const publishers = Array.isArray(topicData.publishers) ? topicData.publishers : [];
  const subscribers = Array.isArray(topicData.subscribers) ? topicData.subscribers : [];
  const status = topicData.status || selectedState?.status || topicDataStatus;
  const frequency = Number(topicData.frequency_hz || 0).toFixed(2);
  const age = topicData.message_age_seconds;
  const rows = [
    ['ROS Topic', topicData.ros_topic || selectedBlock?.ros_topic || ''],
    ['Message Type', topicData.message_type || selectedBlock?.message_type || ''],
    ['Status', status],
    ['Publishers', String(publishers.length)],
    ['Subscribers', String(subscribers.length)],
    ['Frequency Hz', frequency],
    ['Last Received', topicData.last_received_at || 'No message received yet'],
    ['Data Age', age === null || age === undefined ? 'unknown' : `${age}s`],
    ['Stale', topicData.is_stale ? 'true' : 'false'],
  ];

  if (topicDataError) {
    rows.push(['Error', topicDataError]);
  }

  return `
    <section class="detail-section">
      <h3>Live Topic</h3>
      <div class="detail-rows topic-live-rows">
        ${renderRows(rows)}
      </div>
    </section>

    <section class="detail-section">
      <h3>Publishers</h3>
      ${renderEndpointList(publishers)}
    </section>

    <section class="detail-section">
      <h3>Subscribers</h3>
      ${renderEndpointList(subscribers)}
    </section>

    <section class="detail-section">
      <h3>Latest Message</h3>
      ${renderTopicLatestMessage(topicData)}
    </section>
  `;
}

function renderTopicPublishForm() {
  const response = topicPublishResponse;
  const tone = response?.success ? 'success' : 'error';
  const messageType = topicPublishDraft.messageType || selectedBlock?.message_type || '';
  const simpleMode = !topicPublishDraft.advanced;
  const simpleHint = isSimpleStdMessage(messageType)
    ? 'Value'
    : 'Value or JSON';

  return `
    <section class="detail-section">
      <h3>Publish</h3>
      <form id="topicPublishForm" class="topic-publish-form">
        <label>
          <span>Topic</span>
          <input
            id="topicPublishTopic"
            type="text"
            value="${escapeHtml(topicPublishDraft.topic)}"
            autocomplete="off"
          >
        </label>
        <label>
          <span>Message Type</span>
          <input
            id="topicPublishMessageType"
            type="text"
            list="messageTypeOptions"
            value="${escapeHtml(messageType)}"
            autocomplete="off"
          >
          <datalist id="messageTypeOptions">
            <option value="std_msgs/Float64"></option>
            <option value="std_msgs/Float32"></option>
            <option value="std_msgs/Int32"></option>
            <option value="std_msgs/Int64"></option>
            <option value="std_msgs/Bool"></option>
            <option value="std_msgs/String"></option>
            <option value="geometry_msgs/Twist"></option>
          </datalist>
        </label>
        <label class="toggle-control inline-toggle" for="topicPublishAdvanced">
          <input
            id="topicPublishAdvanced"
            type="checkbox"
            ${topicPublishDraft.advanced ? 'checked' : ''}
          >
          <span>Advanced JSON</span>
        </label>
        <label>
          <span>${escapeHtml(simpleMode ? simpleHint : 'JSON Payload')}</span>
          ${simpleMode ? `
            <input
              id="topicPublishValue"
              type="text"
              value="${escapeHtml(topicPublishDraft.value)}"
              autocomplete="off"
            >
          ` : `
            <textarea id="topicPublishJson" rows="8">${escapeHtml(topicPublishDraft.jsonValue)}</textarea>
          `}
        </label>
        <button type="submit">Publish</button>
      </form>
      ${response ? `
        <div class="response-box" data-tone="${tone}">
          ${escapeHtml(response.message || 'Publish response received.')}
        </div>
      ` : ''}
    </section>
  `;
}

function captureFocusedField() {
  const element = document.activeElement;
  if (!element?.id || !selectionDetailsElement.contains(element)) {
    return null;
  }

  return {
    id: element.id,
    start: typeof element.selectionStart === 'number' ? element.selectionStart : null,
    end: typeof element.selectionEnd === 'number' ? element.selectionEnd : null,
  };
}

function restoreFocusedField(focusedField) {
  if (!focusedField) {
    return;
  }

  const element = document.getElementById(focusedField.id);
  if (!element) {
    return;
  }

  try {
    element.focus({ preventScroll: true });
  } catch (error) {
    element.focus();
  }
  if (
    focusedField.start !== null
    && focusedField.end !== null
    && typeof element.setSelectionRange === 'function'
  ) {
    element.setSelectionRange(focusedField.start, focusedField.end);
  }
}

function renderBlockDetails() {
  if (!selectedBlock) {
    renderEmptyDetails();
    return;
  }

  const controls = selectedState?.controls || selectedBlock.commands || [];
  const status = selectedTopicData?.status || selectedState?.status || 'loading';
  const topicBlock = isTopicBlock(selectedBlock);
  const focusedField = captureFocusedField();

  selectionDetailsElement.className = 'details-card';
  selectionDetailsElement.innerHTML = `
    <div class="details-header">
      <div>
        <span class="type-chip">${escapeHtml(formatType(selectedBlock.type))}</span>
        <h2>${escapeHtml(selectedBlock.name)}</h2>
      </div>
      <span class="status-pill">${escapeHtml(status)}</span>
    </div>

    <div class="detail-rows">
      ${renderRows(detailRows(selectedBlock))}
    </div>

    <section class="detail-section">
      <h3>Status</h3>
      <pre class="data-box">${prettyJson(selectedState?.status_detail || {})}</pre>
    </section>

    ${topicBlock ? renderTopicLiveData() : `
      <section class="detail-section">
        <h3>Data</h3>
        <pre class="data-box">${prettyJson(selectedState?.data || {})}</pre>
      </section>
    `}

    ${renderMedia(selectedBlock, selectedState)}

    ${topicBlock ? renderTopicPublishForm() : `
      <section class="detail-section">
        <h3>Controls</h3>
        <div class="commands-grid">
          ${renderControls(controls)}
        </div>
        ${renderCommandResponse(commandResponse)}
      </section>
    `}

    <section class="detail-section">
      <button id="blockLogsButton" class="secondary-button" type="button">Logs</button>
    </section>

    ${renderLogs(selectedLogs)}
  `;
  restoreFocusedField(focusedField);
}

function resetTopicPublishDraft(block) {
  topicPublishDraft = {
    ...topicPublishDraft,
    topic: block?.ros_topic || block?.id || '',
    messageType: block?.message_type || '',
    value: '',
    advanced: false,
  };
  topicPublishResponse = null;
}

function stopTopicPolling() {
  if (topicPollTimer) {
    window.clearInterval(topicPollTimer);
    topicPollTimer = null;
  }
  topicPollInFlight = false;
}

function shouldPollSelectedTopic() {
  return activePanel === 'block' && selectedBlockId && isTopicBlock(selectedBlock);
}

function syncTopicPolling() {
  if (!shouldPollSelectedTopic()) {
    stopTopicPolling();
    return;
  }

  if (topicPollTimer) {
    return;
  }

  refreshSelectedTopicData();
  topicPollTimer = window.setInterval(refreshSelectedTopicData, 400);
}

async function refreshSelectedTopicData() {
  if (!shouldPollSelectedTopic() || topicPollInFlight) {
    return;
  }

  const blockId = selectedBlockId;
  topicPollInFlight = true;
  topicDataStatus = selectedTopicData ? 'refreshing' : 'loading';
  topicDataError = '';

  try {
    const response = await fetch(`${blockApiPath(blockId)}/data`, {
      cache: 'no-store',
    });

    if (selectedBlockId !== blockId) {
      return;
    }

    if (!response.ok) {
      throw new Error(`Topic data request failed with ${response.status}`);
    }

    selectedTopicData = await response.json();
    topicDataStatus = 'ready';
    selectedState = {
      ...(selectedState || {}),
      status: selectedTopicData.status || selectedState?.status,
      data: selectedTopicData,
    };
    renderBlockDetails();
  } catch (error) {
    topicDataStatus = 'error';
    topicDataError = error.message || 'Topic data refresh failed.';
    renderBlockDetails();
  } finally {
    topicPollInFlight = false;
  }
}

async function fetchSelectedBlock(blockId) {
  stopTopicPolling();
  selectedBlockId = blockId;
  selectedBlock = null;
  selectedState = null;
  selectedLogs = null;
  selectedTopicData = null;
  commandResponse = null;
  topicPublishResponse = null;
  topicDataStatus = 'idle';
  topicDataError = '';
  setPanel('block');
  renderEmptyDetails('Loading block.');
  updateStatusBar();

  const [blockResponse, stateResponse] = await Promise.all([
    fetch(blockApiPath(blockId), { cache: 'no-store' }),
    fetch(`${blockApiPath(blockId)}/state`, { cache: 'no-store' }),
  ]);

  if (!blockResponse.ok || !stateResponse.ok) {
    throw new Error('Block request failed.');
  }

  selectedBlock = await blockResponse.json();
  selectedState = await stateResponse.json();
  if (isTopicBlock(selectedBlock)) {
    selectedTopicData = selectedState.data || null;
    resetTopicPublishDraft(selectedBlock);
    topicDataStatus = 'loading';
    syncTopicPolling();
  }
  renderBlockDetails();
  updateStatusBar();
}

async function refreshSelectedState() {
  if (!selectedBlockId || !selectedBlock) {
    return;
  }

  try {
    const response = await fetch(`${blockApiPath(selectedBlockId)}/state`, {
      cache: 'no-store',
    });
    if (!response.ok) {
      return;
    }
    selectedState = await response.json();
    renderBlockDetails();
  } catch (error) {
    setSaveStatus('State refresh failed', 'error');
  }
}

async function sendSelectedCommand(index) {
  const controls = selectedState?.controls || selectedBlock?.commands || [];
  const definition = controls[index];
  if (!selectedBlockId || !definition) {
    return;
  }

  let value = definition.value ?? definition.default ?? null;
  if (definition.type === 'number') {
    const input = document.querySelector(`[data-command-input="${index}"]`);
    value = input ? Number(input.value) : value;
  }

  const response = await fetch(`${blockApiPath(selectedBlockId)}/command`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      command: definition.name,
      value,
    }),
  });

  commandResponse = await response.json();
  if (!response.ok) {
    commandResponse.success = false;
  }
  renderBlockDetails();
}

function updateTopicPublishDraftFromForm() {
  const topicInput = document.getElementById('topicPublishTopic');
  const messageTypeInput = document.getElementById('topicPublishMessageType');
  const valueInput = document.getElementById('topicPublishValue');
  const advancedInput = document.getElementById('topicPublishAdvanced');
  const jsonInput = document.getElementById('topicPublishJson');

  if (topicInput) {
    topicPublishDraft.topic = topicInput.value;
  }
  if (messageTypeInput) {
    topicPublishDraft.messageType = messageTypeInput.value;
  }
  if (valueInput) {
    topicPublishDraft.value = valueInput.value;
  }
  if (advancedInput) {
    topicPublishDraft.advanced = advancedInput.checked;
  }
  if (jsonInput) {
    topicPublishDraft.jsonValue = jsonInput.value;
  }
}

async function publishTopicFromDraft() {
  updateTopicPublishDraftFromForm();

  try {
    const value = parsePublishValue(
      topicPublishDraft.messageType,
      topicPublishDraft.advanced ? topicPublishDraft.jsonValue : topicPublishDraft.value,
      topicPublishDraft.advanced,
    );

    const response = await fetch('/api/topic/publish', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        topic: topicPublishDraft.topic,
        message_type: topicPublishDraft.messageType,
        value,
      }),
    });

    topicPublishResponse = await response.json();
    if (!response.ok) {
      topicPublishResponse.success = false;
    }
  } catch (error) {
    topicPublishResponse = {
      success: false,
      message: error.message || 'Publish failed.',
    };
  }

  renderBlockDetails();
}

async function loadSelectedLogs() {
  if (!selectedBlockId) {
    return;
  }

  const response = await fetch(`${blockApiPath(selectedBlockId)}/logs`, {
    cache: 'no-store',
  });
  if (!response.ok) {
    return;
  }
  selectedLogs = await response.json();
  renderBlockDetails();
}

function renderServices() {
  if (!services.length) {
    servicesListElement.innerHTML = '<div class="empty-state">No services configured.</div>';
    return;
  }

  servicesListElement.innerHTML = services.map((service) => {
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

async function loadServices() {
  const response = await fetch('/api/services', { cache: 'no-store' });
  if (!response.ok) {
    throw new Error('Services request failed.');
  }
  const payload = await response.json();
  services = Array.isArray(payload.services) ? payload.services : [];
  renderServices();
}

async function callServiceAction(serviceId, action) {
  if (action === 'logs') {
    const response = await fetch(`/api/services/${encodeURIComponent(serviceId)}/logs`, {
      cache: 'no-store',
    });
    if (response.ok) {
      serviceLogs[serviceId] = await response.json();
      renderServices();
    }
    return;
  }

  const response = await fetch(`/api/services/${encodeURIComponent(serviceId)}/${action}`, {
    method: 'POST',
  });
  if (!response.ok) {
    setSaveStatus('Service action failed', 'error');
    return;
  }

  await loadServices();
  setSaveStatus(`Service ${action} accepted`, 'success');
}

async function loadFlowchart() {
  const response = await fetch('/api/flowchart', { cache: 'no-store' });
  if (!response.ok) {
    throw new Error(`Flowchart request failed with ${response.status}`);
  }

  flowchartState = mergedFlowchart(await response.json());
  projectNameElement.textContent = flowchartState.config.project_name;
  document.title = flowchartState.config.project_name;
  saveLayoutButton.disabled = !flowchartState.config.allow_save_layout;
  applyTheme();
  renderGraph();

  if (selectedBlockId) {
    const selectedNode = cy.getElementById(selectedBlockId);
    if (selectedNode.length) {
      selectedNode.select();
      await fetchSelectedBlock(selectedBlockId);
    } else {
      stopTopicPolling();
      selectedBlockId = null;
      selectedBlock = null;
      selectedState = null;
      selectedTopicData = null;
      renderEmptyDetails();
    }
  }
}

async function saveLayout() {
  if (!cy || !flowchartState.config.allow_save_layout) {
    return;
  }

  saveLayoutButton.disabled = true;
  setSaveStatus('Saving', 'neutral');

  const payload = {
    version: flowchartState.layout.version || 1,
    viewport: currentViewport(),
    positions: currentPositions(),
    groups: flowchartState.layout.groups || [],
  };

  try {
    const response = await fetch('/api/layout', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`Layout save failed with ${response.status}`);
    }

    const saved = await response.json();
    flowchartState.layout = mergedFlowchart({
      ...flowchartState,
      layout: saved.layout,
    }).layout;
    setSaveStatus('Saved', 'success');
  } catch (error) {
    setSaveStatus('Save failed', 'error');
  } finally {
    saveLayoutButton.disabled = !flowchartState.config.allow_save_layout;
  }
}

async function reloadDashboard() {
  setSaveStatus('Loading', 'neutral');
  try {
    await loadFlowchart();
    await loadServices();
    setSaveStatus('Ready', 'neutral');
  } catch (error) {
    setSaveStatus('Load failed', 'error');
  }
}

function resetRefreshTimer() {
  if (refreshTimer) {
    window.clearInterval(refreshTimer);
  }

  const interval = Number(flowchartState.config.refresh_rate_ms) || 1000;
  refreshTimer = window.setInterval(refreshSelectedState, interval);
}

function initializeGraph() {
  cy = cytoscape({
    container: document.getElementById('cy'),
    elements: [],
    boxSelectionEnabled: false,
    minZoom: 0.2,
    maxZoom: 3,
    wheelSensitivity: 0.18,
  });

  cy.on('tap', 'node', async (event) => {
    try {
      await fetchSelectedBlock(event.target.id());
    } catch (error) {
      renderEmptyDetails('Block load failed.');
      setSaveStatus('Block load failed', 'error');
    }
  });

  cy.on('tap', (event) => {
    if (event.target === cy) {
      stopTopicPolling();
      selectedBlockId = null;
      selectedBlock = null;
      selectedState = null;
      selectedLogs = null;
      selectedTopicData = null;
      commandResponse = null;
      topicPublishResponse = null;
      cy.elements().unselect();
      renderEmptyDetails();
      updateStatusBar();
    }
  });
}

function bindEvents() {
  saveLayoutButton.addEventListener('click', saveLayout);
  reloadButton.addEventListener('click', reloadDashboard);
  editModeToggle.addEventListener('change', () => {
    setEditMode(editModeToggle.checked);
  });

  document.querySelectorAll('.tab-button').forEach((button) => {
    button.addEventListener('click', () => setPanel(button.dataset.panel));
  });

  selectionDetailsElement.addEventListener('click', async (event) => {
    const commandButton = event.target.closest('[data-command-index]');
    if (commandButton) {
      await sendSelectedCommand(Number(commandButton.dataset.commandIndex));
      return;
    }

    if (event.target.closest('#blockLogsButton')) {
      await loadSelectedLogs();
    }
  });

  selectionDetailsElement.addEventListener('submit', async (event) => {
    if (event.target.id !== 'topicPublishForm') {
      return;
    }

    event.preventDefault();
    await publishTopicFromDraft();
  });

  selectionDetailsElement.addEventListener('input', (event) => {
    if (!event.target.closest('#topicPublishForm')) {
      return;
    }

    updateTopicPublishDraftFromForm();
  });

  selectionDetailsElement.addEventListener('change', (event) => {
    if (event.target.id !== 'topicPublishAdvanced') {
      return;
    }

    updateTopicPublishDraftFromForm();
    renderBlockDetails();
  });

  servicesListElement.addEventListener('click', async (event) => {
    const actionButton = event.target.closest('[data-service-action]');
    if (!actionButton) {
      return;
    }
    await callServiceAction(
      actionButton.dataset.serviceId,
      actionButton.dataset.serviceAction,
    );
  });
}

async function initializeDashboard() {
  initializeGraph();
  bindEvents();
  renderEmptyDetails();
  await reloadDashboard();
  resetRefreshTimer();
}

window.addEventListener('DOMContentLoaded', initializeDashboard);
