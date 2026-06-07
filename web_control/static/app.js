const wheels = [
  {id: 'LR', name: 'Left Rear'},
  {id: 'LF', name: 'Left Front'},
  {id: 'RR', name: 'Right Rear'},
  {id: 'RF', name: 'Right Front'},
];

const state = {
  activeKey: null,
  activePointer: false,
  activeCommand: null,
  repeatTimer: null,
  scan: null,
  mode: 'manual',
  safeMode: true,
  wheelScales: {LR: 0.75, LF: 1.0, RR: 1.0, RF: 1.0},
  wheelInverts: {LR: true, LF: true, RR: false, RF: false},
  sectors: {front: null, left: null, right: null, rear: null},
};

const shell = document.querySelector('#ivi-shell');
const drawer = document.querySelector('#drawer');
const drawerBackdrop = document.querySelector('#drawer-backdrop');
const linearSlider = document.querySelector('#linear-speed');
const angularSlider = document.querySelector('#angular-speed');
const linearValue = document.querySelector('#linear-value');
const angularValue = document.querySelector('#angular-value');
const testPwm = document.querySelector('#test-pwm');
const testPwmValue = document.querySelector('#test-pwm-value');
const testDuration = document.querySelector('#test-duration');
const testDurationValue = document.querySelector('#test-duration-value');
const safeMode = document.querySelector('#safe-mode');
const canvas = document.querySelector('#lidar-canvas');
const ctx = canvas ? canvas.getContext('2d') : null;

function setText(selector, text) {
  const el = document.querySelector(selector);
  if (el) el.textContent = text;
}

function linearSpeed() {
  return linearSlider ? Number.parseFloat(linearSlider.value) : 0.08;
}

function angularSpeed() {
  return angularSlider ? Number.parseFloat(angularSlider.value) : 0.4;
}

function currentTestPwm() {
  return testPwm ? Number.parseInt(testPwm.value, 10) : 80;
}

function currentTestDuration() {
  return testDuration ? Number.parseFloat(testDuration.value) : 0.4;
}

function updateSliderLabels() {
  if (linearValue) linearValue.textContent = linearSpeed().toFixed(2);
  if (angularValue) angularValue.textContent = angularSpeed().toFixed(2);
  if (testPwmValue) testPwmValue.textContent = String(currentTestPwm());
  if (testDurationValue) testDurationValue.textContent = `${currentTestDuration().toFixed(1)}s`;
}

