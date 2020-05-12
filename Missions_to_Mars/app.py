# UT-TOR-DATA-PT-01-2020-U-C Week 12 Homework
# Web Scraping Challenge
# (C) Boris Smirnov

from flask import Flask, render_template, redirect, jsonify, session, send_from_directory
from flask.logging import create_logger
from flask_pymongo import PyMongo
import scrape_mars
import os
import time
import random
import string
import logging

app = Flask(__name__)
logger = create_logger(app)
logger.setLevel(logging.DEBUG)

app.config["MONGO_URI"] = "mongodb://localhost:27017/mars_app"
app.config["SECRET_KEY"] = "Ou5Y2QS4FWepfiU2"
mongo = PyMongo(app)

# Dictionary to associate session id with progress object
session_data = {}


# Utility function: generate a string of random charactes
def getRandomId(length=16):
    char_set = string.ascii_letters + string.digits
    return "".join([random.choice(char_set) for i in range(length)])


@app.route('/android-chrome-192x192.png')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'android-chrome-192x192.png', mimetype="image/png")


@app.route("/")
def index():
    if not 'id' in session:
        session['id'] = getRandomId()
        session.modified = True
        logger.debug(f"index(): generated session id '{session['id']}'")

    mars_info = mongo.db.trivia.find_one()
    if not mars_info:
        logger.debug("index(): No data in mongo database. Loading defaults")
        #mars_info = scrape_mars.test()
        mars_info = None # Show empty template
    else:
        logger.debug("index(): Data read from mongo database")

    return render_template("index.html", mars_info=mars_info)

@app.route("/scrape")
def scraper():
    if 'id' in session:
        session_id = session['id']
        logger.debug(f"scraper(): session id from the session object '{session_id}'")
    else:
        session_id = getRandomId()
        session['id'] = session_id
        session.modified = True
        logger.debug(f"scraper(): NO session id in the session object. Generated new one '{session_id}'")

    if session_id in session_data:
        logger.debug(f"scraper(): session_data is not empty")
    
    progress = scrape_mars.make_scraping_progress()
    session_data[session_id] = progress
    logger.debug(f"scraper(): new progress object created")

    trivia_collection = mongo.db.trivia
    mars_info = scrape_mars.scrape(progress)
    #mars_info = scrape_mars.test()
    #for i in range(progress.stages): progress.stage_start(); time.sleep(1)
    
    trivia_collection.update({}, mars_info, upsert=True)
    logger.debug("scraper(): Database updated")

    return redirect("/", code=302)

@app.route("/progress")
def progress():
    if 'id' in session:
        session_id = session['id']
        logger.debug(f"progress(): session id from the session object '{session_id}'")
    else:
        session_id = getRandomId()
        session['id'] = session_id
        session.modified = True
        session_data[session_id] = scrape_mars.Progress()
        logger.debug(f"progress(): NO session id in the session object. Generated new one '{session_id}'")

    if session_id in session_data:
        progress = session_data[session_id]
        logger.debug(f"progress(): session_data has progress object. OK")
    else:
        session_data[session_id] = scrape_mars.Progress()
        logger.debug(f"progress(): NO progress object in the session_data for session id '{session_id}'")

    return jsonify(progress.to_dict())

if __name__ == "__main__":
    app.run(debug=True)
