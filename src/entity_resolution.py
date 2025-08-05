import marimo

__generated_with = "0.14.16"
app = marimo.App(width="full")

with app.setup:
    # Initialization code that runs before all other cells

    # from util import run_query
    from util import visualize_query, run_query


@app.cell
def _():

    _query = 'MATCH p=()-[]-() limit 10 RETURN p'
    visualize_query(_query)

    return


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

    It models key relationships like

    - `PURCHASED` – which products a customer has purchased  
    - `ASSOC_ID, ASSOC_EMAIL, ASSOC_PHONE` – PII associated with a customer 
    - `NEXT` – relationship that captures the sequence of orders for a customer
    """
    )
    return


@app.cell
def _():
    _query = 'call db.schema.visualization()'
    visualize_query(_query)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
    ## Clean up any prior runs
    ---
    These queries will reset the data back to a "clean" state so that you can re-run the entity resolution process
    """
    )
    return


@app.cell
def _():
    _query = '\nMATCH (:Customer)-[r:SHARED_PII]->()\nDELETE r\n'
    results = run_query(_query)
    _query = '\nMATCH (n:ValidCommunity)\nREMOVE n:ValidCommunity\n'
    results = run_query(_query)
    _query = '\nMATCH (n:Outlier)\nREMOVE n:Outlier\n'
    results = run_query(_query)
    _query = '\nMATCH (c:Customer)\nREMOVE c.wccId\n'
    results = run_query(_query)
    _query = "\nCALL gds.graph.drop('similarity-projection');\n"
    try:
        results = run_query(_query)
    except Exception:
        print('Ignoring error - projection does not exist')
    _query = "\nCALL gds.graph.drop('wcc-projection');\n"
    try:
        results = run_query(_query)
    except Exception:
        print('Ignoring error - projection does not exist')
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
    ## Entity Resolution Overview
    ---
    Entity resolution is the process of identifying which digital representations of an entity refer to the same real-world entity. In this case, the entities we want to resolve are **Customers** We will use the customer demographics (Phone, Email, Address) to help us in the process. The general steps are:

    - Find cases ("outliers") where the identifying information is shared among many (>10) customers so that we can treat them as a special case
    - Use a community detection algorithm (WCC) to identify groups of customers that are sharing identifiers. We will tag communities of size > 1 for further processing (communities of size 1 w are customers that don't share identifiers).
    - Assign weights to the shared identifiers
    - Run node similarity algorithm to create similarity clusters of customers based on the communities and weighted features
    - Within the clusters, use a string similarity algorithm to compare the customer names
    - Combine (with weighting, if desired) the feature similarity and name similarity scores to create a combined score
    - Analyze the data based on the scores
    """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
    ## Flag outliers
    ---
    Identify features (phone, email, id) that are shared by 10 or more customers. This would seem to indicate some outlier/edge case that we can process differently. The query works as follows:

    - define a parameter containing a list of features (Phone, Email, Identifier) that we could consider as outliers and a value that we consider to be "many" (10, in this case)
    - For each of the features in the list, find all of the nodes with that feature and then filter those nodes to find the ones that are related to more than "many" customers
    - Add an "Outlier" label to those nodes

    Finally at the end, we run a query to show us some of the outliers
    """
    )
    return


