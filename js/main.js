// ナビゲーション トグル
const navToggle = document.getElementById('navToggle');
const mainNav = document.querySelector('.main-nav');
if (navToggle && mainNav) {
  navToggle.addEventListener('click', () => {
    mainNav.classList.toggle('open');
  });
}

// タブ切り替え
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const group = btn.dataset.group;
    const target = btn.dataset.tab;

    document.querySelectorAll(`.tab-btn[data-group="${group}"]`).forEach(b => b.classList.remove('active'));
    document.querySelectorAll(`.tab-content[data-group="${group}"]`).forEach(c => c.classList.remove('active'));

    btn.classList.add('active');
    const targetEl = document.querySelector(`.tab-content[data-group="${group}"][data-tab="${target}"]`);
    if (targetEl) targetEl.classList.add('active');
  });
});

// 現在のページをナビでアクティブに
const currentPage = location.pathname.split('/').pop() || 'index.html';
document.querySelectorAll('.main-nav a').forEach(a => {
  const href = a.getAttribute('href').split('/').pop();
  if (href === currentPage) a.classList.add('active');
  else a.classList.remove('active');
});
