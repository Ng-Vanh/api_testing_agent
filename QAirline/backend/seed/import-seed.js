const mongoose = require('mongoose');
const raw = require('../../seed/data.json');
const { buildSeedData, assertLocalMongoUri } = require('./build-seed');
const Airport = require('../models/AirportModel');
const Aircraft = require('../models/AircraftModel');
const User = require('../models/UserModel');
const Passenger = require('../models/PassengerModel');
const Flight = require('../models/FlightModel');
const Booking = require('../models/BookingModel');

const collections = [
  ['airports', Airport, 'code'],
  ['aircraft', Aircraft, 'code'],
  ['users', User, 'username'],
  ['passengers', Passenger, 'email'],
  ['flights', Flight, 'flightCode'],
  ['bookings', Booking, null]
];

async function assertNoCollisions(seed) {
  for (const [name, Model, naturalKey] of collections) {
    for (const record of seed[name]) {
      const byId = await Model.findById(record._id).lean();
      if (byId && naturalKey && byId[naturalKey] !== record[naturalKey]) {
        throw new Error(`Seed ID collision in ${name}: ${record._id}`);
      }
      if (naturalKey) {
        const byKey = await Model.findOne({ [naturalKey]: record[naturalKey] }).lean();
        if (byKey && String(byKey._id) !== record._id) {
          throw new Error(`Existing ${name} has ${naturalKey}=${record[naturalKey]}. Use an empty local DB for this seed.`);
        }
      }
    }
  }
}

async function insertMissing(seed, password) {
  const counts = {};
  for (const [name, Model] of collections) {
    counts[name] = 0;
    for (const record of seed[name]) {
      if (await Model.exists({ _id: record._id })) continue;
      const values = name === 'users' ? { ...record, password } : record;
      await new Model(values).save();
      counts[name] += 1;
    }
  }
  return counts;
}

async function main() {
  const uri = process.env.QAIRLINE_SEED_MONGO_URI || 'mongodb://127.0.0.1:27017/qairline';
  assertLocalMongoUri(uri);
  const password = process.env.QAIRLINE_SEED_PASSWORD;
  if (!password || password.length < 8) {
    throw new Error('Set QAIRLINE_SEED_PASSWORD to a local demo password of at least 8 characters');
  }
  const seed = buildSeedData(raw);
  await mongoose.connect(uri, { serverSelectionTimeoutMS: 5000 });
  try {
    await assertNoCollisions(seed);
    const counts = await insertMissing(seed, password);
    console.log('Inserted:', counts);
    console.log('Existing seed records were left unchanged. Login usernames:');
    console.log(seed.users.map((user) => `  ${user.username} (${user.role})`).join('\n'));
    console.log('Flight dates are relative to the first import; re-running does not shift existing flights.');
  } finally {
    await mongoose.disconnect();
  }
}

if (require.main === module) {
  main().catch((error) => {
    console.error(`Seed import failed: ${error.message}`);
    process.exitCode = 1;
  });
}

module.exports = { main };