@app.cell
def _():
    _query = '\nWITH {\n    featureParams: [\n        { label: "Phone", rel: "ASSOC_PHONE", prop: "phone" },\n        { label: "EmailAddress", rel: "ASSOC_EMAIL", prop: "emailAddress" },\n        { label: "Identifier", rel: "ASSOC_ID", prop: "govtId" }\n    ],\n    degreeCutoff: 10\n} as params\nUNWIND params.featureParams as feature\nCALL (params, feature) {\n    MATCH (n:$(feature.label))\n    WITH params, n, count { ()-[:$(feature.rel)]->(n) } as countVal\n    ORDER BY countVal DESC\n    WHERE countVal >= params.degreeCutoff\n    RETURN n\n}\nSET n:Outlier;\n'
    run_query(_query)
    _query = '\nmatch (o:Outlier)-[r]-(c) return *\n'
    visualize_query(_query)

    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
    ## Identify groups of similar customers with Graph Analytics
    ---
    The next step is to find groups of similar customers. We do this because doing pairwise comparisons of all of the customers becomes untenable as we deal with more and more customers - it's an O(n^2) problem. Breaking down the customers into groups that are have similar characteristics will let us do those comparisons against smaller sets of customers.

    How do we find groups of similar customers? One way is a technique called "community detection." Neo4j Graph Analytics is a set of data science algorithms that includes several community detection algorithms. The algorithms are already coded and optimized to run against graphs, saving you time in both coding and execution. You can use the algorithms in AuraDB Professional (by enabling the Graph Analytics plugin when creating your database) or by using the serverless Aura Graph Analytics option with AuraDB Business Critical or Virtual Dedicated Cloud. 

    One community detection algorithm provided is called "Weakly Connected Components" or "WCC" for short. To use it, you project a graph into memory that contains the nodes and relationships of interest and then run the algorithm; the algorithm computes community IDs for each node in the projection - we write that ID back to each node in the graph. We will further add a **ValidCommunity** label to each Customer that is in a community with more than one member, as those are the customers that potentially have more than one digital representation.
    """
    )
    return


@app.cell
def _():
    _query = "\nCALL gds.graph.project('wcc-projection', \n    ['Customer', 'Identifier','Phone','EmailAddress'], \n    ['ASSOC_EMAIL', 'ASSOC_PHONE','ASSOC_ID'] \n);\n"
    run_query(_query)
    _query = "\nCALL gds.wcc.write('wcc-projection', { writeProperty: 'wccId' })\nYIELD nodePropertiesWritten, componentCount;\n"
    run_query(_query)
    _query = '\nMATCH (c:Customer|Phone|EmailAddress|Identifier) \nWHERE c.wccId IS NOT NULL\nWITH c, c.wccId as wccId, CASE WHEN c:Customer THEN 1 ELSE 0 END as customerFlag\nWITH wccId, sum(customerFlag) as numberOfCustomers, collect(c) as communityNodes\nWHERE numberOfCustomers > 1\nWITH communityNodes\nUNWIND communityNodes as communityNode\nSET communityNode:ValidCommunity\n'
    run_query(_query)
    _query = '\nMATCH p=(c:Customer&ValidCommunity)-->(:(Phone|EmailAddress|Identifier)&!Outlier)<--(c2)\nRETURN p\nLIMIT 500;\n'
    visualize_query(_query)

    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
    ## Assign weights to features
    ---
    Some features are more important for entity resolution. For example, a shared customer id could be considered more important than a shared phone number when deciding if the customer records represent the same real-world customer. We will assign a weight to each relationship between a customer and its features (ID, Phone, Email) to use when we compare similarity. In our case, we weight the ID twice as strongly as the Phone or Email.
    """
    )
    return


@app.cell
def _():
    _query = '\nMATCH ()-[r:ASSOC_ID]->()\nSET r.weight = 1.0;\n'
    run_query(_query)
    _query = '\nMATCH ()-[r:ASSOC_PHONE]->()\nSET r.weight = 0.5;\n'
    run_query(_query)
    _query = '\nMATCH ()-[r:ASSOC_EMAIL]->()\nSET r.weight = 0.5;\n'
    run_query(_query)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
    ## Run Node Similarity
    ---
    The graph is now set up to do pairwise comparisons between customers in each community and assign a similarity score to each pair. We can do this quickly and efficiently using another algorithm provided by Graph Analytics: Node Similarity. We do this by projecting the graph into memory (including the community IDs and weights from the previous steps). Then, we run the node similarity algorithm and write the similarity scores back to the database by creating a **SHARED_PII** relationship between each pair of customers and include a **featureScore** property on the relationship that represents the strength of the similarity.

    The node similarity algorithm is useful because we can easily specify as many relationship types and their corresponding weights to use for the comparison. This lets us iteratively improve our entity resolution process as we experiment with different features and weights without needing to extensively change the code for each iteration.
    """
    )
    return


@app.cell
def _():
    _query = "\nCALL gds.graph.project('similarity-projection', \n    { \n        ValidCommunity: {properties: 'wccId'} \n    },\n    {\n        ASSOC_ID: { properties: 'weight' },\n        ASSOC_PHONE: { properties: 'weight' },\n        ASSOC_EMAIL: { properties: 'weight' }\n    }\n);\n"
    run_query(_query)
    _query = "\nCALL gds.nodeSimilarity.write('similarity-projection', {\n    writeRelationshipType: 'SHARED_PII',\n    relationshipWeightProperty: 'weight',\n    similarityMetric: 'COSINE',\n    useComponents: 'wccId',\n    writeProperty: 'featureScore'\n});\n"
    run_query(_query)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
    ## Spot check results
    ---
    We can now look at the results. If you want to explore these interactively, you can run these queries using **Explore** in the Aura Console - you will be able to interactively expand relationships to see what identifiers are being shared
    """
    )
    return


@app.cell
def _():
    _query = '\nMATCH p=()-[r:SHARED_PII]->() RETURN p LIMIT 100;\n'
    visualize_query(_query)

    return


