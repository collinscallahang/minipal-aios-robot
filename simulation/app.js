const State = {
  IDLE: "IDLE",
  WAKE: "WAKE",
  TRACK: "TRACK",
  ALERT: "ALERT",
  EMERGENCY: "EMERGENCY_BRAKE",
  COOLDOWN: "COOLDOWN",
};

const AI_BRIDGE_URL =
  new URLSearchParams(window.location.search).get("bridge") || "http://127.0.0.1:8890";
const BRIDGE_TIMEOUT_MS = 3200;
const ALLOWED_ACTIONS = new Set(["GREET", "THINK", "RETREAT", "IDLE"]);

const state = {
  robotState: State.IDLE,
  distance: 36,
  obstacle: false,
  emergencyObstacle: false,
  aiMode: "local",
  bridgeOnline: false,
  action: "IDLE",
  servo: 90,
  led: "standby",
  buzzer: "静音",
  stateStartedAt: performance.now(),
  actionConsumed: false,
};

const els = {
  robotHead: document.querySelector("#robotHead"),
  ledRing: document.querySelector("#ledRing"),
  speakerSlot: document.querySelector("#speakerSlot"),
  connectionStatus: document.querySelector("#connectionStatus"),
  stateReadout: document.querySelector("#stateReadout"),
  distanceValue: document.querySelector("#distanceValue"),
  distanceSlider: document.querySelector("#distanceSlider"),
  distanceBeam: document.querySelector("#distanceBeam"),
  wakeButton: document.querySelector("#wakeButton"),
  resetButton: document.querySelector("#resetButton"),
  localMode: document.querySelector("#localMode"),
  cloudMode: document.querySelector("#cloudMode"),
  bridgeStatus: document.querySelector("#bridgeStatus"),
  chatForm: document.querySelector("#chatForm"),
  chatInput: document.querySelector("#chatInput"),
  chatWindow: document.querySelector("#chatWindow"),
  servoReadout: document.querySelector("#servoReadout"),
  ledReadout: document.querySelector("#ledReadout"),
  buzzerReadout: document.querySelector("#buzzerReadout"),
  actionReadout: document.querySelector("#actionReadout"),
  logWindow: document.querySelector("#logWindow"),
  stateNodes: document.querySelectorAll(".state-node"),
  normalScenario: document.querySelector("#normalScenario"),
  alertScenario: document.querySelector("#alertScenario"),
  thinkingScenario: document.querySelector("#thinkingScenario"),
};

const ledMap = {
  standby: { label: "待机蓝", color: "#2d75b9", glow: "rgba(45, 117, 185, 0.58)" },
  wake: { label: "唤醒绿", color: "#36a269", glow: "rgba(54, 162, 105, 0.58)" },
  track: { label: "运行白", color: "#f7fbff", glow: "rgba(45, 117, 185, 0.35)" },
  alert: { label: "告警红", color: "#c94c3f", glow: "rgba(201, 76, 63, 0.66)" },
  cooldown: { label: "冷却橙", color: "#d58c1f", glow: "rgba(213, 140, 31, 0.6)" },
};

