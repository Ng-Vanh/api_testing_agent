const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = __dirname;
const spec = require('../../QAirline/specs/qairline_openapi.json');
const rawSeed = require('../../QAirline/seed/data.json');
const { buildSeedData } = require('../../QAirline/backend/seed/build-seed');
const datasetRoot = path.join(root, 'datasets');
const scenarioRoot = path.join(root, 'scenarios');
const methods = new Set(['get', 'post', 'put', 'patch', 'delete']);
const subcategories = new Set([
  'happy_path', 'unknown_resource', 'no_matching_resource', 'missing_required',
  'invalid_credentials', 'duplicate_unique', 'invalid_format', 'invalid_enum',
  'boundary_value', 'cross_field_mismatch', 'empty_update', 'capacity_exceeded',
  'derived_value_and_state', 'state_transition', 'atomicity',
  'sensitive_data_exposure', 'filter_correctness', 'aggregate_consistency'
]);
const predicateKinds = new Set([
  'valid_request', 'field_absent', 'otherwise_valid', 'resource_absent',
  'no_matching_resource', 'invalid_credentials', 'existing_value',
  'invalid_format', 'value_outside_enum', 'field_relation', 'length_mismatch',
  'field_equals', 'empty_body', 'capacity_exceeded', 'state_snapshot',
  'destination_capacity_exceeded'
]);
const seed = buildSeedData(rawSeed, new Date('2026-11-25T12:00:00.000Z'));
const fixtureKeys = {
  airports: new Set(seed.airports.map((x) => x.code)),
  aircraft: new Set(seed.aircraft.map((x) => x.code)),
  users: new Set(seed.users.map((x) => x.username)),
  passengers: new Set(seed.passengers.map((x) => x.email)),
  flights: new Set(seed.flights.map((x) => x.flightCode)),
  bookings: new Set(rawSeed.bookings.map((x) => `${x.user}|${x.flight}|${x.class}`))
};

function resolvePointer(pointer) {
  return pointer.split('/').slice(1).reduce((value, part) => value?.[part.replaceAll('~1', '/').replaceAll('~0', '~')], spec);
}

function placeholders(value) {
  if (typeof value === 'string') return [...value.matchAll(/\$\{([^}]+)\}/g)].map((match) => match[1]);
  if (Array.isArray(value)) return value.flatMap(placeholders);
  if (value && typeof value === 'object') return Object.values(value).flatMap(placeholders);
  return [];
}

function filesUnder(dir) {
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const name = path.join(dir, entry.name);
    return entry.isDirectory() ? filesUnder(name) : name.endsWith('.json') ? [name] : [];
  });
}

