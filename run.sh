#!/bin/bash

# calling separately to see logs
#docker-compose create
#docker-compose start
#docker-compose up

sudo npm install
# Create tables
sudo docker-compose run --rm server create_db

# Create database for tests
sudo docker-compose run --rm postgres psql -h postgres -U postgres -c "create database tests"

# Build the frontend code
sudo npm run build

# Start the webpack dev server with the frontend code in place
# Refreshed frontend and backend code everytime
sudo npm run start
