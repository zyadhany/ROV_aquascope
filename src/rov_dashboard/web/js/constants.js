export const DEFAULT_FLOWCHART = {
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
      hardware: '#ec4899',
      topic: '#22c55e',
      nodes: '#3b82f6',
      edge: '#64748b',
      fallback: '#64748b',
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
