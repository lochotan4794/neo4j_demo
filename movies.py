#!/usr/bin/env python
import os
from json import dumps
import logging

from flask import Flask, g, Response, request
from neo4j import GraphDatabase, basic_auth

app = Flask(__name__, static_url_path='/static/')

url = os.getenv("NEO4J_URI", "bolt://localhost:7687")
username = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "123456abc")
neo4jVersion = os.getenv("NEO4J_VERSION", "")
database = os.getenv("NEO4J_DATABASE", "")

port = os.getenv("PORT", 8089)

driver = GraphDatabase.driver(url, auth=basic_auth(username, password))


def get_db():
    if not hasattr(g, 'neo4j_db'):
        if neo4jVersion.startswith("4"):
            g.neo4j_db = driver.session(database=database)
        else:
            g.neo4j_db = driver.session()
    return g.neo4j_db


@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'neo4j_db'):
        g.neo4j_db.close()


@app.route("/")
def get_index():
    return app.send_static_file('index.html')


def serialize_res_item(res_item):
    return {
        'id': res_item['id'],
        'title': res_item['name'],
        'summary': res_item['category'],
        'released': res_item['unit_price'],
        'duration': res_item['status'],
        'rated': res_item['original_unit_price'],
        'tagline': res_item['max_quality'],
        'created_time': res_item['created_time'],
        'updated_time': res_item['updated_time']

    }


def serialize_cast(cast):
    return {
        'name': cast[0],
        'job': cast[1],
        'role': cast[2]
    }


@app.route("/food/<name>")
def get_food(name):
    db = get_db()

    result = db.read_transaction(lambda tx: tx.run(
        "MATCH (n:Restaurent_item{name:$name})"
        "RETURN n.name as Name, n.name as Style", {
            "name": name}
    ).single())

    return Response(dumps({"name_food": result['Name']}),
                    mimetype="application/json")


@app.route("/food/<name>/restaurant/<restaurant>")
def get_recommendation(name, restaurant):
    db = get_db()

    result = db.read_transaction(lambda tx: tx.run(
        "MATCH (ri:Restaurent_item{name:$name}) -[:have] -> (r:Restaurent{name:$restaurent}) <- [:text] - (o:Order) -[i:include] -> (oi:Order_item) RETURN  oi.name AS Item, i AS quantity", {
            "name": name,
            "restaurent": restaurant}
    ).single())

    return Response(dumps({"name_food": result['Item'], "Quantity": result["quantity"]}),
                    mimetype="application/json")


if __name__ == '__main__':
    logging.info('Running on port %d, database is at %s', port, url)
    app.run(port=port)
