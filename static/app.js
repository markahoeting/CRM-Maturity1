const bootstrap = JSON.parse(document.getElementById('bootstrap-data').textContent);
const domains = bootstrap.domains || [];
const stepTitles = bootstrap.step_titles || {};
const maturityLabels = {
  1: 'Ad Hoc',
  2: 'Emerging',
  3: 'Defined',
  4: 'Integrated',
  5: 'Optimized / Intelligent'
};

const state = {
  token: bootstrap.token || localStorage.getItem('crmAssessmentToken') || null,
  status: 'draft',
  context: {
    institutionName: '',
    institutionType: '',
    enrollmentSize: '',
    decentralization: '',
    crmLandscape: '',
    strategicPriorities: ''
  },
  responses: {},
  currentStep: 1
};

domains.forEach(domain => {
  state.responses[domain.id] = {
    scores: Array(domain.questions.length).fill(null),
    evidence: ''
  };
});

const wizardBody = document.getElementById('wizardBody');
const stepper = document.getElementById('stepper');
const stepTitle = document.getElementById('stepTitle');
const progressText = document.getElementById('progressText');
const completionPct = document.getElementById('completionPct');
const overallScore = document.getElementById('overallScore');
const overallLabel = document.getElementById('overallLabel');
const overallNarrative = document.getElementById('overallNarrative');
const consultantRecommendations = document.getElementById('consultantRecommendations');
const reportLink = document.getElementById('reportLink');
const saveState = document.getElementById('saveState');
const nextBtn = document.getElementById('nextBtn');
const prevBtn = document.getElementById('prevBtn');
const saveBtn = document.getElementById('saveBtn');

function setSaveState(message) {
  saveState.textContent = message;
}

function maturityBand(score) {
  if (score < 1.8) return ['Ad Hoc', 'Capabilities are fragmented, reactive, and heavily dependent on local workarounds.'];
  if (score < 2.6) return ['Emerging', 'The institution has early structures in place, but governance and repeatability remain inconsistent.'];
  if (score < 3.4) return ['Defined', 'Core practices are documented and partially standardized, though end-to-end integration is still uneven.'];
  if (score < 4.4) return ['Integrated', 'Capabilities are coordinated across functions with trusted data, repeatable workflows, and clear accountability.'];
  return ['Optimized / Intelligent', 'CRM operates as a strategic enterprise capability with predictive insight and increasingly intelligent orchestration.'];
}

function stepDomains(step) {
  return domains.filter(domain => domain.step === step);
}

function answeredCounts() {
  let answered = 0;
  let total = 0;
  domains.forEach(domain => {
    const scores = state.responses[domain.id].scores;
    answered += scores.filter(Boolean).length;
    total += scores.length;
  });
  return { answered, total };
}

