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


def serialize_movie(movie):
    return {
        'id': movie['id'],
        'title': movie['name'],
        'summary': movie['category'],
        'released': movie['unit_price'],
        'duration': movie['status'],
        'rated': movie['original_unit_price'],
        'tagline': movie['tagline']
    }


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


@app.route("/graph")
def get_graph():
    db = get_db()
    results = db.read_transaction(lambda tx: list(tx.run("MATCH (m:Movie)<-[:ACTED_IN]-(a:Person) "
                                                         "RETURN m.title as movie, collect(a.name) as cast "
                                                         "LIMIT $limit", {
                                                             "limit": request.args.get("limit",
                                                                                       100)})))
    nodes = []
    rels = []
    i = 0
    print(results)
    for record in results:
        nodes.append({"title": record["movie"], "label": "movie"})
        target = i
        i += 1
        for name in record['cast']:
            actor = {"title": name, "label": "actor"}
            try:
                source = nodes.index(actor)
            except ValueError:
                nodes.append(actor)
                source = i
                i += 1
            rels.append({"source": source, "target": target})
    return Response(dumps({"nodes": nodes, "links": rels}),
                    mimetype="application/json")


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


@ app.route("/movie/<title>")
def get_movie(title):
    db = get_db()
    result = db.read_transaction(lambda tx: tx.run("MATCH (movie:Movie {title:$title}) "
                                                   "OPTIONAL MATCH (movie)<-[r]-(person:Person) "
                                                   "RETURN movie.title as title,"
                                                   "COLLECT([person.name, "
                                                   "HEAD(SPLIT(TOLOWER(TYPE(r)), '_')), r.roles]) AS cast "
                                                   "LIMIT 1", {"title": title}).single())

    print(result)
    return Response(dumps({"title": result['title'],
                           "cast": [serialize_cast(member)
                                    for member in result['cast']]}),
                    mimetype="application/json")


if __name__ == '__main__':
    logging.info('Running on port %d, database is at %s', port, url)
    app.run(port=port)
