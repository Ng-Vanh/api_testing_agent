const IDS = { airports: 'a1', aircraft: 'a2', users: 'a3', passengers: 'a4', flights: 'a5', bookings: 'a6' };

function idFor(kind, index) {
  return IDS[kind] + String(index + 1).padStart(22, '0');
}

function uniqueMap(items, key, label) {
  const result = new Map();
  for (const item of items) {
    if (!item[key] || result.has(item[key])) throw new Error(`Missing or duplicate ${label}: ${item[key]}`);
    result.set(item[key], item);
  }
  return result;
}

function required(map, key, label) {
  const value = map.get(key);
  if (!value) throw new Error(`Unknown ${label}: ${key}`);
  return value;
}

function formatDuration(minutes) {
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return [hours && `${hours}hr`, rest && `${rest}m`].filter(Boolean).join(' ') || '0m';
}

function buildSeedData(raw, now = new Date()) {
  if (Number.isNaN(now.getTime())) throw new Error('Invalid import date');
  const airports = raw.airports.map((item, index) => ({ _id: idFor('airports', index), ...item }));
  const aircraft = raw.aircraft.map((item, index) => ({ _id: idFor('aircraft', index), ...item }));
  const users = raw.users.map((item, index) => ({ _id: idFor('users', index), ...item, bookings: [] }));
  const passengers = raw.passengers.map((item, index) => ({ _id: idFor('passengers', index), ...item }));
  const airportsByCode = uniqueMap(airports, 'code', 'airport code');
  const aircraftByCode = uniqueMap(aircraft, 'code', 'aircraft code');
  const usersByName = uniqueMap(users, 'username', 'username');
  const passengersByEmail = uniqueMap(passengers, 'email', 'passenger email');
  const midnight = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());

  const flights = [];
  for (const pattern of raw.flightPatterns) {
    const from = required(airportsByCode, pattern.from, 'departure airport');
    const to = required(airportsByCode, pattern.to, 'arrival airport');
    const plane = required(aircraftByCode, pattern.aircraftCode, 'aircraft');
    if (from.code === to.code || !Number.isInteger(pattern.durationMinutes) || pattern.durationMinutes <= 0 ||
        !Number.isInteger(pattern.departureHourUTC) || pattern.departureHourUTC < 0 || pattern.departureHourUTC > 23 ||
        !Number.isInteger(pattern.economyPrice) || pattern.economyPrice <= 0 ||
        !Number.isInteger(pattern.businessPrice) || pattern.businessPrice <= 0) {
      throw new Error(`Invalid flight pattern: ${pattern.code}`);
    }
    for (const daysAhead of raw.flightDaysAhead) {
      if (!Number.isInteger(daysAhead) || daysAhead < 1) throw new Error('Flight day must be positive');
      const departureTime = new Date(midnight + daysAhead * 86400000 + pattern.departureHourUTC * 3600000);
      const arrivalTime = new Date(departureTime.getTime() + pattern.durationMinutes * 60000);
      const businessSeats = plane.seats === 220 ? 40 : 30;
      flights.push({
        _id: idFor('flights', flights.length),
        flightCode: `${pattern.code}-${daysAhead}`,
        departureAirport: from._id,
        arrivalAirport: to._id,
        departureTime,
        arrivalTime,
        flightDuration: formatDuration(pattern.durationMinutes),
        flightClass: {
          economy: { price: pattern.economyPrice, seatsAvailable: plane.seats - businessSeats },
          business: { price: pattern.businessPrice, seatsAvailable: businessSeats }
        },
        aircraft: plane._id,
        flightStatus: 'Scheduled'
      });
    }
  }
  const flightsByCode = uniqueMap(flights, 'flightCode', 'flight code');
  const bookings = raw.bookings.map((item, index) => {
    const user = required(usersByName, item.user, 'user');
    const flight = required(flightsByCode, item.flight, 'flight');
    const passengerIDs = item.passengers.map((email) => required(passengersByEmail, email, 'passenger')._id);
    const flightClass = flight.flightClass[item.class];
    if (!flightClass || passengerIDs.length === 0 || new Set(passengerIDs).size !== passengerIDs.length ||
        flightClass.seatsAvailable < passengerIDs.length) {
      throw new Error(`Invalid booking for ${item.flight}`);
    }
    flightClass.seatsAvailable -= passengerIDs.length;
    const booking = {
      _id: idFor('bookings', index),
      userID: user._id,
      flightID: flight._id,
      flightClass: item.class,
      passengerCount: passengerIDs.length,
      passengers: passengerIDs,
      bookingDate: new Date(now),
      totalPrice: passengerIDs.length * flightClass.price
    };
    user.bookings.push(booking._id);
    return booking;
  });
  return { airports, aircraft, users, passengers, flights, bookings };
}

function assertLocalMongoUri(uri) {
  if (!/^mongodb:\/\/(localhost|127\.0\.0\.1)(:\d+)?\/qairline$/.test(uri)) {
    throw new Error('Seed import is allowed only into the local qairline MongoDB database');
  }
}

module.exports = { buildSeedData, assertLocalMongoUri };