test('one dataset file for every QAirline method and path', () => {
  const expected = new Set(Object.entries(spec.paths).flatMap(([pathname, item]) =>
    Object.entries(item).filter(([method]) => methods.has(method))
      .map(([method, operation]) => `${method.toUpperCase()} ${pathname} ${operation.operationId}`)));
  const actual = new Set();
  const files = filesUnder(datasetRoot);
  assert.equal(expected.size, 48);
  assert.equal(files.length, 48);
  for (const file of files) {
    const dataset = JSON.parse(fs.readFileSync(file, 'utf8'));
    const { operation } = dataset;
    const key = `${operation.method} ${operation.path} ${operation.operationId}`;
    assert.ok(expected.has(key), `Unknown operation in ${file}: ${key}`);
    assert.ok(!actual.has(key), `Duplicate operation: ${key}`);
    const group = operation.path.startsWith('/scheduler/') ? 'scheduler' : operation.path.split('/')[2];
    assert.equal(path.relative(datasetRoot, file), path.join(group, `${operation.operationId}.json`));
    actual.add(key);
    assert.equal(dataset.version, '0.2');
    assert.ok(['core', 'extension'].includes(operation.scope));
    assert.ok(dataset.sources.openapi.startsWith('QAirline/specs/qairline_openapi.json#/paths/'));
    assert.ok(dataset.sources.route.startsWith('QAirline/backend/routes/'));
    assert.ok(fs.existsSync(path.join(root, '../..', dataset.sources.route)));
    assert.ok(fs.existsSync(path.join(root, '../..', dataset.sources.controller)));
    const pointer = dataset.sources.openapi.split('#')[1];
    const specOperation = resolvePointer(pointer);
    assert.equal(specOperation.operationId, operation.operationId);
    assert.ok(Array.isArray(dataset.obligations) && dataset.obligations.length > 0);
    const ids = new Set();
    for (const obligation of dataset.obligations) {
      assert.ok(obligation.id && !ids.has(obligation.id), `Duplicate obligation in ${file}`);
      ids.add(obligation.id);
      assert.equal(obligation.operation_id, operation.operationId);
      assert.ok(['valid', 'invalid', 'boundary', 'stateful', 'security', 'robustness'].includes(obligation.category));
      assert.ok(subcategories.has(obligation.subcategory), `${obligation.id}: invalid subcategory`);
      assert.equal(obligation.coverage_target?.match, 'semantic');
      assert.ok(Array.isArray(obligation.coverage_target.preconditions));
      assert.ok(Array.isArray(obligation.coverage_target.request_predicates) && obligation.coverage_target.request_predicates.length > 0);
      assert.ok(Array.isArray(obligation.coverage_target.evidence_required) && obligation.coverage_target.evidence_required.includes('oracle_result'));
      for (const predicate of obligation.coverage_target.request_predicates) {
        assert.ok(predicateKinds.has(predicate.kind), `${obligation.id}: unknown predicate ${predicate.kind}`);
      }
      assert.ok(obligation.intent && obligation.input && obligation.expected);
      assert.ok(Array.isArray(obligation.expected.status) && obligation.expected.status.length > 0);
      for (const status of obligation.expected.status) {
        assert.ok(specOperation.responses[String(status)], `${obligation.id}: ${status} missing from OpenAPI`);
      }
      assert.ok(Array.isArray(obligation.expected.assertions));
      for (const assertion of obligation.expected.assertions) {
        if (assertion.ref?.includes('#')) assert.ok(resolvePointer(assertion.ref.split('#')[1]), `${obligation.id}: bad schema ref`);
      }
      assert.ok(['contract', 'business_rule', 'security_rule', 'robustness_rule'].includes(obligation.oracle.basis));
      assert.ok(['draft', 'approved'].includes(obligation.oracle.review));
      if (obligation.oracle.review === 'approved') {
        assert.ok(obligation.oracle.approved_by && obligation.oracle.approved_at && obligation.oracle.verification_evidence?.length);
      }
      assert.ok(Array.isArray(obligation.oracle.evidence) && obligation.oracle.evidence.length > 0);
      assert.ok(['ready', 'needs_fixture', 'needs_rule_review'].includes(obligation.readiness));
      for (const placeholder of placeholders(obligation.input)) {
        const parts = placeholder.split(':');
        assert.ok(['fixture', 'secret', 'clock'].includes(parts[0]), `${obligation.id}: unknown placeholder ${placeholder}`);
        if (parts[0] !== 'fixture') continue;
        assert.equal(parts.length, 4, `${obligation.id}: malformed fixture ${placeholder}`);
        if (obligation.readiness === 'ready') {
          assert.ok(fixtureKeys[parts[1]]?.has(parts[2]), `${obligation.id}: fixture ${parts[1]}/${parts[2]} absent from seed`);
        }
      }
    }
  }
  assert.deepEqual(actual, expected);
  const core = files.map((file) => JSON.parse(fs.readFileSync(file, 'utf8')))
    .filter((dataset) => dataset.operation.scope === 'core');
  assert.equal(core.length, 34);
});

test('cross-operation scenarios reference documented operations and have reviewable assertions', () => {
  const operations = new Map(Object.values(spec.paths).flatMap((item) =>
    Object.entries(item).filter(([method]) => methods.has(method)).map(([, operation]) => [operation.operationId, operation])));
  const files = filesUnder(scenarioRoot);
  assert.ok(files.length >= 2, 'Need representative stateful scenarios');
  const scenarioIds = new Set();
  for (const file of files) {
    const scenario = JSON.parse(fs.readFileSync(file, 'utf8'));
    assert.equal(scenario.version, '0.1');
    assert.ok(scenario.scenario_id && !scenarioIds.has(scenario.scenario_id));
    scenarioIds.add(scenario.scenario_id);
    assert.ok(Array.isArray(scenario.steps) && scenario.steps.length >= 3);
    assert.ok(Array.isArray(scenario.assertions) && scenario.assertions.length > 0);
    assert.ok(['ready', 'needs_fixture', 'needs_rule_review'].includes(scenario.readiness));
    assert.ok(['draft', 'approved'].includes(scenario.oracle?.review));
    assert.ok(Array.isArray(scenario.oracle.evidence) && scenario.oracle.evidence.length > 0);
    const captures = new Set();
    for (const step of scenario.steps) {
      assert.ok(step.id && operations.has(step.operation_id), `${file}: undocumented operation`);
      assert.ok(step.request && Array.isArray(step.expected?.status) && step.expected.status.length > 0);
      for (const status of step.expected.status) {
        assert.ok(operations.get(step.operation_id).responses[String(status)], `${file}: undocumented status ${status}`);
      }
      for (const ref of placeholders(step.request).filter((value) => value.startsWith('memory:'))) {
        assert.ok(captures.has(ref.slice('memory:'.length)), `${file}: ${step.id} uses ${ref} before capture`);
      }
      for (const name of Object.keys(step.capture || {})) captures.add(name);
    }
    for (const ref of placeholders(scenario.assertions).filter((value) => value.startsWith('memory:'))) {
      assert.ok(captures.has(ref.slice('memory:'.length)), `${file}: assertion uses unknown ${ref}`);
    }
  }
});