function nowLabel() {
  return new Date().toLocaleTimeString("zh-CN", { hour12: false });
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function normalizeAction(action) {
  const normalized = String(action || "").trim().toUpperCase();
  return ALLOWED_ACTIONS.has(normalized) ? normalized : "GREET";
}

function log(line, kind = "mcu") {
  const row = document.createElement("div");
  row.className = `log-line ${kind}`;
  row.textContent = `[${nowLabel()}] ${line}`;
  els.logWindow.prepend(row);

  while (els.logWindow.children.length > 80) {
    els.logWindow.lastElementChild.remove();
  }
}

function setBridgeOnline(isOnline) {
  state.bridgeOnline = isOnline;
  els.bridgeStatus.textContent = isOnline ? "已连接" : "离线回退";
  els.bridgeStatus.classList.toggle("is-online", isOnline);
  els.connectionStatus.textContent = isOnline ? "UART SIM + AI Bridge" : "UART SIM 离线回退";
}

function appendChat(role, text) {
  if (!text) {
    return;
  }

  const row = document.createElement("div");
  row.className = `chat-line ${role}`;
  row.textContent = text;
  els.chatWindow.prepend(row);

  while (els.chatWindow.children.length > 8) {
    els.chatWindow.lastElementChild.remove();
  }
}

function elapsed() {
  return performance.now() - state.stateStartedAt;
}

function enterState(nextState) {
  if (state.robotState === nextState) {
    return;
  }

  state.robotState = nextState;
  state.stateStartedAt = performance.now();
  state.actionConsumed = false;
  log(`STATE:${nextState}`, nextState === State.ALERT ? "alert" : "mcu");
}

function updateObstacle() {
  if (!state.obstacle && state.distance < 18) {
    state.obstacle = true;
    log(`DIST:${state.distance.toFixed(1)} ALERT_THRESHOLD`, "alert");
  } else if (state.obstacle && state.distance > 24) {
    state.obstacle = false;
    log(`DIST:${state.distance.toFixed(1)} RECOVERED`, "mcu");
  }

  if (!state.emergencyObstacle && state.distance < 14) {
    state.emergencyObstacle = true;
    log(`EVENT:EMERGENCY_BRAKE:RAW_DISTANCE`, "alert");
  } else if (state.emergencyObstacle && state.distance > 24) {
    state.emergencyObstacle = false;
    log(`EVENT:EMERGENCY_RECOVERED`, "mcu");
  }
}

function fallbackAction(eventKind, message = "") {
  const text = message.toLowerCase();

  if (state.distance < 20) {
    return "RETREAT";
  }

  if (/(退|避让|危险|靠太近|后退|retreat|danger)/i.test(text)) {
    return "RETREAT";
  }

  if (/(想|思考|分析|为什么|\?|？|think)/i.test(text)) {
    return "THINK";
  }

  if (eventKind === "BUTTON" || /(你好|hello|hi|嗨|打招呼|问候|greet)/i.test(text)) {
    return "GREET";
  }

  if (state.aiMode === "cloud") {
    return state.distance > 34 ? "GREET" : "THINK";
  }

  return message ? "THINK" : "GREET";
}

function fallbackReply(action) {
  return {
    GREET: "你好，我是 MiniPal，已经准备好互动啦。",
    THINK: "我会先想一想，再用动作回应你。",
    RETREAT: "前方距离偏近，我先保持安全距离。",
    IDLE: "我先保持待机。",
  }[normalizeAction(action)];
}

async function fetchAiDecision(eventKind, message = "") {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), BRIDGE_TIMEOUT_MS);

  try {
    const response = await fetch(`${AI_BRIDGE_URL}/ai/decide`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        mode: state.aiMode,
        event: eventKind,
        distanceCm: state.distance,
        robotState: state.robotState,
        message,
      }),
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    if (!data.ok) {
      throw new Error(data.error || "AI bridge error");
    }

    setBridgeOnline(true);
    return {
      action: normalizeAction(data.action),
      reply: data.reply || fallbackReply(data.action),
      mode: data.mode || state.aiMode,
      source: data.source || "python-bridge",
      reason: data.reason || "bridge decision",
      latencyMs: Number(data.latency_ms || 0),
      bridge: true,
    };
  } catch (error) {
    setBridgeOnline(false);
    const action = fallbackAction(eventKind, message);
    return {
      action,
      reply: fallbackReply(action),
      mode: state.aiMode,
      source: "browser-fallback",
      reason: `Python bridge offline: ${error.message}`,
      latencyMs: 0,
      bridge: false,
    };
  } finally {
    clearTimeout(timeoutId);
  }
}

async function requestAiDecision(eventKind, message = "") {
  const startedAt = performance.now();
  const minLatency = state.aiMode === "cloud" ? 520 : 130;
  const modeLog = state.aiMode === "cloud" ? "HOST:cloud policy request" : "HOST:local rule decision";
  log(modeLog, "host");

  const decision = await fetchAiDecision(eventKind, message);
  const spent = performance.now() - startedAt;
  if (spent < minLatency) {
    await sleep(minLatency - spent);
  }

  const latency = decision.bridge ? `${decision.latencyMs}ms` : "offline";
  log(`AI:${decision.mode}/${decision.source} -> ${decision.action} ${latency}`, "host");
  return decision;
}

function sendAction(action) {
  state.action = normalizeAction(action);
  log(`ACT:${state.action}`, "host");
  log(`ACK:${state.action}`, "mcu");
}

function beep(label = "短鸣") {
  state.buzzer = label;
  els.speakerSlot.classList.add("is-beeping");
  setTimeout(() => {
    state.buzzer = "静音";
    els.speakerSlot.classList.remove("is-beeping");
    render();
  }, 360);
}

async function pressWakeButton() {
  log("EVENT:BUTTON", "mcu");
  enterState(State.WAKE);
  state.action = "THINK";
  beep("确认音");

  const decision = await requestAiDecision("BUTTON");
  sendAction(decision.action);
  appendChat("robot", decision.reply);

  if (state.robotState === State.WAKE) {
    enterState(State.TRACK);
  }
}

async function sendChatMessage(event) {
  event.preventDefault();
  const message = els.chatInput.value.trim();
  if (!message) {
    return;
  }

  els.chatInput.value = "";
  appendChat("user", `你：${message}`);
  log(`USER:${message}`, "host");

  if (state.robotState === State.IDLE) {
    enterState(State.WAKE);
  }

  state.action = "THINK";
  beep("确认音");
  const decision = await requestAiDecision("MESSAGE", message);
  sendAction(decision.action);
  appendChat("robot", `MiniPal：${decision.reply}`);

  if (state.robotState === State.WAKE) {
    enterState(State.TRACK);
  }
}