@app.cell
def _():
    _query = '\nMATCH p=(c:Customer)-[r:SHARED_PII WHERE r.featureScore > 0.8]->(c2)\nWITH c, collect(p) as paths\nWHERE size(paths) <= 5\nRETURN paths\nLIMIT 50;\n'
    visualize_query(_query)

    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
    ## Compute name similarity
    ---
    Our graph now has communities of customers with weighted **SHARED_PII** relationships between pairs of customers in the community. The similarity weights are based on ID, Phone, and Email. We can further improve our entity resolution by comparing the customer names in each pair and incorporating the name similarities into our similarity scores.

    **Sorensen Dice** is a string similarity algorithm that Neo4j provides in its included APOC library of functions and procedures. We can use it to compute a pairwise similarity score for customer first and last names - in our example we will use the average of the first name and last name similarity scores as an overall name score. We can also compute an overall score by combining the feature score (frome the node similarity algorithm) and name similarity score (with weighting, if desired).
    """
    )
    return


@app.cell
def _():
    _query = '\nMATCH (c:Customer)-[r:SHARED_PII]->(c2)\nWITH r, apoc.text.sorensenDiceSimilarity(c.firstName, c2.firstName) as firstNameScore,\n    apoc.text.sorensenDiceSimilarity(c.lastName, c2.lastName) as lastNameScore\nWITH r, firstNameScore, lastNameScore, (1.0 * firstNameScore + lastNameScore) / 2 as nameScore\nSET r += {\n    firstNameScore: firstNameScore,\n    lastNameScore: lastNameScore,\n    nameScore: nameScore\n};\n'
    run_query(_query)
    _query = '\nMATCH ()-[r:SHARED_PII]->()\nSET r.combinedScore = (r.featureScore + r.nameScore) / 2;\n'
    run_query(_query)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
    ## Use results to analyze suggested resolutions
    ---
    Now we can run some queries to explore our results. You may also want to run these in the **Explore** tool of Aura Console to interactively explore the results.

    First, we can look at customers that are not a part of a community (in other words, they are likely to be "clean" - without duplicates):
    """
    )
    return


@app.cell
def _():
    _query = '\nMATCH p=(c:Customer&!ValidCommunity)\nMATCH p2=ALL SHORTEST (c)-[:ASSOC_EMAIL|ASSOC_PHONE|ASSOC_ID]->(:!Outlier)\nRETURN *\nLIMIT 100;\n'
    visualize_query(_query)

    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
    ## Highly scored matches
    ---
    Next, let's look at pairs of customers with a combined score greater than 0.8. These pairs are strong matches and suggest that the pair may represent the same customer:
    """
    )
    return


@app.cell
def _():
    _query = '\nMATCH p=(c:Customer)-[r:SHARED_PII WHERE r.combinedScore > 0.8]->(c2)\nMATCH p2=ALL SHORTEST (c)-[:ASSOC_EMAIL|ASSOC_PHONE|ASSOC_ID]->(:!Outlier)<-[:ASSOC_EMAIL|ASSOC_PHONE|ASSOC_ID]-(c2)\nRETURN *;\n'
    visualize_query(_query)

    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(
        r"""
    ## Use last name similarities to identify potential households
    ---
    Often times we want to know which of our customers live in the same household; that helps us understand each customer better. For example, if one of
    """
    )
    return


@app.cell
def _():
    _query = '\nMATCH p=(c:Customer)-[r:SHARED_PII WHERE r.combinedScore <= 0.8]->(c2)\nWITH c.wccId as wccId, count(r) as numRels, sum(r.lastNameScore) as lastNameTotal, collect({p:p,c:c,c2:c2}) as resultList\nWHERE (lastNameTotal / numRels) >= 0.8\nWITH *\nUNWIND resultList as result\nWITH result.p as p, result.c as c, result.c2 as c2\nMATCH p2=ALL SHORTEST (c)-[:ASSOC_EMAIL|ASSOC_PHONE|ASSOC_ID]->(:!Outlier)<-[:ASSOC_EMAIL|ASSOC_PHONE|ASSOC_ID]-(c2)\nRETURN *;\n'
    visualize_query(_query)

    return


@app.cell
def _():
    _query = '\nMATCH p=(c:Customer)-[r:SHARED_PII]->(c2)\nMATCH p2=ALL SHORTEST (c)-[:ASSOC_EMAIL|ASSOC_PHONE|ASSOC_ID]->(:!Outlier)<-[:ASSOC_EMAIL|ASSOC_PHONE|ASSOC_ID]-(c2)\nRETURN *\nLIMIT 500;\n'
    visualize_query(_query)

    return


@app.cell
def _():
    _query = '\nMATCH (o:Outlier)<-[:ASSOC_EMAIL|ASSOC_PHONE|ASSOC_ID]-(c:Customer)\nMATCH p2=ALL SHORTEST (c)-[:ASSOC_EMAIL|ASSOC_PHONE|ASSOC_ID]->()\nRETURN *;\n'
    visualize_query(_query)

    return


@app.cell
def _():
    import marimo as mo
    return (mo,)


if __name__ == "__main__":
    app.run()
