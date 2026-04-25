export function createDomRefs() {
  return {
    projectNameElement: document.getElementById('projectName'),
    editModeToggle: document.getElementById('editModeToggle'),
    saveLayoutButton: document.getElementById('saveLayoutButton'),
    reloadButton: document.getElementById('reloadButton'),
    selectionDetailsElement: document.getElementById('selectionDetails'),
    servicesListElement: document.getElementById('servicesList'),
    saveStatusElement: document.getElementById('saveStatus'),
    blockCountElement: document.getElementById('blockCount'),
    connectionCountElement: document.getElementById('connectionCount'),
    selectedBlockLabelElement: document.getElementById('selectedBlockLabel'),
    blockPanel: document.getElementById('blockPanel'),
    servicesPanel: document.getElementById('servicesPanel'),
    tabButtons: Array.from(document.querySelectorAll('.tab-button')),
    graphContainer: document.getElementById('cy'),
  };
}
