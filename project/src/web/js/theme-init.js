// Apply the saved preference before first paint; storage may be unavailable.
(() => {
  let theme;
  try { theme = localStorage.getItem('spotted-theme'); } catch (_) { /* private mode */ }
  if (theme !== 'dark' && theme !== 'light') {
    theme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  document.documentElement.dataset.theme = theme;
})();
