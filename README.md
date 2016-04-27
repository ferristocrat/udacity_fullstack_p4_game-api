# Hangman API
Udacity Full Stack Web Development - Project 4: Design a Game API

## Synopsis

This is my fourth of a series of projects through Udacity's **Full Stack Web Development** course, through which I have been learning web development.  This is an application using Google App Engine.

## Files

* **index.html:** HTML template for frontend form
* **hangman.py:** Application code and data models
* **app.yaml:** Configuration file
* **index.yaml:** Autogenerated file that contains query indexes
* **main.css:** styles

## Instructions

The following are needed to run a local development environment as well as upload the application.  You must be within the directory that contains your project folder:

**DEV Environment**
```
python "path\to\dev_appserver.py" directory_where_application_sits/
```
Example:
```
python "C:\Program Files (x86)\Google\google_appengine\dev_appserver.py" udacity_fullstack_p4_game-api/
```
**Upload to production environment**
```
python "path\to\appcfg.py" -A project-name -V v1 update directory_where_application_sits/
```
Example:
```
python "C:\Program Files (x86)\Google\google_appengine\appcfg.py" -A ferristocrat-hangman -V v1 update udacity_fullstack_p4_game-api/
```