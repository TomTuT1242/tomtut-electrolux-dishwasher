/**
 * TomTuT Dishwasher Card v1.2.1
 * A Home Assistant Lovelace custom card for monitoring dishwasher status
 * with status-dependent images, animated overlays, power display, and controls.
 *
 * (c) 2026 TomTuT
 */

const STATIC_BASE = "/local/tomtut-dishwasher/";

const STATE_TRANSLATIONS = {
  OFF: "Aus",
  IDLE: "Bereit",
  READY_TO_START: "Startbereit",
  RUNNING: "Läuft",
  PAUSED: "Pausiert",
  DELAYED_START: "Zeitvorwahl",
  END_OF_CYCLE: "Fertig",
  ALARM: "Alarm",
  unavailable: "Nicht verfügbar",
  unknown: "Unbekannt",
};

const PHASE_TRANSLATIONS = {
  PREWASH: "Vorwäsche",
  MAINWASH: "Hauptwäsche",
  HOTRINSE: "Heißspülen",
  COLDRINSE: "Kaltspülen",
  EXTRARINSE: "Nachspülen",
  DRYING: "Trocknung",
  ADO_DRYING: "Türtrocknung",
  unavailable: "\u2014",
  unknown: "\u2014",
};

const RUNNING_STATES = ["RUNNING", "PAUSED"];
const DONE_STATES = ["END_OF_CYCLE"];

function getImageForState(state) {
  if (RUNNING_STATES.includes(state)) return STATIC_BASE + "running.png";
  if (DONE_STATES.includes(state)) return STATIC_BASE + "done.png";
  return STATIC_BASE + "closed.png";
}

function getStatusColor(state) {
  if (state === "RUNNING") return "#4CAF50";
  if (state === "PAUSED") return "#FF9800";
  if (DONE_STATES.includes(state)) return "#2196F3";
  if (state === "ALARM") return "#F44336";
  if (state === "READY_TO_START") return "#9E9E9E";
  return "#616161";
}

function formatMinutes(value) {
  if (!value || value === "unavailable" || value === "unknown") return null;
  const num = parseInt(value, 10);
  if (isNaN(num) || num <= 0) return null;
  const h = Math.floor(num / 60);
  const m = num % 60;
  return h > 0
    ? `${h}:${String(m).padStart(2, "0")}`
    : `0:${String(m).padStart(2, "0")}`;
}

function formatFinishTime(minutes) {
  if (!minutes) return null;
  const num = parseInt(minutes, 10);
  if (isNaN(num) || num <= 0) return null;
  const now = new Date();
  const finish = new Date(now.getTime() + num * 60000);
  return `${String(finish.getHours()).padStart(2, "0")}:${String(finish.getMinutes()).padStart(2, "0")}`;
}

// Which buttons to show per state
function getButtonsForState(state) {
  switch (state) {
    case "OFF": return [{ cmd: "ON", label: "Ein", icon: "power" }];
    case "IDLE":
    case "READY_TO_START":
      return [
        { cmd: "START", label: "Start", icon: "play" },
        { cmd: "OFF", label: "Aus", icon: "power-off" },
      ];
    case "RUNNING":
      return [
        { cmd: "PAUSE", label: "Pause", icon: "pause" },
        { cmd: "STOPRESET", label: "Stop", icon: "stop" },
      ];
    case "PAUSED":
      return [
        { cmd: "RESUME", label: "Weiter", icon: "play" },
        { cmd: "STOPRESET", label: "Stop", icon: "stop" },
      ];
    case "DELAYED_START":
      return [{ cmd: "STOPRESET", label: "Abbrechen", icon: "stop" }];
    case "END_OF_CYCLE":
      return [{ cmd: "STOPRESET", label: "Reset", icon: "refresh" }];
    default:
      return [];
  }
}

