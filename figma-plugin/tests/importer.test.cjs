const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

let nextId = 1;

class MockNode {
  constructor(type, page) {
    this.id = String(nextId++);
    this.type = type;
    this.name = type;
    this.x = 0;
    this.y = 0;
    this.width = 100;
    this.height = 100;
    this.children = [];
    this.parent = null;
    this.removed = false;
    this.pluginData = new Map();
    if (page && type !== "PAGE") page.appendChild(this);
  }
  resize(width, height) { this.width = width; this.height = height; }
  setPluginData(key, value) { this.pluginData.set(key, value); }
  getPluginData(key) { return this.pluginData.get(key) || ""; }
  appendChild(node) {
    if (node.parent) node.parent.children = node.parent.children.filter((child) => child !== node);
    node.parent = this;
    this.children.push(node);
  }
  findAll(predicate) {
    const result = [];
    const visit = (node) => {
      if (predicate(node)) result.push(node);
      for (const child of node.children || []) visit(child);
    };
    for (const child of this.children) visit(child);
    return result;
  }
  findOne(predicate) { return this.findAll(predicate)[0] || null; }
  remove() {
    this.removed = true;
    if (this.parent) this.parent.children = this.parent.children.filter((child) => child !== this);
  }
}

class MockText extends MockNode {
  constructor(page) {
    super("TEXT", page);
    this._characters = "";
    this.fontSize = 18;
  }
  set characters(value) { this._characters = value; this.height = Math.max(this.height, Math.ceil(value.length / 24) * 24); }
  get characters() { return this._characters; }
}

function createRuntime() {
  const messages = [];
  const root = { children: [] };
  const firstPage = new MockNode("PAGE");
  firstPage.name = "04 Storyboard";
  root.children.push(firstPage);
  const figma = {
    root,
    currentPage: firstPage,
    ui: { onmessage: null, postMessage: (message) => messages.push(message) },
    viewport: { scrollAndZoomIntoView() {} },
    showUI() {},
    loadFontAsync: async () => {},
    setCurrentPageAsync: async (page) => { figma.currentPage = page; },
    createPage: () => {
      const page = new MockNode("PAGE");
      root.children.push(page);
      return page;
    },
    createFrame: () => new MockNode("FRAME", figma.currentPage),
    createRectangle: () => new MockNode("RECTANGLE", figma.currentPage),
    createLine: () => new MockNode("LINE", figma.currentPage),
    createText: () => new MockText(figma.currentPage),
  };
  const context = vm.createContext({ figma, __html__: "", console, JSON, Map, Set, Math, Number, Array, Object, String, Boolean, Error, Promise, parseInt });
  vm.runInContext(fs.readFileSync(require.resolve("../dist/code.js"), "utf8"), context);
  return { figma, messages, page: firstPage };
}

function annotations() {
  return {
    purpose: "Purpose", message: "Message", voiceover: "Voiceover", on_screen_copy: "Copy",
    attention_sequence: ["one"], motion: ["move"], transition_out: "cut",
    reference_ids: [], evidence_ids: ["EV-1"], locked: ["meaning"], creative_freedom: ["style"],
  };
}

function scene(id, revision, contentHash, text) {
  return {
    semantic_id: `scene/${id}`, id, name: `${id} scene`, source_revision: revision,
    content_hash: contentHash, duration_seconds: 5, composition_pattern: "hero-ui", pattern_version: "1.0",
    recipe: "focus-detail", recipe_version: "1.0", recipe_selection: "explicit",
    nodes: [{ semantic_id: `${id}/copy/headline`, type: "text", role: "copy", name: "HEADLINE", bounds: { x: 20, y: 20, width: 500, height: 80 }, style: "headline", text }],
    states: [{ id: "hero", at_seconds: 0, object_ids: [`${id}/hero`], description: "Hero state" }],
    events: [{ id: "hold", at_seconds: 1, type: "hold", object_ids: [`${id}/hero`], description: "Hold state" }],
    transition_anchors: [{ id: "out", edge: "out", at_seconds: 5, object_id: `${id}/hero`, description: "Carry hero" }],
    production_semantics: { objects: [{ semantic_id: `${id}/hero`, name: "Hero", type: "ui-panel", role: "primary", bounds: { x: 20, y: 20, width: 500, height: 80 }, asset_id: null, editable: true }] },
    annotations: annotations(), assets: { raster_semantic_ids: [], missing: [] }, warnings: [],
  };
}

