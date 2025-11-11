import marimo

__generated_with = "0.18.0"
app = marimo.App(width="full")

with app.setup:
    from util import run_query, visualize_query, run_query_df


@app.cell
def _():
    # Test to make sure database is accessible and working 

    visualize_query('MATCH p=()-[]-() limit 10 RETURN p')
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

    It models key relationships like

    - `PURCHASED` – which products a customer has purchased
    - `ASSOC_ID, ASSOC_EMAIL, ASSOC_PHONE` – PII associated with a customer
    - `NEXT` – relationship that captures the sequence of orders for a customer
    """)
    return


@app.cell
def _():
    visualize_query('call db.schema.visualization()')
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Clean up any prior runs
    ---
    These queries will reset the data back to a "clean" state so that you can re-run the entity resolution process
    """)
    return


@app.cell
def _():

    results = run_query('''
    MATCH (:Customer)-[r:SHARED_PII]->()
    DELETE r
    ''')

    results = run_query('''
    MATCH (n:ValidCommunity)
    REMOVE n:ValidCommunity
    ''')

    results = run_query('''
    MATCH (n:Outlier)
    REMOVE n:Outlier
    ''')

    results = run_query('''
    MATCH (c:Customer)
    REMOVE c.wccId
    ''')

    try:
        results = run_query("CALL gds.graph.drop('similarity-projection');")
    except Exception:
        print('Ignoring error - projection does not exist')

    try:
        results = run_query("CALL gds.graph.drop('wcc-projection');")
    except Exception:
        print('Ignoring error - projection does not exist')

    cleanup = True
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
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
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Flag outliers
    ---
    Identify features (phone, email, id) that are shared by 10 or more customers. This would seem to indicate some outlier/edge case that we can process differently. The query works as follows:

    - define a parameter containing a list of features (Phone, Email, Identifier) that we could consider as outliers and a value that we consider to be "many" (10, in this case)
    - For each of the features in the list, find all of the nodes with that feature and then filter those nodes to find the ones that are related to more than "many" customers
    - Add an "Outlier" label to those nodes

    Finally at the end, we run a query to show us some of the outliers
    """)
    return


@app.cell
def _():
    run_query('''
    WITH {
    featureParams: [
        { label: "Phone", rel: "ASSOC_PHONE", prop: "phone" },
        { label: "EmailAddress", rel: "ASSOC_EMAIL", prop: "emailAddress" },
        { label: "Identifier", rel: "ASSOC_ID", prop: "govtId" }
        ],
        degreeCutoff: 10
        } as params
    UNWIND params.featureParams as feature
    CALL (params, feature) {
        MATCH (n:$(feature.label))
        WITH params, n, count { ()-[:$(feature.rel)]->(n) } as countVal
        ORDER BY countVal DESC
        WHERE countVal >= params.degreeCutoff
        RETURN n
    }
    SET n:Outlier;
    ''')

    visualize_query('match (o:Outlier)-[r]-(c) return *')
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Identify groups of similar customers with Graph Analytics
    ---
    The next step is to find groups of similar customers. We do this because doing pairwise comparisons of all of the customers becomes untenable as we deal with more and more customers - it's an O(n^2) problem. Breaking down the customers into groups that are have similar characteristics will let us do those comparisons against smaller sets of customers.

    How do we find groups of similar customers? One way is a technique called "community detection." Neo4j Graph Analytics is a set of data science algorithms that includes several community detection algorithms. The algorithms are already coded and optimized to run against graphs, saving you time in both coding and execution. You can use the algorithms in AuraDB Professional (by enabling the Graph Analytics plugin when creating your database) or by using the serverless Aura Graph Analytics option with AuraDB Business Critical or Virtual Dedicated Cloud.

    One community detection algorithm provided is called "Weakly Connected Components" or "WCC" for short. To use it, you project a graph into memory that contains the nodes and relationships of interest and then run the algorithm; the algorithm computes community IDs for each node in the projection - we write that ID back to each node in the graph. We will further add a **ValidCommunity** label to each Customer that is in a community with more than one member, as those are the customers that potentially have more than one digital representation.
    """)
    return


