/* utils.js — shared helpers for all pages */

const API =
  window.location.hostname === "localhost"
    ? "http://localhost:5000/api"
    : "/api";

/* ---------- HTTP helpers ---------- */
async function apiFetch(path, options = {}) {
  const res = await fetch(API + path, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Something went wrong");
  return data;
}

/* ---------- Toast ---------- */
function showToast(msg, type = "") {
  let t = document.getElementById("toast");
  if (!t) {
    t = document.createElement("div");
    t.id = "toast";
    document.body.appendChild(t);
  }
  t.textContent = msg;
  t.className = type ? `toast-${type}` : "";
  t.classList.add("show");
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove("show"), 3200);
}

/* ---------- Loading overlay ---------- */
function showLoading(msg = "Generating quiz…") {
  let el = document.getElementById("loading-overlay");
  if (!el) {
    el = document.createElement("div");
    el.id = "loading-overlay";
    el.className = "loading-overlay";
    el.innerHTML = `<div class="spinner"></div><p id="loading-msg"></p>`;
    document.body.appendChild(el);
  }
  document.getElementById("loading-msg").textContent = msg;
  el.classList.add("show");
}

function hideLoading() {
  const el = document.getElementById("loading-overlay");
  if (el) el.classList.remove("show");
}

/* ---------- Auth guard ---------- */
function requireAuth() {
  const user = getUser();
  if (!user) {
    window.location.href = "login.html";
    return false;
  }
  return true;
}

function getUser() {
  try { return JSON.parse(localStorage.getItem("quizgenius_user")); }
  catch { return null; }
}

function setUser(user) {
  localStorage.setItem("quizgenius_user", JSON.stringify(user));
}

function clearUser() {
  localStorage.removeItem("quizgenius_user");
}

/* ---------- Render navbar user state ---------- */
function renderNavUser() {
  const user = getUser();
  const slot = document.getElementById("nav-user-slot");
  if (!slot) return;
  if (user) {
    slot.innerHTML = `
      <span class="text-muted" style="font-size:0.85rem">Hi, ${user.username}</span>
      <a href="dashboard.html" class="nav-links-link">Dashboard</a>
      <a href="history.html" class="nav-links-link">History</a>
      <button class="btn btn-outline btn-sm" onclick="logout()">Logout</button>
    `;
  } else {
    slot.innerHTML = `
      <a href="login.html">Login</a>
     <a href="login.html#register" class="btn-nav">Sign Up</a>
      
    `;
  }
}
// <a href="register.html" class="btn-nav">Sign Up</a>
async function logout() {
  try { await apiFetch("/logout", { method: "POST" }); } catch {}
  clearUser();
  window.location.href = "index.html";
}

/* ---------- Format helpers ---------- */
function formatTime(seconds) {
  if (!seconds) return "—";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}m ${String(s).padStart(2, "0")}s`;
}

function formatDate(iso) {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric",
  });
}

function gradeClass(g) { return `grade-${g}`; }

/* ---------- localStorage quiz state (for refresh safety) ---------- */
function saveQuizState(state) {
  localStorage.setItem("qg_quiz_state", JSON.stringify(state));
}
function loadQuizState() {
  try { return JSON.parse(localStorage.getItem("qg_quiz_state")); } catch { return null; }
}
function clearQuizState() {
  localStorage.removeItem("qg_quiz_state");
}
