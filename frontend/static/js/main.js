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

/* ==========================================================================
   Cancelling an appointment: ask for the reason, do not park a text box in
   every table row. The reason is optional, so an empty answer still cancels —
   only dismissing the prompt calls the whole thing off.
   ========================================================================== */

document.querySelectorAll('form[data-cancel]').forEach(function (form) {
  form.addEventListener('submit', function (e) {
    if (form.dataset.asked) return;           // second pass: let it through
    e.preventDefault();

    var reason = prompt('Cancel this appointment?\nReason (optional):');
    if (reason === null) return;              // dismissed — nothing is sent

    var field = form.querySelector('input[name="cancel_reason"]');
    if (field) field.value = reason;
    form.dataset.asked = '1';
    form.submit();                            // bypasses this handler
  });
});

/* ==========================================================================
   Repeating form rows: medicines on the consultation page, breaks on the
   schedule page. The button names the container it grows; the first row in
   that container is the template, cloned and blanked. Every row reuses the
   same input names, so the view reads them back with getlist and zips the
   lists into one item per position.
   ========================================================================== */

document.querySelectorAll('[data-clone-row]').forEach(function (btn) {
  btn.addEventListener('click', function () {
    var box = document.getElementById(btn.dataset.cloneRow);
    if (!box || !box.firstElementChild) return;

    var copy = box.firstElementChild.cloneNode(true);
    copy.querySelectorAll('input').forEach(function (i) { i.value = ''; });
    box.appendChild(copy);
    copy.querySelector('input').focus();
  });
});

/* ==========================================================================
   Printing a prescription from the list page: the document is loaded into an
   off-screen iframe and that frame is printed, so the user never leaves the
   list. Chrome refuses to print a zero-sized or display:none frame, so the
   frame gets a real page-sized box and is pushed off-screen instead.
   ========================================================================== */

document.querySelectorAll('a[data-print]').forEach(function (link) {
  link.addEventListener('click', function (e) {
    e.preventDefault();
    if (link.dataset.busy) return;                // ignore double clicks
    link.dataset.busy = '1';

    var frame = document.createElement('iframe');
    frame.setAttribute('aria-hidden', 'true');
    frame.style.cssText = 'position:fixed;left:-10000px;top:0;width:794px;height:1123px;border:0;';

    frame.addEventListener('load', function () {
      // one beat so webfonts and Tailwind have painted inside the frame
      setTimeout(function () {
        try {
          frame.contentWindow.focus();            // Safari prints the parent without this
          frame.contentWindow.print();
        } catch (err) {
          window.location.href = link.href;       // blocked: fall back to navigating
          return;
        }
        setTimeout(function () {
          frame.remove();
          delete link.dataset.busy;
        }, 1000);
      }, 250);
    });

    document.body.appendChild(frame);
    frame.src = link.dataset.print;               // set src after it is in the DOM
  });
});

/* ==========================================================================
   The printed page itself, opened with ?print=1: print, then go back, so the
   reader ends up where they started. Other pages ignore this entirely.
   ========================================================================== */

if (new URLSearchParams(location.search).get('print') === '1') {
  window.addEventListener('afterprint', function () {
    if (history.length > 1) history.back();
  });
  // one frame, so fonts and CSS are applied before the preview is built
  requestAnimationFrame(function () { window.print(); });
}

/* ==========================================================================
   Dismissable bars (the welcome strip on the patient dashboard).
   ========================================================================== */

document.querySelectorAll('[data-dismiss]').forEach(function (btn) {
  btn.addEventListener('click', function () {
    var box = btn.closest('[id], div');
    if (box) box.remove();
  });
});

/* ==========================================================================
   Reception dashboard charts. The data arrives through json_script tags, so
   this reads them with JSON.parse rather than having Django write JavaScript.
   Every page loads main.js, so both the canvases and Chart itself are checked
   before anything runs.
   ========================================================================== */

(function () {
  var doctorEl = document.getElementById('doctorChart');
  var statusEl = document.getElementById('statusChart');
  if (!doctorEl || !statusEl || typeof Chart === 'undefined') return;

  var perDoctor = JSON.parse(document.getElementById('per-doctor-data').textContent);
  var stats = JSON.parse(document.getElementById('stats-data').textContent);

  new Chart(doctorEl, {
    type: 'bar',
    data: {
      labels: perDoctor.map(function (row) { return 'Dr. ' + row.doctor__username; }),
      datasets: [{
        label: 'Appointments',
        data: perDoctor.map(function (row) { return row.total; }),
        backgroundColor: '#1666C4',
        borderRadius: 4,
      }]
    },
    options: {
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
      maintainAspectRatio: false,
    }
  });

  new Chart(statusEl, {
    type: 'doughnut',
    data: {
      labels: ['Pending', 'Confirmed', 'Completed', 'Cancelled', 'No show'],
      datasets: [{
        data: [stats.pending, stats.confirmed, stats.completed, stats.cancelled, stats.no_show],
        backgroundColor: ['#D97706', '#1666C4', '#16A34A', '#DC2626', '#94A3B8'],
        borderWidth: 0,
      }]
    },
    options: {
      plugins: { legend: { position: 'bottom', labels: { boxWidth: 12 } } },
      maintainAspectRatio: false,
    }
  });
})();
