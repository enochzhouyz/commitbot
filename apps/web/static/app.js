const state = {
  events: [],
  projects: [],
  goals: [],
  plans: [],
};

const today = new Date().toISOString().slice(0, 10);

document.addEventListener("DOMContentLoaded", () => {
  bindForms();
  refresh();
});

function bindForms() {
  document.getElementById("refreshButton").addEventListener("click", refresh);
  document.getElementById("captureGitButton").addEventListener("click", captureGit);

  document.getElementById("noteForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const input = document.getElementById("noteInput");
    await api("/events", {
      method: "POST",
      body: {
        source: "cli",
        type: "cli.note",
        payload: { message: input.value },
      },
    });
    input.value = "";
    await refresh();
  });

  document.getElementById("goalForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    await api("/goals", {
      method: "POST",
      body: {
        title: document.getElementById("goalTitle").value,
        type: document.getElementById("goalType").value,
        description: document.getElementById("goalDescription").value,
      },
    });
    event.target.reset();
    await refresh();
  });

  document.getElementById("planForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    await api("/plans", {
      method: "POST",
      body: {
        title: document.getElementById("planTitle").value,
        horizon: document.getElementById("planHorizon").value,
        narrative: document.getElementById("planNarrative").value,
      },
    });
    event.target.reset();
    await refresh();
  });

  document.getElementById("askForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const input = document.getElementById("askInput");
    const result = await api("/agent/ask", {
      method: "POST",
      body: { question: input.value },
    });
    document.getElementById("answerBox").textContent = result.answer;
    input.value = "";
    await refresh();
  });
}

async function refresh() {
  const [timeline, projects, goals, plans, summary] = await Promise.all([
    api("/timeline?limit=80"),
    api("/projects"),
    api("/goals"),
    api("/plans"),
    api(`/summaries/daily/${today}`),
  ]);
  state.events = timeline;
  state.projects = projects;
  state.goals = goals;
  state.plans = plans;
  renderStatus(summary);
  renderTimeline();
  renderProjects();
  renderGoals();
  renderPlans();
}

async function captureGit() {
  await api("/collectors/git", { method: "POST" });
  await refresh();
}

async function api(path, options = {}) {
  const init = { method: options.method || "GET", headers: {} };
  if (options.body) {
    init.headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(options.body);
  }
  const response = await fetch(path, init);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text);
  }
  return response.json();
}

function renderStatus(summary) {
  document.getElementById("statusText").textContent = `${summary.event_count} event(s) captured today`;
  const highlights = summary.highlights.length
    ? summary.highlights.map((item) => `<li>${escapeHtml(item)}</li>`).join("")
    : "<li>No highlights yet. Log a note or capture Git activity.</li>";
  document.getElementById("summaryPanel").innerHTML = `
    <strong>${escapeHtml(summary.text)}</strong>
    <ul>${highlights}</ul>
  `;
}

function renderTimeline() {
  const container = document.getElementById("timelineList");
  if (!state.events.length) {
    container.innerHTML = `<div class="empty">No events captured yet.</div>`;
    return;
  }
  container.innerHTML = state.events.map((event) => `
    <article class="event">
      <div class="eventMeta">
        <span>${formatDate(event.timestamp)}</span>
        <span>${escapeHtml(event.source)}</span>
        <span>${escapeHtml(event.type)}</span>
      </div>
      <div class="eventTitle">${escapeHtml(event.label)}</div>
    </article>
  `).join("");
}

function renderProjects() {
  const container = document.getElementById("projectList");
  if (!state.projects.length) {
    container.innerHTML = `<div class="empty">No Git project activity yet.</div>`;
    return;
  }
  container.innerHTML = state.projects.map((project) => `
    <article class="item">
      <div class="itemMeta">
        <span>${escapeHtml(project.latest_branch || "no branch")}</span>
        <span>${project.event_count} event(s)</span>
      </div>
      <div class="itemTitle">${escapeHtml(project.name)}</div>
      <p>${escapeHtml(project.root_path)}</p>
      <p>${escapeHtml(project.latest_commit?.message || "No commit captured")}</p>
    </article>
  `).join("");
}

function renderGoals() {
  const container = document.getElementById("goalList");
  if (!state.goals.length) {
    container.innerHTML = `<div class="empty">No goals yet.</div>`;
    return;
  }
  container.innerHTML = state.goals.map((goal) => `
    <article class="item">
      <div class="itemMeta">
        <span>${escapeHtml(goal.type)}</span>
        <span>${escapeHtml(goal.status)}</span>
      </div>
      <div class="itemTitle">${escapeHtml(goal.title)}</div>
      <p>${escapeHtml(goal.description || "No description")}</p>
    </article>
  `).join("");
}

function renderPlans() {
  const container = document.getElementById("planList");
  if (!state.plans.length) {
    container.innerHTML = `<div class="empty">No plans yet.</div>`;
    return;
  }
  container.innerHTML = state.plans.map((plan) => `
    <article class="item">
      <div class="itemMeta">
        <span>${escapeHtml(plan.horizon)}</span>
        <span>${escapeHtml(plan.status)}</span>
      </div>
      <div class="itemTitle">${escapeHtml(plan.title)}</div>
      <p>${escapeHtml(plan.narrative || "No narrative")}</p>
    </article>
  `).join("");
}

function formatDate(value) {
  return new Date(value).toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
