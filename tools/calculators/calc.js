/*
 * Dream Planners educational calculators: shared maths.
 * Pure functions only. No network, no storage. Loaded by the HTML pages
 * (same folder) and by the Node unit tests in calc.test.js.
 *
 * All rates are entered by the user as percentages (e.g. 2 for 2%) and
 * passed here as decimals (0.02).
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.DPCalc = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  /* Figures from compliance/sg-fact-pack-2026-11.md, section 1.3 (VERIFIED, read 3 Nov 2026). */
  var RETIREMENT_SUMS = {
    2026: { BRS: 110200, FRS: 220400, ERS: 440800 },
    2027: { BRS: 114100, FRS: 228200, ERS: 456400 }
  };
  var RETIREMENT_SUMS_SOURCE =
    'https://www.cpf.gov.sg/member/infohub/educational-resources/what-is-the-cpf-retirement-sum';

  function num(x, name) {
    if (typeof x !== 'number' || !isFinite(x)) throw new Error(name + ' must be a number');
    return x;
  }
  function nonNeg(x, name) {
    num(x, name);
    if (x < 0) throw new Error(name + ' cannot be negative');
    return x;
  }
  function rate(x, name) {
    num(x, name);
    if (x <= -1) throw new Error(name + ' must be above -100%');
    return x;
  }

  /* (1) Emergency fund */
  function emergencyFund(o) {
    var exp = nonNeg(o.monthlyExpenses, 'Monthly expenses');
    var months = nonNeg(o.targetMonths, 'Target months');
    var saved = nonNeg(o.currentSavings, 'Current emergency savings');
    if (exp === 0) throw new Error('Monthly expenses must be more than 0');
    var target = exp * months;
    return {
      target: target,
      monthsCovered: saved / exp,
      shortfall: Math.max(0, target - saved),
      surplus: Math.max(0, saved - target)
    };
  }

  /*
   * Present value at the start of retirement of a yearly withdrawal that
   * starts at `firstPayment` and grows by `growth` each year, for `years`
   * years, paid at the start of each year, while the money earns `r`.
   * Fractional years are rounded up to whole years.
   */
  function pvGrowingAnnuityDue(firstPayment, r, growth, years) {
    var n = Math.ceil(years);
    if (n <= 0 || firstPayment === 0) return 0;
    if (Math.abs(r - growth) < 1e-12) return firstPayment * n;
    var q = (1 + growth) / (1 + r);
    return firstPayment * (1 - Math.pow(q, n)) / (1 - q);
  }

  /* (2) Retirement income gap (illustration, inflation-adjusted) */
  function retirementGap(o) {
    var age = nonNeg(o.currentAge, 'Current age');
    var retAge = nonNeg(o.retirementAge, 'Retirement age');
    var yearsIn = nonNeg(o.yearsInRetirement, 'Years in retirement');
    var want = nonNeg(o.desiredMonthlyIncome, 'Monthly income wanted');
    var other = nonNeg(o.otherMonthlyIncome, 'Other monthly income');
    var saved = nonNeg(o.currentSavings, 'Savings set aside for retirement');
    var infl = rate(o.inflationRate, 'Inflation rate');
    var rPre = rate(o.returnBeforeRetirement, 'Return before retirement');
    var rPost = rate(o.returnInRetirement, 'Return during retirement');
    if (retAge < age) throw new Error('Retirement age must not be before current age');

    var yearsTo = retAge - age;
    var inflFactor = Math.pow(1 + infl, yearsTo);
    var monthlyGapToday = Math.max(0, want - other);
    var monthlyGapAtRetirement = monthlyGapToday * inflFactor;
    var needed = pvGrowingAnnuityDue(monthlyGapAtRetirement * 12, rPost, infl, yearsIn);
    var savingsAtRetirement = saved * Math.pow(1 + rPre, yearsTo);
    var shortfall = Math.max(0, needed - savingsAtRetirement);
    return {
      yearsToRetirement: yearsTo,
      inflationFactor: inflFactor,
      monthlyGapToday: monthlyGapToday,
      monthlyGapAtRetirement: monthlyGapAtRetirement,
      lumpSumNeeded: needed,
      savingsAtRetirement: savingsAtRetirement,
      shortfall: shortfall,
      shortfallInTodaysDollars: shortfall / inflFactor
    };
  }

  /* (3) CPF Retirement Sum reference */
  function retirementSumGap(o) {
    var year = o.cohortYear;
    var sums = RETIREMENT_SUMS[year];
    if (!sums) throw new Error('No retirement sums in the fact pack for ' + year);
    var bal = nonNeg(o.raBalance, 'Retirement Account balance');
    var out = {};
    ['BRS', 'FRS', 'ERS'].forEach(function (k) {
      var diff = sums[k] - bal;
      out[k] = {
        sum: sums[k],
        away: Math.max(0, diff),
        above: Math.max(0, -diff),
        percentOf: bal / sums[k] * 100
      };
    });
    return out;
  }

  /* Future value of a fixed monthly saving, paid at the end of each month. */
  function fvMonthly(monthly, annualRate, months) {
    if (months <= 0) return 0;
    var m = Math.pow(1 + annualRate, 1 / 12) - 1;
    if (Math.abs(m) < 1e-15) return monthly * months;
    return monthly * (Math.pow(1 + m, months) - 1) / m;
  }

  /* (4) Cost of delay */
  function costOfDelay(o) {
    var monthly = nonNeg(o.monthlySaving, 'Monthly saving');
    var r = rate(o.annualReturn, 'Yearly return');
    var horizon = nonNeg(o.horizonYears, 'Years until the end date');
    var delay = nonNeg(o.delayYears, 'Years of delay');
    if (delay > horizon) throw new Error('Delay cannot be longer than the total period');
    var nNow = Math.round(horizon * 12);
    var nLater = Math.round((horizon - delay) * 12);
    var now = fvMonthly(monthly, r, nNow);
    var later = fvMonthly(monthly, r, nLater);
    return {
      startNow: { value: now, contributed: monthly * nNow },
      startLater: { value: later, contributed: monthly * nLater },
      difference: now - later
    };
  }

  return {
    RETIREMENT_SUMS: RETIREMENT_SUMS,
    RETIREMENT_SUMS_SOURCE: RETIREMENT_SUMS_SOURCE,
    emergencyFund: emergencyFund,
    retirementGap: retirementGap,
    retirementSumGap: retirementSumGap,
    costOfDelay: costOfDelay,
    pvGrowingAnnuityDue: pvGrowingAnnuityDue,
    fvMonthly: fvMonthly
  };
});
