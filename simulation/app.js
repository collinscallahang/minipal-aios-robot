const State = {
  IDLE: "IDLE",
  WAKE: "WAKE",
  TRACK: "TRACK",
  ALERT: "ALERT",
  COOLDOWN: "COOLDOWN",
};

const state = {
  robotState: State.IDLE,
  distance: 36,
  obstacle: false,
  aiMode: "local",
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
  stateReadout: document.querySelector("#stateReadout"),
  distanceValue: document.querySelector("#distanceValue"),
  distanceSlider: document.querySelector("#distanceSlider"),
  distanceBeam: document.querySelector("#distanceBeam"),
  wakeButton: document.querySelector("#wakeButton"),
  resetButton: document.querySelector("#resetButton"),
  localMode: document.querySelector("#localMode"),
  cloudMode: document.querySelector("#cloudMode"),
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

function log(line, kind = "mcu") {
  const row = document.createElement("div");
  row.className = `log-line ${kind}`;
  row.textContent = `[${nowLabel()}] ${line}`;
  els.logWindow.prepend(row);

  while (els.logWindow.children.length > 80) {
    els.logWindow.lastElementChild.remove();
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
}

function decideAction(eventKind) {
  if (eventKind === "BUTTON" && state.distance < 20) {
    return "RETREAT";
  }

  if (state.aiMode === "cloud") {
    return state.distance > 34 ? "GREET" : "THINK";
  }

  return "GREET";
}

function sendAction(action) {
  state.action = action;
  log(`ACT:${action}`, "host");
  log(`ACK:${action}`, "mcu");
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

function pressWakeButton() {
  log("EVENT:BUTTON", "mcu");
  enterState(State.WAKE);
  state.action = "THINK";
  beep("确认音");

  const latency = state.aiMode === "cloud" ? 760 : 180;
  log(state.aiMode === "cloud" ? "HOST:cloud policy request" : "HOST:local rule decision", "host");
  setTimeout(() => {
    sendAction(decideAction("BUTTON"));
    if (state.robotState === State.WAKE) {
      enterState(State.TRACK);
    }
  }, latency);
}

function applyStateOutputs() {
  if (state.obstacle && state.robotState !== State.ALERT && state.robotState !== State.COOLDOWN) {
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

els.wakeButton.addEventListener("click", pressWakeButton);
els.resetButton.addEventListener("click", resetSimulation);
els.distanceSlider.addEventListener("input", (event) => setDistance(event.target.value));
els.localMode.addEventListener("click", () => setMode("local"));
els.cloudMode.addEventListener("click", () => setMode("cloud"));
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

log("BOOT:MINIPAL_SIM", "mcu");
log("HOST:UART_SIM_READY", "host");
render();
tick();