@app.cell
def _():

    run_query("""
    CALL gds.graph.project('wcc-projection', 
        ['Customer', 'Identifier', 'Phone', 'EmailAddress'], 
        ['ASSOC_EMAIL', 'ASSOC_PHONE', 'ASSOC_ID'] 
        );
    """)

    run_query("""
    CALL gds.wcc.write('wcc-projection', { writeProperty: 'wccId' })
    YIELD nodePropertiesWritten, componentCount;
    """)

    run_query('''
    MATCH (c:Customer|Phone|EmailAddress|Identifier) 
    WHERE c.wccId IS NOT NULL
    WITH c, c.wccId as wccId, CASE WHEN c:Customer THEN 1 ELSE 0 END as customerFlag
    WITH wccId, sum(customerFlag) as numberOfCustomers, collect(c) as communityNodes
        WHERE numberOfCustomers > 1
    WITH communityNodes
    UNWIND communityNodes as communityNode
    SET communityNode:ValidCommunity
    ''')

    visualize_query('''
    MATCH p=(c:Customer&ValidCommunity)-->(:(Phone|EmailAddress|Identifier)&!Outlier)<--(c2)
    RETURN p
    LIMIT 500;
    ''')
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Assign weights to features
    ---
    Some features are more important for entity resolution. For example, a shared customer id could be considered more important than a shared phone number when deciding if the customer records represent the same real-world customer. We will assign a weight to each relationship between a customer and its features (ID, Phone, Email) to use when we compare similarity. In our case, we weight the ID twice as strongly as the Phone or Email.
    """)
    return


@app.cell
def _():
    run_query('''
    MATCH ()-[r:ASSOC_ID]->()
    SET r.weight = 1.0;
    ''')

    run_query('''
    MATCH ()-[r:ASSOC_PHONE]->()
    SET r.weight = 0.5;
    ''')

    run_query('''
    MATCH ()-[r:ASSOC_EMAIL]->()
    SET r.weight = 0.5;
    ''')
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Run Node Similarity
    ---
    The graph is now set up to do pairwise comparisons between customers in each community and assign a similarity score to each pair. We can do this quickly and efficiently using another algorithm provided by Graph Analytics: Node Similarity. We do this by projecting the graph into memory (including the community IDs and weights from the previous steps). Then, we run the node similarity algorithm and write the similarity scores back to the database by creating a **SHARED_PII** relationship between each pair of customers and include a **featureScore** property on the relationship that represents the strength of the similarity.

    The node similarity algorithm is useful because we can easily specify as many relationship types and their corresponding weights to use for the comparison. This lets us iteratively improve our entity resolution process as we experiment with different features and weights without needing to extensively change the code for each iteration.
    """)
    return


@app.cell
def _():
    run_query("""
    CALL gds.graph.project('similarity-projection', 
        { 
            ValidCommunity: {properties: 'wccId'} 
        },
        {
            ASSOC_ID: { properties: 'weight' },
            ASSOC_PHONE: { properties: 'weight' },
            ASSOC_EMAIL: { properties: 'weight' }
        }
    );
    """)

    run_query("""
    CALL gds.nodeSimilarity.write('similarity-projection',
        {
            writeRelationshipType: 'SHARED_PII',
            relationshipWeightProperty: 'weight',
            similarityMetric: 'COSINE',
            useComponents: 'wccId',
            writeProperty: 'featureScore'
        });
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Spot check results
    ---
    We can now look at the results. If you want to explore these interactively, you can run these queries using **Explore** in the Aura Console - you will be able to interactively expand relationships to see what identifiers are being shared
    """)
    return


@app.cell
def _():
    visualize_query('MATCH p=()-[r:SHARED_PII]->() RETURN p LIMIT 100;')
    return


