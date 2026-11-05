(function () {
  'use strict';
  var U = window.DPUI;
  U.wire('f', 'out', function () {
    var monthly = U.read('monthly'), rate = U.read('rate', true), horizon = U.read('horizon'), delay = U.read('delay');
    var r = DPCalc.costOfDelay({ monthlySaving: monthly, annualReturn: rate, horizonYears: horizon, delayYears: delay });
    return '<table><thead><tr><th></th><th class="n">Put in</th><th class="n">Illustrative value at end</th></tr></thead><tbody>' +
      '<tr><td>Start now</td><td class="n">' + U.money(r.startNow.contributed) + '</td><td class="n">' + U.money(r.startNow.value) + '</td></tr>' +
      '<tr><td>Start in ' + U.one(delay) + ' years</td><td class="n">' + U.money(r.startLater.contributed) + '</td><td class="n">' + U.money(r.startLater.value) + '</td></tr>' +
      '</tbody></table>' +
      '<p>Illustrative difference: <span class="big">' + U.money(r.difference) + '</span></p>' +
      '<p class="hint">Of this, ' + U.money(r.startNow.contributed - r.startLater.contributed) + ' is the money not put in during the wait; the rest is the difference in growth at the return you assumed.</p>' +
      '<p class="notice">Illustration only, not a projection or guarantee.</p>';
  });
})();
