import { DEFAULT_FLOWCHART } from './constants.js';
import { createDomRefs } from './dom.js';
import { renderBlockDetails, renderEmptyDetails } from './renderers/block-panel.js';
import { renderServices } from './renderers/services-panel.js';
import {
  blockApiPath,
  cloneValue,
  formatType,
  isTopicBlock,
  mergedFlowchart,
  parsePublishValue,
} from './utils.js';

export class DashboardApp {
  constructor(dom = createDomRefs()) {
    this.dom = dom;
    this.cy = null;
    this.flowchartState = cloneValue(DEFAULT_FLOWCHART);
    this.selectedBlockId = null;
    this.selectedBlock = null;
    this.selectedState = null;
    this.selectedLogs = null;
    this.selectedTopicData = null;
    this.commandResponse = null;
    this.topicPublishResponse = null;
    this.services = [];
    this.serviceLogs = {};
    this.editMode = true;
    this.refreshTimer = null;
    this.topicPollTimer = null;
    this.topicPollInFlight = false;
    this.topicDataStatus = 'idle';
    this.topicDataError = '';
    this.activePanel = 'block';
    this.topicPublishDraft = {
      topic: '',
      messageType: '',
      value: '',
      advanced: false,
      jsonValue: '{\n  "linear": {\n    "x": 1.0,\n    "y": 0.0,\n    "z": 0.0\n  },\n  "angular": {\n    "x": 0.0,\n    "y": 0.0,\n    "z": 0.5\n  }\n}',
    };
  }

  setPanel(panelName) {
    this.activePanel = panelName;
    this.dom.tabButtons.forEach((button) => {
      button.classList.toggle('active', button.dataset.panel === panelName);
    });
    this.dom.blockPanel.classList.toggle('active', panelName === 'block');
    this.dom.servicesPanel.classList.toggle('active', panelName === 'services');
    this.syncTopicPolling();
  }

  setSaveStatus(message, tone = 'neutral') {
    this.dom.saveStatusElement.textContent = message;
    this.dom.saveStatusElement.dataset.tone = tone;
  }

  updateStatusBar() {
    this.dom.blockCountElement.textContent = String(this.flowchartState.blocks.length);
    this.dom.connectionCountElement.textContent = String(this.flowchartState.connections.length);
    this.dom.selectedBlockLabelElement.textContent = this.selectedBlock ? this.selectedBlock.name : 'None';
  }

  applyTheme() {
    const rootStyle = document.documentElement.style;
    const theme = this.flowchartState.config.theme;
    rootStyle.setProperty('--app-bg', theme.background);
    rootStyle.setProperty('--panel-bg', theme.panel_background);
    rootStyle.setProperty('--text-main', theme.text);
    rootStyle.setProperty('--text-muted', theme.muted_text);
    rootStyle.setProperty('--accent', this.flowchartState.config.colors.interface);
  }

  blockColor(blockType) {
    return this.flowchartState.config.colors[blockType]
      || this.flowchartState.config.colors.subsystem;
  }

  fallbackPosition(index) {
    const column = index % 4;
    const row = Math.floor(index / 4);
    return {
      x: 140 + column * 260,
      y: 130 + row * 170,
    };
  }

  graphElements() {
    const nodes = this.flowchartState.blocks.map((block, index) => ({
      data: {
        ...block,
        label: `${block.name}\n${formatType(block.type)}`,
        color: this.blockColor(block.type),
      },
      position: this.flowchartState.layout.positions[block.id] || this.fallbackPosition(index),
    }));

    const edges = this.flowchartState.connections.map((connection, index) => ({
      data: {
        ...connection,
        id: connection.id || `${connection.from}-${connection.to}-${index}`,
        source: connection.from,
        target: connection.to,
        color: this.flowchartState.config.colors.interface,
      },
    }));

    return [...nodes, ...edges];
  }

