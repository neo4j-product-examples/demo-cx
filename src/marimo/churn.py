import marimo

__generated_with = "0.20.4"
app = marimo.App()

with app.setup:
    # Initialization code that runs before all other cells

    from util import run_query, visualize_query


@app.cell
def _():
    _query = 'MATCH p=()-[]-() limit 10 RETURN p'
    visualize_query(_query)
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
    _query = 'call db.schema.visualization()'
    visualize_query(_query)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Perform some data prep after the initial load
    ---
    Create **FIRST_ORDER** and **LAST_ORDER** relationships for each customer

    Create **NEXT** relationships to track the sequence of orders for a customer

    Create **RETURN** labels on orders that were cancelled
    """)
    return


@app.cell
def _():
    _query = '\nMATCH (o:Order) WHERE o.isCancelled SET o:Return\n'
    results = run_query(_query)
    _query = '\nMATCH (c:Customer)-[:ORDERED]->(o:Order)\nWITH c, o\nORDER BY o.invoiceDate \nWITH c, collect(o) as orders\nWITH c, head(orders) as firstOrder, last(orders) as lastOrder,\n  [pair IN apoc.coll.pairs(orders) WHERE pair[1] IS NOT NULL | pair] as pairs\nMERGE (c)-[:FIRST_ORDER]->(firstOrder)\nMERGE (c)-[:LAST_ORDER]->(lastOrder)\nWITH pairs\nUNWIND pairs as pair\nWITH pair[0] as prevOrder, pair[1] as nextOrder\nMERGE (prevOrder)-[:NEXT]->(nextOrder)\n'
    results = run_query(_query)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Identify customers with a lot of returns
    ---
    This query identifies **Customers** who have placed over 10 orders and have returned "a lot of" them (over 40% of their orders)
    """)
    return


@app.cell
def _():
    _query = '\nMATCH p=(c:Customer)-[:FIRST_ORDER]->(o:Order)-[:NEXT*]->(last:Order)\nWHERE (last)<-[:LAST_ORDER]-(c)\nWITH p, tail(nodes(p)) as orders\nWITH p, orders, size([o IN orders WHERE o:Return]) as numReturns\nWHERE 100.0*numReturns / size(orders) >= 40\n  AND size(orders) >= 10\nRETURN p\nLIMIT 5;\n'
    visualize_query(_query)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Find Customers with a lot of returns in a window of orders
    ---
    This query is similar to the previous one in that it is looking for customers who are returning a significant percentage of their orders, but here we are looking for the returns in a sliding window (of 6 orders) instead of looking at all historical orders. This could be indicative of a customer that has become unhappy and is likely to churn.
    """)
    return


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _():
    _query = '\nMATCH p=(firstInChain:Order) ((:Order)-[:NEXT]->()){6,6}\nWITH firstInChain, nodes(p) as orders\nWITH firstInChain, last(orders) as lastInChain, \n  orders, size([o IN orders WHERE o:Return]) as numReturns\nWHERE (100.0*numReturns / size(orders)) >= 50\nWITH lastInChain,\n  CASE WHEN exists { (:Customer)-[:FIRST_ORDER]->(firstInChain) } \n    THEN firstInChain\n    ELSE head([(first:Order)-[:NEXT*]->(firstInChain) WHERE (:Customer)-[:FIRST_ORDER]->(first) | first])\n  END as firstOrder\nMATCH p=(c:Customer)-[:FIRST_ORDER]->(firstOrder:Order) \n  ((:Order)-[:NEXT]->())* \n  (lastInChain:Order)\nWITH c, collect(p) as paths\nLIMIT 5\nRETURN paths;\n'
    visualize_query(_query)
    return


if __name__ == "__main__":
    app.run()
