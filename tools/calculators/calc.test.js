// Run with: node --test tools/calculators/calc.test.js
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const C = require('./calc.js');

const close = (a, b, tol = 0.01) =>
  assert.ok(Math.abs(a - b) <= tol, `expected ${a} to be within ${tol} of ${b}`);

test('retirement sums match fact pack section 1.3', () => {
  assert.deepEqual(C.RETIREMENT_SUMS[2026], { BRS: 110200, FRS: 220400, ERS: 440800 });
  assert.deepEqual(C.RETIREMENT_SUMS[2027], { BRS: 114100, FRS: 228200, ERS: 456400 });
  for (const y of [2026, 2027]) {
    const s = C.RETIREMENT_SUMS[y];
    assert.equal(s.FRS, 2 * s.BRS);
    assert.equal(s.ERS, 4 * s.BRS); // "Since 2025 the ERS is 4 times the BRS"
  }
});

test('emergency fund: shortfall and months covered', () => {
  const r = C.emergencyFund({ monthlyExpenses: 3000, targetMonths: 6, currentSavings: 9000 });
  assert.equal(r.target, 18000);
  assert.equal(r.monthsCovered, 3);
  assert.equal(r.shortfall, 9000);
  assert.equal(r.surplus, 0);
});

test('emergency fund: surplus when above target', () => {
  const r = C.emergencyFund({ monthlyExpenses: 2000, targetMonths: 3, currentSavings: 7000 });
  assert.equal(r.shortfall, 0);
  assert.equal(r.surplus, 1000);
});

test('emergency fund: rejects zero expenses and negatives', () => {
  assert.throws(() => C.emergencyFund({ monthlyExpenses: 0, targetMonths: 6, currentSavings: 0 }));
  assert.throws(() => C.emergencyFund({ monthlyExpenses: 100, targetMonths: -1, currentSavings: 0 }));
  assert.throws(() => C.emergencyFund({ monthlyExpenses: NaN, targetMonths: 6, currentSavings: 0 }));
});

test('growing annuity due: equal rate and growth is payment x years', () => {
  assert.equal(C.pvGrowingAnnuityDue(1000, 0.03, 0.03, 10), 10000);
});

test('growing annuity due: level payments discounted at 4%', () => {
  // 100 + 100/1.04 + 100/1.04^2
  close(C.pvGrowingAnnuityDue(100, 0.04, 0, 3), 288.6095, 0.001);
});

test('growing annuity due: fractional years round up', () => {
  assert.equal(C.pvGrowingAnnuityDue(100, 0, 0, 2.1), 300);
});

test('retirement gap: worked example', () => {
  const r = C.retirementGap({
    currentAge: 45, retirementAge: 65, yearsInRetirement: 20,
    desiredMonthlyIncome: 4000, otherMonthlyIncome: 1500, currentSavings: 100000,
    inflationRate: 0.02, returnBeforeRetirement: 0.03, returnInRetirement: 0.02
  });
  assert.equal(r.yearsToRetirement, 20);
  close(r.inflationFactor, Math.pow(1.02, 20), 1e-9);
  assert.equal(r.monthlyGapToday, 2500);
  close(r.monthlyGapAtRetirement, 2500 * Math.pow(1.02, 20));
  close(r.lumpSumNeeded, 2500 * Math.pow(1.02, 20) * 12 * 20);
  close(r.savingsAtRetirement, 100000 * Math.pow(1.03, 20));
  close(r.shortfall, r.lumpSumNeeded - r.savingsAtRetirement);
  close(r.shortfallInTodaysDollars, r.shortfall / Math.pow(1.02, 20));
});

test('retirement gap: no gap when other income covers the need', () => {
  const r = C.retirementGap({
    currentAge: 60, retirementAge: 65, yearsInRetirement: 20,
    desiredMonthlyIncome: 2000, otherMonthlyIncome: 2500, currentSavings: 0,
    inflationRate: 0.02, returnBeforeRetirement: 0.02, returnInRetirement: 0.02
  });
  assert.equal(r.lumpSumNeeded, 0);
  assert.equal(r.shortfall, 0);
});

test('retirement gap: rejects retirement age before current age', () => {
  assert.throws(() => C.retirementGap({
    currentAge: 70, retirementAge: 65, yearsInRetirement: 20,
    desiredMonthlyIncome: 1, otherMonthlyIncome: 0, currentSavings: 0,
    inflationRate: 0, returnBeforeRetirement: 0, returnInRetirement: 0
  }));
});

test('retirement sum gap: distances for 2026 cohort', () => {
  const r = C.retirementSumGap({ cohortYear: 2026, raBalance: 150000 });
  assert.equal(r.BRS.away, 0);
  assert.equal(r.BRS.above, 39800);
  assert.equal(r.FRS.away, 70400);
  assert.equal(r.ERS.away, 290800);
  close(r.FRS.percentOf, 150000 / 220400 * 100, 1e-9);
});

test('retirement sum gap: 2027 cohort and unknown year', () => {
  const r = C.retirementSumGap({ cohortYear: 2027, raBalance: 0 });
  assert.equal(r.FRS.away, 228200);
  assert.throws(() => C.retirementSumGap({ cohortYear: 2030, raBalance: 0 }));
});

test('monthly future value: zero rate and exact 1% monthly rate', () => {
  assert.equal(C.fvMonthly(100, 0, 12), 1200);
  close(C.fvMonthly(100, Math.pow(1.01, 12) - 1, 12), 100 * (Math.pow(1.01, 12) - 1) / 0.01, 1e-6);
  assert.equal(C.fvMonthly(100, 0.05, 0), 0);
});

test('cost of delay: zero return shows only lost contributions', () => {
  const r = C.costOfDelay({ monthlySaving: 500, annualReturn: 0, horizonYears: 20, delayYears: 5 });
  assert.equal(r.startNow.value, 120000);
  assert.equal(r.startLater.value, 90000);
  assert.equal(r.difference, 30000);
});

test('cost of delay: positive return makes the gap bigger than contributions missed', () => {
  const r = C.costOfDelay({ monthlySaving: 500, annualReturn: 0.03, horizonYears: 20, delayYears: 5 });
  assert.ok(r.difference > r.startNow.contributed - r.startLater.contributed);
  assert.throws(() => C.costOfDelay({ monthlySaving: 500, annualReturn: 0.03, horizonYears: 5, delayYears: 6 }));
});
