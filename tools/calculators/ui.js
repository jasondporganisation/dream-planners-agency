/* Small page helpers. Nothing is stored or sent: no cookies, no storage, no network. */
(function () {
  'use strict';
  var fmt = new Intl.NumberFormat('en-SG', { style: 'currency', currency: 'SGD', maximumFractionDigits: 0 });
  window.DPUI = {
    money: function (x) { return fmt.format(Math.round(x)); },
    one: function (x) { return (Math.round(x * 10) / 10).toLocaleString('en-SG'); },
    /* Read a required number input. Percent inputs are converted to decimals. */
    read: function (id, percent) {
      var el = document.getElementById(id);
      var label = (el.labels && el.labels[0] ? el.labels[0].firstChild.textContent : id).trim();
      if (el.value.trim() === '') throw new Error('Please fill in: ' + label);
      var v = Number(el.value);
      if (!isFinite(v)) throw new Error('Please enter a number for: ' + label);
      return percent ? v / 100 : v;
    },
    wire: function (formId, outId, render) {
      var form = document.getElementById(formId), out = document.getElementById(outId);
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        try { out.innerHTML = render(); }
        catch (err) {
          out.innerHTML = '';
          var p = document.createElement('p'); p.className = 'error'; p.textContent = err.message; out.appendChild(p);
        }
      });
    }
  };
})();