@app.cell
def _():
    visualize_query('''
    MATCH p=(c:Customer)-[r:SHARED_PII WHERE r.featureScore > 0.8]->(c2)
    WITH c, collect(p) as paths
    WHERE size(paths) <= 5
    RETURN paths\nLIMIT 50;
    ''')
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Compute name similarity
    ---
    Our graph now has communities of customers with weighted **SHARED_PII** relationships between pairs of customers in the community. The similarity weights are based on ID, Phone, and Email. We can further improve our entity resolution by comparing the customer names in each pair and incorporating the name similarities into our similarity scores.

    **Sorensen Dice** is a string similarity algorithm that Neo4j provides in its included APOC library of functions and procedures. We can use it to compute a pairwise similarity score for customer first and last names - in our example we will use the average of the first name and last name similarity scores as an overall name score. We can also compute an overall score by combining the feature score (frome the node similarity algorithm) and name similarity score (with weighting, if desired).
    """)
    return


@app.cell
def _():
    run_query('''
    MATCH (c:Customer)-[r:SHARED_PII]->(c2)
    WITH r, apoc.text.sorensenDiceSimilarity(c.firstName, c2.firstName) as firstNameScore,
        apoc.text.sorensenDiceSimilarity(c.lastName, c2.lastName) as lastNameScore
    WITH r, firstNameScore, lastNameScore, (1.0 * firstNameScore + lastNameScore) / 2 as nameScore
    SET r += {
        firstNameScore: firstNameScore,
        lastNameScore: lastNameScore,
        nameScore: nameScore
        };
    ''')

    run_query('''
    MATCH ()-[r:SHARED_PII]->()
    SET r.combinedScore = (r.featureScore + r.nameScore) / 2;
    ''')
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Use results to analyze suggested resolutions
    ---
    Now we can run some queries to explore our results. You may also want to run these in the **Explore** tool of Aura Console to interactively explore the results.

    First, we can look at customers that are not a part of a community (in other words, they are likely to be "clean" - without duplicates):
    """)
    return


@app.cell
def _():
    visualize_query('''
    MATCH p=(c:Customer&!ValidCommunity)
    MATCH p2=ALL SHORTEST (c)-[:ASSOC_EMAIL|ASSOC_PHONE|ASSOC_ID]->(:!Outlier)
    RETURN *
    LIMIT 100;
    ''')
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Highly scored matches
    ---
    Next, let's look at pairs of customers with a combined score greater than 0.8. These pairs are strong matches and suggest that the pair may represent the same customer:
    """)
    return


@app.cell
def _():
    visualize_query('''
    MATCH p=(c:Customer)-[r:SHARED_PII WHERE r.combinedScore > 0.8]->(c2)
    MATCH p2=ALL SHORTEST (c)-[:ASSOC_EMAIL|ASSOC_PHONE|ASSOC_ID]->(:!Outlier)<-[:ASSOC_EMAIL|ASSOC_PHONE|ASSOC_ID]-(c2)
    RETURN *;
    ''')
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Use last name similarities to identify potential households
    ---
    Oftentimes we want to know which of our customers live in the same household; that helps us understand each customer better. For example, if one of the members of a household buys cat food, we can infer that other household members are also cat owners
    """)
    return


@app.cell
def _():
    visualize_query('''
    MATCH p=(c:Customer)-[r:SHARED_PII WHERE r.combinedScore <= 0.8]->(c2)
    WITH c.wccId as wccId, count(r) as numRels, 
        sum(r.lastNameScore) as lastNameTotal, 
        collect({p:p,c:c,c2:c2}) as resultList
    WHERE (lastNameTotal / numRels) >= 0.8
    WITH *
    UNWIND resultList as result
    WITH result.p as p, result.c as c, result.c2 as c2
    MATCH p2=ALL SHORTEST (c)-[:ASSOC_EMAIL|ASSOC_PHONE|ASSOC_ID]->(:!Outlier)<-[:ASSOC_EMAIL|ASSOC_PHONE|ASSOC_ID]-(c2)
    RETURN *;
    ''')
    return


@app.cell
def _():
    visualize_query('''
    MATCH p=(c:Customer)-[r:SHARED_PII]->(c2)
    MATCH p2=ALL SHORTEST (c)-[:ASSOC_EMAIL|ASSOC_PHONE|ASSOC_ID]->(:!Outlier)<-[:ASSOC_EMAIL|ASSOC_PHONE|ASSOC_ID]-(c2)
    RETURN *
    LIMIT 500;
    ''')
    return


@app.cell
def _():
    visualize_query('''
    MATCH (o:Outlier)<-[:ASSOC_EMAIL|ASSOC_PHONE|ASSOC_ID]-(c:Customer)
    MATCH p2=ALL SHORTEST (c)-[:ASSOC_EMAIL|ASSOC_PHONE|ASSOC_ID]->()
    RETURN *;
    ''')
    return


@app.cell
def _():
    import marimo as mo
    return (mo,)


if __name__ == "__main__":
    app.run()
