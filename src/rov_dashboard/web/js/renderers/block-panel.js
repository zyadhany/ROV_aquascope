import {
  escapeHtml,
  formatType,
  isSimpleStdMessage,
  isTopicBlock,
  prettyJson,
} from '../utils.js';

function renderRows(rows) {
  return rows.map(([label, value]) => `
    <div class="detail-row">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
    </div>
  `).join('');
}

function renderFieldRow(label, attribute, field, value) {
  return `
    <div class="detail-row">
      <span>${escapeHtml(label)}</span>
      <strong ${attribute}="${escapeHtml(field)}">${escapeHtml(value)}</strong>
    </div>
  `;
}

function formatValue(value, unit = '') {
  if (value === null || value === undefined || value === '') {
    return 'Waiting for data';
  }

  const formatted = typeof value === 'object'
    ? JSON.stringify(value)
    : String(value);
  return unit ? `${formatted} ${unit}` : formatted;
}

function formatSourceValue(source) {
  if (source.label) {
    return source.value === null || source.value === undefined
      ? source.label
      : `${source.label} (${source.value})`;
  }

  return formatValue(source.value, source.unit);
}

function formatSourceMeta(source) {
  const parts = [
    source.topic,
    source.message_type,
    source.frequency_hz !== undefined ? `${Number(source.frequency_hz || 0).toFixed(2)} Hz` : '',
  ].filter(Boolean);

  return parts.join(' | ');
}

function getValueEntries(snapshot) {
  const values = snapshot.selectedState?.data?.values;
  if (!values || typeof values !== 'object' || Array.isArray(values)) {
    return [];
  }

  return Object.entries(values).map(([name, source]) => ({
    name,
    source: source && typeof source === 'object' ? source : { value: source },
  }));
}

