import marimo

__generated_with = "0.14.16"
app = marimo.App()


@app.cell
def _():
    from neo4j import GraphDatabase
    from neo4j_viz.neo4j import from_neo4j
    from dotenv import load_dotenv
    import os
    load_dotenv('cx.env', override=True)
    NEO4J_URI = os.getenv('NEO4J_URI')
    NEO4J_USERNAME = os.getenv('NEO4J_USERNAME')
    NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')
    NEO4J_DATABASE = os.getenv('NEO4J_DATABASE')
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    print('Checking the connection:')

    def run_query(query, parameters=None):
        with driver.session() as session:
            result = session.run(_query, parameters)
            records = [record.data() for record in result]
            for record in records:
                print(record)
            return records

    def run_query_v(query, parameters=None):
        with driver.session() as session:
            result = session.run(_query, parameters)
            VG = from_neo4j(result)
            return VG
    _query = 'MATCH p=()-[]-() limit 10 RETURN p'
    _vis = run_query_v(_query)
    _vis.render()
    return run_query, run_query_v


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
        ## Understanding the Data Model
        ---
        This **graph model** maps information about customers and their orders including key entities such as:

        - **Customers**
        - **Orders and Line Items**
        - **Products**
        - Customers' identifying information including **Email**, **Phone**, and **Country**

        It models key relationships like:
        - `PURCHASED` – which products a customer has purchased  
        - `ASSOC_ID, ASSOC_EMAIL, ASSOC_PHONE` – PII associated with a customer 
        - `NEXT` – relationship that captures the sequence of orders for a customer

        """
    )
    return


@app.cell
def _(run_query_v):
    _query = 'call db.schema.visualization()'
    _vis = run_query_v(_query)
    _vis.render()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
        ## Clean up any prior runs
        """
    )
    return


@app.cell
def _(run_query):
    _query = '\nMATCH (:Customer)-[r:PURCHASED]->(:Product)\nREMOVE r.totalPurchased\n'
    results = run_query(_query)
    _query = '\nMATCH (:Customer)-[r:SIMILAR_PURCHASE_TO]->()\nDELETE r\n'
    results = run_query(_query)
    _query = '\nMATCH (c:Customer)\nREMOVE c.segmentId, c.embedding\n'
    results = run_query(_query)
    _query = "\nCALL gds.graph.drop('embedding-projection')\n"
    try:
        results = run_query(_query)
    except Exception:
        print('Ignoring error - projection does not exist')
    _query = "\nCALL gds.graph.drop('cf-projection')\n"
    try:
        results = run_query(_query)
    except Exception:
        print('Ignoring error - projection does not exist')
    _query = "\nCALL gds.graph.drop('co-purchase')\n"
    try:
        results = run_query(_query)
    except Exception:
        print('Ignoring error - projection does not exist')
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""

        ## Data preparation
        ---
        Compute the total number of each product ordered and save in a **totalPurchased** property

        """
    )
    return


@app.cell
def _(run_query):
    _query = '\nMATCH (c:Customer)-[:ORDERED]->(:Order)-[:LINE_ITEM]->(li:OrderLineItem)-[:PRODUCT]->(p:Product)\nWITH c, p, sum(li.quantity) as totalPurchased\nMATCH (c)-[r:PURCHASED]->(p)\nSET r.totalPurchased = totalPurchased;\n'
    run_query(_query)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
        ## Compute Graph embeddings using Fast Random Projection
        ---
        Fast Random Projection (FastRP) is a node embedding algorithm for each node in which the embedding vector will be similar for two nodes that have similar neighborhoods. This cell creates the projection based on tho PURCHASED relationship between **Customers** and **Products** and considers how many of each product the customer purchased. The results of the FastRP algorithm will be written back to the graph as a property named **embedding** on the **Customer** nodes
        """
    )
    return


