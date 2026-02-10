import marimo

__generated_with = "0.19.9"
app = marimo.App()

with app.setup:
    # Initialization code that runs before all other cells

    from util import run_query, visualize_query, run_query_df, get_result_graph, project_graph, visualize_projection, wcc, drop_graph

    from NvlWidget import NvlWidget


@app.cell
def _():
    _result = get_result_graph('MATCH p=()-[]-() limit 10 RETURN p')
    _widget = NvlWidget.from_result(_result)

    _widget
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
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
    """)
    return


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _():
    _result = get_result_graph('call db.schema.visualization')
    _widget = NvlWidget.from_result(_result)

    _widget
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Clean up any prior runs
    """)
    return


@app.cell
def _():
    _query = 'MATCH (:Customer)-[r:PURCHASED]->(:Product) REMOVE r.totalPurchased'
    results = run_query(_query)
    _query = 'MATCH (:Customer)-[r:SIMILAR_PURCHASE_TO]->() DELETE r'
    results = run_query(_query)
    _query = 'MATCH (c:Customer) REMOVE c.segmentId, c.embedding'
    results = run_query(_query)
    _query = "CALL gds.graph.drop('embedding-projection')"
    try:
        results = run_query(_query)
    except Exception:
        print('Ignoring error - projection does not exist')
    _query = "CALL gds.graph.drop('cf-projection')"
    try:
        results = run_query(_query)
    except Exception:
        print('Ignoring error - projection does not exist')
    _query = "CALL gds.graph.drop('co-purchase')"
    try:
        results = run_query(_query)
    except Exception:
        print('Ignoring error - projection does not exist')
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Data preparation
    ---
    Compute the total number of each product ordered and save in a **totalPurchased** property
    """)
    return


@app.cell
def _():
    _query = 'MATCH (c:Customer)-[:ORDERED]->(:Order)-[:LINE_ITEM]->(li:OrderLineItem)-[:PRODUCT]->(p:Product) WITH c, p, sum(li.quantity) as totalPurchased MATCH (c)-[r:PURCHASED]->(p) SET r.totalPurchased = totalPurchased;'
    run_query(_query)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Compute Graph embeddings using Fast Random Projection
    ---
    Fast Random Projection (FastRP) is a node embedding algorithm for each node in which the embedding vector will be similar for two nodes that have similar neighborhoods. This cell creates the projection based on tho PURCHASED relationship between **Customers** and **Products** and considers how many of each product the customer purchased. The results of the FastRP algorithm will be written back to the graph as a property named **embedding** on the **Customer** nodes
    """)
    return


@app.cell
def _():
    _query = "\nCALL gds.graph.project('embedding-projection', ['Customer', 'Product'], {\n    PURCHASED:{\n        orientation:'UNDIRECTED',\n        properties: {\n            weight: {\n                property: 'totalPurchased', \n                defaultValue: 1.0\n            }\n        }\n    }\n})\n"
    run_query(_query)
    _query = "\nCALL gds.fastRP.mutate('embedding-projection', {\n    embeddingDimension: 256,\n    randomSeed: 7474, \n    relationshipWeightProperty: 'weight',\n    mutateProperty: 'embedding'\n})\n"
    run_query(_query)
    _query = "\nCALL gds.graph.nodeProperties.write('embedding-projection', ['embedding'], ['Customer'])\n"
    run_query(_query)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Use K-Nearest-Neighbors to create SIMILAR_PURCHASE_TO relationships
    ---
    K-Nearest-Neighbors (KNN) is an algorithm that finds the closest K number of embeddings. We will use the purchase similarity embeddings for this and use the KNN results to write a SIMILAR_PURCHASE_TO relationship between the closest K customers
    """)
    return


@app.cell
def _():
    _query = "\nCALL gds.graph.project('cf-projection', \n        {Customer:{properties:['embedding']}},'*')\n"
    run_query(_query)
    _query = "\nCALL gds.knn.write('cf-projection', {\n  nodeProperties:['embedding'],\n  writeRelationshipType:'SIMILAR_PURCHASE_TO',\n  writeProperty:'score',\n  sampleRate:1.0,\n  maxIterations:1000\n})\n"
    run_query(_query)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Community Detection for segmentation / product recommendations
    ---
    Leiden is an algorithm for detecting communities. We will use it to segment our customers besad on their knn similarity scores and purchase similarities. We will write a **segmentId** property to the **Customer** nodes
    """)
    return


@app.cell
def _():
    _query = "\nMATCH (c1:Customer)-[r:SIMILAR_PURCHASE_TO]-(c2:Customer)\nWITH gds.graph.project('co-purchase', c1, c2, { \n    relationshipProperties: { score: r.score }}, \n    {undirectedRelationshipTypes: ['*']}) AS g\nRETURN g.graphName AS graph, g.nodeCount AS nodes, g.relationshipCount AS rels\n"
    run_query(_query)
    _query = "\nCALL gds.leiden.write('co-purchase', { \n    relationshipWeightProperty: 'score', randomSeed: 7474, writeProperty: 'segmentId', concurrency:1})\nYIELD communityCount, nodePropertiesWritten\nRETURN communityCount, nodePropertiesWritten   \n"
    run_query(_query)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Show communities and their sizes
    ---
    Now that we have segmented our Customers, we can show the segments (identified with an id) and their sizes (how many customers)
    """)
    return


@app.cell
def _():
    _query = '\nMATCH(c:Customer) WHERE c.segmentId IS NOT NULL\nRETURN c.segmentId AS segmentId, count(c) AS numberOfCustomers ORDER BY numberOfCustomers DESC; \n'
    run_query(_query)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Visualize a community and some of its common purchases
    ---
    Now that we have segmented our Customers, we can show the segments (identified with an id) and their sizes (how many customers)
    """)
    return


@app.cell
def _():
    _result = get_result_graph('''
    WITH {
    communityMinSize: 10,
    communityMaxSize: 40
    } as params
    MATCH (c:Customer) WHERE c.segmentId IS NOT NULL
    WITH params, c.segmentId AS segmentId, count(c) AS numberOfCustomers 
    WHERE params.communityMinSize <= numberOfCustomers <= params.communityMaxSize
    LIMIT 1
    MATCH p=(c:Customer {segmentId: segmentId})-[:SIMILAR_PURCHASE_TO]->(c2 {segmentId: segmentId})
    WITH *
    CALL (c, c2) {
    MATCH p2=(c:Customer)-[:PURCHASED]->()<-[:PURCHASED]-(c2)
    RETURN p2
    LIMIT 20
    }
    RETURN p, p2
    ''')

    _widget = NvlWidget.from_result(_result)
    _widget

    return


if __name__ == "__main__":
    app.run()
