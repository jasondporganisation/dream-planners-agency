(function () {
  'use strict';
  var U = window.DPUI;
  U.wire('f', 'out', function () {
    var r = DPCalc.retirementGap({
      currentAge: U.read('age'), retirementAge: U.read('ret'), yearsInRetirement: U.read('yrs'),
      desiredMonthlyIncome: U.read('want'), otherMonthlyIncome: U.read('other'), currentSavings: U.read('saved'),
      inflationRate: U.read('infl', true), returnBeforeRetirement: U.read('rpre', true), returnInRetirement: U.read('rpost', true)
    });
    if (r.monthlyGapToday === 0) {
      return '<p>On these inputs, your other income covers the monthly income you want, so this illustration shows no gap.</p>' +
        '<p class="notice">Illustration only, not a projection or guarantee.</p>';
    }
    return '<p>Monthly gap in today\'s dollars: <strong>' + U.money(r.monthlyGapToday) + '</strong></p>' +
      '<p>The same gap in ' + r.yearsToRetirement + ' years, at your inflation rate: <strong>' + U.money(r.monthlyGapAtRetirement) + ' a month</strong></p>' +
      '<p>Illustrative money needed at retirement: <strong>' + U.money(r.lumpSumNeeded) + '</strong></p>' +
      '<p>Your current savings at your assumed return: <strong>' + U.money(r.savingsAtRetirement) + '</strong></p>' +
      (r.shortfall > 0
        ? '<p>Illustrative shortfall: <span class="big">' + U.money(r.shortfall) + '</span><br><span class="hint">About ' + U.money(r.shortfallInTodaysDollars) + ' in today\'s dollars.</span></p>'
        : '<p>On these inputs, your savings would cover the illustrative amount needed.</p>') +
      '<p class="notice">Illustration only, not a projection or guarantee. Change the rates to see how sensitive the result is.</p>';
  });
})();