function detailRows(block) {
  const rows = [
    // ['Name', block.name],
    // ['Type', formatType(block.type)],
    // ['ID', block.id],
    // ['Category', block.category],
    // ['Enabled', block.enabled ? 'true' : 'false'],
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
  const rows = [
    ['Source', media.topic || media.stream_url || 'Not configured'],
    ['Status', media.status || (media.available ? 'configured' : 'not_configured')],
    ['Message Type', media.message_type || ''],
    ['Frequency Hz', media.frequency_hz === undefined ? '' : Number(media.frequency_hz || 0).toFixed(2)],
    ['Last Frame', media.last_received_at || 'No frame received yet'],
  ];

  return `
    <section class="detail-section">
      <h3>Media</h3>
      <div class="media-viewer">
        <strong>${escapeHtml(media.message || 'Camera media source configured.')}</strong>
        <div class="detail-rows compact-rows">
          ${renderRows(rows.filter(([, value]) => value !== undefined && value !== null && value !== ''))}
        </div>
      </div>
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

function renderCommandResponseSlot(response) {
  return `
    <div data-command-response>
      ${renderCommandResponse(response)}
    </div>
  `;
}

function renderEndpointList(items) {
  if (!Array.isArray(items) || items.length === 0) {
    return '<div class="subtle-text">None detected.</div>';
  }

  return `<pre class="data-box compact-box">${prettyJson(items)}</pre>`;
}

function renderTopicLatestMessage(topicData) {
  const latestMessage = topicData?.latest_message;
  if (!latestMessage || latestMessage.data === null || latestMessage.data === undefined) {
    return '<div class="subtle-text">No message received yet</div>';
  }

  return `
    <pre class="data-box">${prettyJson(latestMessage.data)}</pre>
  `;
}

function getTopicLiveValues(snapshot) {
  const topicData = snapshot.selectedTopicData || snapshot.selectedState?.data || {};
  const publishers = Array.isArray(topicData.publishers)
    ? topicData.publishers
        .map((publisher) => publisher.node_name)
        .filter(Boolean)
    : [];

  const subscribers = Array.isArray(topicData.subscribers)
    ? topicData.subscribers
        .map((subscriber) => subscriber.node_name)
        .filter(Boolean)
    : [];
  const status = topicData.status || snapshot.selectedState?.status || snapshot.topicDataStatus;
  const frequency = Number(topicData.frequency_hz || 0).toFixed(2);
  const age = topicData.message_age_seconds;

  return {
    latestMessageHtml: renderTopicLatestMessage(topicData),
    status,
    publishersCount: String(publishers.length),
    subscribersCount: String(subscribers.length),
    frequency,
    lastReceived: topicData.last_received_at || 'No message received yet',
    dataAge: age === null || age === undefined ? 'unknown' : `${age}s`,
    stale: topicData.is_stale ? 'true' : 'false',
    error: snapshot.topicDataError || '',
    publishersHtml: renderEndpointList(publishers),
    subscribersHtml: renderEndpointList(subscribers),
  };
}

function renderTopicValueRow(label, field) {
  return `
    <div class="detail-row">
      <span>${escapeHtml(label)}</span>
      <strong data-topic-field="${escapeHtml(field)}"></strong>
    </div>
  `;
}

function renderTopicLiveData(snapshot) {
  const values = getTopicLiveValues(snapshot);

  return `
    <section class="detail-section">
      <h3>Latest Message</h3>
      <div data-topic-field="latestMessageHtml">
        ${values.latestMessageHtml}
      </div>
    </section>

    <section class="detail-section">
      <h3>Live Topic</h3>
      <div class="detail-rows topic-live-rows">
        ${renderTopicValueRow('Status', 'status')}
        ${renderTopicValueRow('Publishers', 'publishersCount')}
        ${renderTopicValueRow('Subscribers', 'subscribersCount')}
        ${renderTopicValueRow('Frequency Hz', 'frequency')}
        ${renderTopicValueRow('Last Received', 'lastReceived')}
        ${renderTopicValueRow('Data Age', 'dataAge')}
        ${renderTopicValueRow('Error', 'error')}
      </div>
    </section>

    <section class="detail-section">
      <h3>Publishers</h3>
      <div data-topic-field="publishersHtml">
        ${values.publishersHtml}
      </div>
    </section>

    <section class="detail-section">
      <h3>Subscribers</h3>
      <div data-topic-field="subscribersHtml">
        ${values.subscribersHtml}
      </div>
    </section>

  `;
}

function renderStateData(snapshot) {
  if (snapshot.selectedBlock?.type === 'node') {
    return renderNodeData(snapshot);
  }

  const entries = getValueEntries(snapshot);
  const statusDetail = snapshot.selectedState?.status_detail || {};

  return `
    <section class="detail-section">
      <h3>Telemetry</h3>
      ${entries.length ? `
        <div class="metric-list">
          ${entries.map(({ name, source }, index) => `
            <div class="metric-row">
              <div>
                <span>${escapeHtml(name)}</span>
                <small data-source-meta="${index}">${escapeHtml(formatSourceMeta(source))}</small>
              </div>
              <strong data-source-value="${index}">${escapeHtml(formatSourceValue(source))}</strong>
              <em data-source-status="${index}">${escapeHtml(source.status || 'unknown')}</em>
            </div>
          `).join('')}
        </div>
      ` : '<div class="subtle-text">No telemetry sources configured.</div>'}
    </section>

    <section class="detail-section">
      <h3>Runtime</h3>
      <div class="detail-rows compact-rows">
        ${renderFieldRow('State', 'data-runtime-field', 'state', snapshot.selectedState?.status || statusDetail.state || 'unknown')}
        ${renderFieldRow('Message', 'data-runtime-field', 'message', statusDetail.message || '')}
        ${renderFieldRow('Last Update', 'data-runtime-field', 'lastUpdate', snapshot.selectedState?.last_update || statusDetail.last_update || '')}
      </div>
    </section>
  `;
}

function renderNodeData(snapshot) {
  const data = snapshot.selectedState?.data || {};
  const publishers = Array.isArray(data.publishers) ? data.publishers : [];
  const subscribers = Array.isArray(data.subscribers) ? data.subscribers : [];
  const services = Array.isArray(data.services) ? data.services : [];

  return `
    <section class="detail-section">
      <h3>ROS Node</h3>
      <div class="detail-rows compact-rows">
        ${renderFieldRow('Status', 'data-node-field', 'status', data.status || snapshot.selectedState?.status || 'unknown')}
        ${renderFieldRow('Namespace', 'data-node-field', 'namespace', data.node_namespace || '')}
        ${renderFieldRow('Publishers', 'data-node-field', 'publishersCount', String(publishers.length))}
        ${renderFieldRow('Subscribers', 'data-node-field', 'subscribersCount', String(subscribers.length))}
        ${renderFieldRow('Services', 'data-node-field', 'servicesCount', String(services.length))}
      </div>
    </section>

    <section class="detail-section">
      <h3>Publishers</h3>
      <div data-node-field="publishersHtml">${renderEndpointList(publishers)}</div>
    </section>

    <section class="detail-section">
      <h3>Subscribers</h3>
      <div data-node-field="subscribersHtml">${renderEndpointList(subscribers)}</div>
    </section>

    <section class="detail-section">
      <h3>Services</h3>
      <div data-node-field="servicesHtml">${renderEndpointList(services)}</div>
    </section>
  `;
}

function renderDataSection(snapshot) {
  return isTopicBlock(snapshot.selectedBlock)
    ? renderTopicLiveData(snapshot)
    : renderStateData(snapshot);
}

function renderTopicPublishForm(snapshot) {
  const messageType = (
    snapshot.topicPublishDraft.messageType || snapshot.selectedBlock?.message_type || ''
  );
  const simpleMode = !snapshot.topicPublishDraft.advanced;
  const simpleHint = isSimpleStdMessage(messageType) ? 'Value' : 'Value or JSON';

  return `
    <section class="detail-section">
      <h3>Publish</h3>
      <form id="topicPublishForm" class="topic-publish-form">
        <label>
          <span>Topic</span>
          <input
            id="topicPublishTopic"
            type="text"
            value="${escapeHtml(snapshot.topicPublishDraft.topic)}"
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
            ${snapshot.topicPublishDraft.advanced ? 'checked' : ''}
          >
          <span>Advanced JSON</span>
        </label>
        <label>
          <span>${escapeHtml(simpleMode ? simpleHint : 'JSON Payload')}</span>
          ${simpleMode ? `
            <input
              id="topicPublishValue"
              type="text"
              value="${escapeHtml(snapshot.topicPublishDraft.value)}"
              autocomplete="off"
            >
          ` : `
            <textarea id="topicPublishJson" rows="8">${escapeHtml(snapshot.topicPublishDraft.jsonValue)}</textarea>
          `}
        </label>
        <button type="submit">Publish</button>
      </form>
      <div data-topic-publish-response>
        ${renderTopicPublishResponse(snapshot.topicPublishResponse)}
      </div>
    </section>
  `;
}

function renderTopicPublishResponse(response) {
  if (!response) {
    return '';
  }

  const tone = response.success ? 'success' : 'error';
  return `
    <div class="response-box" data-tone="${tone}">
      ${escapeHtml(response.message || 'Publish response received.')}
    </div>
  `;
}

function renderControlsSection(controls, response) {
  return `
    <section class="detail-section">
      <h3>Controls</h3>
      <div class="commands-grid">
        ${renderControls(controls)}
      </div>
      ${renderCommandResponseSlot(response)}
    </section>
  `;
}

function captureFocusedField(container) {
  const element = document.activeElement;
  if (!element?.id || !container.contains(element)) {
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

function setElementHtml(element, html) {
  if (!element || element.innerHTML === html) {
    return;
  }

  element.innerHTML = html;
}

function setElementText(element, value) {
  if (!element) {
    return;
  }

  const nextValue = String(value ?? '');
  if (element.textContent === nextValue) {
    return;
  }

  element.textContent = nextValue;
}

function getTopicStatus(snapshot) {
  return snapshot.selectedTopicData?.status || snapshot.selectedState?.status || 'loading';
}

function getControlsSignature(controls) {
  return controls.map((control, index) => [
    index,
    control.name || '',
    control.label || '',
    control.type || '',
    control.min ?? '',
    control.max ?? '',
    control.step ?? '',
  ].join(':')).join('|');
}

function getDataSignature(snapshot) {
  if (isTopicBlock(snapshot.selectedBlock)) {
    return 'topic';
  }

  return getValueEntries(snapshot)
    .map(({ name }, index) => `${index}:${name}`)
    .join('|');
}

function getRenderKey(snapshot, controls) {
  return [
    snapshot.selectedBlock?.id || '',
    snapshot.selectedBlock?.type || '',
    isTopicBlock(snapshot.selectedBlock) ? 'topic' : 'generic',
    snapshot.topicPublishDraft.advanced ? 'advanced' : 'simple',
    getDataSignature(snapshot),
    getControlsSignature(controls),
  ].join('::');
}

function updateBlockDetails(container, snapshot) {
  const statusElement = container.querySelector('[data-detail-status]');
  if (statusElement) {
    statusElement.textContent = getTopicStatus(snapshot);
  }

  if (isTopicBlock(snapshot.selectedBlock)) {
    const values = getTopicLiveValues(snapshot);
    Object.entries(values).forEach(([field, value]) => {
      const element = container.querySelector(`[data-topic-field="${field}"]`);
      if (!element) {
        return;
      }

      if (field.endsWith('Html')) {
        setElementHtml(element, value);
        return;
      }

      setElementText(element, value);
    });

    setElementHtml(
      container.querySelector('[data-topic-publish-response]'),
      renderTopicPublishResponse(snapshot.topicPublishResponse),
    );
  } else {
    getValueEntries(snapshot).forEach(({ source }, index) => {
      setElementText(
        container.querySelector(`[data-source-value="${index}"]`),
        formatSourceValue(source),
      );
      setElementText(
        container.querySelector(`[data-source-status="${index}"]`),
        source.status || 'unknown',
      );
      setElementText(
        container.querySelector(`[data-source-meta="${index}"]`),
        formatSourceMeta(source),
      );
    });

    const statusDetail = snapshot.selectedState?.status_detail || {};
    setElementText(
      container.querySelector('[data-runtime-field="state"]'),
      snapshot.selectedState?.status || statusDetail.state || 'unknown',
    );
    setElementText(
      container.querySelector('[data-runtime-field="message"]'),
      statusDetail.message || '',
    );
    setElementText(
      container.querySelector('[data-runtime-field="lastUpdate"]'),
      snapshot.selectedState?.last_update || statusDetail.last_update || '',
    );

    const nodeData = snapshot.selectedState?.data || {};
    const nodePublishers = Array.isArray(nodeData.publishers) ? nodeData.publishers : [];
    const nodeSubscribers = Array.isArray(nodeData.subscribers) ? nodeData.subscribers : [];
    const nodeServices = Array.isArray(nodeData.services) ? nodeData.services : [];
    setElementText(
      container.querySelector('[data-node-field="status"]'),
      nodeData.status || snapshot.selectedState?.status || 'unknown',
    );
    setElementText(
      container.querySelector('[data-node-field="namespace"]'),
      nodeData.node_namespace || '',
    );
    setElementText(
      container.querySelector('[data-node-field="publishersCount"]'),
      String(nodePublishers.length),
    );
    setElementText(
      container.querySelector('[data-node-field="subscribersCount"]'),
      String(nodeSubscribers.length),
    );
    setElementText(
      container.querySelector('[data-node-field="servicesCount"]'),
      String(nodeServices.length),
    );
    setElementHtml(
      container.querySelector('[data-node-field="publishersHtml"]'),
      renderEndpointList(nodePublishers),
    );
    setElementHtml(
      container.querySelector('[data-node-field="subscribersHtml"]'),
      renderEndpointList(nodeSubscribers),
    );
    setElementHtml(
      container.querySelector('[data-node-field="servicesHtml"]'),
      renderEndpointList(nodeServices),
    );

    setElementHtml(
      container.querySelector('[data-command-response]'),
      renderCommandResponse(snapshot.commandResponse),
    );
  }

  setElementHtml(
    container.querySelector('[data-detail-media]'),
    renderMedia(snapshot.selectedBlock, snapshot.selectedState),
  );
}

export function renderEmptyDetails(container, message = 'No block selected.') {
  container.className = 'empty-state';
  delete container.dataset.renderKey;
  container.innerHTML = escapeHtml(message);
}

export function renderBlockDetails(container, snapshot) {
  if (!snapshot.selectedBlock) {
    renderEmptyDetails(container);
    return;
  }

  const controls = snapshot.selectedState?.controls || snapshot.selectedBlock.commands || [];
  const status = getTopicStatus(snapshot);
  const topicBlock = isTopicBlock(snapshot.selectedBlock);
  const renderKey = getRenderKey(snapshot, controls);

  if (container.dataset.renderKey === renderKey) {
    updateBlockDetails(container, snapshot);
    return;
  }

  const focusedField = captureFocusedField(container);

  container.className = 'details-card';
  container.dataset.renderKey = renderKey;
  container.innerHTML = `
    <div class="details-header">
      <div>
        <span class="type-chip">${escapeHtml(formatType(snapshot.selectedBlock.type))}</span>
        <h2>${escapeHtml(snapshot.selectedBlock.name)}</h2>
      </div>
      <span class="status-pill" data-detail-status>${escapeHtml(status)}</span>
    </div>

    <div class="detail-rows">
      ${renderRows(detailRows(snapshot.selectedBlock))}
    </div>

    <div data-detail-data>
      ${renderDataSection(snapshot)}
    </div>

    <div data-detail-media>
      ${renderMedia(snapshot.selectedBlock, snapshot.selectedState)}
    </div>

    ${topicBlock ? renderTopicPublishForm(snapshot) : renderControlsSection(controls, snapshot.commandResponse)}
  `;
  restoreFocusedField(focusedField);
}
