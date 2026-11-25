const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const spec = require('../../specs/qairline_openapi.json');

const prefixes = {
  AircraftRoute: '/api/aircrafts',
  AirportRoute: '/api/airports',
  BookingRoute: '/api/bookings',
  ContentRoute: '/api/content',
  FileRoute: '/api/files',
  FlightRoute: '/api/flights',
  PassengerRoute: '/api/passengers',
  SchedulerRoute: '/scheduler',
  StatisticsRoute: '/api/statistics',
  UserRoute: '/api/users'
};

test('OpenAPI documents every mounted route and no extra operation', () => {
  const fromRoutes = [];
  for (const [routeName, prefix] of Object.entries(prefixes)) {
    const source = fs.readFileSync(path.join(__dirname, '../routes', `${routeName}.js`), 'utf8');
    for (const match of source.matchAll(/^\s*router\.(get|post|put|patch|delete)\('([^']+)'/gm)) {
      const pathname = `${prefix}${match[2] === '/' ? '' : match[2]}`.replace(/:([A-Za-z]+)/g, '{parameter}');
      fromRoutes.push(`${match[1].toUpperCase()} ${pathname}`);
    }
  }
  const fromSpec = Object.entries(spec.paths).flatMap(([pathname, item]) =>
    Object.keys(item).filter((key) => /^(get|post|put|patch|delete)$/.test(key))
      .map((method) => `${method.toUpperCase()} ${pathname.replace(/\{[^}]+\}/g, '{parameter}')}`));
  assert.equal(fromRoutes.length, 48);
  assert.deepEqual(fromSpec.sort(), fromRoutes.sort());
  assert.equal(new Set(fromSpec).size, 48);
  assert.ok(spec.openapi.startsWith('3.0.'));
  for (const [pathname, item] of Object.entries(spec.paths)) {
    for (const [method, operation] of Object.entries(item)) {
      if (!/^(get|post|put|patch|delete)$/.test(method)) continue;
      assert.ok(operation.operationId, `${method} ${pathname} needs operationId`);
      assert.ok(Object.keys(operation.responses || {}).length, `${method} ${pathname} needs responses`);
    }
  }
});

test('core write operations describe request bodies for test generation', () => {
  for (const group of ['users', 'airports', 'aircrafts', 'flights', 'passengers', 'bookings']) {
    for (const [pathname, item] of Object.entries(spec.paths)) {
      if (!pathname.startsWith(`/api/${group}`)) continue;
      for (const method of ['post', 'put']) {
        if (item[method]) assert.ok(item[method].requestBody, `${method} ${pathname} needs requestBody`);
      }
    }
  }
});
