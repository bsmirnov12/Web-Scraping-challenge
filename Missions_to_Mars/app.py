# UT-TOR-DATA-PT-01-2020-U-C Week 12 Homework
# Web Scraping Challenge
# (C) Boris Smirnov

from flask import Flask, render_template, redirect, send_from_directory
from flask_pymongo import PyMongo
import scrape_mars
import time
import os

app = Flask(__name__)

app.config["MONGO_URI"] = "mongodb://localhost:27017/mars_app"
mongo = PyMongo(app)

@app.route('/android-chrome-192x192.png')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'android-chrome-192x192.png', mimetype="image/png")

@app.route("/")
def index():
    mars_info = mongo.db.trivia.find_one()
    if not mars_info:
        print("index(): No data in mongo database. Loading defaults")
        mars_info = scrape_mars.test()
    else:
        print("index(): Data read from mongo database")

    return render_template("index.html", mars_info=mars_info)

@app.route("/scrape")
def scraper():
    trivia_collection = mongo.db.trivia
    mars_info = scrape_mars.scrape()
    # mars_info = scrape_mars.test()
    # time.sleep(3)

    trivia_collection.update({}, mars_info, upsert=True)
    print("scraper(): Database updated")

    return redirect("/", code=302)

if __name__ == "__main__":
    app.run(debug=True)