function computeResults() {
  const domainResults = domains.map(domain => {
    const scores = state.responses[domain.id].scores.filter(Boolean).map(Number);
    const average = scores.length ? Number((scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(2)) : 0;
    const phase = average < 2.6 ? 'quick' : average < 3.8 ? 'mid' : 'long';
    return {
      id: domain.id,
      title: domain.title,
      weight: domain.weight,
      focus: domain.focus,
      average,
      phase,
      recommendations: domain.recommendations,
      consultant_actions: domain.consultant_actions
    };
  });
  const overall = Number(domainResults.reduce((sum, item) => sum + item.average * (item.weight / 100), 0).toFixed(2));
  const [label, narrative] = maturityBand(overall || 1);
  const counts = answeredCounts();
  const completion = counts.total ? Number(((counts.answered / counts.total) * 100).toFixed(1)) : 0;
  const lowDomains = [...domainResults].sort((a, b) => a.average - b.average).slice(0, 4);
  return { overall, label, narrative, completion, domainResults, lowDomains };
}

function updateSidebar() {
  const results = computeResults();
  completionPct.textContent = `${results.completion}%`;
  overallScore.textContent = results.overall.toFixed(2);
  overallLabel.textContent = results.label;
  overallNarrative.textContent = results.narrative;

  if (results.lowDomains.some(item => item.average > 0)) {
    consultantRecommendations.innerHTML = results.lowDomains.map(item => `
      <div class="consultant-card">
        <div class="consultant-header">
          <strong>${item.title}</strong>
          <span class="priority ${item.average < 2.6 ? 'priority-high' : 'priority-medium'}">${item.average < 2.6 ? 'High' : 'Medium'} priority</span>
        </div>
        <p><strong>Engagement focus:</strong> ${item.recommendations[item.phase]}</p>
        <ul>${item.consultant_actions.map(action => `<li>${action}</li>`).join('')}</ul>
      </div>
    `).join('');
  } else {
    consultantRecommendations.className = 'consultant-list empty-state';
    consultantRecommendations.textContent = 'Complete the assessment to surface engagement recommendations.';
  }

  if (state.status === 'submitted' && state.token) {
    reportLink.href = `/report/${state.token}.pdf`;
    reportLink.classList.remove('disabled');
  }
}

function renderStepper() {
  stepper.innerHTML = Object.entries(stepTitles).map(([index, title]) => {
    const step = Number(index);
    const active = step === state.currentStep ? 'active' : '';
    const done = step < state.currentStep ? 'done' : '';
    return `
      <div class="step-item ${active} ${done}">
        <div class="step-index">${step}</div>
        <div class="step-label">${title}</div>
        <div class="step-caption">${step === 1 ? 'Institution profile' : step === 5 ? 'Submit and export' : 'Score capabilities'}</div>
      </div>
    `;
  }).join('');
}

function renderContextStep() {
  wizardBody.innerHTML = `
    <div class="review-panel">
      <p class="muted">Capture the institutional context that shapes CRM complexity, priorities, and governance realities.</p>
      <div class="field-grid">
        <div>
          <label for="institutionName">Institution name</label>
          <input id="institutionName" type="text" value="${state.context.institutionName || ''}" placeholder="Example: North Valley University" />
        </div>
        <div>
          <label for="institutionType">Institution type</label>
          <select id="institutionType">
            ${['','Research university','Regional university','Community college','Liberal arts college','Private university','System office / multi-campus','Other'].map(option => `<option ${state.context.institutionType === option ? 'selected' : ''} value="${option}">${option || 'Select institution type'}</option>`).join('')}
          </select>
        </div>
        <div>
          <label for="enrollmentSize">Enrollment size</label>
          <select id="enrollmentSize">
            ${['','Under 2,500','2,500–10,000','10,001–25,000','25,001–50,000','Over 50,000'].map(option => `<option ${state.context.enrollmentSize === option ? 'selected' : ''} value="${option}">${option || 'Select enrollment range'}</option>`).join('')}
          </select>
        </div>
        <div>
          <label for="decentralization">Decentralization level</label>
          <select id="decentralization">
            ${['','Highly centralized','Mostly centralized','Hybrid','Mostly decentralized','Highly decentralized'].map(option => `<option ${state.context.decentralization === option ? 'selected' : ''} value="${option}">${option || 'Select operating model'}</option>`).join('')}
          </select>
        </div>
      </div>
      <div style="margin-top:16px;">
        <label for="crmLandscape">Current CRM landscape</label>
        <textarea id="crmLandscape" placeholder="List platforms and major systems used across admissions, advancement, student success, continuing education, marketing, and partner engagement.">${state.context.crmLandscape || ''}</textarea>
      </div>
      <div>
        <label for="strategicPriorities">Strategic priorities</label>
        <textarea id="strategicPriorities" placeholder="Summarize priorities such as enrollment growth, retention, advising transformation, alumni engagement, fundraising, constituent experience, or analytics modernization.">${state.context.strategicPriorities || ''}</textarea>
      </div>
    </div>
  `;

  ['institutionName','institutionType','enrollmentSize','decentralization','crmLandscape','strategicPriorities'].forEach(id => {
    document.getElementById(id).addEventListener('input', event => {
      state.context[id] = event.target.value;
    });
  });
}

function renderDomainStep(step) {
  const cards = stepDomains(step).map(domain => `
    <article class="domain-card">
      <div class="domain-top">
        <div>
          <h3>${domain.title}</h3>
          <p class="muted">${domain.focus}</p>
        </div>
        <div class="score-pill">Weight ${domain.weight}%</div>
      </div>
      <div class="domain-meta">
        <span class="meta-chip">Low maturity: ${domain.weak_signal}</span>
        <span class="meta-chip">High maturity: ${domain.strong_signal}</span>
      </div>
      ${domain.questions.map((question, qIndex) => `
        <div class="question-block">
          <div class="question-title">${qIndex + 1}. ${question}</div>
          <div class="scale-grid">
            ${[1,2,3,4,5].map(score => `
              <label class="choice-card">
                <input type="radio" name="${domain.id}_${qIndex}" value="${score}" ${state.responses[domain.id].scores[qIndex] === score ? 'checked' : ''} />
                <strong>${score}</strong>
                <small>${maturityLabels[score]}</small>
              </label>
            `).join('')}
          </div>
        </div>
      `).join('')}
      <div class="question-block">
        <label for="evidence_${domain.id}">Narrative evidence</label>
        <textarea id="evidence_${domain.id}" placeholder="Summarize evidence, examples, or comments for this domain.">${state.responses[domain.id].evidence || ''}</textarea>
      </div>
    </article>
  `).join('');

  wizardBody.innerHTML = `<div class="domain-stack">${cards}</div>`;

  stepDomains(step).forEach(domain => {
    domain.questions.forEach((_, qIndex) => {
      document.querySelectorAll(`input[name="${domain.id}_${qIndex}"]`).forEach(input => {
        input.addEventListener('change', event => {
          state.responses[domain.id].scores[qIndex] = Number(event.target.value);
          updateSidebar();
        });
      });
    });
    document.getElementById(`evidence_${domain.id}`).addEventListener('input', event => {
      state.responses[domain.id].evidence = event.target.value;
    });
  });
}

function renderReviewStep() {
  const results = computeResults();
  const contextEntries = [
    ['Institution', state.context.institutionName || 'Not provided'],
    ['Type', state.context.institutionType || 'Not provided'],
    ['Enrollment', state.context.enrollmentSize || 'Not provided'],
    ['Decentralization', state.context.decentralization || 'Not provided'],
    ['CRM landscape', state.context.crmLandscape || 'Not provided'],
    ['Strategic priorities', state.context.strategicPriorities || 'Not provided']
  ];

  wizardBody.innerHTML = `
    <div class="review-grid">
      <section class="review-panel">
        <div class="eyebrow">Executive summary preview</div>
        <h3>${state.context.institutionName || 'This institution'} scores ${results.overall.toFixed(2)} / 5.00</h3>
        <p>${results.narrative}</p>
        <div class="metric-grid">
          <div class="metric-box"><strong>${results.completion}%</strong><span>completion</span></div>
          <div class="metric-box"><strong>${results.label}</strong><span>maturity band</span></div>
        </div>
      </section>

      <section class="review-panel">
        <div class="eyebrow">Institution context</div>
        ${contextEntries.map(item => `<p><strong>${item[0]}:</strong> ${item[1]}</p>`).join('')}
      </section>

      <section class="review-panel">
        <div class="eyebrow">Domain scorecard</div>
        <div class="domain-table">
          ${results.domainResults.map(domain => `
            <div class="domain-row">
              <div>
                <strong>${domain.title}</strong>
                <div class="record-meta">${domain.focus}</div>
                <div class="record-meta">Recommended next move: ${domain.recommendations[domain.phase]}</div>
              </div>
              <div class="score-pill">${domain.average.toFixed(2)}</div>
            </div>
          `).join('')}
        </div>
      </section>

      <section class="review-panel">
        <div class="eyebrow">Consultant-facing recommendations</div>
        <div class="consultant-list">
          ${results.lowDomains.map(item => `
            <div class="consultant-card">
              <div class="consultant-header">
                <strong>${item.title}</strong>
                <span class="priority ${item.average < 2.6 ? 'priority-high' : 'priority-medium'}">${item.average < 2.6 ? 'High' : 'Medium'} priority</span>
              </div>
              <p><strong>Engagement focus:</strong> ${item.recommendations[item.phase]}</p>
              <ul>${item.consultant_actions.map(action => `<li>${action}</li>`).join('')}</ul>
            </div>
          `).join('')}
        </div>
      </section>
    </div>
  `;
}

function renderCurrentStep() {
  renderStepper();
  stepTitle.textContent = stepTitles[state.currentStep];
  progressText.textContent = `Step ${state.currentStep} of 5`;
  prevBtn.style.visibility = state.currentStep === 1 ? 'hidden' : 'visible';
  nextBtn.textContent = state.currentStep === 5 ? 'Submit assessment' : 'Next';

  if (state.currentStep === 1) renderContextStep();
  if ([2, 3, 4].includes(state.currentStep)) renderDomainStep(state.currentStep);
  if (state.currentStep === 5) renderReviewStep();
  updateSidebar();
}

function payloadForApi() {
  return {
    token: state.token,
    status: state.status,
    context: state.context,
    responses: state.responses
  };
}

async function saveDraft() {
  setSaveState('Saving draft...');
  const response = await fetch('/api/assessment/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payloadForApi())
  });
  if (!response.ok) {
    setSaveState('Draft save failed');
    alert('Unable to save the assessment draft right now.');
    return;
  }
  const data = await response.json();
  state.token = data.token;
  state.status = data.status;
  localStorage.setItem('crmAssessmentToken', state.token);
  reportLink.href = data.report_url;
  setSaveState(`Draft saved · ${new Date().toLocaleTimeString()}`);
  updateSidebar();
}