function tokens(accent = "#4F46E5", headline = 56) {
  return {
    colors: { canvas: "#F9FAFB", surface: "#F9FAFB", raised: "#FFFFFF", muted: "#F3F4F6", dark: "#111827", accent, accent_surface: "#EEF2FF", success: "#ECFDF5", warning: "#FFF7ED", raster: "#FFF1F2", border: "#D1D5DB", text_primary: "#111827", text_secondary: "#4B5563", text_on_accent: "#FFFFFF" },
    spacing: { base: 8, corner_radius: 18, stroke_width: 2 },
    type_scale: { headline, title: 30, body: 18, eyebrow: 15 },
  };
}

function manifest(operation, hash, scenes) {
  return {
    schema_version: "1.0", contract: "saas-creative-director/figma-manifest",
    project: { id: "receipt-test", name: "Receipt test" }, source_revision: operation,
    operation: { id: operation, manifest_hash: hash, mode: "preserve-human-create-revision" },
    document_pages: ["04 Storyboard"], target_page: "04 Storyboard",
    canvas: { width: 800, height: 600, scene_gap: 100, annotation_width: 300, annotation_gap: 20 },
    typography: { family: "Inter", style: "Regular", fallbacks: ["Roboto"] },
    tokens: tokens(), recipes: ["source-convergence", "horizontal-flow", "focus-detail"], limits: {}, scenes, warnings: [],
  };
}

async function send(runtime, value) {
  await runtime.figma.ui.onmessage({ type: "import", manifest: value });
  const result = runtime.messages.at(-1);
  assert.equal(result.type, "done", result.message);
  return result.summary;
}

async function assertVisualEditDetected(label, mutate) {
  const runtime = createRuntime();
  const value = manifest(`op-edit-${label}`, "dddddddddddddddddddddddd", [scene("S01", "r1", "5555555555555555", "Visual edit")]);
  await send(runtime, value);
  const board = runtime.page.findAll((node) => node.getPluginData("scd:board") === "true")[0];
  const headline = runtime.page.findAll((node) => node.getPluginData("scd:semantic-id") === "S01/copy/headline")[0];
  mutate({ board, headline });
  const retry = await send(runtime, value);
  assert.equal(retry.created, 0, `${label}: edited board should be reused`);
  assert.equal(retry.conflicts, 1, `${label}: edit should be reported`);
  assert.ok(retry.warnings.some((warning) => warning.includes("human edits detected")), `${label}: missing edit warning`);
}

