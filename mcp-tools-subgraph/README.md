# Customer Graph with MCP
In this subdirectory we create a graph from a sample of the main [customer experience demo](https://neo4j.com/developer/demos/cx-demo/) and configure some MCP servers to allow agents to access and reason over the data. It focuses on a subset of the data model that describes customer product ordering behavior.

Data is loaded from an `orders.csv` file, after which graph analytics algorithms are used to create customer segments based on purchasing behavior. These segments are then labeled with titles and descriptions based on purchase patterns using an LLM workflow. We then configure MCP servers via both [MCP Toolbox](https://neo4j.com/blog/developer/ai-agents-gen-ai-toolbox/) (for a specialized query template for calculating churn risks) and [mcp-neo4j-cypher](https://github.com/neo4j-contrib/mcp-neo4j/tree/main/servers/mcp-neo4j-cypher) that allow agents to write and execute their own Cypher queries based on the graph schema and user input.

**Note that you will need an OpenAI API key to run this example**

## Steps

### 1) Aura Instance and Environment Credentials
You will want to create an empty Neo4j instance with Graph Analytics. The easiest way to do this is via an [Aura Pro instance](https://neo4j.com/product/auradb/) with the Neo4j Graph Analytics **plugin** toggled on. Make sure to:
1. Download the credentials file when prompted
2. In the `mcp-tools-subgraph` directory copy `cx.env.template` to `cx.env` and put in the Neo4j credentials
3. Also provide an OpenAI key in that `cx.env` file

### 2) Python Environment

Go ahead and create your venv however you want. `uv` works great - running the below from the main directory:
```shell
pip install uv
uv sync
```

### 3) Create the Graph & MCP Toolbox Configuration
Run the `create-sample-graph-and-tools.ipynb` notebook to populate the graph and create the [MCP Toolbox server](https://neo4j.com/blog/developer/ai-agents-gen-ai-toolbox/) configuration. You can look at the documentation inside the notebook to see the process which includes customer segmentation with Graph Analytics.

### 4) Deploy MCP Toolbox Server
You can do this locally or, if you have a GCP account, deploy remotely via Cloud Run.

For local deployment see `deploy-toolbox-local.sh`. For remote GCP see `deploy-toolbox-gcp.sh`.

Optional: Once the Toolbox MCP server is running you can test with [MCP Inspector](https://modelcontextprotocol.io/legacy/tools/inspector).

### 5) Configure for your AI Agent (Client) of Choice
You can use any [MCP client](https://modelcontextprotocol.io/clients), but here we will assume [Claude Desktop](https://claude.ai/download) for which you would use the below configuration. See [MCP Desktop instructions](https://modelcontextprotocol.io/quickstart/user#installing-the-filesystem-server) for more details on how to set this up. Other client configurations will vary, please see their associated docs.
```json
{
  "mcpServers": {
    "customer-cypher": {
      "command": "uvx",
      "args": [
        "mcp-neo4j-cypher"
      ],
      "env": {
        "NEO4J_URI":"neo4j+s://xxxxxxxx.databases.neo4j.io",
        "NEO4J_USERNAME":"neo4j",
        "NEO4J_PASSWORD": "xxxxxxxxxxxx"
      }
    },
    "customer-tools": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "https://customer-toolbox-xxxxxxxxxxxx.us-central1.run.app/mcp"
      ]
    }
  }
}
```
- `customer-cypher`: Enables the client (AI agent) to get the schema and execute its own Cypher (graph queries) against the customer graph
- `customer-tools`: Provides specific Cypher templates to the AI agent via the [MCP Toolbox server](https://neo4j.com/blog/developer/ai-agents-gen-ai-toolbox/). Think of these as expert-crafted tools. In this case we have a simple example with a query template for calculating churn risk by customer segment.
