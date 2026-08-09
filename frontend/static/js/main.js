/* ==========================================================================
   Smart OPD — shared page behaviour (opd-fx v2 runtime)
   Loaded once from base.html, so every page gets it.
   ========================================================================== */

/* mobile sidebar open/close. Called from the hamburger button and the overlay. */
function toggleSidebar() {
  var sidebar = document.getElementById('sidebar');
  var overlay = document.getElementById('overlay');
  if (!sidebar) return;                     // logged-out pages have no sidebar
  sidebar.classList.toggle('-translate-x-full');
  overlay.classList.toggle('hidden');
}

(function () {
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---- reading-progress bar + sticky-header shadow ---- */
  var prog = document.createElement('div');
  prog.id = 'opd-progress';
  document.body.appendChild(prog);

  var hdr = document.querySelector('header.sticky');
  if (hdr) hdr.setAttribute('data-opd-head', '');

  function onScroll() {
    var h = document.documentElement;
    var max = h.scrollHeight - h.clientHeight;
    prog.style.width = max > 0 ? (h.scrollTop / max * 100) + '%' : '0';
    if (hdr) hdr.classList.toggle('opd-scrolled', window.scrollY > 4);
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  /* an element that is already drifting must not also be lifted or faded in —
     two transforms on one box fight each other */
  function isFloating(el) {
    return el.classList.contains('opd-float') || el.classList.contains('opd-float-slow');
  }

  /* ---- cards get the hover lift; sidebar panels are not cards ---- */
  document.querySelectorAll('.rounded-xl').forEach(function (el) {
    if (!el.closest('#sidebar') && !isFloating(el)) el.classList.add('opd-card');
  });

  /* ---- current sidebar link keeps its teal rail permanently ---- */
  document.querySelectorAll('#sidebar nav a').forEach(function (a) {
    if (/bg-white\/10/.test(a.className)) a.classList.add('opd-nav-active');
  });

  /* ---- click ripple on brand-coloured buttons and links ---- */
  document.querySelectorAll('a, button').forEach(function (el) {
    if (!/#1666C4/.test(el.className)) return;
    if (getComputedStyle(el).position === 'static') el.style.position = 'relative';
    el.style.overflow = 'hidden';
    el.addEventListener('click', function (e) {
      if (reduce) return;
      var r = el.getBoundingClientRect();
      var size = Math.max(r.width, r.height);
      var sp = document.createElement('span');
      sp.className = 'opd-ripple';
      sp.style.width = sp.style.height = size + 'px';
      sp.style.left = (e.clientX - r.left - size / 2) + 'px';
      sp.style.top = (e.clientY - r.top - size / 2) + 'px';
      el.appendChild(sp);
      setTimeout(function () { sp.remove(); }, 600);
    });
  });

  if (reduce) return;                       // user asked the OS for no motion

  /* ---- big stat numbers count up from 0 when they scroll into view ---- */
  function countUp(el) {
    var text = el.textContent.trim();
    if (!/^\d{1,6}$/.test(text)) return;    // only plain whole numbers
    var target = parseInt(text, 10);
    if (target <= 0) return;

    var dur = 900, start = null;
    function step(ts) {
      if (!start) start = ts;
      var p = Math.min((ts - start) / dur, 1);
      el.textContent = Math.floor((1 - Math.pow(1 - p, 3)) * target);   // ease-out
      if (p < 1) requestAnimationFrame(step);
      else el.textContent = target;
    }
    el.textContent = '0';
    requestAnimationFrame(step);
  }

  /* ---- scroll reveal ---- */
  var items = document.querySelectorAll('.rounded-xl, main h1, section h2, main table tbody tr');

  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (!e.isIntersecting) return;
      var d = e.target.__opdDelay || 0;
      setTimeout(function () {
        e.target.classList.add('opd-in');
        e.target.querySelectorAll('.tnum').forEach(function (n) {
          if (parseFloat(getComputedStyle(n).fontSize) >= 24) countUp(n);
        });
      }, d);
      io.unobserve(e.target);               // animate once, then stop watching
    });
  }, { threshold: .05, rootMargin: '0px 0px -32px 0px' });

  var i = 0;
  items.forEach(function (el) {
    if (el.closest('#sidebar') || isFloating(el)) return;
    el.classList.add('opd-reveal');
    el.__opdDelay = (i % 6) * 70;           // stagger in groups of six
    i++;
    io.observe(el);
  });
})();