(async () => {
  const runtime = createRuntime();
  const first = manifest("op-a", "aaaaaaaaaaaaaaaaaaaaaaaa", [scene("S01", "r1", "1111111111111111", "First"), scene("S02", "r1", "2222222222222222", "Second")]);
  const initial = await send(runtime, first);
  assert.equal(initial.created, 2);
  assert.equal(initial.receipt, "written");
  assert.deepEqual(initial.scenes[0].stateIds, ["hero"]);
  assert.deepEqual(initial.scenes[0].eventIds, ["hold"]);
  assert.deepEqual(initial.scenes[0].transitionAnchorIds, ["out"]);
  assert.deepEqual(initial.scenes[0].productionObjectIds, ["S01/hero"]);
  const headline = runtime.page.findAll((node) => node.getPluginData("scd:semantic-id") === "S01/copy/headline")[0];
  assert.equal(headline.fontSize, 56);

  const second = manifest("op-b", "bbbbbbbbbbbbbbbbbbbbbbbb", [scene("S01", "r2", "3333333333333333", "First changed"), scene("S02", "r1", "2222222222222222", "Second")]);
  const mixed = await send(runtime, second);
  assert.equal(mixed.created, 1);
  assert.equal(mixed.reused, 1);
  assert.equal(runtime.page.findAll((node) => node.getPluginData("scd:board") === "true").length, 3);

  const exactRetry = await send(runtime, second);
  assert.equal(exactRetry.created, 0);
  assert.equal(exactRetry.reused, 2);
  assert.equal(exactRetry.receipt, "validated");
  assert.equal(runtime.page.findAll((node) => node.getPluginData("scd:board") === "true").length, 3);

  runtime.page.setPluginData("scd:receipt:bbbbbbbbbbbbbbbbbbbbbbbb", "{corrupt");
  const repaired = await send(runtime, second);
  assert.equal(repaired.created, 0);
  assert.equal(repaired.reused, 2);
  assert.equal(repaired.receipt, "reconstructed");
  assert.equal(runtime.page.findAll((node) => node.getPluginData("scd:board") === "true").length, 3);

  const tokenRuntime = createRuntime();
  const tokenManifest = manifest("op-token", "cccccccccccccccccccccccc", [scene("S01", "r1", "4444444444444444", "Token render")]);
  tokenManifest.tokens = tokens("#123456", 64);
  await send(tokenRuntime, tokenManifest);
  const tokenHeadline = tokenRuntime.page.findAll((node) => node.getPluginData("scd:semantic-id") === "S01/copy/headline")[0];
  assert.equal(tokenHeadline.fontSize, 64);

  await assertVisualEditDetected("fill", ({ headline }) => { headline.fills = [{ type: "SOLID", color: { r: 1, g: 0, b: 0 } }]; });
  await assertVisualEditDetected("stroke", ({ headline }) => { headline.strokes = [{ type: "SOLID", color: { r: 0, g: 1, b: 0 } }]; });
  await assertVisualEditDetected("opacity", ({ headline }) => { headline.opacity = 0.42; });
  await assertVisualEditDetected("typography", ({ headline }) => { headline.fontSize = 71; });
  await assertVisualEditDetected("effect", ({ headline }) => { headline.effects = [{ type: "DROP_SHADOW", radius: 12, visible: true, blendMode: "NORMAL", color: { r: 0, g: 0, b: 0, a: 0.5 }, offset: { x: 2, y: 4 }, spread: 0 }]; });
  await assertVisualEditDetected("name", ({ headline }) => { headline.name = "RENAMED_HEADLINE"; });
  await assertVisualEditDetected("child-order", ({ board }) => { board.children.reverse(); });

  const legacyRuntime = createRuntime();
  const legacyManifest = manifest("op-legacy-fingerprint", "eeeeeeeeeeeeeeeeeeeeeeee", [scene("S01", "r1", "6666666666666666", "Legacy")]);
  await send(legacyRuntime, legacyManifest);
  const legacyBoard = legacyRuntime.page.findAll((node) => node.getPluginData("scd:board") === "true")[0];
  legacyBoard.pluginData.delete("scd:generated-fingerprint-v2");
  const legacyRetry = await send(legacyRuntime, legacyManifest);
  assert.equal(legacyRetry.conflicts, 0, "unchanged legacy boards should not be reported as edited");

  const panelRuntime = createRuntime();
  const panelScene = scene("S01", "panel-r1", "7777777777777777", "unused");
  panelScene.nodes = [];
  panelScene.sequence_mode = "panel-sequence";
  panelScene.panels = Array.from({ length: 4 }, (_, index) => ({
    semantic_id: `scene/S01/panel/P0${index + 1}`, id: `P0${index + 1}`, name: `State ${index + 1}`,
    at_seconds: index, duration_seconds: 1, state_id: "hero", event_ids: ["hold"],
    focal_object_id: "S01/hero",
    continuity: index ? "continuous" : "cut", transition_from_previous: index ? "Carry product" : null,
    nodes: [{ semantic_id: `S01/P0${index + 1}/headline`, type: "text", role: "copy", name: "PANEL_COPY", bounds: { x: 20, y: 20, width: 500, height: 80 }, style: "headline", text: `Panel ${index + 1}`, metadata: { object_id: "S01/hero" } }],
    object_instance_ids: [`S01/P0${index + 1}/headline`],
  }));
  const panelManifest = manifest("op-panels", "ffffffffffffffffffffffff", [panelScene]);
  panelManifest.schema_version = "1.1";
  const panelResult = await send(panelRuntime, panelManifest);
  assert.equal(panelResult.created, 1, "one revision container per scene");
  assert.equal(panelResult.scenes[0].panelIds.length, 4);
  const panels = panelRuntime.page.findAll((node) => Boolean(node.getPluginData("scd:panel-id")));
  assert.equal(panels.length, 4);
  assert.equal(panels[0].y, panels[2].y);
  assert.equal(panels[3].x, panels[0].x, "fourth panel starts a second row");
  assert.ok(panels[3].y >= panels[0].y + panels[0].height);
  assert.ok(panels.every((panel) => panel.width === 800 && panel.height === 600));
  assert.equal(panelRuntime.page.findAll((node) => node.name === "90_VISIBLE_HANDOFF_NOTES").length, 1);
  const panelRetry = await send(panelRuntime, panelManifest);
  assert.equal(panelRetry.created, 0);
  panels[1].children[0].characters = "Human correction";
  const editedRetry = await send(panelRuntime, panelManifest);
  assert.equal(editedRetry.conflicts, 1);
  assert.equal(panels[1].children[0].characters, "Human correction");
  const changedPanels = JSON.parse(JSON.stringify(panelManifest));
  changedPanels.operation = { ...changedPanels.operation, id: "op-panels-v2", manifest_hash: "121212121212121212121212" };
  changedPanels.scenes[0].content_hash = "8888888888888888";
  changedPanels.scenes[0].source_revision = "panel-r2";
  changedPanels.scenes[0].panels[0].nodes[0].text = "Revised sequence";
  const changedResult = await send(panelRuntime, changedPanels);
  assert.equal(changedResult.created, 1, "panel change creates one complete scene revision");
  assert.equal(panelRuntime.page.findAll((node) => node.getPluginData("scd:board") === "true").length, 2);
  assert.equal(panels[1].children[0].characters, "Human correction", "old revision remains untouched");
  for (const mutate of [
    (value) => { value.scenes[0].panels[1].id = "P01"; },
    (value) => { value.scenes[0].panels[0].state_id = "unknown"; },
    (value) => { value.scenes[0].panels[0].event_ids = ["unknown"]; },
    (value) => { value.scenes[0].panels[0].duration_seconds = 20; },
    (value) => { value.scenes[0].panels[2].at_seconds = value.scenes[0].panels[1].at_seconds; },
    (value) => { value.scenes[0].panels[0].object_instance_ids = []; },
    (value) => { value.scenes[0].panels[0].focal_object_id = "S01/missing"; },
  ]) {
    const invalid = JSON.parse(JSON.stringify(panelManifest));
    mutate(invalid);
    const invalidRuntime = createRuntime();
    await invalidRuntime.figma.ui.onmessage({ type: "import", manifest: invalid });
    assert.equal(invalidRuntime.messages.at(-1).type, "error");
    assert.equal(invalidRuntime.page.children.length, 0, "invalid panels fail before canvas writes");
  }

  if (process.env.SCD_FIGMA_MANIFEST) {
    const compiled = JSON.parse(fs.readFileSync(process.env.SCD_FIGMA_MANIFEST, "utf8"));
    const compiledRuntime = createRuntime();
    const compiledResult = await send(compiledRuntime, compiled);
    assert.equal(compiledResult.created, compiled.scenes.length);
    const compiledRetry = await send(compiledRuntime, compiled);
    assert.equal(compiledRetry.created, 0);
    assert.equal(compiledRetry.reused, compiled.scenes.length);
  }
  console.log("receipt and panel-sequence importer tests passed");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