const ICON_PATHS = {
  power: "M16.56 5.44l-1.45 1.45A5.97 5.97 0 0118 12c0 3.31-2.69 6-6 6s-6-2.69-6-6c0-2.17 1.16-4.06 2.88-5.12L7.44 5.44A7.96 7.96 0 004 12c0 4.42 3.58 8 8 8s8-3.58 8-8c0-2.56-1.2-4.83-3.07-6.31zM13 3h-2v10h2V3z",
  "power-off": "M16.56 5.44l-1.45 1.45A5.97 5.97 0 0118 12c0 3.31-2.69 6-6 6s-6-2.69-6-6c0-2.17 1.16-4.06 2.88-5.12L7.44 5.44A7.96 7.96 0 004 12c0 4.42 3.58 8 8 8s8-3.58 8-8c0-2.56-1.2-4.83-3.07-6.31zM13 3h-2v10h2V3z",
  play: "M8 5v14l11-7z",
  pause: "M6 19h4V5H6v14zm8-14v14h4V5h-4z",
  stop: "M6 6h12v12H6z",
  refresh: "M17.65 6.35A7.96 7.96 0 0012 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08A5.99 5.99 0 0112 18c-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z",
  bolt: "M11 21h-1l1-7H7.5c-.88 0-.33-.75-.31-.78C8.48 10.94 10.42 7.54 13.01 3h1l-1 7h3.51c.4 0 .62.19.4.66C12.97 17.55 11 21 11 21z",
};

class TomtutDishwasherCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = null;
    this._hass = null;
    this._imageCache = {};
  }

  static getStubConfig() {
    return { type: "custom:tomtut-dishwasher-card" };
  }

  setConfig(config) {
    // entity_state not required anymore — auto-discover fills it
    this._config = { ...config };
    this._autoDiscovered = false;
    this._render();
  }

  _autoDiscover(hass) {
    if (this._autoDiscovered) return;
    this._autoDiscovered = true;

    // Find entities from the electrolux_dishwasher integration
    const allIds = Object.keys(hass.states);
    const find = (prefix, suffix) => {
      // First try configured value
      const configKey = `entity_${suffix.replace("binary_", "")}`;
      if (this._config[configKey]) return;
      // Auto-discover: find entity matching pattern
      const match = allIds.find(id =>
        id.startsWith(prefix) && id.includes("geschirrspulmaschine") && id.includes(suffix)
      ) || allIds.find(id =>
        id.startsWith(prefix) && id.includes("spulmaschine") && id.includes(suffix)
      ) || allIds.find(id =>
        id.startsWith(prefix) && id.includes("dishwasher") && id.includes(suffix)
      );
      if (match) this._config[`entity_${suffix.replace("binary_", "")}`] = match;
    };

    const findBtn = (suffix, configKey) => {
      if (this._config[configKey]) return;
      const match = allIds.find(id =>
        id.startsWith("button.") && id.includes("geschirrspulmaschine") && id.includes(suffix)
      ) || allIds.find(id =>
        id.startsWith("button.") && id.includes("spulmaschine") && id.includes(suffix)
      ) || allIds.find(id =>
        id.startsWith("button.") && id.includes("dishwasher") && id.includes(suffix)
      );
      if (match) this._config[configKey] = match;
    };

    // Auto-discover sensors
    if (!this._config.entity_state) {
      const s = allIds.find(id => id.startsWith("sensor.") && id.includes("spulmaschine") && id.endsWith("_status"));
      if (s) this._config.entity_state = s;
    }
    if (!this._config.entity_phase) {
      const s = allIds.find(id => id.startsWith("sensor.") && id.includes("spulmaschine") && id.endsWith("_phase"));
      if (s) this._config.entity_phase = s;
    }
    if (!this._config.entity_program) {
      const s = allIds.find(id => id.startsWith("sensor.") && id.includes("spulmaschine") && id.endsWith("_programm"));
      if (s) this._config.entity_program = s;
    }
    if (!this._config.entity_time) {
      const s = allIds.find(id => id.startsWith("sensor.") && id.includes("spulmaschine") && id.endsWith("_restzeit"));
      if (s) this._config.entity_time = s;
    }
    if (!this._config.entity_door) {
      const s = allIds.find(id => id.startsWith("binary_sensor.") && id.includes("spulmaschine") && id.endsWith("_tur"));
      if (s) this._config.entity_door = s;
    }
    if (!this._config.entity_running) {
      const s = allIds.find(id => id.startsWith("binary_sensor.") && id.includes("spulmaschine") && id.endsWith("_lauft"));
      if (s) this._config.entity_running = s;
    }
    if (!this._config.entity_salt) {
      const s = allIds.find(id => id.startsWith("binary_sensor.") && id.includes("spulmaschine") && id.endsWith("_salz_fehlt"));
      if (s) this._config.entity_salt = s;
    }
    if (!this._config.entity_rinse_aid) {
      const s = allIds.find(id => id.startsWith("binary_sensor.") && id.includes("spulmaschine") && id.endsWith("_klarspuler_niedrig"));
      if (s) this._config.entity_rinse_aid = s;
    }

    // Auto-discover buttons
    findBtn("einschalten", "button_on");
    findBtn("ausschalten", "button_off");
    findBtn("_start", "button_start");
    findBtn("_pause", "button_pause");
    findBtn("fortsetzen", "button_resume");
    findBtn("stop_reset", "button_stopreset");
  }

  set hass(hass) {
    const oldHass = this._hass;
    this._hass = hass;
    if (this._config) {
      this._autoDiscover(hass);
      const keys = [
        "entity_state", "entity_phase", "entity_program", "entity_time",
        "entity_door", "entity_running", "entity_salt", "entity_rinse_aid",
        "entity_power",
      ];
      let changed = !oldHass;
      if (!changed) {
        for (const key of keys) {
          const eid = this._config[key];
          if (eid && oldHass.states[eid] !== hass.states[eid]) {
            changed = true;
            break;
          }
        }
      }
      if (changed) this._render();
    }
  }

  getCardSize() {
    return 7;
  }

  _getStateValue(entityKey) {
    const entityId = this._config[entityKey];
    if (!entityId || !this._hass) return "unavailable";
    const entity = this._hass.states[entityId];
    if (!entity) return "unavailable";
    return entity.state;
  }

  _getEntity(entityKey) {
    const entityId = this._config[entityKey];
    if (!entityId || !this._hass) return null;
    return this._hass.states[entityId] || null;
  }

  _preloadImages() {
    const urls = [STATIC_BASE + "closed.png", STATIC_BASE + "running.png", STATIC_BASE + "done.png"];
    for (const url of urls) {
      if (!this._imageCache[url]) {
        const img = new Image();
        img.src = url;
        this._imageCache[url] = img;
      }
    }
  }

  _callService(command) {
    if (!this._hass) return;
    // Find the button entity for this command
    // All button entity_ids must come from config
    const cmdConfigKey = {
      ON: "button_on",
      OFF: "button_off",
      START: "button_start",
      PAUSE: "button_pause",
      RESUME: "button_resume",
      STOPRESET: "button_stopreset",
    };
    const entityId = this._config[cmdConfigKey[command]];
    if (entityId) {
      this._hass.callService("button", "press", { entity_id: entityId });
    }
  }

  _render() {
    if (!this._config || !this.shadowRoot) return;
    this._preloadImages();

    const rawState = this._getStateValue("entity_state");
    const state = rawState ? rawState.toUpperCase() : "UNAVAILABLE";
    const stateLabel = STATE_TRANSLATIONS[rawState] || STATE_TRANSLATIONS[state] || rawState;
    const statusColor = getStatusColor(state);

    const rawPhase = this._getStateValue("entity_phase");
    const phase = rawPhase ? rawPhase.toUpperCase() : "";
    const phaseLabel = PHASE_TRANSLATIONS[rawPhase] || PHASE_TRANSLATIONS[phase] || rawPhase;

    const rawProgram = this._getStateValue("entity_program");
    const program = rawProgram && rawProgram !== "unavailable" && rawProgram !== "unknown" ? rawProgram : null;

    const timeRaw = this._getStateValue("entity_time");
    const timeFormatted = formatMinutes(timeRaw);
    const finishTime = formatFinishTime(timeRaw);

    const isRunning = state === "RUNNING";
    const isPaused = state === "PAUSED";
    const isActive = RUNNING_STATES.includes(state);
    const isDone = DONE_STATES.includes(state);

    const saltAlert = this._getStateValue("entity_salt") === "on";
    const rinseAlert = this._getStateValue("entity_rinse_aid") === "on";

    // Power (optional)
    const powerEntity = this._getEntity("entity_power");
    const powerValue = powerEntity && powerEntity.state !== "unavailable" && powerEntity.state !== "unknown"
      ? Math.round(parseFloat(powerEntity.state)) : null;
    const powerUnit = powerEntity?.attributes?.unit_of_measurement || "W";

    const imageSrc = getImageForState(state);
    const buttons = getButtonsForState(state);

    // --- Build IMAGE OVERLAY (only badges + time, NO buttons/warnings) ---
    const programHtml = program ? `<div class="program-badge">${this._esc(program)}</div>` : "";

    // Phase: moved to control bar
    const showPhase = isActive && phaseLabel && phaseLabel !== "\u2014" && rawPhase !== "UNAVAILABLE" && rawPhase !== "unavailable";
    const phaseHtml = ""; // no longer on image

    // Time + finish time on image
    let timeHtml = "";
    if (isActive && timeFormatted) {
      timeHtml = `<div class="time-display">
        <div class="time-icon">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="white">
            <path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z"/>
          </svg>
        </div>
        <span class="time-value">${this._esc(timeFormatted)}</span>
        ${finishTime ? `<span class="finish-time">| ${finishTime}</span>` : ""}
      </div>`;
    }

    // Done indicator on image
    const doneHtml = isDone ? `<div class="done-indicator">
      <svg viewBox="0 0 24 24" width="40" height="40">
        <path fill="#4CAF50" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
      </svg>
    </div>` : "";

    const runningOverlayHtml = isRunning ? `<div class="running-overlay"></div>` : "";

    // --- CONTROL BAR under image: warnings + power + buttons ---
    let warningBadges = "";
    if (saltAlert) {
      warningBadges += `<div class="warning-badge">
        <svg viewBox="0 0 24 24" width="18" height="18"><path fill="#FFA726" d="M8 2h8v2H8V2zm0 4h8l1 2H7l1-2zm-1 4h10l1 10c0 1.1-.9 2-2 2H8c-1.1 0-2-.9-2-2L7 10zm3 2v7h1v-7h-1zm3 0v7h1v-7h-1z"/></svg>
        <span>Salz</span>
      </div>`;
    }
    if (rinseAlert) {
      warningBadges += `<div class="warning-badge">
        <svg viewBox="0 0 24 24" width="18" height="18"><path fill="#FFA726" d="M12 2c-5.33 4.55-8 8.48-8 11.8 0 4.98 3.8 8.2 8 8.2s8-3.22 8-8.2C20 10.48 17.33 6.55 12 2zm0 18c-3.35 0-6-2.57-6-6.2 0-2.34 1.95-5.44 6-9.14 4.05 3.7 6 6.79 6 9.14 0 3.63-2.65 6.2-6 6.2z"/></svg>
        <span>Klarspüler</span>
      </div>`;
    }

    let powerBadge = "";
    if (powerValue !== null) {
      const powerColor = powerValue > 10 ? "#FFA726" : "#666";
      powerBadge = `<div class="power-badge" style="color: ${powerColor};">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="${powerColor}">
          <path d="${ICON_PATHS.bolt}"/>
        </svg>
        <span>${powerValue} ${this._esc(powerUnit)}</span>
      </div>`;
    }

    let btnHtml = buttons.map(b => `
      <button class="ctrl-btn" data-cmd="${b.cmd}" title="${b.label}">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
          <path d="${ICON_PATHS[b.icon] || ""}"/>
        </svg>
        <span>${this._esc(b.label)}</span>
      </button>
    `).join("");

    // Phase badge for control bar
    const phaseBadge = showPhase ? `<div class="phase-badge">${this._esc(phaseLabel)}</div>` : "";

    // Always show control bar when there's anything to show
    const hasControlBar = phaseBadge || warningBadges || powerBadge || btnHtml;
    const controlHtml = hasControlBar ? `<div class="control-bar">
      <div class="control-left">${phaseBadge}${warningBadges}${powerBadge}</div>
      <div class="ctrl-buttons">${btnHtml}</div>
    </div>` : "";

    this.shadowRoot.innerHTML = `
      <style>${TomtutDishwasherCard._styles()}</style>
      <ha-card>
        <div class="card-container">
          <div class="image-wrapper" style="${this._config.image_height ? `height:${this._config.image_height}px` : ""}">
            <img class="dish-image" src="${imageSrc}" alt="Geschirrspülmaschine" />
            ${runningOverlayHtml}
          </div>
          <div class="overlay">
            <div class="status-badge" style="background-color: ${statusColor};">${this._esc(stateLabel)}</div>
            ${programHtml}
            ${timeHtml}
            ${doneHtml}
          </div>
        </div>
        ${controlHtml}
      </ha-card>
    `;

    // Attach button click handlers
    this.shadowRoot.querySelectorAll(".ctrl-btn").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const cmd = btn.getAttribute("data-cmd");
        if (cmd) this._callService(cmd);
      });
    });
  }

  _esc(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  static _styles() {
    return `
      :host { display: block; }

      ha-card {
        overflow: hidden;
        background: #1c1c1e;
        border-radius: var(--ha-card-border-radius, 12px);
        border: none;
      }

      .card-container {
        position: relative;
        width: 100%;
        overflow: hidden;
      }

      .image-wrapper {
        position: relative;
        width: 100%;
        line-height: 0;
        overflow: hidden;
      }

      .dish-image {
        width: 100%;
        height: 100%;
        object-fit: cover;
        display: block;
        transition: opacity 0.8s ease-in-out;
      }

      .running-overlay {
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        pointer-events: none;
        background: radial-gradient(ellipse at 50% 55%, rgba(33,150,243,0.20) 0%, rgba(33,150,243,0.08) 35%, transparent 65%);
        animation: pulseGlow 2.5s ease-in-out infinite;
      }

      @keyframes pulseGlow {
        0%, 100% { opacity: 0.35; }
        50% { opacity: 1; }
      }

      .overlay {
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        pointer-events: none;
      }

      .status-badge {
        position: absolute;
        top: 12px; left: 12px;
        padding: 5px 14px;
        border-radius: 20px;
        color: white;
        font-size: 13px;
        font-weight: 600;
        letter-spacing: 0.4px;
        text-transform: uppercase;
        box-shadow: 0 2px 8px rgba(0,0,0,0.45);
        backdrop-filter: blur(6px);
        -webkit-backdrop-filter: blur(6px);
      }

      .program-badge {
        position: absolute;
        top: 12px; right: 12px;
        padding: 5px 14px;
        border-radius: 20px;
        color: white;
        font-size: 13px;
        font-weight: 600;
        letter-spacing: 0.4px;
        background: rgba(255,255,255,0.16);
        box-shadow: 0 2px 8px rgba(0,0,0,0.35);
        backdrop-filter: blur(6px);
        -webkit-backdrop-filter: blur(6px);
      }

      /* Phase badge in control bar */
      .phase-badge {
        padding: 4px 12px;
        border-radius: 16px;
        color: rgba(255,255,255,0.85);
        font-size: 12px;
        font-weight: 500;
        background: rgba(255,255,255,0.1);
        white-space: nowrap;
      }

      .time-display {
        position: absolute;
        bottom: 10px;
        left: 50%;
        transform: translateX(-50%);
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 6px 20px;
        border-radius: 24px;
        background: rgba(0,0,0,0.6);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        box-shadow: 0 2px 14px rgba(0,0,0,0.45);
      }

      .time-icon { display: flex; align-items: center; opacity: 0.85; }

      .time-value {
        color: white;
        font-size: 24px;
        font-weight: 700;
        font-variant-numeric: tabular-nums;
        letter-spacing: 1.5px;
      }

      .finish-time {
        color: rgba(255,255,255,0.6);
        font-size: 14px;
        font-weight: 400;
        margin-left: 4px;
      }

      /* Warnings moved to control bar */

      .done-indicator {
        position: absolute;
        bottom: 10px;
        left: 50%;
        transform: translateX(-50%);
        display: flex;
        align-items: center;
        justify-content: center;
        width: 58px; height: 58px;
        border-radius: 50%;
        background: rgba(0,0,0,0.5);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        box-shadow: 0 2px 18px rgba(76,175,80,0.45);
        animation: doneAppear 0.5s ease-out;
      }

      @keyframes doneAppear {
        0% { transform: translateX(-50%) scale(0); opacity: 0; }
        100% { transform: translateX(-50%) scale(1); opacity: 1; }
      }

      /* ── Control bar under image ── */
      .control-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 10px 14px;
        background: #2c2c2e;
        border-top: 1px solid rgba(255,255,255,0.06);
        gap: 8px;
      }

      .control-left {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-shrink: 0;
      }

      .warning-badge {
        display: flex;
        align-items: center;
        gap: 4px;
        padding: 4px 10px;
        border-radius: 16px;
        background: rgba(255,167,38,0.12);
        border: 1px solid rgba(255,167,38,0.3);
        color: #FFA726;
        font-size: 11px;
        font-weight: 500;
        animation: warningPulse 2s ease-in-out infinite;
      }

      @keyframes warningPulse {
        0%, 100% { border-color: rgba(255,167,38,0.3); }
        50% { border-color: rgba(255,167,38,0.7); }
      }

      .power-badge {
        display: flex;
        align-items: center;
        gap: 5px;
        font-size: 14px;
        font-weight: 600;
        font-variant-numeric: tabular-nums;
      }

      .ctrl-buttons {
        display: flex;
        gap: 8px;
      }

      .ctrl-btn {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 8px 16px;
        border: none;
        border-radius: 20px;
        background: rgba(255,255,255,0.08);
        color: rgba(255,255,255,0.85);
        font-size: 13px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
        pointer-events: auto;
      }

      .ctrl-btn:hover {
        background: rgba(255,255,255,0.16);
        color: white;
      }

      .ctrl-btn:active {
        transform: scale(0.95);
        background: rgba(255,255,255,0.22);
      }

      /* Responsive */
      @media (max-width: 400px) {
        .status-badge, .program-badge { font-size: 11px; padding: 4px 10px; }
        .time-value { font-size: 18px; }
        .finish-time { font-size: 11px; }
        .phase-label { font-size: 11px; }
        .warning-icon { width: 34px; height: 34px; }
        .warning-icon svg { width: 22px; height: 22px; }
        .done-indicator { width: 46px; height: 46px; }
        .done-indicator svg { width: 32px; height: 32px; }
        .ctrl-btn { padding: 6px 10px; font-size: 11px; }
        .ctrl-btn span { display: none; }
        .power-badge { font-size: 12px; }
      }
    `;
  }
}

customElements.define("tomtut-dishwasher-card", TomtutDishwasherCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "tomtut-dishwasher-card",
  name: "TomTuT Dishwasher Card",
  description: "Visual dishwasher status card with state-dependent images and controls",
  preview: true,
});

console.info(
  "%c TOMTUT-DISHWASHER-CARD %c v1.2.1 ",
  "color: white; background: #4CAF50; font-weight: bold; padding: 2px 6px; border-radius: 4px 0 0 4px;",
  "color: #4CAF50; background: #1c1c1e; font-weight: bold; padding: 2px 6px; border-radius: 0 4px 4px 0;"
);
