import { DEFAULT_FLOWCHART } from './constants.js';

export function cloneValue(value) {
  return JSON.parse(JSON.stringify(value));
}

export function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

export function formatType(value) {
  return String(value || 'unknown')
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function prettyJson(value) {
  return escapeHtml(JSON.stringify(value ?? {}, null, 2));
}

export function normalizeMessageType(messageType) {
  return String(messageType || '').replace('/msg/', '/');
}

export function isTopicBlock(block) {
  return block?.type === 'topic';
}

export function isNodeBlock(block) {
  return ['node', 'nodes'].includes(block?.type);
}

export function isHardwareBlock(block) {
  return block?.type === 'hardware';
}

export function isSimpleStdMessage(messageType) {
  return [
    'std_msgs/Float64',
    'std_msgs/Float32',
    'std_msgs/Int32',
    'std_msgs/Int64',
    'std_msgs/Bool',
    'std_msgs/String',
  ].includes(normalizeMessageType(messageType));
}

export function parseBool(value) {
  const normalized = String(value).trim().toLowerCase();
  if (['true', '1', 'yes', 'on'].includes(normalized)) {
    return true;
  }
  if (['false', '0', 'no', 'off'].includes(normalized)) {
    return false;
  }
  throw new Error('Bool value must be true or false.');
}

export function parsePublishValue(messageType, valueText, advanced) {
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

export function mergedFlowchart(payload) {
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

export function blockApiPath(blockId) {
  const cleanId = String(blockId || '').replace(/^\/+/, '');
  const encoded = cleanId.split('/').map(encodeURIComponent).join('/');
  return `/api/block/${encoded}`;
}

export function nodeApiPath(nodeName) {
  const cleanName = String(nodeName || '').replace(/^\/+/, '');
  const encoded = cleanName.split('/').map(encodeURIComponent).join('/');
  return `/api/nodes/${encoded}`;
}
