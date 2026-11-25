// MediBook: small page behaviours. Every page works without this file; it only saves clicks.
(function () {
  'use strict';

  // Filter bars and the date of the slot picker: send the form as soon as a choice changes.
  document.querySelectorAll('form[data-autosubmit]').forEach(function (form) {
    form.querySelectorAll('select, input[type="date"]').forEach(function (input) {
      input.addEventListener('change', function () {
        if (form.reportValidity()) {
          form.submit();
        }
      });
    });
  });

  // Forms with data-confirm="question": ask in a dialog before sending.
  var dialog = document.getElementById('confirm');
  if (!dialog || !window.bootstrap) {
    return;
  }
  var modal = new bootstrap.Modal(dialog);
  var waiting = null;

  document.addEventListener('submit', function (event) {
    var form = event.target;
    if (!form.dataset.confirm) {
      return;
    }
    event.preventDefault();
    waiting = form;
    document.getElementById('confirm-text').textContent = form.dataset.confirm;
    modal.show();
  });

  document.getElementById('confirm-yes').addEventListener('click', function () {
    if (waiting) {
      waiting.submit();   // submit() does not fire the submit event again
    }
  });
})();
