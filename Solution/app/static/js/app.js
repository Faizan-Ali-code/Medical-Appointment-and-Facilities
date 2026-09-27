// MediBook front-end helpers: theme toggle, confirm dialog, form validation.
(function () {
  'use strict';

  // ---------------------------------------------------------- dark / light theme
  var root = document.documentElement;

  function setTheme(theme) {
    root.setAttribute('data-bs-theme', theme);
    try { localStorage.setItem('theme', theme); } catch (e) { /* private mode */ }
    document.querySelectorAll('[data-theme-toggle] i').forEach(function (icon) {
      icon.className = theme === 'dark' ? 'bi bi-sun' : 'bi bi-moon-stars';
    });
  }

  document.querySelectorAll('[data-theme-toggle]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      setTheme(root.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark');
    });
  });
  setTheme(root.getAttribute('data-bs-theme') || 'light');

  // ---------------------------------------------------------- confirm dialog
  // <form data-confirm="Question?"> asks first; "Yes" submits the form (POST + CSRF token).
  var modalEl = document.getElementById('confirmModal');
  if (modalEl && window.bootstrap) {
    var modal = new bootstrap.Modal(modalEl);
    var text = modalEl.querySelector('[data-confirm-text]');
    var ok = modalEl.querySelector('[data-confirm-ok]');
    var pendingForm = null;

    document.addEventListener('submit', function (event) {
      var form = event.target.closest('form[data-confirm]');
      if (!form || form.dataset.confirmed === '1') return;
      event.preventDefault();
      pendingForm = form;
      text.textContent = form.getAttribute('data-confirm');
      modal.show();
    });

    ok.addEventListener('click', function (event) {
      event.preventDefault();
      if (!pendingForm) return;
      pendingForm.dataset.confirmed = '1';
      modal.hide();
      pendingForm.submit();
    });
  }

  // ---------------------------------------------------------- filter dropdowns submit on change
  document.querySelectorAll('select[data-autosubmit]').forEach(function (select) {
    select.addEventListener('change', function () { select.form.submit(); });
  });

  // ---------------------------------------------------------- live slot availability
  // Asks /api/doctors/<id>/availability?date=... and disables booked slots.
  document.querySelectorAll('[data-slot-picker]').forEach(function (picker) {
    var dateInput = picker.querySelector('input[name="date"]');
    var select = picker.querySelector('select[name="slot"]');
    var message = picker.querySelector('[data-slot-message]');
    var labels = {};
    Array.prototype.forEach.call(select.options, function (o) { labels[o.value] = o.textContent; });

    function show(text, isError) {
      message.textContent = text;
      message.classList.toggle('text-danger', !!isError);
    }

    function refresh() {
      if (!dateInput.value) return;
      var url = picker.getAttribute('data-url');
      url += (url.indexOf('?') === -1 ? '?' : '&') + 'date=' + encodeURIComponent(dateInput.value);
      fetch(url, { headers: { 'Accept': 'application/json' } })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.error) { show(data.error, true); return; }
          var free = 0;
          data.slots.forEach(function (s) {
            var option = select.querySelector('option[value="' + CSS.escape(s.slot) + '"]');
            if (!option) return;
            var usable = s.free && data.works && !data.past;
            option.disabled = !usable;
            option.textContent = labels[s.slot] + (s.free ? '' : ' (booked)');
            if (usable) free += 1;
            if (!usable && option.selected) select.value = '';
          });
          if (data.past) show('Please choose today or a future date.', true);
          else if (!data.works) show('The doctor does not work on this day. Working days: ' + data.days.join(', '), true);
          else if (!free) show('All slots are booked on this day. Please choose another date.', true);
          else show(free + ' slot' + (free === 1 ? '' : 's') + ' available.', false);
        })
        .catch(function () { show('', false); });  // the server still validates the booking
    }

    dateInput.addEventListener('change', refresh);
    refresh();
  });

  // ---------------------------------------------------------- form validation (Bootstrap style)
  document.querySelectorAll('form.needs-validation').forEach(function (form) {
    form.addEventListener('submit', function (event) {
      if (!form.checkValidity()) {
        event.preventDefault();
        event.stopPropagation();
      }
      form.classList.add('was-validated');
    });
  });
})();