function applyStateOutputs() {
  if (state.emergencyObstacle && state.robotState !== State.EMERGENCY) {
    enterState(State.EMERGENCY);
  }

  if (
    state.obstacle &&
    state.robotState !== State.ALERT &&
    state.robotState !== State.EMERGENCY &&
    state.robotState !== State.COOLDOWN
  ) {
    enterState(State.ALERT);
  }

  if (state.robotState === State.IDLE) {
    state.servo = 90;
    state.led = "standby";
    state.action = "IDLE";
  }

  if (state.robotState === State.WAKE) {
    state.servo = 84;
    state.led = "wake";
    if (elapsed() > 2300) {
      enterState(State.TRACK);
    }
  }

  if (state.robotState === State.TRACK) {
    state.led = "track";

    if (state.action === "RETREAT") {
      enterState(State.ALERT);
      return;
    }

    if (!state.actionConsumed) {
      if (state.action === "GREET") {
        state.servo = 112;
        beep("问候音");
      } else if (state.action === "THINK") {
        state.servo = 76;
      } else {
        state.servo = 90;
      }
      state.actionConsumed = true;
    }

    if (elapsed() > 1700) {
      enterState(State.COOLDOWN);
    }
  }

  if (state.robotState === State.ALERT) {
    state.servo = 142;
    state.led = "alert";
    state.action = "RETREAT";

    if (!state.actionConsumed) {
      beep("告警音");
      state.actionConsumed = true;
    }

    if (!state.obstacle && elapsed() > 900) {
      enterState(State.COOLDOWN);
    }
  }

  if (state.robotState === State.EMERGENCY) {
    state.servo = 155;
    state.led = "alert";

    if (elapsed() < 350) {
      state.action = "DRIVE:REVERSE";
    } else if (elapsed() < 800) {
      state.action = "DRIVE:TURN_RIGHT";
    } else {
      state.action = "DRIVE:HOLD";
    }

    if (!state.actionConsumed) {
      beep("EMERGENCY");
      state.actionConsumed = true;
    }

    if (!state.emergencyObstacle && elapsed() > 900) {
      state.action = "DRIVE:STOP";
      enterState(State.COOLDOWN);
    }
  }

  if (state.robotState === State.COOLDOWN) {
    state.servo = 90;
    state.led = "cooldown";

    if (elapsed() > 1400) {
      enterState(State.IDLE);
    }
  }
}

function setDistance(value) {
  state.distance = Number(value);
  els.distanceSlider.value = String(state.distance);
  updateObstacle();
  render();
}

function setMode(mode) {
  state.aiMode = mode;
  els.localMode.classList.toggle("is-active", mode === "local");
  els.cloudMode.classList.toggle("is-active", mode === "cloud");
  log(`HOST:AI_MODE=${mode.toUpperCase()}`, "host");
}

function resetSimulation() {
  state.distance = 36;
  state.obstacle = false;
  state.emergencyObstacle = false;
  state.action = "IDLE";
  state.servo = 90;
  state.led = "standby";
  state.buzzer = "静音";
  enterState(State.IDLE);
  log("BOOT:MINIPAL_SIM", "mcu");
  render();
}

function render() {
  const led = ledMap[state.led];
  const beamWidth = Math.max(8, Math.min(38, state.distance * 0.46));

  els.stateReadout.textContent = state.robotState;
  els.distanceValue.textContent = `${state.distance} cm`;
  els.robotHead.style.transform = `rotate(${state.servo - 90}deg)`;
  els.ledRing.style.borderColor = led.color;
  els.ledRing.style.boxShadow = `0 0 24px ${led.glow}`;
  els.distanceBeam.style.width = `${beamWidth}%`;
  els.distanceBeam.classList.toggle("is-alert", state.obstacle);
  els.servoReadout.textContent = `${state.servo} deg`;
  els.ledReadout.textContent = led.label;
  els.buzzerReadout.textContent = state.buzzer;
  els.actionReadout.textContent = state.action;

  els.stateNodes.forEach((node) => {
    node.classList.toggle("is-active", node.dataset.state === state.robotState);
  });
}

function tick() {
  updateObstacle();
  applyStateOutputs();
  render();
  requestAnimationFrame(tick);
}

async function checkBridgeHealth() {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 1200);

  try {
    const response = await fetch(`${AI_BRIDGE_URL}/health`, { signal: controller.signal });
    setBridgeOnline(response.ok);
  } catch {
    setBridgeOnline(false);
  } finally {
    clearTimeout(timeoutId);
  }
}

els.wakeButton.addEventListener("click", pressWakeButton);
els.resetButton.addEventListener("click", resetSimulation);
els.distanceSlider.addEventListener("input", (event) => setDistance(event.target.value));
els.localMode.addEventListener("click", () => setMode("local"));
els.cloudMode.addEventListener("click", () => setMode("cloud"));
els.chatForm.addEventListener("submit", sendChatMessage);
els.normalScenario.addEventListener("click", () => {
  setDistance(42);
  pressWakeButton();
});
els.alertScenario.addEventListener("click", () => {
  setDistance(12);
});
els.thinkingScenario.addEventListener("click", () => {
  setDistance(26);
  setMode("cloud");
  pressWakeButton();
});

setBridgeOnline(false);
log("BOOT:MINIPAL_SIM", "mcu");
log("HOST:UART_SIM_READY", "host");
appendChat("robot", "MiniPal：你好，按按钮或直接输入一句话都可以。");
checkBridgeHealth();
setInterval(checkBridgeHealth, 5000);
render();
tick();
