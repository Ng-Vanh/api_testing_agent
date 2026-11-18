require('dotenv').config();
const mongoose = require('mongoose');
const { startScheduler } = require('../controllers/SchedulerController');

const dbURI = process.env.MONGO_URI || 'mongodb://localhost:27017/qairline';

let bucket;
let isConnected = false;

const connectDB = async () => {
  try {
    const conn = await mongoose.connect(dbURI, {
      useNewUrlParser: true,
      useUnifiedTopology: true,
    });

    console.log('Connected to MongoDB Atlas via shared config');

    bucket = new mongoose.mongo.GridFSBucket(conn.connection.db, {
      bucketName: 'uploads',
    });

    console.log('GridFSBucket initialized');
    isConnected = true;

    startScheduler();

    ///////////////////////////////////////////
    console.log('Successfully started backend');
  } catch (err) {
    console.error('MongoDB connection error:', err);
    process.exit(1);
  }
};

// Get the GridFSBucket
const getBucket = () => {
  if (!isConnected) {
    throw new Error('MongoDB is not connected. Call connectDB first.');
  }
  return bucket;
};


module.exports = {
  dbURI,
  connectDB,
  getBucket,
};
