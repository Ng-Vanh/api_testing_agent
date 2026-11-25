const test = require('node:test');
const assert = require('node:assert/strict');
const raw = require('../../seed/data.json');
const { buildSeedData, assertLocalMongoUri } = require('../seed/build-seed');

test('builds a connected, future-dated dataset with correct prices and seats', () => {
  const seed = buildSeedData(raw, new Date('2026-11-25T12:00:00.000Z'));

  assert.deepEqual(
    Object.fromEntries(['airports', 'aircraft', 'users', 'passengers', 'flights', 'bookings']
      .map((name) => [name, seed[name].length])),
    { airports: 8, aircraft: 4, users: 4, passengers: 8, flights: 24, bookings: 6 }
  );
  assert.equal(new Set(seed.flights.map((flight) => flight.flightCode)).size, 24);
  assert.ok(seed.flights.every((flight) => flight.departureTime > new Date('2026-11-25T12:00:00.000Z')));
  assert.ok(seed.flights.every((flight) => flight.arrivalTime > flight.departureTime));

  const flight = seed.flights.find((item) => item.flightCode === 'QA101-2');
  const flightBookings = seed.bookings.filter((booking) => String(booking.flightID) === String(flight._id));
  assert.equal(flightBookings.length, 2);
  assert.equal(flight.flightClass.economy.seatsAvailable, 178);
  assert.equal(flight.flightClass.business.seatsAvailable, 39);
  assert.equal(flightBookings[0].totalPrice, 2 * 1650000);
  assert.equal(flightBookings[1].totalPrice, 3450000);
  assert.ok(seed.users.find((user) => user.username === 'qa_seed_user_01').bookings.length === 2);
});

test('rejects a booking referencing an unknown flight', () => {
  const broken = structuredClone(raw);
  broken.bookings[0].flight = 'MISSING-2';
  assert.throws(() => buildSeedData(broken, new Date('2026-11-25T12:00:00.000Z')), /unknown flight/i);
});

test('accepts only the local qairline MongoDB database', () => {
  assert.equal(assertLocalMongoUri('mongodb://127.0.0.1:27017/qairline'), undefined);
  assert.equal(assertLocalMongoUri('mongodb://localhost/qairline'), undefined);
  assert.throws(() => assertLocalMongoUri('mongodb+srv://cluster.example/qairline'), /local/i);
  assert.throws(() => assertLocalMongoUri('mongodb://127.0.0.1:27017/production'), /local/i);
  assert.throws(() => assertLocalMongoUri('mongodb://127.0.0.1:27017/qairline?replicaSet=rs0'), /local/i);
});
