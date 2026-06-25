(function () {
  const form = document.getElementById("validator-form");
  const progress = document.getElementById("val-progress");
  const progressBar = document.getElementById("val-progress-bar");
  const progressPct = document.getElementById("val-progress-pct");
  const progressMsg = document.getElementById("val-progress-msg");
  const progressPhase = document.getElementById("val-progress-phase");
  const progressStepper = document.getElementById("val-progress-stepper");
  const progressSteps = document.getElementById("val-progress-steps");
  const resultHost = document.getElementById("val-result");
  const registerPanel = document.getElementById("val-register");
  const registerHeading = document.getElementById("val-register-heading");
  const registerForm = document.getElementById("val-register-form");
  const registerMsg = document.getElementById("val-register-msg");
  const registerCurrentUrl = document.getElementById("val-register-current-url");
  const registerSubmit = document.getElementById("val-register-submit");
  const registerDone = document.getElementById("val-register-done");
  const submitBtn = document.getElementById("validator-submit");
  let pollTimer = null;
  let startedAt = null;
  let currentRunId = null;

  function setBusy(busy) {
    if (submitBtn) submitBtn.disabled = busy;
    if (form) {
      form.querySelectorAll("input").forEach((el) => { el.disabled = busy; });
    }
    if (progress) progress.setAttribute("aria-busy", busy ? "true" : "false");
  }

  function formatElapsed(ms) {
    const sec = Math.max(0, Math.floor(ms / 1000));
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return m > 0 ? `${m}m ${s}s` : `${s}s`;
  }

  function renderStepper(phases) {
    if (!progressStepper) return;
    progressStepper.innerHTML = "";
    (phases || []).forEach((phase, index) => {
      const li = document.createElement("li");
      li.className = `val-phase val-phase--${phase.status || "pending"}`;
      li.innerHTML =
        `<span class="val-phase-marker" aria-hidden="true">${index + 1}</span>`
        + `<span class="val-phase-label">${phase.label}</span>`;
      progressStepper.appendChild(li);
    });
  }

  function renderProgress(data) {
    const pct = data.progress_percent ?? 0;
    if (progressBar) {
      progressBar.style.width = `${pct}%`;
      progressBar.parentElement?.setAttribute("aria-valuenow", String(pct));
    }
    if (progressPct) progressPct.textContent = `${pct}%`;
    if (progressPhase) progressPhase.textContent = data.phase_label || "Working…";
    if (progressMsg) {
      const elapsed = startedAt ? formatElapsed(Date.now() - startedAt) : "";
      const detail = data.message || "Contacting registry…";
      progressMsg.textContent = elapsed ? `${detail} · ${elapsed} elapsed` : detail;
    }
    renderStepper(data.phases);
    renderSteps(data.steps || []);
  }

  function renderSteps(steps) {
    if (!progressSteps) return;
    progressSteps.innerHTML = "";
    steps.forEach((step) => {
      const li = document.createElement("li");
      li.textContent = step.message || step.status || "…";
      if (step.status === "error") li.className = "val-progress-step--error";
      else if (step.status === "completed") li.className = "val-progress-step--done";
      progressSteps.appendChild(li);
    });
    progressSteps.lastElementChild?.scrollIntoView({ block: "nearest" });
  }

  function finishProgress(success) {
    if (progressBar) progressBar.style.width = success ? "100%" : progressBar.style.width;
    if (progressPct && success) progressPct.textContent = "100%";
    progress?.classList.remove("val-progress--running");
    if (progressBar) progressBar.classList.remove("val-progress-bar--active");
  }

  async function pollJob(runId) {
    const resp = await fetch(`/validator/jobs/${encodeURIComponent(runId)}`);
    if (!resp.ok) throw new Error("Could not read validation status");
    const data = await resp.json();
    renderProgress(data);
    if (data.state === "complete") {
      clearInterval(pollTimer);
      pollTimer = null;
      setBusy(false);
      finishProgress(true);
      const resultResp = await fetch(data.result_url);
      if (!resultResp.ok) throw new Error("Could not load validation results");
      const html = await resultResp.text();
      if (resultHost) {
        resultHost.innerHTML = `<section class="result" aria-labelledby="result-heading">`
          + `<h2 id="result-heading">Validation result</h2>${html}</section>`;
      }
      if (progress) progress.hidden = true;
      currentRunId = runId;
      await showRegistrationPanel(runId);
      registerPanel?.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }
    if (data.state === "error" || data.state === "canceled") {
      clearInterval(pollTimer);
      pollTimer = null;
      setBusy(false);
      finishProgress(false);
      if (progressMsg) progressMsg.textContent = data.error || data.message || "Validation failed";
      if (progress) progress.classList.add("val-progress--error");
    }
  }

  function registrationBlockedMessage(data) {
    if (data.update_blocked_by === "identify_identifier") {
      return (
        "All validation checks passed, but the Identify response did not include a registry identifier. "
        + "Updates require a live identifier that matches the registered listing."
      );
    }
    if (data.update_blocked_by === "identify_identifier_mismatch") {
      return (
        "All validation checks passed, but the live Identify identifier does not match the registered listing."
      );
    }
    if (data.update_blocked_by === "endpoint_conflict" && data.reason) {
      return data.reason;
    }
    if (data.registration_blocked_by === "builtin_schemas") {
      return (
        "All validation checks passed, but registration requires built-in XSD schemas. "
        + "Run validation again with “Use built-in XSD schemas” checked."
      );
    }
    if (data.report_all_passed && data.reason) {
      return data.reason;
    }
    if (!data.report_all_passed && data.reason) {
      return `${data.reason} See the validation results above for details.`;
    }
    return data.reason || "Registration is not available for this validation run.";
  }

  function hideRegistrationPanel() {
    if (registerPanel) {
      registerPanel.hidden = true;
      registerPanel.classList.remove("val-register--blocked");
    }
    if (registerDone) registerDone.hidden = true;
    if (registerCurrentUrl) {
      registerCurrentUrl.hidden = true;
      registerCurrentUrl.textContent = "";
    }
    if (registerForm) {
      registerForm.hidden = false;
      registerForm.reset();
    }
    const idInput = document.getElementById("reg-oai-id");
    if (idInput) idInput.readOnly = false;
    if (registerHeading) registerHeading.textContent = "Register publishing registry";
    if (registerSubmit) registerSubmit.textContent = "Register with RofR";
    if (registerMsg) {
      registerMsg.textContent = "";
      registerMsg.classList.remove("val-register-msg--warn");
    }
  }

  function applyRegistrationDefaults(data) {
    const idInput = document.getElementById("reg-oai-id");
    const titleInput = document.getElementById("reg-title");
    const isUpdate = data.mode === "update";

    if (registerHeading) {
      registerHeading.textContent = isUpdate
        ? "Update publishing registry listing"
        : "Register publishing registry";
    }
    if (registerSubmit) {
      registerSubmit.textContent = isUpdate ? "Update listing" : "Register with RofR";
    }

    if (registerCurrentUrl) {
      if (isUpdate && data.existing_entry?.harvest_access_url) {
        registerCurrentUrl.hidden = false;
        if (data.endpoint_changed) {
          registerCurrentUrl.textContent =
            `Current listed URL: ${data.existing_entry.harvest_access_url}. `
            + `Validated URL: ${data.endpoint || ""}.`;
        } else {
          registerCurrentUrl.textContent =
            `Current listed URL: ${data.existing_entry.harvest_access_url}.`;
        }
      } else {
        registerCurrentUrl.hidden = true;
        registerCurrentUrl.textContent = "";
      }
    }

    if (idInput) {
      idInput.readOnly = isUpdate;
      if (isUpdate && data.existing_entry?.oai_identifier) {
        idInput.value = data.existing_entry.oai_identifier;
      } else if (data.suggested_oai_identifier) {
        idInput.value = data.suggested_oai_identifier;
      } else {
        const ep = form?.querySelector("#endpoint")?.value || data.endpoint || "";
        const host = ep ? new URL(ep).hostname.replace(/\./g, "/") : "";
        if (host) idInput.placeholder = `ivo://${host}/registry`;
      }
    }
    if (titleInput) {
      if (isUpdate && data.existing_entry?.title && !data.suggested_title) {
        titleInput.value = data.existing_entry.title;
      } else if (data.suggested_title) {
        titleInput.value = data.suggested_title;
      }
    }
  }

  async function showRegistrationPanel(runId) {
    if (!registerPanel) return;
    hideRegistrationPanel();
    registerPanel.hidden = false;
    try {
      const resp = await fetch(`/api/v1/registry/publishers/eligibility/${encodeURIComponent(runId)}`);
      if (!resp.ok) throw new Error("Could not read registration eligibility");
      const data = await resp.json();
      if (data.eligible && registerForm) {
        registerForm.hidden = false;
        if (registerMsg) {
          registerMsg.textContent = data.reason || "";
          registerMsg.classList.remove("val-register-msg--warn");
        }
        registerPanel.classList.remove("val-register--blocked");
        applyRegistrationDefaults(data);
      } else {
        if (registerForm) registerForm.hidden = true;
        if (registerMsg) {
          registerMsg.textContent = registrationBlockedMessage(data);
          registerMsg.classList.add("val-register-msg--warn");
        }
        registerPanel.classList.add("val-register--blocked");
      }
    } catch (err) {
      if (registerMsg) {
        registerMsg.textContent = err.message || String(err);
        registerMsg.classList.add("val-register-msg--warn");
      }
      if (registerForm) registerForm.hidden = true;
      registerPanel.classList.add("val-register--blocked");
    }
  }

  async function watchJob(runId) {
    currentRunId = runId;
    if (progress) {
      progress.hidden = false;
      progress.classList.add("val-progress--running");
      progress.classList.remove("val-progress--error");
    }
    if (progressBar) progressBar.classList.add("val-progress-bar--active");
    if (resultHost) resultHost.innerHTML = "";
    hideRegistrationPanel();
    startedAt = Date.now();
    setBusy(true);
    renderProgress({
      progress_percent: 5,
      phase_label: "Starting",
      message: "Preparing validation…",
      phases: [
        { label: "OAI-PMH", status: "active" },
        { label: "IVOA harvest", status: "pending" },
        { label: "VOResource", status: "pending" },
      ],
      steps: [],
    });
    await pollJob(runId);
    if (!pollTimer) pollTimer = window.setInterval(() => pollJob(runId).catch(showError), 2000);
  }

  function showError(err) {
    clearInterval(pollTimer);
    pollTimer = null;
    setBusy(false);
    finishProgress(false);
    if (progress) {
      progress.hidden = false;
      progress.classList.add("val-progress--error");
    }
    if (progressMsg) progressMsg.textContent = err.message || String(err);
  }

  form?.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const body = new FormData(form);
    try {
      const resp = await fetch("/validator/jobs", { method: "POST", body });
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text || "Could not start validation");
      }
      const data = await resp.json();
      await watchJob(data.run_id);
    } catch (err) {
      showError(err);
    }
  });

  registerForm?.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (!currentRunId) return;
    const body = new FormData(registerForm);
    try {
      const resp = await fetch(`/validator/jobs/${encodeURIComponent(currentRunId)}/register`, {
        method: "POST",
        body,
      });
      const text = await resp.text();
      if (!resp.ok) throw new Error(text || "Registration failed");
      let created = true;
      try {
        const payload = JSON.parse(text);
        created = payload.created !== false;
      } catch (_err) {
        created = resp.status === 201;
      }
      if (registerForm) registerForm.hidden = true;
      if (registerDone) {
        registerDone.hidden = false;
        registerDone.textContent = created
          ? "Registry registered successfully. It will appear on the home page."
          : "Registry listing updated successfully. The home page will show the new URL.";
      }
    } catch (err) {
      if (registerDone) {
        registerDone.hidden = false;
        registerDone.textContent = err.message || String(err);
      }
    }
  });

  const initialRun = form?.dataset.runId;
  if (initialRun) watchJob(initialRun).catch(showError);
})();
