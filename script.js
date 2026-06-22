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
});

// Language toggle
function setLang(lang) {
  document.body.className = lang;
  document.querySelectorAll('.lang-btn').forEach(b => {
    b.classList.toggle('active', b.textContent === lang.toUpperCase());
  });
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

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.overlay.open').forEach(o => o.classList.remove('open'));
    document.querySelectorAll('.diploma-modal.open').forEach(m => m.classList.remove('open'));
    document.body.style.overflow = '';
  }
});
