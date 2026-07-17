// ── TAB SYSTEM ──
function showPage(id) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  const target = document.getElementById('page-' + id);
  if (target) {
    target.classList.add('active');
    target.scrollTop = 0;
    window.scrollTo(0, 0);
  }
  document.querySelectorAll('.nav-links a').forEach(a => {
    a.classList.toggle('active', a.dataset.page === id);
  });
  history.replaceState(null, '', '#' + id);
}

window.addEventListener('DOMContentLoaded', () => {
  const hash = location.hash.replace('#', '') || 'home';
  showPage(hash);
  const saved = localStorage.getItem('preferred-lang') || 'en';
  setLang(saved);
});

// Language toggle
function setLang(lang) {
  document.body.classList.remove('en', 'es');
  document.body.classList.add(lang);
  document.querySelectorAll('.lang-btn').forEach(b => {
    b.classList.toggle('active', b.textContent === lang.toUpperCase());
  });
  localStorage.setItem('preferred-lang', lang);
}

// Scroll reveal — re-trigger on each page show
const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach(e => {
    if (e.isIntersecting) e.target.classList.add('visible');
  });
}, { threshold: 0.06 });

document.querySelectorAll('[data-reveal], .edu-item, .exp-item, .project-card').forEach(el => {
  revealObserver.observe(el);
});

// Education tower parallax
const eduGraphic = document.querySelector('.edu-graphic');
if (eduGraphic) {
  window.addEventListener('scroll', () => {
    const section = document.getElementById('education');
    if (!section) return;
    const rect = section.getBoundingClientRect();
    const offset = Math.max(Math.min((rect.top / window.innerHeight) * 60, 60), -40);
    eduGraphic.style.transform = `translateY(${offset}px)`;
  }, { passive: true });
}

// Project overlays
function openOverlay(id) {
  document.getElementById('overlay-' + id).classList.add('open');
  document.body.style.overflow = 'hidden';
}
function closeOverlay(id) {
  document.getElementById('overlay-' + id).classList.remove('open');
  document.body.style.overflow = '';
}

// Diploma modals
function openDiploma(id) {
  document.getElementById('diploma-' + id).classList.add('open');
  document.body.style.overflow = 'hidden';
}
function closeDiploma(id) {
  document.getElementById('diploma-' + id).classList.remove('open');
  document.body.style.overflow = '';
}