  currentPositions() {
    const positions = {};
    if (!this.cy) {
      return positions;
    }

    this.cy.nodes().forEach((node) => {
      positions[node.id()] = {
        x: node.position('x'),
        y: node.position('y'),
      };
    });

    return positions;
  }

  currentViewport() {
    if (!this.cy) {
      return cloneValue(DEFAULT_FLOWCHART.layout.viewport);
    }

    return {
      zoom: this.cy.zoom(),
      pan_x: this.cy.pan().x,
      pan_y: this.cy.pan().y,
    };
  }

  applyViewport() {
    const viewport = this.flowchartState.layout.viewport;
    this.cy.zoom(viewport.zoom ?? 1);
    this.cy.pan({
      x: viewport.pan_x ?? 0,
      y: viewport.pan_y ?? 0,
    });
  }

  setEditMode(nextValue) {
    this.editMode = Boolean(nextValue && this.flowchartState.config.allow_drag);
    this.dom.editModeToggle.checked = this.editMode;
    this.dom.editModeToggle.disabled = !this.flowchartState.config.allow_drag;

    if (!this.cy) {
      return;
    }

    this.cy.autoungrabify(!this.editMode);
    this.cy.nodes().forEach((node) => {
      if (this.editMode) {
        node.unlock();
        node.grabify();
      } else {
        node.ungrabify();
        node.lock();
      }
    });
  }

