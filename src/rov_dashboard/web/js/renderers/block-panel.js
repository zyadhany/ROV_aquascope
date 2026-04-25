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

function renderTopicLiveData(snapshot) {
  const topicData = snapshot.selectedTopicData || snapshot.selectedState?.data || {};
  const publishers = Array.isArray(topicData.publishers) ? topicData.publishers : [];
  const subscribers = Array.isArray(topicData.subscribers) ? topicData.subscribers : [];
  const status = topicData.status || snapshot.selectedState?.status || snapshot.topicDataStatus;
  const frequency = Number(topicData.frequency_hz || 0).toFixed(2);
  const age = topicData.message_age_seconds;
  const rows = [
    // ['ROS Topic', topicData.ros_topic || snapshot.selectedBlock?.ros_topic || ''],
    // ['Message Type', topicData.message_type || snapshot.selectedBlock?.message_type || ''],
    ['Status', status],
    ['Publishers', String(publishers.length)],
    ['Subscribers', String(subscribers.length)],
    ['Frequency Hz', frequency],
    ['Last Received', topicData.last_received_at || 'No message received yet'],
    ['Data Age', age === null || age === undefined ? 'unknown' : `${age}s`],
    ['Stale', topicData.is_stale ? 'true' : 'false'],
  ];

  if (snapshot.topicDataError) {
    rows.push(['Error', snapshot.topicDataError]);
  }

  return `
    <section class="detail-section">
      <h3>Latest Message</h3>
      ${renderTopicLatestMessage(topicData)}
    </section>
    
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

  `;
}

function renderTopicPublishForm(snapshot) {
  const response = snapshot.topicPublishResponse;
  const tone = response?.success ? 'success' : 'error';
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
      ${response ? `
        <div class="response-box" data-tone="${tone}">
          ${escapeHtml(response.message || 'Publish response received.')}
        </div>
      ` : ''}
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

export function renderEmptyDetails(container, message = 'No block selected.') {
  container.className = 'empty-state';
  container.innerHTML = escapeHtml(message);
}

export function renderBlockDetails(container, snapshot) {
  if (!snapshot.selectedBlock) {
    renderEmptyDetails(container);
    return;
  }

  const controls = snapshot.selectedState?.controls || snapshot.selectedBlock.commands || [];
  const status = (
    snapshot.selectedTopicData?.status || snapshot.selectedState?.status || 'loading'
  );
  const topicBlock = isTopicBlock(snapshot.selectedBlock);
  const focusedField = captureFocusedField(container);

  container.className = 'details-card';
  container.innerHTML = `
    <div class="details-header">
      <div>
        <span class="type-chip">${escapeHtml(formatType(snapshot.selectedBlock.type))}</span>
        <h2>${escapeHtml(snapshot.selectedBlock.name)}</h2>
      </div>
      <span class="status-pill">${escapeHtml(status)}</span>
    </div>

    <div class="detail-rows">
      ${renderRows(detailRows(snapshot.selectedBlock))}
    </div>

    ${topicBlock ? renderTopicLiveData(snapshot) : `
      <section class="detail-section">
        <h3>Data</h3>
        <pre class="data-box">${prettyJson(snapshot.selectedState?.data || {})}</pre>
      </section>
    `}

    ${renderMedia(snapshot.selectedBlock, snapshot.selectedState)}

    ${topicBlock ? renderTopicPublishForm(snapshot) : `
      <section class="detail-section">
        <h3>Controls</h3>
        <div class="commands-grid">
          ${renderControls(controls)}
        </div>
        ${renderCommandResponse(snapshot.commandResponse)}
      </section>
    `}
  `;
  restoreFocusedField(focusedField);
}