function validateBeforeSubmit() {
  if (!state.context.institutionName || !state.context.institutionType) {
    alert('Please complete the institution name and institution type before submitting.');
    state.currentStep = 1;
    renderCurrentStep();
    return false;
  }
  const missing = [];
  domains.forEach(domain => {
    domain.questions.forEach((_, index) => {
      if (!state.responses[domain.id].scores[index]) {
        missing.push(domain.title);
      }
    });
  });
  if (missing.length) {
    const firstMissing = domains.find(domain => domain.questions.some((_, index) => !state.responses[domain.id].scores[index]));
    alert(`Please complete all scoring questions before submitting. First incomplete domain: ${firstMissing.title}.`);
    state.currentStep = firstMissing.step;
    renderCurrentStep();
    return false;
  }
  return true;
}

async function submitAssessment() {
  if (!validateBeforeSubmit()) return;
  if (!state.token) {
    await saveDraft();
  }
  setSaveState('Submitting assessment...');
  const response = await fetch(`/api/assessment/${state.token}/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payloadForApi())
  });
  if (!response.ok) {
    setSaveState('Submission failed');
    alert('Unable to submit the assessment right now.');
    return;
  }
  const data = await response.json();
  state.status = 'submitted';
  reportLink.href = data.report_url;
  reportLink.classList.remove('disabled');
  setSaveState('Submitted successfully');
  updateSidebar();
  renderReviewStep();
  alert('Assessment submitted. The scored PDF report is now available for download.');
}

async function loadSavedAssessment(token) {
  try {
    const response = await fetch(`/api/assessment/${token}`);
    if (!response.ok) return;
    const data = await response.json();
    state.token = data.token;
    state.status = data.status;
    state.context = { ...state.context, ...(data.payload.context || {}) };
    Object.keys(state.responses).forEach(domainId => {
      if (data.payload.responses && data.payload.responses[domainId]) {
        state.responses[domainId] = {
          scores: data.payload.responses[domainId].scores || state.responses[domainId].scores,
          evidence: data.payload.responses[domainId].evidence || ''
        };
      }
    });
    setSaveState(`Loaded saved ${state.status} assessment`);
    updateSidebar();
    renderCurrentStep();
  } catch (error) {
    console.error(error);
  }
}

prevBtn.addEventListener('click', () => {
  if (state.currentStep > 1) {
    state.currentStep -= 1;
    renderCurrentStep();
  }
});

nextBtn.addEventListener('click', async () => {
  if (state.currentStep < 5) {
    state.currentStep += 1;
    renderCurrentStep();
  } else {
    await submitAssessment();
  }
});

saveBtn.addEventListener('click', async () => {
  await saveDraft();
});

renderCurrentStep();
if (state.token) {
  loadSavedAssessment(state.token);
}