async function postJson(url, payload = {}) {
  const res = await fetch(url, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  updateStatus(data);
  return data;
}

async function drive(linear, angular) {
  return postJson('/api/drive', {linear, angular});
}

function startRepeating(command) {
  state.activeCommand = command;
  drive(command.linear, command.angular);
  if (state.repeatTimer) clearInterval(state.repeatTimer);
  state.repeatTimer = setInterval(() => {
    if (state.activeCommand) drive(state.activeCommand.linear, state.activeCommand.angular);
  }, 250);
}

async function stop() {
  state.activeKey = null;
  state.activePointer = false;
  state.activeCommand = null;
  if (state.repeatTimer) {
    clearInterval(state.repeatTimer);
    state.repeatTimer = null;
  }
  return postJson('/api/stop');
}

function distanceColor(distance) {
  if (distance == null || !Number.isFinite(distance)) return 'none';
  if (distance < 0.22) return 'red';
  if (distance < 0.42) return 'yellow';
  if (distance < 0.75) return 'green';
  return 'none';
}

function updateStatus(data) {
  if (!data) return;
  state.safeMode = Boolean(data.safe_mode);

  setText('#connected', data.connected ? 'OK' : 'Off');
  setText('#safety', data.safety_stop_active ? 'Active' : 'Clear');
  setText('#lidar', data.lidar_stale ? 'Stale' : 'Fresh');
  setText('#last-command', data.last_command || 'STOP');
  setText('#safety-reason', data.safety_reason || '—');
  setText('#front-min-small', data.front_min == null ? '—' : Number(data.front_min).toFixed(2));

  const chipSerial = document.querySelector('#chip-serial');
  const chipSafety = document.querySelector('#chip-safety');
  const chipLidar = document.querySelector('#chip-lidar');
  if (chipSerial) chipSerial.className = `chip ${data.connected ? 'ok' : 'err'}`;
  if (chipSafety) chipSafety.className = `chip ${data.safety_stop_active ? 'warn' : 'ok'}`;
  if (chipLidar) chipLidar.className = `chip ${data.lidar_stale ? 'err' : 'ok'}`;

  if (safeMode) safeMode.checked = state.safeMode;
  if (data.wheel_scales) state.wheelScales = data.wheel_scales;
  if (data.wheel_inverts) state.wheelInverts = data.wheel_inverts;
  if (!state.safeMode) clearMapAndSensing();
  syncWheelControls();
}

async function pollStatus() {
  try {
    const res = await fetch('/api/status');
    updateStatus(await res.json());
  } catch {
    setText('#connected', 'Off');
  }
}

function commandForButton(button) {
  return {
    linear: Number.parseFloat(button.dataset.linear || '0') * linearSpeed(),
    angular: Number.parseFloat(button.dataset.angular || '0') * angularSpeed(),
  };
}

function buildWheelControls() {
  const list = document.querySelector('#wheel-list');
  const testList = document.querySelector('#test-wheel-list');
  if (list) list.innerHTML = '';
  if (testList) testList.innerHTML = '';

  for (const wheel of wheels) {
    if (list) {
      const row = document.createElement('div');
      row.className = 'wheel-row';
      row.innerHTML = `
        <div class="wheel-name"><strong>${wheel.id}</strong><span>${wheel.name}</span></div>
        <label class="scale-control">
          <span>Scale</span>
          <div class="scale-stack">
            <input class="wheel-scale" data-wheel="${wheel.id}" type="range" min="0.20" max="1.00" value="${state.wheelScales[wheel.id]}" step="0.01">
            <input class="wheel-scale-number" data-wheel="${wheel.id}" type="number" min="0.20" max="1.00" value="${state.wheelScales[wheel.id].toFixed(2)}" step="0.01">
          </div>
        </label>
        <label class="invert-control">
          <input class="wheel-invert" data-wheel="${wheel.id}" type="checkbox" ${state.wheelInverts[wheel.id] ? 'checked' : ''}>
          <span>Invert</span>
        </label>`;
      list.appendChild(row);
    }
    if (testList) {
      const tile = document.createElement('div');
      tile.className = 'test-tile';
      tile.innerHTML = `
        <div><strong>${wheel.id}</strong><span>${wheel.name}</span></div>
        <button class="test-wheel" data-wheel="${wheel.id}" data-dir="1">Test +</button>
        <button class="test-wheel secondary" data-wheel="${wheel.id}" data-dir="-1">Test -</button>`;
      testList.appendChild(tile);
    }
  }

  document.querySelectorAll('.wheel-scale').forEach((input) => {
    input.addEventListener('input', () => {
      setWheelScaleControls(input.dataset.wheel, Number.parseFloat(input.value), input);
    });
    input.addEventListener('change', () => {
      tuneWheel(input.dataset.wheel, {scale: clampScale(Number.parseFloat(input.value))});
    });
  });
  document.querySelectorAll('.wheel-scale-number').forEach((input) => {
    input.addEventListener('input', () => {
      setWheelScaleControls(input.dataset.wheel, Number.parseFloat(input.value), input);
    });
    input.addEventListener('change', () => {
      const scale = clampScale(Number.parseFloat(input.value));
      setWheelScaleControls(input.dataset.wheel, scale);
      tuneWheel(input.dataset.wheel, {scale});
    });
  });
  document.querySelectorAll('.wheel-invert').forEach((input) => {
    input.addEventListener('change', () => tuneWheel(input.dataset.wheel, {invert: input.checked}));
  });
  document.querySelectorAll('.test-wheel').forEach((button) => {
    button.addEventListener('click', () => testWheel(
      button.dataset.wheel,
      currentTestPwm() * Number.parseInt(button.dataset.dir, 10),
    ));
  });
}

function syncWheelControls() {
  for (const wheel of wheels) {
    const scale = document.querySelector(`.wheel-scale[data-wheel="${wheel.id}"]`);
    const scaleNumber = document.querySelector(`.wheel-scale-number[data-wheel="${wheel.id}"]`);
    const invert = document.querySelector(`.wheel-invert[data-wheel="${wheel.id}"]`);
    if (scale && document.activeElement !== scale) {
      scale.value = state.wheelScales[wheel.id];
    }
    if (scaleNumber && document.activeElement !== scaleNumber) {
      scaleNumber.value = Number(state.wheelScales[wheel.id]).toFixed(2);
    }
    if (invert && document.activeElement !== invert) {
      invert.checked = Boolean(state.wheelInverts[wheel.id]);
    }
  }
}

function clampScale(value) {
  if (!Number.isFinite(value)) return 0.2;
  return Math.min(Math.max(value, 0.2), 1.0);
}

function setWheelScaleControls(wheel, value, source = null) {
  const scale = clampScale(value);
  const range = document.querySelector(`.wheel-scale[data-wheel="${wheel}"]`);
  const number = document.querySelector(`.wheel-scale-number[data-wheel="${wheel}"]`);
  if (range && range !== source) range.value = scale.toFixed(2);
  if (number && number !== source) number.value = scale.toFixed(2);
}

async function tuneWheel(wheel, patch) {
  await postJson('/api/tuning', {wheel, ...patch});
}

async function testWheel(wheel, pwm) {
  await stop();
  await postJson('/api/wheel_test', {wheel, pwm, duration: currentTestDuration()});
}

async function setSafeMode(enabled) {
  await postJson('/api/safe_mode', {enabled});
  if (!enabled) clearMapAndSensing();
}

function toggleDrawer(open) {
  drawer?.classList.toggle('open', open);
  drawerBackdrop?.classList.toggle('open', open);
}

function switchMode(mode) {
  state.mode = mode;
  shell.className = `ivi-shell ${mode}-mode`;
  document.querySelectorAll('.drawer-item').forEach((button) => {
    button.classList.toggle('active', button.dataset.mode === mode);
  });
  document.querySelectorAll('.ctrl-pane').forEach((pane) => pane.classList.remove('active'));

  if (mode === 'manual' || mode === 'auto') document.querySelector('#pane-manual')?.classList.add('active');
  if (mode === 'settings') document.querySelector('#pane-settings')?.classList.add('active');
  if (mode === 'test') document.querySelector('#pane-test')?.classList.add('active');

  setText('#mode-readout', mode === 'auto' ? 'Auto-Drive' : mode === 'manual' ? 'Manual-Drive' : mode);
  toggleDrawer(false);
  drawScan();
}

document.querySelector('#menu-button')?.addEventListener('click', () => toggleDrawer(true));
drawerBackdrop?.addEventListener('click', () => toggleDrawer(false));
document.querySelectorAll('.drawer-item').forEach((button) => {
  button.addEventListener('click', () => switchMode(button.dataset.mode));
});

document.querySelectorAll('.drive-btn').forEach((button) => {
  button.addEventListener('pointerdown', (event) => {
    event.preventDefault();
    state.activePointer = true;
    button.setPointerCapture(event.pointerId);
    startRepeating(commandForButton(button));
  });
  button.addEventListener('pointerup', stop);
  button.addEventListener('pointercancel', stop);
  button.addEventListener('pointerleave', () => { if (state.activePointer) stop(); });
});

linearSlider?.addEventListener('input', updateSliderLabels);
angularSlider?.addEventListener('input', updateSliderLabels);
testPwm?.addEventListener('input', updateSliderLabels);
testDuration?.addEventListener('input', updateSliderLabels);
safeMode?.addEventListener('change', () => setSafeMode(safeMode.checked));

document.addEventListener('keydown', (event) => {
  if (event.repeat) return;
  const key = event.key.toLowerCase();
  const code = event.code;
  state.activeKey = code;
  if (key === 'w' || code === 'ArrowUp') { event.preventDefault(); startRepeating({linear: linearSpeed(), angular: 0.0}); }
  if (key === 's' || code === 'ArrowDown') { event.preventDefault(); startRepeating({linear: -linearSpeed(), angular: 0.0}); }
  if (key === 'a' || code === 'ArrowLeft') { event.preventDefault(); startRepeating({linear: 0.0, angular: angularSpeed()}); }
  if (key === 'd' || code === 'ArrowRight') { event.preventDefault(); startRepeating({linear: 0.0, angular: -angularSpeed()}); }
  if (code === 'Space') { event.preventDefault(); stop(); }
});

document.addEventListener('keyup', (event) => {
  const key = event.key.toLowerCase();
  const code = event.code;
  if ((['w', 'a', 's', 'd'].includes(key) || ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(code)) && code === state.activeKey) {
    stop();
  }
});

function computeSectors(points) {
  const sectors = {front: Infinity, left: Infinity, right: Infinity, rear: Infinity};
  for (const p of points) {
    const distance = Math.hypot(p.x, p.y);
    const angle = Math.atan2(p.x, p.y);
    if (Math.abs(angle) <= Math.PI / 4) sectors.front = Math.min(sectors.front, distance);
    else if (Math.abs(angle) >= Math.PI * 3 / 4) sectors.rear = Math.min(sectors.rear, distance);
    else if (angle < 0) sectors.left = Math.min(sectors.left, distance);
    else sectors.right = Math.min(sectors.right, distance);
  }
  for (const key of Object.keys(sectors)) {
    if (!Number.isFinite(sectors[key])) sectors[key] = null;
  }
  return sectors;
}

function updateSensing() {
  const points = state.safeMode ? (state.scan?.points || []) : [];
  state.sectors = computeSectors(points);
  for (const key of ['front', 'left', 'right', 'rear']) {
    const value = state.sectors[key];
    const arc = document.querySelector(`#arc-${key}`);
    const readout = document.querySelector(`#sector-${key}`);
    const level = distanceColor(value);
    if (arc) arc.className.baseVal = `sense-arc ${level !== 'none' ? level : ''}`;
    if (readout) readout.textContent = value == null ? '—' : value.toFixed(2);
  }
  updateObstaclePopup();
}

function updateObstaclePopup() {
  const popup = document.querySelector('#obstacle-popup');
  if (!popup || !state.safeMode) {
    popup?.classList.remove('show');
    return;
  }
  const labels = {front: '전방', rear: '후방', left: '좌측', right: '우측'};
  const close = Object.entries(state.sectors).filter(([, value]) => value != null && value < 0.35);
  if (close.length === 0) {
    popup.classList.remove('show');
    return;
  }
  close.sort((a, b) => a[1] - b[1]);
  popup.textContent = `${labels[close[0][0]]}에 장애물이 있습니다.`;
  popup.classList.add('show');
}

async function fetchScan() {
  if (!state.safeMode) {
    clearMapAndSensing();
    return;
  }
  try {
    const res = await fetch(`/static/scan_latest.json?t=${Date.now()}`);
    if (!res.ok) return;
    state.scan = await res.json();
  } catch {
    state.scan = null;
  }
  drawScan();
  updateSensing();
}

function clearMapAndSensing() {
  state.scan = null;
  state.sectors = {front: null, left: null, right: null, rear: null};
  drawScan();
  updateSensing();
}

function drawScan() {
  if (!canvas || !ctx) return;
  const w = canvas.width;
  const h = canvas.height;
  const cx = w / 2;
  const cy = h / 2;
  const scale = Math.min(w, h) / 7;

  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = '#f5f5f7';
  ctx.fillRect(0, 0, w, h);

  ctx.strokeStyle = 'rgba(0, 0, 0, 0.08)';
  ctx.lineWidth = 1;
  ctx.font = '18px Inter, system-ui, sans-serif';
  ctx.fillStyle = 'rgba(17, 17, 17, 0.42)';
  ctx.textAlign = 'center';
  for (let r = 1; r <= 4; r++) {
    ctx.beginPath();
    ctx.arc(cx, cy, r * scale, 0, Math.PI * 2);
    ctx.stroke();
    ctx.fillText(`${r}m`, cx + 26, cy - r * scale + 7);
  }

  ctx.strokeStyle = 'rgba(0, 0, 0, 0.16)';
  ctx.setLineDash([6, 12]);
  ctx.beginPath();
  ctx.moveTo(cx, 22);
  ctx.lineTo(cx, h - 22);
  ctx.moveTo(22, cy);
  ctx.lineTo(w - 22, cy);
  ctx.stroke();
  ctx.setLineDash([]);

  ctx.strokeStyle = '#0066cc';
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.moveTo(cx, cy - 122);
  ctx.lineTo(cx, cy - 62);
  ctx.stroke();

  if (state.safeMode) {
    const points = state.scan?.points || [];
    ctx.fillStyle = '#0066cc';
    for (const p of points) {
      const x = cx + p.x * scale;
      const y = cy - p.y * scale;
      ctx.beginPath();
      ctx.arc(x, y, 3.2, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  drawCenterCross(cx, cy);
}

function drawCenterCross(cx, cy) {
  ctx.save();
  ctx.lineCap = 'round';
  ctx.strokeStyle = '#0066cc';
  ctx.lineWidth = 7;
  ctx.beginPath();
  ctx.moveTo(cx - 28, cy);
  ctx.lineTo(cx + 28, cy);
  ctx.moveTo(cx, cy - 28);
  ctx.lineTo(cx, cy + 28);
  ctx.stroke();
  ctx.strokeStyle = '#ffffff';
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(cx - 18, cy);
  ctx.lineTo(cx + 18, cy);
  ctx.moveTo(cx, cy - 18);
  ctx.lineTo(cx, cy + 18);
  ctx.stroke();
  ctx.restore();
}

canvas?.addEventListener('click', async (event) => {
  const rect = canvas.getBoundingClientRect();
  const x = event.clientX - rect.left - rect.width / 2;
  const y = rect.height / 2 - (event.clientY - rect.top);
  await postJson('/api/direction', {angle: Math.atan2(x, y), duration: 0.5, speed: linearSpeed()});
});

function updateClock() {
  const now = new Date();
  const date = now.toLocaleDateString('en-US', {month: 'long', day: 'numeric'});
  const time = now.toLocaleTimeString('en-US', {hour: 'numeric', minute: '2-digit', hour12: true});
  setText('#date-label', date);
  setText('#clock', time);
}

window.addEventListener('blur', stop);
buildWheelControls();
updateSliderLabels();
drawScan();
pollStatus();
updateClock();
setInterval(pollStatus, 500);
setInterval(fetchScan, 200);
setInterval(updateClock, 30000);
