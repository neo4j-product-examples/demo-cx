import marimo

__generated_with = "0.14.16"
app = marimo.App(width="medium")

with app.setup:
    # Initialization code that runs before all other cells

    from neo4j import GraphDatabase
    from neo4j_viz.neo4j import from_neo4j
    from dotenv import load_dotenv
    import os
    import marimo

    _path = "cx.env"
    load_dotenv(_path, override=True)
    NEO4J_URI = os.getenv('NEO4J_URI')
    NEO4J_USERNAME = os.getenv('NEO4J_USERNAME')
    NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')
    NEO4J_DATABASE = os.getenv('NEO4J_DATABASE')
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))


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


if __name__ == "__main__":
    app.run()
