(function () {
  'use strict';
  var U = window.DPUI;
  var NAMES = { BRS: 'Basic Retirement Sum', FRS: 'Full Retirement Sum', ERS: 'Enhanced Retirement Sum' };
  U.wire('f', 'out', function () {
    var year = Number(document.getElementById('year').value);
    var r = DPCalc.retirementSumGap({ cohortYear: year, raBalance: U.read('ra') });
    var rows = ['BRS', 'FRS', 'ERS'].map(function (k) {
      var x = r[k];
      var status = x.away > 0 ? U.money(x.away) + ' to go' : (x.above > 0 ? U.money(x.above) + ' above' : 'Exactly at this sum');
      return '<tr><td>' + NAMES[k] + ' (' + U.money(x.sum) + ')</td><td class="n">' + U.one(x.percentOf) + '%</td><td class="n">' + status + '</td></tr>';
    }).join('');
    return '<p>Compared with the sums for members turning 55 in ' + year + ':</p>' +
      '<table><thead><tr><th>Sum</th><th class="n">Balance as % of sum</th><th class="n">Difference</th></tr></thead><tbody>' + rows + '</tbody></table>' +
      '<p class="hint">A comparison of numbers only. The Retirement Sums are CPF benchmarks, not a personal retirement need.</p>';
  });
})();