// ── AI PROJECT SEARCH ──
(function () {

  // ── Placeholders (EN + ES) ────────────────────────────────────────────────
  const PLACEHOLDERS = {
    en: [
      "Show me machine learning projects",
      "What have you built with Flutter?",
      "Looking for data engineering work",
      "Find projects related to healthcare",
      "Show me full-stack applications"
    ],
    es: [
      "Mostrar proyectos de machine learning",
      "¿Qué has construido con Flutter?",
      "Buscar trabajo en ingeniería de datos",
      "Proyectos relacionados con salud",
      "Mostrar aplicaciones full-stack"
    ]
  };

  const DEFAULT_LABEL = {
    en: '✦ Ask me anything',
    es: '✦ Pregúntame algo'
  };

  // ── System prompts (EN + ES) ──────────────────────────────────────────────
  const SYSTEM_PROMPT_EN = `You are an intelligent filter for Carlota Huertas' portfolio website. Your job is to read what a visitor types and return a JSON object identifying which projects are most relevant to their query and a short human-readable label describing what you're showing.

Here are the projects in the portfolio:

1. InMaps — Indoor navigation app. Co-founder & Full-Stack Developer. Stack: Flutter, BLE Beacons, Python, Flask, A* Search, IMU Fusion, sensor fusion. Category: mobile, full-stack, hardware. Key results: 0.41m positioning accuracy, 4.6/5 usability.

2. World News Bias Analyzer — Live intelligence dashboard tracking how world events are framed across 12 countries. Stack: Python, sentence-transformers, scikit-learn, Plotly Dash, SQLite, spaCy, NLP. Category: machine learning, data engineering, analytics, NLP.

3. Tripic — Data-driven mobile platform. Co-founder & Lead Engineer. Stack: Flutter, Supabase, SQL, data pipelines, backend architecture. Category: mobile, full-stack, data engineering. Status: in development.

4. Heart Disease ML — Machine learning pipeline for early detection and subtype classification of heart disease. Stack: Python, scikit-learn, PCA, K-Means, SVM, logistic regression. Category: machine learning, healthcare, analytics. Key results: 88% accuracy, 918 patient records.

5. World Cup Prediction — Data-driven tournament simulator using FIFA player statistics. Stack: Python, SQL, statistics, data cleaning. Category: analytics, data engineering, sports.

When the visitor types something, figure out their intent — even if it's vague, conversational, or role-based. Return ONLY a valid JSON object in this exact format, nothing else:
{"matched":[1,4],"label":"ML & Healthcare projects","confidence":"high"}

Where "matched" is an array of project numbers (1-5). If everything matches or the query is vague, return all 5. "label" is 2-5 words describing what you are showing. If confidence is low, return all projects and set label to "All projects".`;

  const SYSTEM_PROMPT_ES = `Eres un filtro inteligente para el portfolio de Carlota Huertas. Tu tarea es leer lo que escribe un visitante y devolver un objeto JSON identificando qué proyectos son más relevantes para su búsqueda, junto con una etiqueta legible que describa lo que se está mostrando.

Estos son los proyectos del portfolio:

1. InMaps — App de navegación en interiores. Co-fundadora y desarrolladora full-stack. Stack: Flutter, BLE Beacons, Python, Flask, A* Search, IMU Fusion, fusión de sensores. Categoría: móvil, full-stack, hardware. Resultados: 0.41m de precisión, 4.6/5 de usabilidad.

2. World News Bias Analyzer — Dashboard de inteligencia en tiempo real que analiza cómo se enmarcan los mismos eventos mundiales en 12 países. Stack: Python, sentence-transformers, scikit-learn, Plotly Dash, SQLite, spaCy, NLP. Categoría: machine learning, ingeniería de datos, analítica, NLP.

3. Tripic — Plataforma móvil basada en datos. Co-fundadora e ingeniería líder. Stack: Flutter, Supabase, SQL, pipelines de datos, arquitectura backend. Categoría: móvil, full-stack, ingeniería de datos. Estado: en desarrollo.

4. Heart Disease ML — Pipeline de machine learning para detección temprana y clasificación de subtipos de enfermedades cardíacas. Stack: Python, scikit-learn, PCA, K-Means, SVM, regresión logística. Categoría: machine learning, salud, analítica. Resultados: 88% de precisión, 918 registros de pacientes.

5. World Cup Prediction — Simulador de torneos basado en estadísticas de jugadores de FIFA. Stack: Python, SQL, estadística, limpieza de datos. Categoría: analítica, ingeniería de datos, deportes.

Cuando el visitante escribe algo, interpreta su intención — aunque sea vaga, conversacional o basada en su rol profesional. Devuelve ÚNICAMENTE un objeto JSON válido en este formato exacto, sin nada más:
{"matched":[1,4],"label":"ML y Salud","confidence":"high"}

Donde "matched" es un array de números de proyecto (1-5) relevantes. Si todo coincide o la consulta es muy vaga, devuelve los 5. "label" debe ser una descripción corta de 2-5 palabras en español. Si la confianza es baja, devuelve todos los proyectos y pon "Todos los proyectos" como label.`;

  // ── Keyword fallback (EN + ES) ────────────────────────────────────────────
  const PROJECT_KEYWORDS = {
    1: ['inmaps', 'indoor', 'navigation', 'navegación', 'navegacion', 'interiores', 'flutter', 'ble', 'beacon', 'flask', 'python', 'mobile', 'móvil', 'movil', 'full-stack', 'fullstack', 'hardware', 'sensor', 'positioning', 'posicionamiento'],
    2: ['news', 'noticias', 'bias', 'sesgo', 'analyzer', 'nlp', 'scikit', 'sklearn', 'plotly', 'dash', 'sqlite', 'spacy', 'machine learning', 'aprendizaje automático', 'aprendizaje automatico', 'data engineering', 'ingeniería de datos', 'ingenieria de datos', 'analytics', 'analítica', 'analitica', 'media', 'medios', 'journalism'],
    3: ['tripic', 'flutter', 'supabase', 'sql', 'mobile', 'móvil', 'movil', 'app', 'aplicación', 'aplicacion', 'pipeline', 'backend', 'full-stack', 'startup'],
    4: ['heart', 'corazón', 'corazon', 'disease', 'health', 'healthcare', 'salud', 'medical', 'médico', 'medico', 'cardíaco', 'cardiaco', 'ml', 'machine learning', 'aprendizaje automático', 'scikit', 'pca', 'svm', 'logistic', 'regression', 'clustering', 'classification', 'clasificación', 'clasificacion', 'clinical', 'clínico'],
    5: ['world cup', 'mundial', 'football', 'fútbol', 'futbol', 'soccer', 'copa', 'fifa', 'prediction', 'predicción', 'prediccion', 'sports', 'deportes', 'statistics', 'estadística', 'estadistica', 'pandas', 'matplotlib', 'beautifulsoup']
  };

  function keywordFallback(query) {
    const q = query.toLowerCase();
    const matched = [];
    for (const [id, keywords] of Object.entries(PROJECT_KEYWORDS)) {
      if (keywords.some(kw => q.includes(kw))) matched.push(Number(id));
    }
    return matched.length > 0 ? matched : [1, 2, 3, 4, 5];
  }

  // ── Language helper ───────────────────────────────────────────────────────
  function getLang() {
    return document.body.classList.contains('es') ? 'es' : 'en';
  }

  // ── DOM ───────────────────────────────────────────────────────────────────
  const searchInput = document.getElementById('project-search');
  const searchClear = document.getElementById('search-clear');
  const sfbLabel    = document.getElementById('sfb-label');
  const sfbLabelTxt = document.getElementById('sfb-label-text');
  const sfbPh       = document.getElementById('sfb-ph');
  const sfbPhTxt    = document.getElementById('sfb-ph-text');

  if (!searchInput) return;

  const allCards = document.querySelectorAll('[data-project-id]');
  console.log('[AI Search] Found cards:', allCards.length); // should be 5

  // ── State ─────────────────────────────────────────────────────────────────
  let debounceTimer   = null;
  let abortController = null;
  let placeholderIdx  = 0;
  let placeholderTimer = null;

  // ── Card filtering ────────────────────────────────────────────────────────
  function applyFilter(matched) {
    console.log('[AI Search] Filtering to project IDs:', matched);
    allCards.forEach(card => {
      const id      = Number(card.getAttribute('data-project-id'));
      const isMatch = matched.includes(id);
      card.style.opacity       = isMatch ? '1'    : '0.2';
      card.style.filter        = isMatch ? 'none' : 'grayscale(40%)';
      card.style.pointerEvents = isMatch ? 'auto' : 'none';
      card.style.transition    = 'opacity 0.4s ease, filter 0.4s ease';
    });
  }

  function resetFilter() {
    allCards.forEach(card => {
      card.style.opacity = card.style.filter = card.style.pointerEvents = card.style.transition = '';
    });
  }

  // ── Label pill ────────────────────────────────────────────────────────────
  function setLabel(html, dimmed) {
    if (!sfbLabelTxt || !sfbLabel) return;
    sfbLabelTxt.innerHTML = html;
    sfbLabel.classList.toggle('active', !dimmed);
  }

  function resetLabel() {
    setLabel(DEFAULT_LABEL[getLang()], true);
  }

  // ── Cycling placeholder ───────────────────────────────────────────────────
  function cyclePlaceholder() {
    if (searchInput.value || !sfbPhTxt) return;
    sfbPhTxt.classList.add('fading');
    setTimeout(() => {
      const lang = getLang();
      placeholderIdx = (placeholderIdx + 1) % PLACEHOLDERS[lang].length;
      sfbPhTxt.textContent = PLACEHOLDERS[lang][placeholderIdx];
      sfbPhTxt.classList.remove('fading');
    }, 380);
  }

  function startPlaceholders() {
    if (placeholderTimer) return;
    if (sfbPhTxt) sfbPhTxt.textContent = PLACEHOLDERS[getLang()][0];
    placeholderTimer = setInterval(cyclePlaceholder, 3000);
  }

  // ── Language change observer ──────────────────────────────────────────────
  new MutationObserver(() => {
    const lang = getLang();
    if (searchInput.value) {
      searchInput.value = '';
      searchClear.style.display = 'none';
      clearTimeout(debounceTimer);
      if (abortController) abortController.abort();
      resetFilter();
      if (sfbPh) sfbPh.style.visibility = 'visible';
    }
    placeholderIdx = 0;
    if (sfbPhTxt) sfbPhTxt.textContent = PLACEHOLDERS[lang][0];
    resetLabel();
  }).observe(document.body, { attributes: true, attributeFilter: ['class'] });

  // ── Main search flow ──────────────────────────────────────────────────────
  searchInput.addEventListener('input', () => {
    const query = searchInput.value.trim();

    searchClear.style.display = query ? 'flex' : 'none';
    clearTimeout(debounceTimer);
    if (abortController) abortController.abort();

    if (query.length === 0) {
      resetFilter();
      resetLabel();
      if (sfbPh) sfbPh.style.visibility = 'visible';
      return;
    }

    if (sfbPh) sfbPh.style.visibility = 'hidden';
    if (query.length < 3) return;

    debounceTimer = setTimeout(async () => {
      console.log('[AI Search] Debounce fired, query:', query);
      setLabel('<span class="sfb-dots">···</span>', false);

      try {
        abortController = new AbortController();
        const systemPrompt = getLang() === 'es' ? SYSTEM_PROMPT_ES : SYSTEM_PROMPT_EN;

        console.log('[AI Search] Calling Claude API...');
        const response = await fetch('https://api.anthropic.com/v1/messages', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          signal: abortController.signal,
          body: JSON.stringify({
            model: 'claude-sonnet-4-6',
            max_tokens: 200,
            system: systemPrompt,
            messages: [{ role: 'user', content: query }]
          })
        });

        if (!response.ok) {
          console.error('[AI Search] API error:', response.status, await response.text());
          throw new Error('api-error');
        }

        const data = await response.json();
        console.log('[AI Search] API response:', data);

        const text = data.content[0].text;
        console.log('[AI Search] Raw text from Claude:', text);

        const cleaned = text.replace(/```json|```/g, '').trim();
        const result  = JSON.parse(cleaned);
        console.log('[AI Search] Parsed result:', result);

        const matched = Array.isArray(result.matched) && result.matched.length > 0
          ? result.matched.map(Number)
          : [1, 2, 3, 4, 5];

        applyFilter(matched);
        setLabel('Showing: ' + (result.label || 'matched projects'), false);

      } catch (err) {
        if (err.name === 'AbortError') return;
        console.warn('[AI Search] API failed, keyword fallback:', err.message);
        const matched = keywordFallback(query);
        applyFilter(matched);
        setLabel(getLang() === 'es' ? 'Mostrando: proyectos' : 'Showing: matched projects', false);
      }
    }, 600);
  });

  // ── Focus / blur ──────────────────────────────────────────────────────────
  searchInput.addEventListener('focus', () => {
    if (sfbPh) sfbPh.style.visibility = 'hidden';
  });
  searchInput.addEventListener('blur', () => {
    if (!searchInput.value && sfbPh) sfbPh.style.visibility = 'visible';
  });

  // ── Clear button ──────────────────────────────────────────────────────────
  if (searchClear) {
    searchClear.addEventListener('click', () => {
      searchInput.value = '';
      searchClear.style.display = 'none';
      clearTimeout(debounceTimer);
      if (abortController) abortController.abort();
      resetFilter();
      resetLabel();
      if (sfbPh) sfbPh.style.visibility = 'visible';
      searchInput.focus();
    });
  }

  // ── Init ──────────────────────────────────────────────────────────────────
  startPlaceholders();
  resetLabel();

})();

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.overlay.open').forEach(o => o.classList.remove('open'));
    document.querySelectorAll('.diploma-modal.open').forEach(m => m.classList.remove('open'));
    document.body.style.overflow = '';
  }
});

// ── World Cup expand/collapse ──
document.querySelectorAll('.wc-expand-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const card    = btn.closest('.wc-method-card');
    const content = card.querySelector('.wc-expanded-content');
    const isOpen  = card.classList.contains('open');

    card.classList.toggle('open');
    btn.textContent = isOpen ? '▾ See full methodology' : '▴ Hide methodology';
    btn.setAttribute('aria-expanded', String(!isOpen));

    if (!isOpen) {
      content.style.maxHeight = content.scrollHeight + 'px';
      content.style.opacity   = '1';
    } else {
      content.style.maxHeight = '0';
      content.style.opacity   = '0';
    }
  });
});
