# -*- coding: utf-8 -*-

import json
import hashlib
import traceback
import time
import pickle
import jsonschema
import pymongo
import numpy as np
from flask import Flask
from flask import request
from flask import make_response
from flask import render_template

# Machine learning libaries from scikit-learn
from sklearn.preprocessing import LabelEncoder
from sklearn import ensemble
from sklearn import linear_model
from sklearn.model_selection import GridSearchCV
from sklearn import preprocessing
from sklearn.model_selection import train_test_split
import sklearn.metrics as metrics

housing_schema = {
    "type": "object",
    "properties": {
        "area": {"type": "string"},
        "areacode": {"type": "string"},
        "desc": {"type": "string"},
        "type": {"type": "string"},
        "size": {"type": "number"},
        "price": {"type": "number"},
        "year": {"type": "string"},
        "floor": {"type": "number"},
        "elevator": {"type": "number"},
        "condition": {"type": "number"},
        "energy": {"type": "string"},
        "rooms": {"type": "number"},
        "city": {"type": "string"},
        "floors": {"type": "number"},
        "date": {"type": "number"},
        "hash": {"type": "string"},
    },
    "required": ["area","areacode","desc","type","size","price","year","floor","condition","rooms","city","floors"]
}

class DB():
    def __init__(self):
        pass

    def get(self, collection=None, count=1):
        with pymongo.MongoClient() as client:
            if collection == "apartments":
                db = client.housing_outliers.apartments
            elif collection == "outliers":
                db = client.housing_outliers.outliers
            else:
                return []
            
            entries = []
            for entry in db.find().sort('date', pymongo.DESCENDING).limit(count):
                entry['_id'] = str(entry['_id'])
                if count == 1:
                    return entry
                entries.append(entry)
                
            return entries

    def get_count(self, collection=None):
        with pymongo.MongoClient() as client:
            if collection == "apartments":
                db = client.housing_outliers.apartments
            elif collection == "outliers":
                db = client.housing_outliers.outliers
            else:
                return 0
            
            count = db.count()
            return count
    
    def add(self, entry, collection=None):
        with pymongo.MongoClient() as client:
            if collection == "apartments":
                db = client.housing_outliers.apartments
            elif collection == "outliers":
                db = client.housing_outliers.outliers
            else:
                return False, "Unknown collection %s" % collection
            
            # secondary check for required fields, for when entries are added directly instead of via web API
            for required_field in housing_schema['required']:
                if required_field not in entry:
                    return False, "Missing required field '%s'" % required_field
            
            for field in entry.keys():
                if housing_schema['properties'][field]['type'] == "string":
                    if field in housing_schema['required'] and entry[field] == "":
                        return False, "Field '%s' is empty" % field
                    entry[field] = entry[field].encode('utf-8')
            
            str_to_hash = '.'.join(str(entry[field]) for field in housing_schema['required'] if field != "price")
            entry_hash = hashlib.sha1()
            entry_hash.update(str_to_hash)
            
            entry['date'] = time.time() * 1000
            entry['hash'] = entry_hash.hexdigest()
            
            # check duplicates
            exists = False
            for entry in db.find({"hash": entry['hash']}):
                exists = True
                break
                
            if not exists:
                db.insert_one(entry)
                return True, "Entry %s added to database." % entry['hash']
            else:
                return False, "Entry already exists"


db = DB()
app = Flask(__name__)

with open('workflowdemo/model.dat', 'r') as f:
    model = pickle.loads(f.read())
predictor = model['predictor']
areacode_le = model['areacode_encoder']


@app.route("/")
def index():
    return render_template("index.html", apartments_count=db.get_count("apartments"), outliers_count=db.get_count("outliers"))
    
@app.route('/price/area/<int:area>/size/<int:size>', methods=["GET"])
def price_api(area,size):
    try:
        resp = make_response(json.dumps({"price": ((size*150000)/area)}), 200)
        resp.headers['Content-Type'] = "application/json"
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp
        
    except Exception, ex:
        err = "ERROR: " + traceback.format_exc()
        print err
        return make_response(err, 500)

@app.route('/apartments', methods=["GET", "POST"])
def apartments_api():
    try:
        if request.method == "GET":     
            count = 1 if "count" not in request.args else int(request.args.get("count"))
            
            resp = make_response(json.dumps(db.get(collection="apartments", count=count)), 200)
            
            resp.headers['Content-Type'] = "application/json"
            return resp
            
        elif request.method == "POST":        
            if request.headers.get("Content-Type") != "application/json":
                return make_response("Invalid Content-Type, expected application/json", 400)
                
            try:
                input_data = json.loads(request.data)
                jsonschema.validate(input_data, housing_schema)
            except ValueError, err:
                return make_response("Invalid input JSON: " + str(err), 400)
            except jsonschema.exceptions.ValidationError, err:
                return make_response("Input JSON doesn't match schema: " + str(err), 400)
                            
            result, ret = db.add(input_data, collection="apartments")
            code = 200 if result else 400

            resp = make_response(ret, code)

            return resp
    except Exception, ex:
        err = "ERROR: " + traceback.format_exc()
        print err
        return make_response(err, 500)

@app.route('/outliers', methods=["GET", "POST"])
def outliers_api():
    try:
        if request.method == "GET":            
            count = 1 if "count" not in request.args else int(request.args.get("count"))
            
            resp = make_response(json.dumps(db.get(collection="outliers", count=count)), 200)
            resp.headers['Content-Type'] = "application/json"
            return resp
            
        elif request.method == "POST":        
            if request.headers.get("Content-Type") != "application/json":
                return make_response("Invalid Content-Type, expected application/json", 400)
                
            try:
                input_data = json.loads(request.data)
                jsonschema.validate(input_data, housing_schema)
            except ValueError, err:
                return make_response("Invalid input JSON: " + str(err), 400)
            except jsonschema.exceptions.ValidationError, err:
                return make_response("Input JSON doesn't match schema: " + str(err), 400)
                            
            result, ret = db.add(input_data, collection="outliers")
            code = 200 if result else 400

            resp = make_response(ret, code)
                
            return resp
    except Exception, ex:
        err = "ERROR: " + traceback.format_exc()
        print err
        return make_response(err, 500)
        

@app.route('/predict', methods=["GET"])
def predict_api():
    try:
       if request.method == "GET":
            areacode = request.args.get("areacode")
            year = request.args.get("year")
            size = request.args.get("size")
            elevator = request.args.get("elevator")
            condition = request.args.get("condition")
            floor = request.args.get("floor")
            floors = request.args.get("floors")

            areacode = areacode_le.transform([areacode])[0]
            feature = np.array([areacode,size,year,elevator,condition,floor,floors])
            price = predictor.predict(feature.reshape(1,-1))
           
            resp = make_response(json.dumps({'price' : price[0]}), 200)
            resp.headers['Content-Type'] = "application/json"
            resp.headers['Access-Control-Allow-Origin'] = '*'
            return resp

    except Exception, ex:
        err = "ERROR: " + traceback.format_exc()
        print err
        return make_response(err, 500)
        