  applyGraphStyle() {
    this.cy.style([
      {
        selector: 'node',
        style: {
          'background-color': 'data(color)',
          'border-color': '#dbeafe',
          'border-width': 2,
          'color': '#f8fafc',
          'font-size': this.flowchartState.config.font_sizes.block_title,
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
          'label': this.flowchartState.config.show_connection_labels ? 'data(label)' : '',
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

  renderGraph() {
    this.cy.elements().remove();
    this.cy.add(this.graphElements());
    this.cy.layout({
      name: 'preset',
      fit: false,
    }).run();
    this.applyGraphStyle();
    this.applyViewport();
    this.setEditMode(this.flowchartState.config.edit_mode_enabled);
    this.updateStatusBar();
  }

  buildBlockSnapshot() {
    return {
      selectedBlock: this.selectedBlock,
      selectedState: this.selectedState,
      selectedLogs: this.selectedLogs,
      selectedTopicData: this.selectedTopicData,
      commandResponse: this.commandResponse,
      topicPublishResponse: this.topicPublishResponse,
      topicDataStatus: this.topicDataStatus,
      topicDataError: this.topicDataError,
      topicPublishDraft: this.topicPublishDraft,
    };
  }

  renderEmptyDetails(message = 'No block selected.') {
    renderEmptyDetails(this.dom.selectionDetailsElement, message);
  }

  renderBlockDetails() {
    renderBlockDetails(
      this.dom.selectionDetailsElement,
      this.buildBlockSnapshot(),
    );
  }

  renderServices() {
    renderServices(this.dom.servicesListElement, this.services, this.serviceLogs);
  }

  resetTopicPublishDraft(block) {
    this.topicPublishDraft = {
      ...this.topicPublishDraft,
      topic: block?.ros_topic || block?.id || '',
      messageType: block?.message_type || '',
      value: '',
      advanced: false,
    };
    this.topicPublishResponse = null;
  }

  stopTopicPolling() {
    if (this.topicPollTimer) {
      window.clearInterval(this.topicPollTimer);
      this.topicPollTimer = null;
    }
    this.topicPollInFlight = false;
  }

  shouldPollSelectedTopic() {
    return this.activePanel === 'block'
      && this.selectedBlockId
      && isTopicBlock(this.selectedBlock);
  }

  syncTopicPolling() {
    if (!this.shouldPollSelectedTopic()) {
      this.stopTopicPolling();
      return;
    }

    if (this.topicPollTimer) {
      return;
    }

    this.refreshSelectedTopicData();
    this.topicPollTimer = window.setInterval(
      () => this.refreshSelectedTopicData(),
      400,
    );
  }

  async refreshSelectedTopicData() {
    if (!this.shouldPollSelectedTopic() || this.topicPollInFlight) {
      return;
    }

    const blockId = this.selectedBlockId;
    this.topicPollInFlight = true;
    this.topicDataStatus = this.selectedTopicData ? 'refreshing' : 'loading';
    this.topicDataError = '';

    try {
      const response = await fetch(`${blockApiPath(blockId)}/data`, {
        cache: 'no-store',
      });

      if (this.selectedBlockId !== blockId) {
        return;
      }

      if (!response.ok) {
        throw new Error(`Topic data request failed with ${response.status}`);
      }

      this.selectedTopicData = await response.json();
      this.topicDataStatus = 'ready';
      this.selectedState = {
        ...(this.selectedState || {}),
        status: this.selectedTopicData.status || this.selectedState?.status,
        data: this.selectedTopicData,
      };
      this.renderBlockDetails();
    } catch (error) {
      this.topicDataStatus = 'error';
      this.topicDataError = error.message || 'Topic data refresh failed.';
      this.renderBlockDetails();
    } finally {
      this.topicPollInFlight = false;
    }
  }

  async fetchSelectedBlock(blockId) {
    this.stopTopicPolling();
    this.selectedBlockId = blockId;
    this.selectedBlock = null;
    this.selectedState = null;
    this.selectedLogs = null;
    this.selectedTopicData = null;
    this.commandResponse = null;
    this.topicPublishResponse = null;
    this.topicDataStatus = 'idle';
    this.topicDataError = '';
    this.setPanel('block');
    this.renderEmptyDetails('Loading block.');
    this.updateStatusBar();

    const [blockResponse, stateResponse] = await Promise.all([
      fetch(blockApiPath(blockId), { cache: 'no-store' }),
      fetch(`${blockApiPath(blockId)}/state`, { cache: 'no-store' }),
    ]);

    if (!blockResponse.ok || !stateResponse.ok) {
      throw new Error('Block request failed.');
    }

    this.selectedBlock = await blockResponse.json();
    this.selectedState = await stateResponse.json();
    if (isTopicBlock(this.selectedBlock)) {
      this.selectedTopicData = this.selectedState.data || null;
      this.resetTopicPublishDraft(this.selectedBlock);
      this.topicDataStatus = 'loading';
      this.syncTopicPolling();
    }
    this.renderBlockDetails();
    this.updateStatusBar();
  }

  async refreshSelectedState() {
    if (!this.selectedBlockId || !this.selectedBlock) {
      return;
    }

    try {
      const response = await fetch(`${blockApiPath(this.selectedBlockId)}/state`, {
        cache: 'no-store',
      });
      if (!response.ok) {
        return;
      }
      this.selectedState = await response.json();
      this.renderBlockDetails();
    } catch (error) {
      this.setSaveStatus('State refresh failed', 'error');
    }
  }

  async sendSelectedCommand(index) {
    const controls = this.selectedState?.controls || this.selectedBlock?.commands || [];
    const definition = controls[index];
    if (!this.selectedBlockId || !definition) {
      return;
    }

    let value = definition.value ?? definition.default ?? null;
    if (definition.type === 'number') {
      const input = document.querySelector(`[data-command-input="${index}"]`);
      value = input ? Number(input.value) : value;
    }

    const response = await fetch(`${blockApiPath(this.selectedBlockId)}/command`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        command: definition.name,
        value,
      }),
    });

    this.commandResponse = await response.json();
    if (!response.ok) {
      this.commandResponse.success = false;
    }
    this.renderBlockDetails();
  }

  updateTopicPublishDraftFromForm() {
    const topicInput = document.getElementById('topicPublishTopic');
    const messageTypeInput = document.getElementById('topicPublishMessageType');
    const valueInput = document.getElementById('topicPublishValue');
    const advancedInput = document.getElementById('topicPublishAdvanced');
    const jsonInput = document.getElementById('topicPublishJson');

    if (topicInput) {
      this.topicPublishDraft.topic = topicInput.value;
    }
    if (messageTypeInput) {
      this.topicPublishDraft.messageType = messageTypeInput.value;
    }
    if (valueInput) {
      this.topicPublishDraft.value = valueInput.value;
    }
    if (advancedInput) {
      this.topicPublishDraft.advanced = advancedInput.checked;
    }
    if (jsonInput) {
      this.topicPublishDraft.jsonValue = jsonInput.value;
    }
  }

  async publishTopicFromDraft() {
    this.updateTopicPublishDraftFromForm();

    try {
      const value = parsePublishValue(
        this.topicPublishDraft.messageType,
        this.topicPublishDraft.advanced
          ? this.topicPublishDraft.jsonValue
          : this.topicPublishDraft.value,
        this.topicPublishDraft.advanced,
      );

      const response = await fetch('/api/topic/publish', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          topic: this.topicPublishDraft.topic,
          message_type: this.topicPublishDraft.messageType,
          value,
        }),
      });

      this.topicPublishResponse = await response.json();
      if (!response.ok) {
        this.topicPublishResponse.success = false;
      }
    } catch (error) {
      this.topicPublishResponse = {
        success: false,
        message: error.message || 'Publish failed.',
      };
    }

