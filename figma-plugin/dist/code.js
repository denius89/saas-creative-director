"use strict";
const LIMITS = {
    maxManifestBytes: 2000000,
    maxScenes: 48,
    maxNodes: 2500,
    maxNodesPerScene: 200,
    maxTextChars: 4000,
    maxTotalTextChars: 100000,
    maxCanvasDimension: 8192,
    maxPages: 12,
};
const ALLOWED_NODE_TYPES = new Set(["annotation-card", "asset-placeholder", "connector", "frame", "pill", "raster-placeholder", "rectangle", "text", "ui-card", "ui-row"]);
const ALLOWED_RECIPES = new Set(["source-convergence", "horizontal-flow", "focus-detail"]);
const ALLOWED_EVENT_TYPES = new Set(["enter", "exit", "emphasize", "transform", "move", "hold", "state-change", "camera", "other"]);
const COLOR_ROLES = ["canvas", "surface", "raised", "muted", "dark", "accent", "accent_surface", "success", "warning", "raster", "border", "text_primary", "text_secondary", "text_on_accent"];
const fontCache = new Map();
figma.showUI(__html__, { width: 420, height: 420 });
function isRecord(value) {
    return typeof value === "object" && value !== null && !Array.isArray(value);
}
function requireRecord(value, path) {
    if (!isRecord(value))
        throw new Error(`${path}: expected object`);
    return value;
}
function requireString(value, path, allowEmpty = false) {
    if (typeof value !== "string" || (!allowEmpty && value.trim().length === 0))
        throw new Error(`${path}: expected ${allowEmpty ? "string" : "non-empty string"}`);
    return value;
}
function requireNumber(value, path, positive = false) {
    if (typeof value !== "number" || !Number.isFinite(value) || (positive && value <= 0))
        throw new Error(`${path}: expected ${positive ? "positive " : ""}number`);
    return value;
}
function requireStringArray(value, path, max = 200) {
    if (!Array.isArray(value) || value.length > max || value.some((item) => typeof item !== "string"))
        throw new Error(`${path}: expected at most ${max} strings`);
    return value;
}
function assertKeys(value, path, allowed, required = allowed) {
    const allowedSet = new Set(allowed);
    const extra = Object.keys(value).filter((key) => !allowedSet.has(key));
    if (extra.length)
        throw new Error(`${path}: unsupported fields ${extra.join(", ")}`);
    const missing = required.filter((key) => !(key in value));
    if (missing.length)
        throw new Error(`${path}: missing fields ${missing.join(", ")}`);
}
function requireBoolean(value, path) {
    if (typeof value !== "boolean")
        throw new Error(`${path}: expected boolean`);
    return value;
}
function requireNullableString(value, path) {
    if (value === undefined)
        return undefined;
    if (value === null)
        return null;
    return requireString(value, path);
}
function validateTokens(value) {
    const tokens = requireRecord(value, "tokens");
    assertKeys(tokens, "tokens", ["colors", "spacing", "type_scale"]);
    const colorsValue = requireRecord(tokens.colors, "tokens.colors");
    assertKeys(colorsValue, "tokens.colors", COLOR_ROLES);
    const colors = {};
    for (const role of COLOR_ROLES) {
        const color = requireString(colorsValue[role], `tokens.colors.${role}`);
        if (!/^#[0-9A-Fa-f]{6}$/.test(color))
            throw new Error(`tokens.colors.${role}: expected #RRGGBB`);
        colors[role] = color.toUpperCase();
    }
    const spacingValue = requireRecord(tokens.spacing, "tokens.spacing");
    assertKeys(spacingValue, "tokens.spacing", ["base", "corner_radius", "stroke_width"]);
    const spacing = {
        base: requireNumber(spacingValue.base, "tokens.spacing.base", true),
        corner_radius: requireNumber(spacingValue.corner_radius, "tokens.spacing.corner_radius", true),
        stroke_width: requireNumber(spacingValue.stroke_width, "tokens.spacing.stroke_width", true),
    };
    if (Object.values(spacing).some((number) => number > 128))
        throw new Error("tokens.spacing: values must be at most 128");
    const typeScaleValue = requireRecord(tokens.type_scale, "tokens.type_scale");
    assertKeys(typeScaleValue, "tokens.type_scale", ["headline", "title", "body", "eyebrow"]);
    const type_scale = {
        headline: requireNumber(typeScaleValue.headline, "tokens.type_scale.headline", true),
        title: requireNumber(typeScaleValue.title, "tokens.type_scale.title", true),
        body: requireNumber(typeScaleValue.body, "tokens.type_scale.body", true),
        eyebrow: requireNumber(typeScaleValue.eyebrow, "tokens.type_scale.eyebrow", true),
    };
    if (Object.values(type_scale).some((number) => number < 8 || number > 144))
        throw new Error("tokens.type_scale: values must be from 8 to 144");
    return { colors: colors, spacing, type_scale };
}
function validateState(value, path) {
    const state = requireRecord(value, path);
    assertKeys(state, path, ["id", "at_seconds", "object_ids", "description"]);
    return { id: requireString(state.id, `${path}.id`), at_seconds: requireNumber(state.at_seconds, `${path}.at_seconds`), object_ids: requireStringArray(state.object_ids, `${path}.object_ids`), description: requireString(state.description, `${path}.description`) };
}
function validateEvent(value, path) {
    const event = requireRecord(value, path);
    assertKeys(event, path, ["id", "at_seconds", "duration_seconds", "type", "object_ids", "from_state_id", "to_state_id", "description"], ["id", "at_seconds", "type", "object_ids", "description"]);
    const type = requireString(event.type, `${path}.type`);
    if (!ALLOWED_EVENT_TYPES.has(type))
        throw new Error(`${path}.type: unsupported ${type}`);
    const duration = event.duration_seconds === undefined ? undefined : requireNumber(event.duration_seconds, `${path}.duration_seconds`);
    return { id: requireString(event.id, `${path}.id`), at_seconds: requireNumber(event.at_seconds, `${path}.at_seconds`), duration_seconds: duration, type, object_ids: requireStringArray(event.object_ids, `${path}.object_ids`), from_state_id: requireNullableString(event.from_state_id, `${path}.from_state_id`), to_state_id: requireNullableString(event.to_state_id, `${path}.to_state_id`), description: requireString(event.description, `${path}.description`) };
}
function validateAnchor(value, path) {
    const anchor = requireRecord(value, path);
    assertKeys(anchor, path, ["id", "edge", "at_seconds", "object_id", "state_id", "carry_to_scene_id", "description"], ["id", "edge", "at_seconds"]);
    const edge = requireString(anchor.edge, `${path}.edge`);
    if (edge !== "in" && edge !== "out")
        throw new Error(`${path}.edge: expected in or out`);
    return { id: requireString(anchor.id, `${path}.id`), edge, at_seconds: requireNumber(anchor.at_seconds, `${path}.at_seconds`), object_id: requireNullableString(anchor.object_id, `${path}.object_id`), state_id: requireNullableString(anchor.state_id, `${path}.state_id`), carry_to_scene_id: requireNullableString(anchor.carry_to_scene_id, `${path}.carry_to_scene_id`), description: anchor.description === undefined ? undefined : requireString(anchor.description, `${path}.description`, true) };
}
function validateProductionObject(value, path) {
    const object = requireRecord(value, path);
    assertKeys(object, path, ["semantic_id", "name", "type", "role", "bounds", "asset_id", "editable"]);
    const boundsValue = requireRecord(object.bounds, `${path}.bounds`);
    assertKeys(boundsValue, `${path}.bounds`, ["x", "y", "width", "height"]);
    return {
        semantic_id: requireString(object.semantic_id, `${path}.semantic_id`), name: requireString(object.name, `${path}.name`), type: requireString(object.type, `${path}.type`), role: requireString(object.role, `${path}.role`),
        bounds: { x: requireNumber(boundsValue.x, `${path}.bounds.x`), y: requireNumber(boundsValue.y, `${path}.bounds.y`), width: requireNumber(boundsValue.width, `${path}.bounds.width`, true), height: requireNumber(boundsValue.height, `${path}.bounds.height`, true) },
        asset_id: requireNullableString(object.asset_id, `${path}.asset_id`) || null, editable: requireBoolean(object.editable, `${path}.editable`),
    };
}
function utf8Bytes(value) {
    let bytes = 0;
    for (const character of JSON.stringify(value)) {
        const codePoint = character.codePointAt(0) || 0;
        bytes += codePoint <= 0x7f ? 1 : codePoint <= 0x7ff ? 2 : codePoint <= 0xffff ? 3 : 4;
    }
    return bytes;
}
function validateNode(value, path, semanticIds, counters) {
    const node = requireRecord(value, path);
    assertKeys(node, path, ["semantic_id", "type", "role", "name", "bounds", "style", "text", "children", "metadata"], ["semantic_id", "type", "role", "name", "bounds", "style"]);
    const semanticId = requireString(node.semantic_id, `${path}.semantic_id`);
    if (semanticId.length > 200)
        throw new Error(`${path}.semantic_id: too long`);
    if (semanticIds.has(semanticId))
        throw new Error(`${path}.semantic_id: duplicate ${semanticId}`);
    semanticIds.add(semanticId);
    const type = requireString(node.type, `${path}.type`);
    if (!ALLOWED_NODE_TYPES.has(type))
        throw new Error(`${path}.type: unsupported ${type}`);
    const boundsValue = requireRecord(node.bounds, `${path}.bounds`);
    assertKeys(boundsValue, `${path}.bounds`, ["x", "y", "width", "height"]);
    const bounds = {
        x: requireNumber(boundsValue.x, `${path}.bounds.x`),
        y: requireNumber(boundsValue.y, `${path}.bounds.y`),
        width: requireNumber(boundsValue.width, `${path}.bounds.width`, true),
        height: requireNumber(boundsValue.height, `${path}.bounds.height`, true),
    };
    if (Object.values(bounds).some((number) => Math.abs(number) > LIMITS.maxCanvasDimension))
        throw new Error(`${path}.bounds: exceeds safe dimension`);
    let text;
    if (node.text !== undefined) {
        text = requireString(node.text, `${path}.text`, true);
        if (text.length > LIMITS.maxTextChars)
            throw new Error(`${path}.text: exceeds ${LIMITS.maxTextChars} characters`);
        counters.text += text.length;
    }
    let children;
    if (node.children !== undefined) {
        if (!Array.isArray(node.children) || node.children.length > LIMITS.maxNodesPerScene)
            throw new Error(`${path}.children: invalid array`);
        children = node.children.map((child, index) => validateNode(child, `${path}.children[${index}]`, semanticIds, counters));
    }
    if (node.metadata !== undefined)
        requireRecord(node.metadata, `${path}.metadata`);
    counters.nodes += 1;
    if (type === "raster-placeholder")
        counters.raster += 1;
    return {
        semantic_id: semanticId,
        type: type,
        role: requireString(node.role, `${path}.role`),
        name: requireString(node.name, `${path}.name`),
        bounds,
        style: requireString(node.style, `${path}.style`),
        text,
        children,
        metadata: node.metadata,
    };
}
function validateAnnotations(value, path, counters) {
    const annotations = requireRecord(value, path);
    const scalarKeys = ["purpose", "message", "voiceover", "on_screen_copy", "transition_out"];
    const arrayKeys = ["attention_sequence", "motion", "reference_ids", "evidence_ids", "locked", "creative_freedom"];
    assertKeys(annotations, path, [...scalarKeys, ...arrayKeys]);
    const scalars = {};
    for (const key of scalarKeys) {
        scalars[key] = requireString(annotations[key], `${path}.${key}`, true);
        if (scalars[key].length > LIMITS.maxTextChars)
            throw new Error(`${path}.${key}: too long`);
        counters.text += scalars[key].length;
    }
    const arrays = {};
    for (const key of arrayKeys) {
        arrays[key] = requireStringArray(annotations[key], `${path}.${key}`);
        counters.text += arrays[key].reduce((total, item) => total + item.length, 0);
    }
    return {
        purpose: scalars.purpose,
        message: scalars.message,
        voiceover: scalars.voiceover,
        on_screen_copy: scalars.on_screen_copy,
        transition_out: scalars.transition_out,
        attention_sequence: arrays.attention_sequence,
        motion: arrays.motion,
        reference_ids: arrays.reference_ids,
        evidence_ids: arrays.evidence_ids,
        locked: arrays.locked,
        creative_freedom: arrays.creative_freedom,
    };
}
function preflight(raw) {
    const manifest = requireRecord(raw, "$manifest");
    assertKeys(manifest, "$manifest", ["schema_version", "contract", "project", "source_revision", "operation", "document_pages", "target_page", "canvas", "typography", "tokens", "recipes", "limits", "scenes", "warnings"]);
    if (manifest.schema_version !== "1.0" || manifest.contract !== "saas-creative-director/figma-manifest")
        throw new Error("Unsupported manifest contract; expected Figma manifest 1.0");
    const manifestBytes = utf8Bytes(raw);
    if (manifestBytes > LIMITS.maxManifestBytes)
        throw new Error(`Manifest exceeds ${LIMITS.maxManifestBytes} bytes`);
    const project = requireRecord(manifest.project, "project");
    assertKeys(project, "project", ["id", "name"]);
    const operation = requireRecord(manifest.operation, "operation");
    assertKeys(operation, "operation", ["id", "manifest_hash", "mode"]);
    if (operation.mode !== "preserve-human-create-revision")
        throw new Error("operation.mode is not supported");
    const pages = requireStringArray(manifest.document_pages, "document_pages", LIMITS.maxPages);
    if (!pages.length || new Set(pages).size !== pages.length)
        throw new Error("document_pages must contain unique page names");
    const canvasValue = requireRecord(manifest.canvas, "canvas");
    assertKeys(canvasValue, "canvas", ["width", "height", "scene_gap", "annotation_width", "annotation_gap"]);
    const canvas = {
        width: requireNumber(canvasValue.width, "canvas.width", true),
        height: requireNumber(canvasValue.height, "canvas.height", true),
        scene_gap: requireNumber(canvasValue.scene_gap, "canvas.scene_gap", true),
        annotation_width: requireNumber(canvasValue.annotation_width, "canvas.annotation_width", true),
        annotation_gap: requireNumber(canvasValue.annotation_gap, "canvas.annotation_gap", true),
    };
    if (canvas.width > LIMITS.maxCanvasDimension || canvas.height > LIMITS.maxCanvasDimension)
        throw new Error("canvas exceeds safe dimensions");
    const typographyValue = requireRecord(manifest.typography, "typography");
    assertKeys(typographyValue, "typography", ["family", "style", "fallbacks"]);
    const typography = {
        family: requireString(typographyValue.family, "typography.family"),
        style: requireString(typographyValue.style, "typography.style"),
        fallbacks: requireStringArray(typographyValue.fallbacks, "typography.fallbacks", 8),
    };
    const tokens = validateTokens(manifest.tokens);
    requireRecord(manifest.limits, "limits");
    const recipes = requireStringArray(manifest.recipes, "recipes", 3);
    if (recipes.length !== 3 || recipes.some((recipe) => !ALLOWED_RECIPES.has(recipe)))
        throw new Error("recipes must list the three supported recipes");
    const warnings = requireStringArray(manifest.warnings, "warnings", 500);
    if (!Array.isArray(manifest.scenes) || !manifest.scenes.length || manifest.scenes.length > LIMITS.maxScenes)
        throw new Error(`scenes must contain 1-${LIMITS.maxScenes} scenes`);
    const counters = { nodes: 0, text: 0, raster: 0 };
    const semanticIds = new Set();
    const sceneIds = new Set();
    const scenes = manifest.scenes.map((sceneValue, sceneIndex) => {
        const path = `scenes[${sceneIndex}]`;
        const scene = requireRecord(sceneValue, path);
        assertKeys(scene, path, ["semantic_id", "id", "name", "source_revision", "content_hash", "duration_seconds", "composition_pattern", "pattern_version", "recipe", "recipe_version", "recipe_selection", "nodes", "states", "events", "transition_anchors", "production_semantics", "annotations", "assets", "warnings"]);
        const sceneId = requireString(scene.id, `${path}.id`);
        if (!/^S[0-9]{2,}$/.test(sceneId) || sceneIds.has(sceneId))
            throw new Error(`${path}.id: invalid or duplicate`);
        sceneIds.add(sceneId);
        const recipe = requireString(scene.recipe, `${path}.recipe`);
        if (!ALLOWED_RECIPES.has(recipe))
            throw new Error(`${path}.recipe: unsupported`);
        if (scene.recipe_version !== "1.0")
            throw new Error(`${path}.recipe_version: unsupported`);
        if (scene.recipe_selection !== "explicit" && scene.recipe_selection !== "legacy-inferred")
            throw new Error(`${path}.recipe_selection: unsupported`);
        if (!Array.isArray(scene.nodes) || !scene.nodes.length)
            throw new Error(`${path}.nodes: expected non-empty array`);
        const beforeNodes = counters.nodes;
        const nodes = scene.nodes.map((node, nodeIndex) => validateNode(node, `${path}.nodes[${nodeIndex}]`, semanticIds, counters));
        if (counters.nodes - beforeNodes > LIMITS.maxNodesPerScene)
            throw new Error(`${path}.nodes: exceeds ${LIMITS.maxNodesPerScene}`);
        const assets = requireRecord(scene.assets, `${path}.assets`);
        assertKeys(assets, `${path}.assets`, ["raster_semantic_ids", "missing"]);
        if (!Array.isArray(scene.states) || scene.states.length > 24)
            throw new Error(`${path}.states: invalid array`);
        if (!Array.isArray(scene.events) || scene.events.length > 100)
            throw new Error(`${path}.events: invalid array`);
        if (!Array.isArray(scene.transition_anchors) || scene.transition_anchors.length > 24)
            throw new Error(`${path}.transition_anchors: invalid array`);
        const states = scene.states.map((item, index) => validateState(item, `${path}.states[${index}]`));
        const events = scene.events.map((item, index) => validateEvent(item, `${path}.events[${index}]`));
        const transitionAnchors = scene.transition_anchors.map((item, index) => validateAnchor(item, `${path}.transition_anchors[${index}]`));
        const durationSeconds = requireNumber(scene.duration_seconds, `${path}.duration_seconds`, true);
        if ([...states, ...events, ...transitionAnchors].some((item) => item.at_seconds < 0 || item.at_seconds > durationSeconds))
            throw new Error(`${path}: state, event, or anchor time is outside scene duration`);
        const timelineIds = [...states.map((item) => item.id), ...events.map((item) => item.id), ...transitionAnchors.map((item) => item.id)];
        if (new Set(timelineIds).size !== timelineIds.length)
            throw new Error(`${path}: duplicate state, event, or anchor id`);
        counters.text += states.reduce((total, item) => total + item.id.length + item.description.length + item.object_ids.join("").length, 0);
        counters.text += events.reduce((total, item) => total + item.id.length + item.type.length + item.description.length + item.object_ids.join("").length, 0);
        counters.text += transitionAnchors.reduce((total, item) => total + item.id.length + (item.description || "").length, 0);
        const productionValue = requireRecord(scene.production_semantics, `${path}.production_semantics`);
        assertKeys(productionValue, `${path}.production_semantics`, ["objects"]);
        if (!Array.isArray(productionValue.objects) || !productionValue.objects.length || productionValue.objects.length > 200)
            throw new Error(`${path}.production_semantics.objects: invalid array`);
        const productionObjects = productionValue.objects.map((item, index) => validateProductionObject(item, `${path}.production_semantics.objects[${index}]`));
        counters.text += productionObjects.reduce((total, item) => total + item.semantic_id.length + item.name.length + item.type.length + item.role.length + (item.asset_id || "").length, 0);
        return {
            semantic_id: requireString(scene.semantic_id, `${path}.semantic_id`),
            id: sceneId,
            name: requireString(scene.name, `${path}.name`),
            source_revision: requireString(scene.source_revision, `${path}.source_revision`),
            content_hash: requireString(scene.content_hash, `${path}.content_hash`),
            duration_seconds: durationSeconds,
            composition_pattern: requireString(scene.composition_pattern, `${path}.composition_pattern`),
            pattern_version: requireString(scene.pattern_version, `${path}.pattern_version`),
            recipe: recipe,
            recipe_version: "1.0",
            recipe_selection: scene.recipe_selection,
            nodes,
            states,
            events,
            transition_anchors: transitionAnchors,
            production_semantics: { objects: productionObjects },
            annotations: validateAnnotations(scene.annotations, `${path}.annotations`, counters),
            assets: {
                raster_semantic_ids: requireStringArray(assets.raster_semantic_ids, `${path}.assets.raster_semantic_ids`),
                missing: requireStringArray(assets.missing, `${path}.assets.missing`),
            },
            warnings: requireStringArray(scene.warnings, `${path}.warnings`, 200),
        };
    });
    if (counters.nodes > LIMITS.maxNodes)
        throw new Error(`nodes exceed ${LIMITS.maxNodes}`);
    if (counters.text > LIMITS.maxTotalTextChars)
        throw new Error(`text exceeds ${LIMITS.maxTotalTextChars} total characters`);
    return {
        manifest: {
            schema_version: "1.0",
            contract: "saas-creative-director/figma-manifest",
            project: { id: requireString(project.id, "project.id"), name: requireString(project.name, "project.name") },
            source_revision: requireString(manifest.source_revision, "source_revision"),
            operation: {
                id: requireString(operation.id, "operation.id"),
                manifest_hash: requireString(operation.manifest_hash, "operation.manifest_hash"),
                mode: "preserve-human-create-revision",
            },
            document_pages: pages,
            target_page: requireString(manifest.target_page, "target_page"),
            canvas,
            typography,
            tokens,
            recipes,
            limits: manifest.limits,
            scenes,
            warnings,
        },
        stats: { sceneCount: scenes.length, nodeCount: counters.nodes, textChars: counters.text, rasterCount: counters.raster, manifestBytes },
    };
}
async function resolveFont(manifest) {
    const key = `${manifest.typography.family}/${manifest.typography.style}/${manifest.typography.fallbacks.join(",")}`;
    const cached = fontCache.get(key);
    if (cached)
        return cached;
    const promise = (async () => {
        const families = Array.from(new Set([manifest.typography.family, ...manifest.typography.fallbacks, "Inter", "Roboto"]));
        for (const family of families) {
            const styles = Array.from(new Set([manifest.typography.style, "Regular"]));
            for (const style of styles) {
                const font = { family, style };
                try {
                    await figma.loadFontAsync(font);
                    return { font, report: { requested: `${manifest.typography.family} ${manifest.typography.style}`, resolved: family, style, fallback: family !== manifest.typography.family || style !== manifest.typography.style } };
                }
                catch (_error) {
                    // Try the next local font. The importer never downloads fonts.
                }
            }
        }
        throw new Error(`No local font available for ${manifest.typography.family}; tried ${families.join(", ")}`);
    })();
    fontCache.set(key, promise);
    return promise;
}
function solid(hex) {
    const value = hex.replace("#", "");
    return [{ type: "SOLID", color: { r: parseInt(value.slice(0, 2), 16) / 255, g: parseInt(value.slice(2, 4), 16) / 255, b: parseInt(value.slice(4, 6), 16) / 255 } }];
}
function palette(style, tokens) {
    const c = tokens.colors;
    const styles = {
        "accent": { fill: c.accent, stroke: c.accent, text: c.text_on_accent },
        "accent-surface": { fill: c.accent_surface, stroke: c.accent, text: c.text_primary },
        "dark": { fill: c.dark, stroke: c.dark, text: c.text_on_accent },
        "success": { fill: c.success, stroke: c.accent, text: c.text_primary },
        "warning": { fill: c.warning, stroke: c.accent, text: c.text_primary },
        "raster": { fill: c.raster, stroke: c.accent, text: c.text_primary },
        "muted": { fill: c.muted, stroke: c.border, text: c.text_secondary },
        "raised": { fill: c.raised, stroke: c.border, text: c.text_primary },
        "surface": { fill: c.surface, stroke: c.border, text: c.text_primary },
        "headline": { fill: c.raised, stroke: c.raised, text: c.text_primary },
        "title": { fill: c.raised, stroke: c.raised, text: c.text_primary },
        "body": { fill: c.raised, stroke: c.raised, text: c.text_secondary },
        "eyebrow": { fill: c.raised, stroke: c.raised, text: c.accent },
    };
    return styles[style] || styles.surface;
}
function markGenerated(node, spec) {
    node.setPluginData("scd:managed", "true");
    node.setPluginData("scd:semantic-id", spec.semantic_id);
    node.setPluginData("scd:type", spec.type);
    node.setPluginData("scd:role", spec.role);
}
async function createText(content, bounds, style, font, tokens, name, semanticId) {
    const node = figma.createText();
    node.name = name;
    node.fontName = font;
    node.fontSize = style === "headline" ? tokens.type_scale.headline : style === "title" ? tokens.type_scale.title : style === "eyebrow" ? tokens.type_scale.eyebrow : tokens.type_scale.body;
    node.lineHeight = { unit: "PERCENT", value: 130 };
    node.characters = content;
    node.textAutoResize = "HEIGHT";
    node.resize(bounds.width, Math.max(bounds.height, 1));
    node.x = bounds.x;
    node.y = bounds.y;
    node.fills = solid(palette(style, tokens).text);
    if (semanticId) {
        node.setPluginData("scd:managed", "true");
        node.setPluginData("scd:semantic-id", semanticId);
        node.setPluginData("scd:type", "text");
    }
    return { node, overflow: node.height > bounds.height + 1 };
}
function styleContainer(node, style, tokens, dashed = false) {
    const colors = palette(style, tokens);
    node.fills = solid(colors.fill);
    node.strokes = solid(colors.stroke);
    node.strokeWeight = tokens.spacing.stroke_width;
    if (dashed)
        node.dashPattern = [tokens.spacing.base * 1.5, tokens.spacing.base];
    if ("cornerRadius" in node)
        node.cornerRadius = style === "accent" ? 999 : tokens.spacing.corner_radius;
}
async function createNativeNode(spec, parent, font, tokens, overflows) {
    if (spec.type === "text") {
        const created = await createText(spec.text || "", spec.bounds, spec.style, font, tokens, spec.name, spec.semantic_id);
        parent.appendChild(created.node);
        if (created.overflow)
            overflows.push(spec.semantic_id);
        return created.node;
    }
    if (spec.type === "connector") {
        const line = figma.createLine();
        line.name = spec.name;
        line.x = spec.bounds.x;
        line.y = spec.bounds.y;
        line.resize(spec.bounds.width, 0);
        line.strokes = solid(palette(spec.style, tokens).stroke);
        line.strokeWeight = tokens.spacing.stroke_width * 2;
        line.strokeCap = "ARROW_LINES";
        markGenerated(line, spec);
        parent.appendChild(line);
        return line;
    }
    if (spec.type === "rectangle") {
        const rectangle = figma.createRectangle();
        rectangle.name = spec.name;
        rectangle.x = spec.bounds.x;
        rectangle.y = spec.bounds.y;
        rectangle.resize(spec.bounds.width, spec.bounds.height);
        styleContainer(rectangle, spec.style, tokens);
        markGenerated(rectangle, spec);
        parent.appendChild(rectangle);
        return rectangle;
    }
    const frame = figma.createFrame();
    frame.name = spec.name;
    frame.x = spec.bounds.x;
    frame.y = spec.bounds.y;
    frame.resize(spec.bounds.width, spec.bounds.height);
    frame.layoutMode = "NONE";
    frame.clipsContent = false;
    const isPlaceholder = spec.type === "raster-placeholder" || spec.type === "asset-placeholder";
    styleContainer(frame, spec.style, tokens, isPlaceholder);
    if (spec.type === "pill")
        frame.cornerRadius = 999;
    markGenerated(frame, spec);
    parent.appendChild(frame);
    if (spec.text !== undefined) {
        const inset = spec.type === "pill" ? 14 : 20;
        const created = await createText(spec.text, { x: inset, y: inset, width: Math.max(20, spec.bounds.width - inset * 2), height: Math.max(20, spec.bounds.height - inset * 2) }, spec.style, font, tokens, `${spec.name}_TEXT`, `${spec.semantic_id}/text`);
        frame.appendChild(created.node);
        if (created.overflow)
            overflows.push(`${spec.semantic_id}/text`);
    }
    for (const child of spec.children || [])
        await createNativeNode(child, frame, font, tokens, overflows);
    return frame;
}
function annotationRows(scene) {
    const a = scene.annotations;
    const states = scene.states.map((item) => `${item.id}@${item.at_seconds}s · ${item.description}`).join("\n") || "—";
    const events = scene.events.map((item) => `${item.id}@${item.at_seconds}s · ${item.type}`).join(" · ") || "—";
    const anchors = scene.transition_anchors.map((item) => `${item.edge}:${item.id}@${item.at_seconds}s${item.carry_to_scene_id ? ` → ${item.carry_to_scene_id}` : ""}`).join(" · ") || "—";
    const production = scene.production_semantics.objects.map((item) => `${item.semantic_id} · ${item.role} · ${item.editable ? "editable" : "asset"}`).join("\n") || "—";
    return [
        ["PURPOSE", `${a.purpose}\n${a.message}`],
        ["VO / COPY", `${a.voiceover || "—"}\n${a.on_screen_copy || "—"}`],
        ["MOTION / TRANSITION", `${a.motion.join(" → ") || "—"}\nOut: ${a.transition_out || "—"}`],
        ["STATES / EVENTS", `${states}\nEvents: ${events}`],
        ["ANCHORS / PRODUCTION", `${anchors}\nObjects:\n${production}`],
        ["SOURCES", `Refs: ${a.reference_ids.join(", ") || "—"}\nEvidence: ${a.evidence_ids.join(", ") || "—"}`],
        ["LOCKED", a.locked.join(" · ") || "—"],
        ["CREATIVE FREEDOM", a.creative_freedom.join(" · ") || "—"],
    ];
}
async function createAnnotationPanel(scene, manifest, font, overflows) {
    const panel = figma.createFrame();
    try {
        panel.name = "90_VISIBLE_HANDOFF_NOTES";
        panel.resize(manifest.canvas.annotation_width, manifest.canvas.height);
        panel.x = manifest.canvas.width + manifest.canvas.annotation_gap;
        panel.y = 0;
        panel.layoutMode = "NONE";
        panel.clipsContent = false;
        panel.fills = solid(manifest.tokens.colors.dark);
        panel.cornerRadius = manifest.tokens.spacing.corner_radius;
        panel.setPluginData("scd:managed", "true");
        panel.setPluginData("scd:semantic-id", `${scene.semantic_id}/annotations`);
        const heading = await createText(`${scene.id} · ${scene.duration_seconds}s\n${scene.recipe}@${scene.recipe_version} · ${scene.pattern_version}`, { x: 28, y: 28, width: manifest.canvas.annotation_width - 56, height: 70 }, "title", font, manifest.tokens, "91_SCENE_META", `${scene.semantic_id}/annotations/meta`);
        heading.node.fills = solid(manifest.tokens.colors.text_on_accent);
        panel.appendChild(heading.node);
        let y = 126;
        const rows = annotationRows(scene);
        for (let index = 0; index < rows.length; index += 1) {
            const [label, content] = rows[index];
            const height = index < 3 ? 120 : 92;
            const card = figma.createFrame();
            card.name = `92_NOTE_${String(index + 1).padStart(2, "0")}_${label.replace(/[^A-Z]+/g, "_")}`;
            card.resize(manifest.canvas.annotation_width - 56, height);
            card.x = 28;
            card.y = y;
            card.layoutMode = "NONE";
            card.fills = solid(manifest.tokens.colors.dark);
            card.strokes = solid(manifest.tokens.colors.border);
            card.cornerRadius = Math.max(4, manifest.tokens.spacing.corner_radius - manifest.tokens.spacing.base / 2);
            card.setPluginData("scd:managed", "true");
            card.setPluginData("scd:semantic-id", `${scene.semantic_id}/annotations/${index + 1}`);
            const labelNode = await createText(label, { x: 16, y: 14, width: card.width - 32, height: 20 }, "eyebrow", font, manifest.tokens, `${card.name}_LABEL`);
            labelNode.node.fills = solid(manifest.tokens.colors.accent_surface);
            card.appendChild(labelNode.node);
            const contentNode = await createText(content, { x: 16, y: 44, width: card.width - 32, height: height - 56 }, "body", font, manifest.tokens, `${card.name}_CONTENT`);
            contentNode.node.fills = solid(manifest.tokens.colors.text_on_accent);
            card.appendChild(contentNode.node);
            if (contentNode.overflow)
                overflows.push(`${scene.semantic_id}/annotations/${index + 1}`);
            panel.appendChild(card);
            y += height + 12;
        }
        return panel;
    }
    catch (error) {
        panel.remove();
        throw error;
    }
}
function legacyFingerprint(root) {
    const values = [];
    function visit(node) {
        const semantic = node.getPluginData("scd:semantic-id");
        if (semantic) {
            const text = node.type === "TEXT" ? node.characters : "";
            values.push(`${semantic}|${node.type}|${Math.round(node.x * 10)}|${Math.round(node.y * 10)}|${Math.round(node.width * 10)}|${Math.round(node.height * 10)}|${text}`);
        }
        if ("children" in node)
            for (const child of node.children)
                visit(child);
    }
    visit(root);
    let hash = 2166136261;
    const joined = values.sort().join("\n");
    for (let index = 0; index < joined.length; index += 1) {
        hash ^= joined.charCodeAt(index);
        hash = Math.imul(hash, 16777619);
    }
    return (hash >>> 0).toString(16).padStart(8, "0");
}
const VISUAL_FINGERPRINT_PROPERTIES = [
    "visible", "opacity", "blendMode", "isMask", "rotation",
    "fills", "strokes", "strokeWeight", "strokeAlign", "strokeCap", "strokeJoin", "dashPattern",
    "fillStyleId", "strokeStyleId", "effects", "effectStyleId", "boundVariables",
    "cornerRadius", "topLeftRadius", "topRightRadius", "bottomRightRadius", "bottomLeftRadius",
    "clipsContent", "layoutMode", "layoutWrap", "itemSpacing", "counterAxisSpacing",
    "paddingTop", "paddingRight", "paddingBottom", "paddingLeft", "primaryAxisAlignItems", "counterAxisAlignItems",
    "layoutAlign", "layoutGrow", "constraints",
    "characters", "fontName", "fontSize", "fontWeight", "textStyleId", "textAlignHorizontal", "textAlignVertical",
    "lineHeight", "letterSpacing", "paragraphIndent", "paragraphSpacing", "textCase", "textDecoration",
    "variantProperties", "componentProperties",
];
function fingerprintValue(value, seen, depth = 0) {
    if (value === undefined)
        return "[undefined]";
    if (value === null || typeof value === "string" || typeof value === "boolean")
        return value;
    if (typeof value === "number")
        return Number.isFinite(value) ? Math.round(value * 10000) / 10000 : String(value);
    if (typeof value === "symbol")
        return String(value);
    if (typeof value !== "object")
        return `[${typeof value}]`;
    if (depth >= 8)
        return "[max-depth]";
    if (seen.has(value))
        return "[circular]";
    seen.add(value);
    let normalized;
    if (Array.isArray(value)) {
        normalized = value.map((item) => fingerprintValue(item, seen, depth + 1));
    }
    else {
        const record = value;
        const result = {};
        for (const key of Object.keys(record).sort())
            result[key] = fingerprintValue(record[key], seen, depth + 1);
        normalized = result;
    }
    seen.delete(value);
    return normalized;
}
function fingerprint(root) {
    const values = [];
    function visit(node, path) {
        const record = node;
        const visual = {
            path,
            semanticId: node.getPluginData("scd:semantic-id"),
            type: node.type,
            name: node.name,
            x: node.x,
            y: node.y,
            width: node.width,
            height: node.height,
        };
        for (const property of VISUAL_FINGERPRINT_PROPERTIES)
            visual[property] = record[property];
        values.push(JSON.stringify(fingerprintValue(visual, new Set())));
        if ("children" in node)
            node.children.forEach((child, index) => visit(child, `${path}.${index}`));
    }
    visit(root, "0");
    const joined = values.join("\n");
    let fnv = 2166136261;
    let djb = 5381;
    for (let index = 0; index < joined.length; index += 1) {
        const code = joined.charCodeAt(index);
        fnv ^= code;
        fnv = Math.imul(fnv, 16777619);
        djb = Math.imul(djb, 33) ^ code;
    }
    return `${(fnv >>> 0).toString(16).padStart(8, "0")}${(djb >>> 0).toString(16).padStart(8, "0")}`;
}
function saveGeneratedFingerprint(board) {
    board.setPluginData("scd:generated-fingerprint", legacyFingerprint(board));
    board.setPluginData("scd:generated-fingerprint-v2", fingerprint(board));
}
function scanBoards(page) {
    return page.findAll((node) => node.type === "FRAME" && node.getPluginData("scd:board") === "true").map((node) => {
        const board = node;
        const savedV2 = board.getPluginData("scd:generated-fingerprint-v2");
        const savedLegacy = board.getPluginData("scd:generated-fingerprint");
        return {
            board,
            sceneId: board.getPluginData("scd:scene-id"),
            revision: board.getPluginData("scd:source-revision"),
            contentHash: board.getPluginData("scd:content-hash"),
            operationId: board.getPluginData("scd:operation-id"),
            state: board.getPluginData("scd:operation-state"),
            humanEdited: savedV2 ? savedV2 !== fingerprint(board) : Boolean(savedLegacy) && savedLegacy !== legacyFingerprint(board),
        };
    });
}
function operationReceiptKey(manifest) {
    return `scd:receipt:${manifest.operation.manifest_hash}`;
}
function exactCompleteBoard(scene, existing) {
    return existing.find((item) => item.sceneId === scene.id && item.revision === scene.source_revision && item.contentHash === scene.content_hash && item.state === "complete");
}
function writeOperationReceipt(page, manifest, boards) {
    const byScene = new Map(boards.map((item) => [item.sceneId, item]));
    const receipt = {
        version: 1,
        operationId: manifest.operation.id,
        manifestHash: manifest.operation.manifest_hash,
        scenes: manifest.scenes.map((scene) => {
            const existing = byScene.get(scene.id);
            if (!existing)
                throw new Error(`Cannot record operation receipt: missing board for ${scene.id}`);
            return {
                sceneId: scene.id,
                boardNodeId: existing.board.id,
                revision: scene.source_revision,
                contentHash: scene.content_hash,
            };
        }),
    };
    page.setPluginData(operationReceiptKey(manifest), JSON.stringify(receipt));
}
function readOperationReceipt(page, manifest, existing) {
    const raw = page.getPluginData(operationReceiptKey(manifest));
    if (!raw)
        return { state: "missing", boards: [] };
    try {
        const value = JSON.parse(raw);
        if (!isRecord(value) || value.version !== 1 || value.operationId !== manifest.operation.id || value.manifestHash !== manifest.operation.manifest_hash || !Array.isArray(value.scenes) || value.scenes.length !== manifest.scenes.length) {
            return { state: "invalid", boards: [] };
        }
        const existingByNodeId = new Map(existing.map((item) => [item.board.id, item]));
        const receiptByScene = new Map();
        for (const entryValue of value.scenes) {
            if (!isRecord(entryValue) || typeof entryValue.sceneId !== "string" || receiptByScene.has(entryValue.sceneId))
                return { state: "invalid", boards: [] };
            receiptByScene.set(entryValue.sceneId, entryValue);
        }
        const boards = [];
        for (const scene of manifest.scenes) {
            const entry = receiptByScene.get(scene.id);
            if (!entry || typeof entry.boardNodeId !== "string" || entry.revision !== scene.source_revision || entry.contentHash !== scene.content_hash)
                return { state: "invalid", boards: [] };
            const board = existingByNodeId.get(entry.boardNodeId);
            if (!board || board.state !== "complete" || board.sceneId !== scene.id || board.revision !== scene.source_revision || board.contentHash !== scene.content_hash)
                return { state: "invalid", boards: [] };
            boards.push(board);
        }
        return { state: "valid", boards };
    }
    catch (_error) {
        return { state: "invalid", boards: [] };
    }
}
function postReuseResult(manifest, stats, fontReport, boards, warnings, receipt) {
    const byScene = new Map(boards.map((item) => [item.sceneId, item]));
    const readback = manifest.scenes.map((scene) => reusedReadback(scene, byScene.get(scene.id)));
    figma.viewport.scrollAndZoomIntoView(boards.map((item) => item.board));
    figma.ui.postMessage({ type: "done", summary: { operationId: manifest.operation.id, receipt, created: 0, reused: readback.length, conflicts: warnings.filter((warning) => warning.includes("human edits")).length, stats, font: fontReport, scenes: readback, warnings } });
}
async function createBoard(scene, manifest, font, x) {
    const board = figma.createFrame();
    try {
        board.name = `[DRAFT ${scene.source_revision}] ${scene.name}`;
        board.resize(manifest.canvas.width + manifest.canvas.annotation_gap + manifest.canvas.annotation_width, manifest.canvas.height);
        board.x = x;
        board.y = 0;
        board.layoutMode = "NONE";
        board.clipsContent = false;
        board.fills = [];
        board.setPluginData("scd:board", "true");
        board.setPluginData("scd:managed", "true");
        board.setPluginData("scd:semantic-id", scene.semantic_id);
        board.setPluginData("scd:scene-id", scene.id);
        board.setPluginData("scd:source-revision", scene.source_revision);
        board.setPluginData("scd:content-hash", scene.content_hash);
        board.setPluginData("scd:operation-id", manifest.operation.id);
        board.setPluginData("scd:operation-state", "draft");
        const sceneFrame = figma.createFrame();
        sceneFrame.name = "00_SCENE_CANVAS";
        sceneFrame.resize(manifest.canvas.width, manifest.canvas.height);
        sceneFrame.x = 0;
        sceneFrame.y = 0;
        sceneFrame.layoutMode = "NONE";
        sceneFrame.clipsContent = true;
        sceneFrame.fills = solid(manifest.tokens.colors.canvas);
        sceneFrame.setPluginData("scd:managed", "true");
        sceneFrame.setPluginData("scd:semantic-id", `${scene.semantic_id}/canvas`);
        board.appendChild(sceneFrame);
        const overflows = [];
        for (const node of scene.nodes)
            await createNativeNode(node, sceneFrame, font, manifest.tokens, overflows);
        board.appendChild(await createAnnotationPanel(scene, manifest, font, overflows));
        saveGeneratedFingerprint(board);
        return {
            board,
            readback: {
                sceneId: scene.id,
                revision: scene.source_revision,
                contentHash: scene.content_hash,
                boardNodeId: board.id,
                status: "created",
                objectCount: board.findAll(() => true).length,
                textOverflow: overflows,
                missingAssets: scene.assets.missing,
                recipe: scene.recipe,
                recipeVersion: scene.recipe_version,
                patternVersion: scene.pattern_version,
                stateIds: scene.states.map((item) => item.id),
                eventIds: scene.events.map((item) => item.id),
                transitionAnchorIds: scene.transition_anchors.map((item) => item.id),
                productionObjectIds: scene.production_semantics.objects.map((item) => item.semantic_id),
            },
        };
    }
    catch (error) {
        board.remove();
        throw error;
    }
}
function reusedReadback(scene, existing) {
    return {
        sceneId: scene.id,
        revision: scene.source_revision,
        contentHash: scene.content_hash,
        boardNodeId: existing.board.id,
        status: "reused",
        objectCount: existing.board.findAll(() => true).length,
        textOverflow: [],
        missingAssets: scene.assets.missing,
        recipe: scene.recipe,
        recipeVersion: scene.recipe_version,
        patternVersion: scene.pattern_version,
        stateIds: scene.states.map((item) => item.id),
        eventIds: scene.events.map((item) => item.id),
        transitionAnchorIds: scene.transition_anchors.map((item) => item.id),
        productionObjectIds: scene.production_semantics.objects.map((item) => item.semantic_id),
    };
}
async function importManifest(raw) {
    const { manifest, stats } = preflight(raw);
    const { font, report: fontReport } = await resolveFont(manifest);
    let targetPage = figma.root.children.find((page) => page.name === manifest.target_page);
    const createdPages = [];
    const createdBoards = [];
    const warnings = [...manifest.warnings];
    try {
        if (!targetPage) {
            targetPage = figma.createPage();
            targetPage.name = manifest.target_page;
            createdPages.push(targetPage);
        }
        await figma.setCurrentPageAsync(targetPage);
        const existing = scanBoards(targetPage);
        const receipt = readOperationReceipt(targetPage, manifest, existing);
        if (receipt.state === "valid") {
            for (const item of receipt.boards)
                if (item.humanEdited)
                    warnings.push(`${item.sceneId}: human edits detected and preserved`);
            postReuseResult(manifest, stats, fontReport, receipt.boards, warnings, "validated");
            return;
        }
        const reconstructable = manifest.scenes.map((scene) => exactCompleteBoard(scene, existing));
        if (reconstructable.every((item) => Boolean(item))) {
            const completeBoards = reconstructable;
            writeOperationReceipt(targetPage, manifest, completeBoards);
            warnings.push(receipt.state === "invalid" ? "Operation receipt was invalid and reconstructed from exact complete boards" : "Operation receipt was reconstructed from exact complete boards");
            for (const item of completeBoards)
                if (item.humanEdited)
                    warnings.push(`${item.sceneId}: human edits detected and preserved`);
            postReuseResult(manifest, stats, fontReport, completeBoards, warnings, "reconstructed");
            return;
        }
        const sameOperation = existing.filter((item) => item.operationId === manifest.operation.id);
        if (sameOperation.length) {
            const completedIds = new Set(sameOperation.filter((item) => item.state === "complete").map((item) => item.sceneId));
            throw new Error(`Found incomplete draft for this operation (${completedIds.size}/${manifest.scenes.length} scenes). It was preserved for inspection; remove it or change the source revision before retrying.`);
        }
        const readback = [];
        let nextX = existing.reduce((right, item) => Math.max(right, item.board.x + item.board.width), -manifest.canvas.scene_gap) + manifest.canvas.scene_gap;
        for (const scene of manifest.scenes) {
            const exact = exactCompleteBoard(scene, existing);
            if (exact) {
                if (exact.humanEdited)
                    warnings.push(`${scene.id}: human edits detected and preserved; existing board reused`);
                readback.push(reusedReadback(scene, exact));
                continue;
            }
            const prior = existing.filter((item) => item.sceneId === scene.id);
            if (prior.length) {
                const edited = prior.filter((item) => item.humanEdited).length;
                warnings.push(`${scene.id}: source changed; created a new draft beside ${prior.length} preserved prior revision${edited ? ` (${edited} with human edits)` : ""}`);
            }
            const created = await createBoard(scene, manifest, font, nextX);
            targetPage.appendChild(created.board);
            createdBoards.push(created.board);
            readback.push(created.readback);
            nextX += created.board.width + manifest.canvas.scene_gap;
        }
        for (const pageName of manifest.document_pages) {
            if (!figma.root.children.some((page) => page.name === pageName)) {
                const page = figma.createPage();
                page.name = pageName;
                createdPages.push(page);
            }
        }
        for (const board of createdBoards) {
            board.setPluginData("scd:operation-state", "complete");
            saveGeneratedFingerprint(board);
        }
        const completedExisting = scanBoards(targetPage);
        const receiptBoards = manifest.scenes.map((scene) => exactCompleteBoard(scene, completedExisting));
        if (!receiptBoards.every((item) => Boolean(item)))
            throw new Error("Cannot finalize operation receipt: one or more complete scene boards are missing");
        writeOperationReceipt(targetPage, manifest, receiptBoards);
        const visible = readback.map((scene) => targetPage.findOne((node) => node.id === scene.boardNodeId)).filter((node) => Boolean(node));
        if (visible.length)
            figma.viewport.scrollAndZoomIntoView(visible);
        figma.ui.postMessage({ type: "done", summary: { operationId: manifest.operation.id, receipt: "written", created: createdBoards.length, reused: readback.length - createdBoards.length, conflicts: warnings.filter((warning) => warning.includes("source changed") || warning.includes("human edits")).length, stats, font: fontReport, scenes: readback, warnings } });
    }
    catch (error) {
        for (const board of createdBoards)
            if (!board.removed)
                board.remove();
        for (const page of createdPages.reverse())
            if (!page.removed && page.children.length === 0)
                page.remove();
        throw error;
    }
}
figma.ui.onmessage = async (message) => {
    if (message.type !== "import")
        return;
    try {
        await importManifest(message.manifest);
    }
    catch (error) {
        figma.ui.postMessage({ type: "error", message: error instanceof Error ? error.message : String(error) });
    }
};