@app.cell
def _(run_query):
    _query = "\nCALL gds.graph.project('embedding-projection', ['Customer', 'Product'], {\n    PURCHASED:{\n        orientation:'UNDIRECTED',\n        properties: {\n            weight: {\n                property: 'totalPurchased', \n                defaultValue: 1.0\n            }\n        }\n    }\n})\n"
    run_query(_query)
    _query = "\nCALL gds.fastRP.mutate('embedding-projection', {\n    embeddingDimension: 256,\n    randomSeed: 7474, \n    relationshipWeightProperty: 'weight',\n    mutateProperty: 'embedding'\n})\n"
    run_query(_query)
    _query = "\nCALL gds.graph.nodeProperties.write('embedding-projection', ['embedding'], ['Customer'])\n"
    run_query(_query)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
        ## Use K-Nearest-Neighbors to create SIMILAR_PURCHASE_TO relationships
        ---
        K-Nearest-Neighbors (KNN) is an algorithm that finds the closest K number of embeddings. We will use the purchase similarity embeddings for this and use the KNN results to write a SIMILAR_PURCHASE_TO relationship between the closest K customers
        """
    )
    return


@app.cell
def _(run_query):
    _query = "\nCALL gds.graph.project('cf-projection', \n        {Customer:{properties:['embedding']}},'*')\n"
    run_query(_query)
    _query = "\nCALL gds.knn.write('cf-projection', {\n  nodeProperties:['embedding'],\n  writeRelationshipType:'SIMILAR_PURCHASE_TO',\n  writeProperty:'score',\n  sampleRate:1.0,\n  maxIterations:1000\n})\n"
    run_query(_query)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
        ## Community Detection for segmentation / product recommendations
        ---
        Leiden is an algorithm for detecting communities. We will use it to segment our customers besad on their knn similarity scores and purchase similarities. We will write a **segmentId** property to the **Customer** nodes
        """
    )
    return


@app.cell
def _(run_query):
    _query = "\nMATCH (c1:Customer)-[r:SIMILAR_PURCHASE_TO]-(c2:Customer)\nWITH gds.graph.project('co-purchase', c1, c2, { \n    relationshipProperties: { score: r.score }}, \n    {undirectedRelationshipTypes: ['*']}) AS g\nRETURN g.graphName AS graph, g.nodeCount AS nodes, g.relationshipCount AS rels\n"
    run_query(_query)
    _query = "\nCALL gds.leiden.write('co-purchase', { \n    relationshipWeightProperty: 'score', randomSeed: 7474, writeProperty: 'segmentId', concurrency:1})\nYIELD communityCount, nodePropertiesWritten\nRETURN communityCount, nodePropertiesWritten   \n"
    run_query(_query)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
        ## Show communities and their sizes
        ---
        Now that we have segmented our Customers, we can show the segments (identified with an id) and their sizes (how many customers)
        """
    )
    return


@app.cell
def _(run_query):
    _query = '\nMATCH(c:Customer) WHERE c.segmentId IS NOT NULL\nRETURN c.segmentId AS segmentId, count(c) AS numberOfCustomers ORDER BY numberOfCustomers DESC; \n'
    run_query(_query)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
        ## Visualize a community and some of its common purchases
        ---
        Now that we have segmented our Customers, we can show the segments (identified with an id) and their sizes (how many customers)
        """
    )
    return


@app.cell
def _(run_query_v):
    _query = '\nWITH {\n    communityMinSize: 10,\n    communityMaxSize: 40\n} as params\nMATCH (c:Customer) WHERE c.segmentId IS NOT NULL\nWITH params, c.segmentId AS segmentId, count(c) AS numberOfCustomers \nWHERE params.communityMinSize <= numberOfCustomers <= params.communityMaxSize\nLIMIT 1\nMATCH p=(c:Customer {segmentId: segmentId})-[:SIMILAR_PURCHASE_TO]->(c2 {segmentId: segmentId})\nWITH *\nCALL (c, c2) {\n  MATCH p2=(c:Customer)-[:PURCHASED]->()<-[:PURCHASED]-(c2)\n  RETURN p2\n  LIMIT 20\n}\nRETURN p, p2\n'
    _vis = run_query_v(_query)
    _vis.render()
    return


@app.cell
def _():
    import marimo as mo
    return (mo,)


if __name__ == "__main__":
    app.run()

