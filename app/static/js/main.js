// ─── FinPilot Core JS ───

// Apply saved theme immediately
(function() {
  const t = localStorage.getItem('finpilot-theme') || 'dark';
  document.documentElement.setAttribute('data-theme', t);
})();

// Currency symbol
function getCurrency() { return localStorage.getItem('finpilot-currency') || '$'; }

// Format currency
function fmt(n) {
  if (n === undefined || n === null) return getCurrency() + '0.00';
  return getCurrency() + parseFloat(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// API helper with error handling
async function api(url, options = {}) {
  const defaults = { headers: { 'Content-Type': 'application/json' } };
  const merged = { ...defaults, ...options };
  if (options.headers) merged.headers = { ...defaults.headers, ...options.headers };
  try {
    const res = await fetch(url, merged);
    if (res.status === 401) { window.location.href = '/login'; return {}; }
    const ct = res.headers.get('content-type') || '';
    if (!ct.includes('application/json')) return {};
    return await res.json();
  } catch (e) {
    console.error('API error:', url, e.message);
    return {};
  }
}

// Modal helpers
function openModal(id) {
  const m = document.getElementById(id);
  if (m) { m.classList.add('open'); document.body.style.overflow = 'hidden'; }
}

function closeModal(id) {
  const m = document.getElementById(id);
  if (m) { m.classList.remove('open'); document.body.style.overflow = ''; }
}

// Close modal on overlay click
document.addEventListener('click', e => {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('open');
    document.body.style.overflow = '';
  }
});

// Close modal on Escape
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-overlay.open').forEach(m => {
      m.classList.remove('open');
      document.body.style.overflow = '';
    });
    closeNotifPanel();
  }
});

// Toast notifications
function toast(message, type = 'info', duration = 3500) {
  const container = document.getElementById('toastContainer');
  if (!container) return;
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  const icons = { success: '✓', error: '✕', info: 'ℹ' };
  el.innerHTML = `<span style="font-size:15px;flex-shrink:0">${icons[type] || 'ℹ'}</span><span>${message}</span>`;
  container.appendChild(el);
  setTimeout(() => {
    el.style.opacity = '0';
    el.style.transform = 'translateX(24px)';
    el.style.transition = 'all .3s ease';
    setTimeout(() => el.remove(), 350);
  }, duration);
}

// Theme toggle
function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'dark';
  const next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('finpilot-theme', next);
  toast(`Switched to ${next} mode`, 'info', 2000);
}

// Sidebar toggle
function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  if (sidebar) sidebar.classList.toggle('open');
}

// Notification panel toggle
function toggleNotifPanel() {
  const panel = document.getElementById('notifPanel');
  const overlay = document.getElementById('notifOverlay');
  if (!panel) return;
  const isOpen = panel.classList.contains('open');
  if (isOpen) {
    panel.classList.remove('open');
    overlay.classList.remove('open');
  } else {
    panel.classList.add('open');
    overlay.classList.add('open');
  }
}

function closeNotifPanel() {
  document.getElementById('notifPanel')?.classList.remove('open');
  document.getElementById('notifOverlay')?.classList.remove('open');
}

// Close sidebar when clicking outside (mobile)
document.addEventListener('click', e => {
  const sidebar = document.getElementById('sidebar');
  const menuBtn = e.target.closest('.mobile-menu-btn');
  if (sidebar && sidebar.classList.contains('open') && !menuBtn && !sidebar.contains(e.target)) {
    sidebar.classList.remove('open');
  }
});
