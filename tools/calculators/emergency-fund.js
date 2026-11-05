(function () {
  'use strict';
  var U = window.DPUI;
  U.wire('f', 'out', function () {
    var r = DPCalc.emergencyFund({
      monthlyExpenses: U.read('exp'), targetMonths: U.read('months'), currentSavings: U.read('saved')
    });
    var s = '<p>Your target: <span class="big">' + U.money(r.target) + '</span></p>' +
      '<p>Your savings cover about <strong>' + U.one(r.monthsCovered) + ' months</strong> of expenses.</p>';
    s += r.shortfall > 0
      ? '<p>To reach your target you would need another <strong>' + U.money(r.shortfall) + '</strong>.</p>'
      : '<p>Your savings are at or above your target' + (r.surplus > 0 ? ' by <strong>' + U.money(r.surplus) + '</strong>' : '') + '.</p>';
    return s;
  });
})();