    this.renderBlockDetails();
  }

  async loadSelectedLogs() {
    if (!this.selectedBlockId) {
      return;
    }

    const response = await fetch(`${blockApiPath(this.selectedBlockId)}/logs`, {
      cache: 'no-store',
    });
    if (!response.ok) {
      return;
    }
    this.selectedLogs = await response.json();
    this.renderBlockDetails();
  }

  async loadServices() {
    const response = await fetch('/api/services', { cache: 'no-store' });
    if (!response.ok) {
      throw new Error('Services request failed.');
    }
    const payload = await response.json();
    this.services = Array.isArray(payload.services) ? payload.services : [];
    this.renderServices();
  }

  async callServiceAction(serviceId, action) {
    if (action === 'logs') {
      const response = await fetch(`/api/services/${encodeURIComponent(serviceId)}/logs`, {
        cache: 'no-store',
      });
      if (response.ok) {
        this.serviceLogs[serviceId] = await response.json();
        this.renderServices();
      }
      return;
    }

    const response = await fetch(`/api/services/${encodeURIComponent(serviceId)}/${action}`, {
      method: 'POST',
    });
    if (!response.ok) {
      this.setSaveStatus('Service action failed', 'error');
      return;
    }

    await this.loadServices();
    this.setSaveStatus(`Service ${action} accepted`, 'success');
  }

  async loadFlowchart() {
    const response = await fetch('/api/flowchart', { cache: 'no-store' });
    if (!response.ok) {
      throw new Error(`Flowchart request failed with ${response.status}`);
    }

    this.flowchartState = mergedFlowchart(await response.json());
    this.dom.projectNameElement.textContent = this.flowchartState.config.project_name;
    document.title = this.flowchartState.config.project_name;
    this.dom.saveLayoutButton.disabled = !this.flowchartState.config.allow_save_layout;
    this.applyTheme();
    this.renderGraph();

    if (this.selectedBlockId) {
      const selectedNode = this.cy.getElementById(this.selectedBlockId);
      if (selectedNode.length) {
        selectedNode.select();
        await this.fetchSelectedBlock(this.selectedBlockId);
      } else {
        this.clearSelection();
      }
    }
  }

  async saveLayout() {
    if (!this.cy || !this.flowchartState.config.allow_save_layout) {
      return;
    }

    this.dom.saveLayoutButton.disabled = true;
    this.setSaveStatus('Saving', 'neutral');

    const payload = {
      version: this.flowchartState.layout.version || 1,
      viewport: this.currentViewport(),
      positions: this.currentPositions(),
      groups: this.flowchartState.layout.groups || [],
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
      this.flowchartState.layout = mergedFlowchart({
        ...this.flowchartState,
        layout: saved.layout,
      }).layout;
      this.setSaveStatus('Saved', 'success');
    } catch (error) {
      this.setSaveStatus('Save failed', 'error');
    } finally {
      this.dom.saveLayoutButton.disabled = !this.flowchartState.config.allow_save_layout;
    }
  }

  async reloadDashboard() {
    this.setSaveStatus('Loading', 'neutral');
    try {
      await this.loadFlowchart();
      await this.loadServices();
      this.setSaveStatus('Ready', 'neutral');
    } catch (error) {
      this.setSaveStatus('Load failed', 'error');
    }
  }

  resetRefreshTimer() {
    if (this.refreshTimer) {
      window.clearInterval(this.refreshTimer);
    }

    const interval = Number(this.flowchartState.config.refresh_rate_ms) || 1000;
    this.refreshTimer = window.setInterval(() => this.refreshSelectedState(), interval);
  }

  clearSelection() {
    this.stopTopicPolling();
    this.selectedBlockId = null;
    this.selectedBlock = null;
    this.selectedState = null;
    this.selectedLogs = null;
    this.selectedTopicData = null;
    this.commandResponse = null;
    this.topicPublishResponse = null;
    this.renderEmptyDetails();
    this.updateStatusBar();
  }

  initializeGraph() {
    if (!window.cytoscape) {
      throw new Error('Cytoscape failed to load.');
    }

    this.cy = window.cytoscape({
      container: this.dom.graphContainer,
      elements: [],
      boxSelectionEnabled: false,
      minZoom: 0.2,
      maxZoom: 3,
      wheelSensitivity: 0.18,
    });

    this.cy.on('tap', 'node', async (event) => {
      try {
        await this.fetchSelectedBlock(event.target.id());
      } catch (error) {
        this.renderEmptyDetails('Block load failed.');
        this.setSaveStatus('Block load failed', 'error');
      }
    });

    this.cy.on('tap', (event) => {
      if (event.target === this.cy) {
        this.cy.elements().unselect();
        this.clearSelection();
      }
    });
  }

  bindEvents() {
    this.dom.saveLayoutButton.addEventListener('click', () => {
      this.saveLayout();
    });
    this.dom.reloadButton.addEventListener('click', () => {
      this.reloadDashboard();
    });
    this.dom.editModeToggle.addEventListener('change', () => {
      this.setEditMode(this.dom.editModeToggle.checked);
    });

    this.dom.tabButtons.forEach((button) => {
      button.addEventListener('click', () => this.setPanel(button.dataset.panel));
    });

    this.dom.selectionDetailsElement.addEventListener('click', async (event) => {
      const commandButton = event.target.closest('[data-command-index]');
      if (commandButton) {
        await this.sendSelectedCommand(Number(commandButton.dataset.commandIndex));
        return;
      }

      if (event.target.closest('#blockLogsButton')) {
        await this.loadSelectedLogs();
      }
    });

    this.dom.selectionDetailsElement.addEventListener('submit', async (event) => {
      if (event.target.id !== 'topicPublishForm') {
        return;
      }

      event.preventDefault();
      await this.publishTopicFromDraft();
    });

    this.dom.selectionDetailsElement.addEventListener('input', (event) => {
      if (!event.target.closest('#topicPublishForm')) {
        return;
      }

      this.updateTopicPublishDraftFromForm();
    });

    this.dom.selectionDetailsElement.addEventListener('change', (event) => {
      if (event.target.id !== 'topicPublishAdvanced') {
        return;
      }

      this.updateTopicPublishDraftFromForm();
      this.renderBlockDetails();
    });

    this.dom.servicesListElement.addEventListener('click', async (event) => {
      const actionButton = event.target.closest('[data-service-action]');
      if (!actionButton) {
        return;
      }
      await this.callServiceAction(
        actionButton.dataset.serviceId,
        actionButton.dataset.serviceAction,
      );
    });
  }

  async initialize() {
    this.initializeGraph();
    this.bindEvents();
    this.renderEmptyDetails();
    await this.reloadDashboard();
    this.resetRefreshTimer();
  }
}
