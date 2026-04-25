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
  return `
    <section class="detail-section">
      <h3>Data</h3>
      <pre class="data-box" data-state-field="dataJson">${prettyJson(snapshot.selectedState?.data || {})}</pre>
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

function getRenderKey(snapshot, controls) {
  return [
    snapshot.selectedBlock?.id || '',
    snapshot.selectedBlock?.type || '',
    isTopicBlock(snapshot.selectedBlock) ? 'topic' : 'generic',
    snapshot.topicPublishDraft.advanced ? 'advanced' : 'simple',
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
    setElementText(
      container.querySelector('[data-state-field="dataJson"]'),
      prettyJson(snapshot.selectedState?.data || {}),
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
