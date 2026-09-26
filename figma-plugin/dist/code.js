figma.showUI(__html__, { width: 360, height: 180 });

function solid(r, g, b) {
  return [{ type: "SOLID", color: { r, g, b } }];
}

async function textNode(content, size) {
  await figma.loadFontAsync({ family: "Inter", style: "Regular" });
  const node = figma.createText();
  node.fontName = { family: "Inter", style: "Regular" };
  node.fontSize = size;
  node.characters = content;
  node.fills = solid(0.12, 0.14, 0.18);
  return node;
}

async function createScene(scene, manifest, x) {
  const frame = figma.createFrame();
  frame.name = scene.name;
  frame.resize(manifest.canvas.width, manifest.canvas.height);
  frame.x = x;
  frame.fills = solid(0.96, 0.97, 0.98);
  frame.layoutMode = "NONE";
  frame.setPluginData("scd:scene", JSON.stringify({
    id: scene.id,
    duration_seconds: scene.duration_seconds,
    composition_pattern: scene.composition_pattern,
    annotations: scene.annotations
  }));

  const label = await textNode(`${scene.id} · ${scene.duration_seconds}s · ${scene.composition_pattern}`, 24);
  label.name = "01_SCENE_META";
  label.x = 64;
  label.y = 48;
  frame.appendChild(label);

  for (const layer of scene.layers) {
    if (layer.type === "text") {
      const node = await textNode(layer.text || "Текст", 52);
      node.name = layer.name;
      node.x = layer.bounds?.x ?? 120;
      node.y = layer.bounds?.y ?? 140;
      node.resize(Math.min(node.width, 1440), node.height);
      frame.appendChild(node);
    } else {
      const node = figma.createRectangle();
      node.name = layer.name;
      node.x = layer.bounds?.x ?? 240;
      node.y = layer.bounds?.y ?? 280;
      node.resize(layer.bounds?.width ?? 640, layer.bounds?.height ?? 420);
      node.fills = layer.role === "background" ? solid(0.96, 0.97, 0.98) : solid(0.82, 0.85, 0.90);
      node.strokes = layer.role === "background" ? [] : solid(0.45, 0.49, 0.56);
      node.dashPattern = layer.role === "background" ? [] : [12, 8];
      node.setPluginData("scd:role", layer.role);
      frame.appendChild(node);
    }
  }
  return frame;
}

figma.ui.onmessage = async (message) => {
  if (message.type !== "import" || !message.manifest) return;
  try {
    const manifest = message.manifest;
    if (manifest.schema_version !== "0.5" || !Array.isArray(manifest.scenes)) {
      throw new Error("Неподдерживаемый manifest. Ожидается schema version 0.5.");
    }
    let storyboard = figma.root.children.find((page) => page.name === "04 Storyboard");
    if (!storyboard) {
      storyboard = figma.createPage();
      storyboard.name = "04 Storyboard";
    }
    for (const pageName of manifest.document_pages) {
      if (!figma.root.children.some((page) => page.name === pageName)) {
        const page = figma.createPage();
        page.name = pageName;
      }
    }
    await figma.setCurrentPageAsync(storyboard);
    const frames = [];
    for (let index = 0; index < manifest.scenes.length; index += 1) {
      frames.push(await createScene(manifest.scenes[index], manifest, index * (manifest.canvas.width + manifest.canvas.gap)));
    }
    figma.viewport.scrollAndZoomIntoView(frames);
    figma.ui.postMessage({ type: "done", count: frames.length });
  } catch (error) {
    figma.ui.postMessage({ type: "error", message: error instanceof Error ? error.message : String(error) });
  }
};

