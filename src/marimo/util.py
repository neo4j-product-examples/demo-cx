import marimo

__generated_with = "0.19.9"
app = marimo.App(width="medium")

with app.setup:
    # Initialization code that runs before all other cells

    from neo4j import GraphDatabase
    from graphdatascience import GraphDataScience
    from neo4j_viz.neo4j import from_neo4j
    from dotenv import load_dotenv
    import os
    import marimo
    import neo4j
    from neo4j_viz.gds import from_gds

    _path = "cx.env"
    load_dotenv(_path, override=True)
    NEO4J_URI = os.getenv('NEO4J_URI')
    NEO4J_USERNAME = os.getenv('NEO4J_USERNAME')
    NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')
    NEO4J_DATABASE = os.getenv('NEO4J_DATABASE')
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    NEO4J_AUTH = (
       NEO4J_USERNAME,
       NEO4J_PASSWORD,
    )
    gds = GraphDataScience(NEO4J_URI, auth=NEO4J_AUTH, database=NEO4J_DATABASE)
    gds.set_database(database=NEO4J_DATABASE)


@app.function
def project_graph(_name, _nodes, _rels):
   _G = gds.graph.project(graph_name=_name,
                          node_spec=_nodes,
                          relationship_spec=_rels)
   return _G


@app.function
def drop_graph(_name):
   gds.graph.drop(_name)

@app.function
def run_query(_query, parameters=None):
    with driver.session() as session:
        result = session.run(_query, parameters)
        records = [record.data() for record in result]
        for record in records:
            print(record)
        return records


@app.function
def visualize_query(_query, parameters=None):
    with driver.session() as session:
        result = session.run(_query, parameters)
        VG = from_neo4j(result)
        VG.color_nodes(field="caption")
        return marimo.iframe(VG.render().data)


@app.function
def visualize_projection(_g, _count):
   VG = from_gds(gds, _g, max_node_count=_count)
   VG.color_nodes(field="caption")
   return marimo.iframe(VG.render().data)


@app.function
def wcc(_G, _prop):
   gds.wcc.write(_G.graph, writeProperty=_prop)


@app.function
def run_query_df(_query, parameters=None):
    with driver.session() as session:
        result = session.run(_query, parameters)
        return result.to_df()


@app.function
def get_result(_query, parameters=None):
    with driver.session() as session:
        result = session.run(_query, parameters)
        return result


@app.function
def get_result_graph(_query, parameters=None):
    with driver.session() as session:
        result = driver.execute_query(_query, parameters, result_transformer_=neo4j.Result.graph)
        return result


if __name__ == "__main__":
    app.run()
